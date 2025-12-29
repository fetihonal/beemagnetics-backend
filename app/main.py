from flask import Blueprint, jsonify, request
import matlab.engine
import os
import threading
import uuid
import logging
from datetime import datetime

# Logging yapılandırması
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Konsola renkli çıktı için yardımcı fonksiyon
def debug_print(title, data, color="blue"):
    """Debug bilgisi yazdır"""
    colors = {
        "blue": "\033[94m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "reset": "\033[0m"
    }
    c = colors.get(color, colors["blue"])
    r = colors["reset"]

    print(f"\n{c}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{r}")
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"  {key}: {value}")
    elif isinstance(data, list):
        for item in data:
            print(f"  - {item}")
    else:
        print(f"  {data}")
    print(f"{c}{'='*60}{r}\n")

main = Blueprint('main', __name__)
results_cache = {}
cache_lock = threading.Lock()
main_results = {}

@main.route('/optimizations', methods=['POST'])
def optimizations():
    try:
        logger.info("=" * 60)
        logger.info("YENİ OPTİMİZASYON İSTEĞİ BAŞLADI")
        logger.info("=" * 60)

        data = request.get_json()
        if data is None:
            logger.error("JSON verisi alınamadı!")
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        # Frontend'den gelen tüm veriyi logla
        debug_print("FRONTEND'DEN GELEN VERİ", data, "cyan")

        none_keys = check_none_values(data)
        if none_keys:
            debug_print("NONE OLAN ANAHTARLAR (DİKKAT!)", none_keys, "yellow")

        eng = matlab.engine.start_matlab()


        matlab_folder_path = os.path.join(os.path.dirname(__file__), 'matlab')
        eng.cd(matlab_folder_path)


        def replace_none(value, default=0):
            return value if value is not None else default

        Fixed_LPFC_Option = float(replace_none(data.get("mode2", 1)))
        L_Fixed_by_User = float(replace_none(data.get("fixedValue2", 10))) / 1000000
        L_Min_Fixed_by_User = float(replace_none(data.get("min2", 0))) / 1000000
        L_Max_Fixed_by_User = float(replace_none(data.get("max2", 0))) / 1000000
        Fixed_FSW_Option = float(replace_none(data.get("mode1", 1)))
        fsw_Min_Fixed_by_User = float(replace_none(data.get("min1", 0))) * 1000
        fsw_Max_Fixed_by_User = float(replace_none(data.get("max1", 0))) * 1000
        fsw_Fixed_by_User = float(replace_none(data.get("fixedValue1", 50))) * 1000

        P_out = float(replace_none(data.get("outPow", 0)))
        V_out = float(replace_none(data.get("outVol", 0)))
        V_in = float(replace_none(data.get("vin", 0)))
        f_in = float(replace_none(data.get("f_in", 0)))
        W_Volume = float(replace_none(data.get("volume", 0))) / 100
        W_Cost = float(replace_none(data.get("cost", 0))) / 100
        W_Efficiency = float(replace_none(data.get("efficiency", 0))) / 100
        FETs_in_Parallel_Min = float(replace_none(data.get("fetsInParallelMin", 0)))
        FETs_in_Parallel_Max = float(replace_none(data.get("fetsInParallelMax", 0)))
        FETs_in_Series = float(replace_none(data.get("maxFetsInSeries", 0)))
        # =====================================================
        # SEÇİLEN PARÇA LİSTELERİ
        # =====================================================
        Checked_FET_List = [str(fet) for fet in (data.get("selectedFets", ["BSC034N10LS5"]))]
        Checked_PFC_Cores_List = [str(lpfc) for lpfc in data.get("selectedLpfc", ["ICERGICORE1"])]
        Checked_Heatsink_pri_List = [str(heatsink) for heatsink in data.get("selectedHeatsinks", ["UB306B"])]
        Checked_CM_Chokes_List = [str(cmc) for cmc in data.get("selectedCmc", ["Choke41005F"])]
        Checked_Capacitors_List = [str(bus_cap) for bus_cap in data.get("selectedBusCaps", ["A477LBA450M2EH"])]

        # Seçilen parçaları logla
        debug_print("SEÇİLEN FET'LER", Checked_FET_List, "green")
        debug_print("SEÇİLEN PFC CORE'LAR", Checked_PFC_Cores_List, "green")
        debug_print("SEÇİLEN HEATSINK'LER", Checked_Heatsink_pri_List, "green")
        debug_print("SEÇİLEN CM CHOKE'LAR", Checked_CM_Chokes_List, "green")
        debug_print("SEÇİLEN KAPASITÖRLER", Checked_Capacitors_List, "green")

        MultiPhase_Min = float(data.get("multiPhaseMin", 1))
        MultiPhase_Max = float(data.get("multiPhaseMax", 1))
        MultiLevel_Min = float(data.get("multiLevelMin", 1))
        MultiLevel_Max = float(data.get("multiLevelMax", 1))
        Tamb_input = float(replace_none(data.get("Tamb_input", 0)))
        FET_Top_input = float(replace_none(data.get("tOperating", 110)))
        FET_Os_Fixed = float(replace_none(data.get("overshootValue", 10)))
        FET_Rgate_Fixed = float(replace_none(data.get("gateResistanceValue", 5)))
        PFC_Core_Jmax_Fixed = float(replace_none(data.get("JmaxValue", 4.5)))
        PFC_Core_dT_Fixed = float(replace_none(data.get("deltaTValue", 40)))
        PFC_Core_Height_Fixed = float(replace_none(data.get("coreHeightValue", 45)))
        MaxOs_Custom_Checked = float(replace_none(data.get("selectedOption", 1)))

        # =====================================================
        # "SELECT ALL BY DEFAULT" PARAMETRELER - KRİTİK!
        # 0 = Sadece seçilen parçaları kullan
        # 1 = Tüm parçaları kullan (seçimleri görmezden gel)
        # 2 = Belirsiz (muhtemelen filtreleme modu)
        # =====================================================
        Select_All_Fets_by_Default = float(replace_none(data.get("AllSelectedFets", 0)))
        Select_All_PFCCores_by_Default = float(replace_none(data.get("Select_All_PFCCores_by_Default", 0)))
        Select_All_Heatsinks_by_Default = float(replace_none(data.get("selectedAllHeatsinksByDefault", 0)))  # VARSAYILAN DEĞİŞTİRİLDİ: 1 -> 0
        Select_All_CMChokes_by_Default = float(replace_none(data.get("Select_All_CMChokes_by_Default", 0)))  # VARSAYILAN DEĞİŞTİRİLDİ: 2 -> 0
        Select_All_Caps_by_Default = float(replace_none(data.get("Select_All_Buscaps_by_Default", 0)))       # VARSAYILAN DEĞİŞTİRİLDİ: 2 -> 0

        # Select All parametrelerini logla
        select_all_params = {
            "Select_All_Fets_by_Default": Select_All_Fets_by_Default,
            "Select_All_PFCCores_by_Default": Select_All_PFCCores_by_Default,
            "Select_All_Heatsinks_by_Default": Select_All_Heatsinks_by_Default,
            "Select_All_CMChokes_by_Default": Select_All_CMChokes_by_Default,
            "Select_All_Caps_by_Default": Select_All_Caps_by_Default,
        }
        debug_print("SELECT ALL BY DEFAULT PARAMETRELERİ (0=Seçilenler, 1=Hepsi)", select_all_params, "magenta")

        # Uyarı: Eğer "Select All" aktifse, seçilen parçalar görmezden gelinecek!
        if Select_All_Fets_by_Default == 1:
            logger.warning("⚠️ DİKKAT: Select_All_Fets_by_Default=1, seçilen FET'ler görmezden gelinecek!")
        if Select_All_PFCCores_by_Default == 1:
            logger.warning("⚠️ DİKKAT: Select_All_PFCCores_by_Default=1, seçilen PFC Core'lar görmezden gelinecek!")
        if Select_All_Heatsinks_by_Default == 1:
            logger.warning("⚠️ DİKKAT: Select_All_Heatsinks_by_Default=1, seçilen Heatsink'ler görmezden gelinecek!")
        if Select_All_CMChokes_by_Default == 1:
            logger.warning("⚠️ DİKKAT: Select_All_CMChokes_by_Default=1, seçilen CM Choke'lar görmezden gelinecek!")
        if Select_All_Caps_by_Default == 1:
            logger.warning("⚠️ DİKKAT: Select_All_Caps_by_Default=1, seçilen Kapasitörler görmezden gelinecek!")

        PlotPFCCore = float(replace_none(data.get("plotPfcCoreViews", 0)))
        PlotEMICore = float(replace_none(data.get("plotEmiCoreViews", 0)))
        WebMode = float(replace_none(data.get("webMode", 1)))
        fsw_step = float(replace_none(data.get("step1", 0))) * 1000
        lpfc_step = float(replace_none(data.get("step2", 0))) / 1000000
        Custom_FETs_Created = float(replace_none(data.get("Custom_FETs_Created", 0)))
        
                
        nosolution = [0, 0] 
        DMC_DM_Noise = [0, 0]
        DMC_DM_L = [0, 0]
        DMC_DM_C = [0, 0]
        CMC_CM_Noise = [0, 0]
        CMC_CM_L = [0, 0]
        CMC_CM_L_Desired = [0, 0]
        CMC_CM_C = [0, 0]
        EMI_Filter_Level = [0, 0]
        EMI_Filter_Volume = [0, 0]
        EMI_Filter_Volume_Choke = [0, 0]
        EMI_Filter_Volume_Cap = [0, 0]
        fsw_decided = [0, 0]
        L_decided = [0, 0]
        ConductionModeDecided = [0, 0]
        CMC_Name = [0, 0]
        CMC_Volume = [0, 0]
        CMC_Loss = [0, 0]
        CMC_Mu = [0, 0]
        CMC_AWG = [0, 0]
        CMC_Turns_Each = [0, 0]
        CMC_Turns = [0, 0]

        LPFC_Name = [0, 0]
        LPFC_Volume = [0, 0]
        LPFC_Stacks = [0, 0]
        LPFC_AWG = [0, 0]
        LPFC_Layers = [0, 0]
        LPFC_Turns = [0, 0]
        LPFC_Loss_Core = [0, 0]
        LPFC_Loss_Copper = [0, 0]
        LPFC_Loss = [0, 0]
        LFFET_Loss = [0, 0]
        HEATSINK_Cost = [0, 0]
        HEATSINK_Volume = [0, 0]
        BUSCAP_Name = [0, 0]
        BUSCAP_Value_Each = [0, 0]
        BUSCAP_Number_in_Parallel = [0, 0]
        BUSCAP_Value = [0, 0]
        BUSCAP_Volume = [0, 0]
        BUSCAP_Loss = [0, 0]
        HFFET_Loss_Cond = [0, 0]
        HFFET_Loss_Qoss = [0, 0]
        HFFET_Loss_Qrr = [0, 0]
        HFFET_Loss_IV = [0, 0]
        HFFET_Loss_DT = [0, 0]
        HFFET_Loss_OFF = [0, 0]
        HFFET_Loss_Gate = [0, 0]
        HFFET_Loss_SW = [0, 0]
        HFFET_Loss = [0, 0]
        HFFET_Cost = [0, 0]
        HFFET_in_Series = [0, 0]
        HFFET_in_Parallel = [0, 0]
        HFFET_Number_in_Total = [0, 0]
        R_Efficiency = [0, 0]
        R_Volume = [0, 0]
        R_Cost = [0, 0]
        HFFET_Name = [0, 0]
        HEATSINK_Name = [0, 0]
        LFFET_Name = [0, 0]
        t_ripple_plot = [0, 0]
        Real_Current_Ripple_Waveform = [0, 0]
        LF_CM_Noise_f = [0, 0]
        LF_CM_Noise_Plot = [0, 0]
        DM_Noise_f = [0, 0]
        DM_Noise_Plot = [0, 0]
        Real_Input_Current_Waveform = [0, 0]

        FET_Achievable_dvdt = [0, 0]
        FET_Achievable_dvdt_per_fet = [0, 0]
        FET_RGate_Result = [0, 0]

        R_Power_Density = [0, 0]

        LPFC_Core_Price = [0, 0]
        LPFC_Wire_Price = [0, 0]
        LPFC_Labour_Price = [0, 0]
        BUSCAP_Price = [0, 0]
        CM_Core_Price = [0, 0]
        CM_Wire_Price = [0, 0]
        CM_Labour_Price = [0, 0]

        LPFC_Core_Temperature_Rise = [0, 0]
        CM_Choke_Temperature_Rise = [0, 0]


        # =====================================================
        # MATLAB'A GÖNDERİLECEK TÜM PARAMETRELER
        # =====================================================
        matlab_params = {
            "Fixed_LPFC_Option": Fixed_LPFC_Option,
            "L_Fixed_by_User": L_Fixed_by_User,
            "L_Min_Fixed_by_User": L_Min_Fixed_by_User,
            "L_Max_Fixed_by_User": L_Max_Fixed_by_User,
            "Fixed_FSW_Option": Fixed_FSW_Option,
            "fsw_Min_Fixed_by_User": fsw_Min_Fixed_by_User,
            "fsw_Max_Fixed_by_User": fsw_Max_Fixed_by_User,
            "fsw_Fixed_by_User": fsw_Fixed_by_User,
            "P_out": P_out,
            "V_out": V_out,
            "V_in": V_in,
            "f_in": f_in,
            "W_Volume": W_Volume,
            "W_Cost": W_Cost,
            "W_Efficiency": W_Efficiency,
            "FETs_in_Parallel_Min": FETs_in_Parallel_Min,
            "FETs_in_Parallel_Max": FETs_in_Parallel_Max,
            "FETs_in_Series": FETs_in_Series,
            "Checked_FET_List": Checked_FET_List,
            "Checked_PFC_Cores_List": Checked_PFC_Cores_List,
            "Checked_Heatsink_pri_List": Checked_Heatsink_pri_List,
            "Checked_CM_Chokes_List": Checked_CM_Chokes_List,
            "Checked_Capacitors_List": Checked_Capacitors_List,
            "MultiPhase_Min": MultiPhase_Min,
            "MultiPhase_Max": MultiPhase_Max,
            "MultiLevel_Min": MultiLevel_Min,
            "MultiLevel_Max": MultiLevel_Max,
            "Tamb_input": Tamb_input,
            "FET_Top_input": FET_Top_input,
            "FET_Os_Fixed": FET_Os_Fixed,
            "FET_Rgate_Fixed": FET_Rgate_Fixed,
            "PFC_Core_Jmax_Fixed": PFC_Core_Jmax_Fixed,
            "PFC_Core_dT_Fixed": PFC_Core_dT_Fixed,
            "PFC_Core_Height_Fixed": PFC_Core_Height_Fixed,
            "MaxOs_Custom_Checked": MaxOs_Custom_Checked,
            "Select_All_Fets_by_Default": Select_All_Fets_by_Default,
            "Select_All_PFCCores_by_Default": Select_All_PFCCores_by_Default,
            "Select_All_Heatsinks_by_Default": Select_All_Heatsinks_by_Default,
            "Select_All_CMChokes_by_Default": Select_All_CMChokes_by_Default,
            "Select_All_Caps_by_Default": Select_All_Caps_by_Default,
        }
        debug_print("MATLAB'A GÖNDERİLEN PARAMETRELER", matlab_params, "blue")

        logger.info("MATLAB Organiser_Function çağrılıyor...")

        result = eng.Organiser_Function(
            Fixed_LPFC_Option, L_Fixed_by_User, L_Min_Fixed_by_User, L_Max_Fixed_by_User,
            Fixed_FSW_Option, fsw_Min_Fixed_by_User, fsw_Max_Fixed_by_User, fsw_Fixed_by_User,
            P_out, V_out, V_in, f_in, W_Volume, W_Cost, W_Efficiency, FETs_in_Parallel_Min,
            FETs_in_Parallel_Max, FETs_in_Series, Checked_FET_List, Checked_PFC_Cores_List,
            Checked_Heatsink_pri_List, Checked_CM_Chokes_List, Checked_Capacitors_List, MultiPhase_Min,
            MultiPhase_Max, MultiLevel_Min, MultiLevel_Max, Tamb_input, FET_Top_input, FET_Os_Fixed,
            FET_Rgate_Fixed, PFC_Core_Jmax_Fixed, PFC_Core_dT_Fixed, PFC_Core_Height_Fixed,
            MaxOs_Custom_Checked, Select_All_Fets_by_Default, Select_All_PFCCores_by_Default,
            Select_All_Heatsinks_by_Default, Select_All_CMChokes_by_Default, Select_All_Caps_by_Default,
            PlotPFCCore, PlotEMICore, WebMode, fsw_step, lpfc_step, Custom_FETs_Created,
            nargout=1
        )

        logger.info("MATLAB Organiser_Function tamamlandı!")
        for i in range(2):
            nosolution[i] = result["combinedResult"]["nosolution"][0][i]



            DMC_DM_Noise[i] = result["combinedResult"]["DMC_DM_Noise"][0][i]


            DMC_DM_L[i] = result["combinedResult"]["DMC_DM_L"][0][i]

            DMC_DM_C[i] = result["combinedResult"]["DMC_DM_C"][0][i]


            CMC_CM_Noise[i] = result["combinedResult"]["CMC_CM_Noise"][0][i]
            CMC_CM_L[i] = result["combinedResult"]["CMC_CM_L"][0][i]
            CMC_CM_L_Desired[i] = result["combinedResult"]["CMC_CM_L_Desired"][0][i]
            CMC_CM_C[i] = result["combinedResult"]["CMC_CM_C"][0][i]
            EMI_Filter_Level[i] = result["combinedResult"]["EMI_Filter_Level"][0][i]
            EMI_Filter_Volume[i] = result["combinedResult"]["EMI_Filter_Volume"][0][i]
            EMI_Filter_Volume_Choke[i] = result["combinedResult"][
                "EMI_Filter_Volume_Choke"
            ][0][i]
            EMI_Filter_Volume_Cap[i] = result["combinedResult"]["EMI_Filter_Volume_Cap"][0][i]
            fsw_decided[i] = result["combinedResult"]["fsw_decided"][0][i]
            L_decided[i] = result["combinedResult"]["L_decided"][0][i]
            ConductionModeDecided[i] = result["combinedResult"]["ConductionModeDecided"][0][i]
            CMC_Name[i] = result["combinedResult"]["CMC_Name"][i]
            CMC_Volume[i] = result["combinedResult"]["CMC_Volume"][0][i]
            CMC_Loss[i] = result["combinedResult"]["CMC_Loss"][0][i]
            CMC_Mu[i] = result["combinedResult"]["CMC_Mu"][0][i]
            CMC_AWG[i] = result["combinedResult"]["CMC_AWG"][0][i]
            CMC_Turns_Each[i] = result["combinedResult"]["CMC_Turns_Each"][0][i]
            CMC_Turns[i] = result["combinedResult"]["CMC_Turns"][0][i]
            LPFC_Name[i] = result["combinedResult"]["LPFC_Name"][i]
            LPFC_Volume[i] = result["combinedResult"]["LPFC_Volume"][0][i]
            LPFC_Stacks[i] = result["combinedResult"]["LPFC_Stacks"][0][i]
            LPFC_AWG[i] = result["combinedResult"]["LPFC_AWG"][0][i]
            LPFC_Layers[i] = result["combinedResult"]["LPFC_Layers"][0][i]
            LPFC_Turns[i] = result["combinedResult"]["LPFC_Turns"][0][i]
            LPFC_Loss_Core[i] = result["combinedResult"]["LPFC_Loss_Core"][0][i]
            LPFC_Loss_Copper[i] = result["combinedResult"]["LPFC_Loss_Copper"][0][i]
            LPFC_Loss[i] = result["combinedResult"]["LPFC_Loss"][0][i]
            LFFET_Loss[i] = result["combinedResult"]["LFFET_Loss"][0][i]
            HEATSINK_Cost[i] = result["combinedResult"]["HEATSINK_Cost"][0][i]
            HEATSINK_Volume[i] = result["combinedResult"]["HEATSINK_Volume"][0][i]
            BUSCAP_Name[i] = result["combinedResult"]["BUSCAP_Name"][i]
            BUSCAP_Value_Each[i] = result["combinedResult"]["BUSCAP_Value_Each"][0][i]
            BUSCAP_Number_in_Parallel[i] = result["combinedResult"][
                "BUSCAP_Number_in_Parallel"
            ][0][i]
            BUSCAP_Value[i] = result["combinedResult"]["BUSCAP_Value"][0][i]
            BUSCAP_Volume[i] = result["combinedResult"]["BUSCAP_Volume"][0][i]
            BUSCAP_Loss[i] = result["combinedResult"]["BUSCAP_Loss"][0][i]
            HFFET_Loss_Cond[i] = result["combinedResult"]["HFFET_Loss_Cond"][0][i]
            HFFET_Loss_Qoss[i] = result["combinedResult"]["HFFET_Loss_Qoss"][0][i]
            HFFET_Loss_Qrr[i] = result["combinedResult"]["HFFET_Loss_Qrr"][0][i]
            HFFET_Loss_IV[i] = result["combinedResult"]["HFFET_Loss_IV"][0][i]
            HFFET_Loss_DT[i] = result["combinedResult"]["HFFET_Loss_DT"][0][i]
            HFFET_Loss_OFF[i] = result["combinedResult"]["HFFET_Loss_OFF"][0][i]
            HFFET_Loss_Gate[i] = result["combinedResult"]["HFFET_Loss_Gate"][0][i]
            HFFET_Loss_SW[i] = result["combinedResult"]["HFFET_Loss_SW"][0][i]
            HFFET_Loss[i] = result["combinedResult"]["HFFET_Loss"][0][i]
            HFFET_Cost[i] = result["combinedResult"]["HFFET_Cost"][0][i]
            HFFET_in_Series[i] = result["combinedResult"]["HFFET_in_Series"][0][i]
            HFFET_in_Parallel[i] = result["combinedResult"]["HFFET_in_Parallel"][0][i]
            HFFET_Number_in_Total[i] = result["combinedResult"]["HFFET_Number_in_Total"][0][
                i
            ]
            R_Efficiency[i] = result["combinedResult"]["R_Efficiency"][0][i]
            R_Volume[i] = result["combinedResult"]["R_Volume"][0][i]
            R_Cost[i] = result["combinedResult"]["R_Cost"][0][i]
            HFFET_Name[i] = result["combinedResult"]["HFFET_Name"][i]
            HEATSINK_Name[i] = result["combinedResult"]["HEATSINK_Name"][i]
            LFFET_Name[i] = result["combinedResult"]["LFFET_Name"][i]
            t_ripple_plot[i] = [
                float(x) for x in result["combinedResult"]["t_ripple_plot"][i]
            ]
            Real_Current_Ripple_Waveform[i] = [
                float(x)
                for x in result["combinedResult"]["Real_Current_Ripple_Waveform"][i]
            ]
            LF_CM_Noise_f[i] = [
                float(x) for x in result["combinedResult"]["LF_CM_Noise_f"][i]
            ]
            LF_CM_Noise_Plot[i] = [
                float(x) for x in result["combinedResult"]["LF_CM_Noise_Plot"][i]
            ]
            DM_Noise_f[i] = [float(x) for x in result["combinedResult"]["DM_Noise_f"][i]]
            DM_Noise_Plot[i] = [
                float(x) for x in result["combinedResult"]["DM_Noise_Plot"][i]
            ]
            Real_Input_Current_Waveform[i] = [
                float(x) for x in result["combinedResult"]["Real_Input_Current_Waveform"][i]
            ]

            FET_Achievable_dvdt[i] = result["combinedResult"]["FET_Achievable_dvdt"][0][i]
            FET_Achievable_dvdt_per_fet[i] = result["combinedResult"][
                "FET_Achievable_dvdt_per_fet"
            ][0][i]
            FET_RGate_Result[i] = result["combinedResult"]["FET_RGate_Result"][0][i]

            R_Power_Density[i] = result["combinedResult"]["R_Power_Density"][0][i]

            LPFC_Core_Price[i] = result["combinedResult"]["LPFC_Core_Price"][0][i]
            LPFC_Wire_Price[i] = result["combinedResult"]["LPFC_Wire_Price"][0][i]
            LPFC_Labour_Price[i] = result["combinedResult"]["LPFC_Labour_Price"][0][i]
            BUSCAP_Price[i] = result["combinedResult"]["BUSCAP_Price"][0][i]
            CM_Core_Price[i] = result["combinedResult"]["CM_Core_Price"][0][i]
            CM_Wire_Price[i] = result["combinedResult"]["CM_Wire_Price"][0][i]
            CM_Labour_Price[i] = result["combinedResult"]["CM_Labour_Price"][0][i]

            LPFC_Core_Temperature_Rise[i] = result["combinedResult"][
                "LPFC_Core_Temperature_Rise"
            ][0][i]
            CM_Choke_Temperature_Rise[i] = result["combinedResult"][
                "CM_Choke_Temperature_Rise"
            ][0][i]

        # =====================================================
        # MATLAB'DAN DÖNEN SONUÇLARI LOGLA
        # =====================================================
        matlab_results = {
            "nosolution": nosolution,
            "HFFET_Name": HFFET_Name,
            "LFFET_Name": LFFET_Name,
            "LPFC_Name": LPFC_Name,
            "CMC_Name": CMC_Name,
            "BUSCAP_Name": BUSCAP_Name,
            "HEATSINK_Name": HEATSINK_Name,
            "R_Efficiency": R_Efficiency,
            "R_Volume": R_Volume,
            "R_Cost": R_Cost,
            "fsw_decided": fsw_decided,
            "L_decided": L_decided,
        }
        debug_print("MATLAB'DAN DÖNEN SONUÇLAR (Seçilen Parçalar)", matlab_results, "green")

        # Uygun parça bulunamadı kontrolü
        for i in range(2):
            if nosolution[i] == 1:
                logger.warning(f"⚠️ SONUÇ {i}: ÇÖZÜM BULUNAMADI (nosolution=1)")

            # Parça isimlerini kontrol et
            if not HFFET_Name[i] or HFFET_Name[i] == 0:
                logger.warning(f"⚠️ SONUÇ {i}: HFFET_Name boş veya 0!")
            if not LFFET_Name[i] or LFFET_Name[i] == 0:
                logger.warning(f"⚠️ SONUÇ {i}: LFFET_Name boş veya 0!")
            if not LPFC_Name[i] or LPFC_Name[i] == 0:
                logger.warning(f"⚠️ SONUÇ {i}: LPFC_Name boş veya 0!")
            if not CMC_Name[i] or CMC_Name[i] == 0:
                logger.warning(f"⚠️ SONUÇ {i}: CMC_Name boş veya 0!")
            if not BUSCAP_Name[i] or BUSCAP_Name[i] == 0:
                logger.warning(f"⚠️ SONUÇ {i}: BUSCAP_Name boş veya 0!")
            if not HEATSINK_Name[i] or HEATSINK_Name[i] == 0:
                logger.warning(f"⚠️ SONUÇ {i}: HEATSINK_Name boş veya 0!")

        logger.info("Sonuçlar cache'e kaydediliyor...")

        main_results["results"] = {
        "nosolution_res0": nosolution[0],
        "fsw_decided_res0": fsw_decided[0],
        "L_decided_res0": L_decided[0],
        "ConductionModeDecided_res0": ConductionModeDecided[0],
        "CMC_Name_res0": CMC_Name[0],
        "LPFC_Name_res0": LPFC_Name[0],
        "BUSCAP_Name_res0": BUSCAP_Name[0],
        "R_Efficiency_res0": R_Efficiency[0],
        "R_Volume_res0": R_Volume[0],
        "R_Cost_res0": R_Cost[0],
        "HFFET_Name_res0": HFFET_Name[0],
        "HEATSINK_Name_res0": HEATSINK_Name[0],
        "LFFET_Name_res0": LFFET_Name[0],
        "HFFET_in_Series_res0": HFFET_in_Series[0],
        "HFFET_in_Parallel_res0": HFFET_in_Parallel[0],
        "HFFET_Number_in_Total_res0": HFFET_Number_in_Total[0],
        "R_Power_Density_res0": R_Power_Density[0],
        "LPFC_Core_Price_res0": LPFC_Core_Price[0],
        "LPFC_Wire_Price_res0": LPFC_Wire_Price[0],
        "LPFC_Labour_Price_res0": LPFC_Labour_Price[0],
        "BUSCAP_Price_res0": BUSCAP_Price[0],
        "CM_Core_Price_res0": CM_Core_Price[0],
        "CM_Wire_Price_res0": CM_Wire_Price[0],
        "CM_Labour_Price_res0": CM_Labour_Price[0],
        "HFFET_Cost_res0": HFFET_Cost[0],
        "HEATSINK_Cost_res0": HEATSINK_Cost[0],
        "CMC_Volume_res0": CMC_Volume[0],
        "EMI_Filter_Volume_res0": EMI_Filter_Volume[0],
        "HEATSINK_Volume_res0": HEATSINK_Volume[0],
        "LPFC_Volume_res0": LPFC_Volume[0],
        "BUSCAP_Volume_res0": BUSCAP_Volume[0],
        "LPFC_Stacks_res0": LPFC_Stacks[0],
        "LPFC_Turns_res0": LPFC_Turns[0],
        "LPFC_Loss_res0": LPFC_Loss[0],
        "LPFC_Core_Price_res0": LPFC_Core_Price[0],
        "LPFC_Wire_Price_res0": LPFC_Wire_Price[0],
        "LPFC_Labour_Price_res0": LPFC_Labour_Price[0],
        "LPFC_Loss_res0": LPFC_Loss[0],
        "LPFC_Volume_res0": LPFC_Volume[0],
        "CMC_CM_L_res0": CMC_CM_L[0],
        "CMC_Volume_res0": CMC_Volume[0],
        "CMC_Loss_res0": CMC_Loss[0],
        "CMC_Turns_res0": CMC_Turns[0],
        "CM_Choke_Temperature_Rise_res0": CM_Choke_Temperature_Rise[0],
        "HFFET_Loss_res0": HFFET_Loss[0],
        "LFFET_Loss_res0": LFFET_Loss[0],
        "BUSCAP_Loss_res0": BUSCAP_Loss[0],
        "HFFET_Loss_Cond_res0": HFFET_Loss_Cond[0],
        "HFFET_Loss_SW_res0": HFFET_Loss_SW[0],
        "FET_Achievable_dvdt_res0": FET_Achievable_dvdt[0],
        "BUSCAP_Value_Each_res0": BUSCAP_Value_Each[0],
        "BUSCAP_Number_in_Parallel_res0": BUSCAP_Number_in_Parallel[0],
        "BUSCAP_Value_res0": BUSCAP_Value[0],
        "nosolution_res1": nosolution[1],
        "fsw_decided_res1": fsw_decided[1],
        "L_decided_res1": L_decided[1],
        "ConductionModeDecided_res1": ConductionModeDecided[1],
        "CMC_Name_res1": CMC_Name[1],
        "LPFC_Name_res1": LPFC_Name[1],
        "BUSCAP_Name_res1": BUSCAP_Name[1],
        "R_Efficiency_res1": R_Efficiency[1],
        "R_Volume_res1": R_Volume[1],
        "R_Cost_res1": R_Cost[1],
        "HFFET_Name_res1": HFFET_Name[1],
        "HEATSINK_Name_res1": HEATSINK_Name[1],
        "LFFET_Name_res1": LFFET_Name[1],
        "HFFET_in_Series_res1": HFFET_in_Series[1],
        "HFFET_in_Parallel_res1": HFFET_in_Parallel[1],
        "HFFET_Number_in_Total_res1": HFFET_Number_in_Total[1],
        "R_Power_Density_res1": R_Power_Density[1],
        "LPFC_Core_Price_res1": LPFC_Core_Price[1],
        "LPFC_Wire_Price_res1": LPFC_Wire_Price[1],
        "LPFC_Labour_Price_res1": LPFC_Labour_Price[1],
        "BUSCAP_Price_res1": BUSCAP_Price[1],
        "CM_Core_Price_res1": CM_Core_Price[1],
        "CM_Wire_Price_res1": CM_Wire_Price[1],
        "CM_Labour_Price_res1": CM_Labour_Price[1],
        "HFFET_Cost_res1": HFFET_Cost[1],
        "HEATSINK_Cost_res1": HEATSINK_Cost[1],
        "CMC_Volume_res1": CMC_Volume[1],
        "EMI_Filter_Volume_res1": EMI_Filter_Volume[1],
        "HEATSINK_Volume_res1": HEATSINK_Volume[1],
        "LPFC_Volume_res1": LPFC_Volume[1],
        "BUSCAP_Volume_res1": BUSCAP_Volume[1],
        "LPFC_Stacks_res1": LPFC_Stacks[1],
        "LPFC_Turns_res1": LPFC_Turns[1],
        "LPFC_Loss_res1": LPFC_Loss[1],
        "LPFC_Core_Price_res1": LPFC_Core_Price[1],
        "LPFC_Wire_Price_res1": LPFC_Wire_Price[1],
        "LPFC_Labour_Price_res1": LPFC_Labour_Price[1],
        "LPFC_Loss_res1": LPFC_Loss[1],
        "LPFC_Volume_res1": LPFC_Volume[1],
        "CMC_CM_L_res1": CMC_CM_L[1],
        "CMC_Volume_res1": CMC_Volume[1],
        "CMC_Loss_res1": CMC_Loss[1],
        "CMC_Turns_res1": CMC_Turns[1],
        "CM_Choke_Temperature_Rise_res1": CM_Choke_Temperature_Rise[1],
        "HFFET_Loss_res1": HFFET_Loss[1],
        "LFFET_Loss_res1": LFFET_Loss[1],
        "BUSCAP_Loss_res1": BUSCAP_Loss[1],
        "HFFET_Loss_Cond_res1": HFFET_Loss_Cond[1],
        "HFFET_Loss_SW_res1": HFFET_Loss_SW[1],
        "FET_Achievable_dvdt_res1": FET_Achievable_dvdt[1],
        "BUSCAP_Value_Each_res1": BUSCAP_Value_Each[1],
        "BUSCAP_Number_in_Parallel_res1": BUSCAP_Number_in_Parallel[1],
        "BUSCAP_Value_res1": BUSCAP_Value[1],
    }




        with cache_lock:
            result_id = str(uuid.uuid4())
            results_cache.clear()
            results_cache[result_id] = {
                'R_Efficiency': R_Efficiency,
                'R_Volume': R_Volume,
                'R_Cost': R_Cost,
                'fsw_decided': fsw_decided,
                'L_decided': L_decided,
                'R_Power_Density': R_Power_Density,
                'ConductionModeDecided': ConductionModeDecided,
                'HFFET_Name': HFFET_Name,
                'LFFET_Name': LFFET_Name,
                'LPFC_Name': LPFC_Name,
                'CMC_Name': CMC_Name,
                'BUSCAP_Name': BUSCAP_Name,
                'HEATSINK_Name': HEATSINK_Name,
                'HFFET_Loss': HFFET_Loss,
                'LFFET_Loss': LFFET_Loss,
                'LPFC_Loss': LPFC_Loss,
                'CMC_Loss': CMC_Loss,
                'BUSCAP_Loss': BUSCAP_Loss,
                'outputPow': P_out,
                'EMI_FilterVolume': EMI_Filter_Volume,
                'LPFC_Volume': LPFC_Volume,
                'BUSCAP_Volume': BUSCAP_Volume,
                'HEATSINK_Volume': HEATSINK_Volume,
                'HFFET_Cost': HFFET_Cost,
                'BUSCAP_Price': BUSCAP_Price,
                'HEATSINK_Cost': HEATSINK_Cost,
                'LPFC_Core_Price': LPFC_Core_Price,
                'LPFC_Wire_Price': LPFC_Wire_Price,
                'LPFC_Labour_Price': LPFC_Labour_Price,
                'CM_Core_Price': CM_Core_Price,
                'CM_Wire_Price': CM_Wire_Price,
                'CM_Labour_Price': CM_Labour_Price,
                'HFFET_Loss_Cond': HFFET_Loss_Cond,
                'HFFET_Loss_SW': HFFET_Loss_SW,
                'FET_Achievable_dvdt': FET_Achievable_dvdt,
                'BUSCAP_Number_in_Parallel': BUSCAP_Number_in_Parallel,
                'BUSCAP_Value_Each': BUSCAP_Value_Each,
                'BUSCAP_Value': BUSCAP_Value,
                'HFFET_Number_in_Total': HFFET_Number_in_Total,
                'HFFET_in_Series': HFFET_in_Series,
                'HFFET_in_Parallel': HFFET_in_Parallel,
                'FET_Achievable_dvdt_per_fet': FET_Achievable_dvdt_per_fet,
                'FET_RGate_Result': FET_RGate_Result,
                'HFFET_Loss_IV': HFFET_Loss_IV,
                'HFFET_Loss_Qoss': HFFET_Loss_Qoss,
                'HFFET_Loss_DT': HFFET_Loss_DT,
                'HFFET_Loss_OFF': HFFET_Loss_OFF,
                'HFFET_Loss_Gate': HFFET_Loss_Gate,
                'HFFET_Loss_Qrr': HFFET_Loss_Qrr,
                'DM_Noise_f': DM_Noise_f,
                'DM_Noise_Plot': DM_Noise_Plot,
                'LF_CM_Noise_f': LF_CM_Noise_f,
                'LF_CM_Noise_Plot': LF_CM_Noise_Plot,
                'CMC_Mu': CMC_Mu,
                'CMC_CM_Noise': CMC_CM_Noise,
                'CMC_CM_L': CMC_CM_L,
                'CMC_CM_C': CMC_CM_C,
                'CM_Choke_Temperature_Rise': CM_Choke_Temperature_Rise,
                'CMC_AWG': CMC_AWG,
                'CMC_Turns_Each': CMC_Turns_Each,
                'CMC_CM_L_Desired': CMC_CM_L_Desired,
                'CMC_Turns': CMC_Turns,
                'DMC_DM_Noise': DMC_DM_Noise,
                'DMC_DM_L': DMC_DM_L,
                'DMC_DM_C': DMC_DM_C,
                'EMI_Filter_Level': EMI_Filter_Level,
                'EMI_Filter_Volume': EMI_Filter_Volume,
                'EMI_Filter_Volume_Choke': EMI_Filter_Volume_Choke,
                'EMI_Filter_Volume_Cap': EMI_Filter_Volume_Cap,
                't_ripple_plot': t_ripple_plot,
                'Real_Current_Ripple_Waveform': Real_Current_Ripple_Waveform,
                'Real_Input_Current_Waveform': Real_Input_Current_Waveform,
                'LPFC_Stacks': LPFC_Stacks,
                'LPFC_AWG': LPFC_AWG,
                'LPFC_Layers': LPFC_Layers,
                'LPFC_Turns': LPFC_Turns,
                'LPFC_Loss_Core': LPFC_Loss_Core,
                'LPFC_Loss_Copper': LPFC_Loss_Copper,
                'LPFC_Core_Temperature_Rise': LPFC_Core_Temperature_Rise,
                'CMC_Volume': CMC_Volume,               
                
            }

        return jsonify({
            "result_id": result_id,
            "R_Efficiency": R_Efficiency,
            "R_Volume": R_Volume,
            "R_Cost": R_Cost,
            "fsw_decided": fsw_decided,
            "L_decided": L_decided,
            "R_Power_Density": R_Power_Density,
            "ConductionModeDecided": ConductionModeDecided,
            "HFFET_Name": HFFET_Name,
            "LFFET_Name": LFFET_Name,
            "LPFC_Name": LPFC_Name,
            "CMC_Name": CMC_Name,
            "BUSCAP_Name": BUSCAP_Name,
            "HEATSINK_Name": HEATSINK_Name,
            "HFFET_Loss": HFFET_Loss,
            "LFFET_Loss": LFFET_Loss,
            "LPFC_Loss": LPFC_Loss,
            "CMC_Loss": CMC_Loss,
            "BUSCAP_Loss": BUSCAP_Loss,
            "outputPow": P_out,
            "EMI_FilterVolume": EMI_Filter_Volume,
            "LPFC_Volume": LPFC_Volume,
            "BUSCAP_Volume": BUSCAP_Volume,
            "HEATSINK_Volume": HEATSINK_Volume,
            "HFFET_Cost": HFFET_Cost,
            "BUSCAP_Price": BUSCAP_Price,
            "HEATSINK_Cost": HEATSINK_Cost,
            "LPFC_Core_Price": LPFC_Core_Price,
            "LPFC_Wire_Price": LPFC_Wire_Price,
            "LPFC_Labour_Price": LPFC_Labour_Price,
            "CM_Core_Price": CM_Core_Price,
            "CM_Wire_Price": CM_Wire_Price,
            "CM_Labour_Price": CM_Labour_Price,
            "HFFET_Loss_Cond": HFFET_Loss_Cond,
            "HFFET_Loss_SW": HFFET_Loss_SW,
            "FET_Achievable_dvdt": FET_Achievable_dvdt,
            "BUSCAP_Number_in_Parallel": BUSCAP_Number_in_Parallel,
            "BUSCAP_Value_Each": BUSCAP_Value_Each,
            "BUSCAP_Value": BUSCAP_Value,
            "HFFET_Number_in_Total": HFFET_Number_in_Total,
            "HFFET_in_Series": HFFET_in_Series,
            "HFFET_in_Parallel": HFFET_in_Parallel,
            "FET_Achievable_dvdt_per_fet": FET_Achievable_dvdt_per_fet,
            "FET_RGate_Result": FET_RGate_Result,
            "HFFET_Loss_IV": HFFET_Loss_IV,
            "HFFET_Loss_Qoss": HFFET_Loss_Qoss,
            "HFFET_Loss_DT": HFFET_Loss_DT,
            "HFFET_Loss_OFF": HFFET_Loss_OFF,
            "HFFET_Loss_Gate": HFFET_Loss_Gate,
            "HFFET_Loss_Qrr": HFFET_Loss_Qrr,
            "DM_Noise_f": DM_Noise_f,
            "DM_Noise_Plot": DM_Noise_Plot,
            "LF_CM_Noise_f": LF_CM_Noise_f,
            "LF_CM_Noise_Plot": LF_CM_Noise_Plot,
            "CMC_Mu": CMC_Mu,
            "CMC_CM_Noise": CMC_CM_Noise,
            "CMC_CM_L": CMC_CM_L,
            "CMC_CM_C": CMC_CM_C,
            "CM_Choke_Temperature_Rise": CM_Choke_Temperature_Rise,
            "CMC_AWG": CMC_AWG,
            "CMC_Turns_Each": CMC_Turns_Each,
            "CMC_Turns": CMC_Turns,
            "DMC_DM_Noise": DMC_DM_Noise,
            "DMC_DM_L": DMC_DM_L,
            "DMC_DM_C": DMC_DM_C,
            "EMI_Filter_Level": EMI_Filter_Level,
            "EMI_Filter_Volume": EMI_Filter_Volume,
            "EMI_Filter_Volume_Choke": EMI_Filter_Volume_Choke,
            "EMI_Filter_Volume_Cap": EMI_Filter_Volume_Cap,
            "t_ripple_plot": t_ripple_plot,
            "Real_Current_Ripple_Waveform": Real_Current_Ripple_Waveform,
            "Real_Input_Current_Waveform": Real_Input_Current_Waveform,
            "LPFC_Stacks": LPFC_Stacks,
            "LPFC_AWG": LPFC_AWG,
            "LPFC_Layers": LPFC_Layers,
            "LPFC_Turns": LPFC_Turns,
            "LPFC_Loss_Core": LPFC_Loss_Core,
            "LPFC_Loss_Copper": LPFC_Loss_Copper,
            "LPFC_Core_Temperature_Rise": LPFC_Core_Temperature_Rise,
            "CMC_Volume": CMC_Volume,
            "CMC_CM_L": CMC_CM_L,
            "CMC_CM_L_Desired": CMC_CM_L_Desired,
                       
            "message": "Optimizasyon başarıyla tamamlandı"
        })
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error("HATA OLUŞTU!")
        logger.error("=" * 60)
        logger.error(f"Hata mesajı: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        debug_print("HATA DETAYI", str(e), "red")
        return jsonify({"error": str(e)}), 500

    finally:
        if 'eng' in locals():
            logger.info("MATLAB engine kapatılıyor...")
            eng.quit()
            logger.info("MATLAB engine kapatıldı.")

@main.route('/pfcresult', methods=['GET'])
def get_pfcresult():
    try:
        with cache_lock:
            if not results_cache:
                return jsonify({"error": "Sonuç bulunamadı"}), 404

            all_results = [{"result_id": result_id,
                            "R_Efficiency": data['R_Efficiency'],
                            "R_Volume": data['R_Volume'],
                            "R_Cost": data['R_Cost'],
                            "fsw_decided": data['fsw_decided'],
                            "L_decided": data['L_decided'],
                            "R_Power_Density": data['R_Power_Density'],
                            "ConductionModeDecided": data['ConductionModeDecided'],
                            "HFFET_Name": data['HFFET_Name'],
                            "LFFET_Name": data['LFFET_Name'],
                            "LPFC_Name": data['LPFC_Name'],
                            "CMC_Name": data['CMC_Name'],
                            "BUSCAP_Name": data['BUSCAP_Name'],
                            "HEATSINK_Name": data['HEATSINK_Name'],
                            "HFFET_Loss": data['HFFET_Loss'],
                            "LFFET_Loss": data['LFFET_Loss'],
                            "LPFC_Loss": data['LPFC_Loss'],
                            "CMC_Loss": data['CMC_Loss'],
                            "BUSCAP_Loss": data['BUSCAP_Loss'],
                            "outputPow": data['outputPow'],
                            "EMI_FilterVolume": data['EMI_FilterVolume'],
                            "LPFC_Volume": data['LPFC_Volume'],
                            "BUSCAP_Volume": data['BUSCAP_Volume'],
                            "HEATSINK_Volume": data['HEATSINK_Volume'],
                            "HFFET_Cost": data['HFFET_Cost'],
                            "BUSCAP_Price": data['BUSCAP_Price'],
                            "HEATSINK_Cost": data['HEATSINK_Cost'],
                            "LPFC_Core_Price": data['LPFC_Core_Price'],
                            "LPFC_Wire_Price": data['LPFC_Wire_Price'],
                            "LPFC_Labour_Price": data['LPFC_Labour_Price'],
                            "CM_Core_Price": data['CM_Core_Price'],
                            "CM_Wire_Price": data['CM_Wire_Price'],
                            "CM_Labour_Price": data['CM_Labour_Price'],
                            "HFFET_Loss_Cond": data['HFFET_Loss_Cond'],
                            "HFFET_Loss_SW": data['HFFET_Loss_SW'],
                            "FET_Achievable_dvdt": data['FET_Achievable_dvdt'],
                            "BUSCAP_Number_in_Parallel": data['BUSCAP_Number_in_Parallel'],
                            "BUSCAP_Value_Each": data['BUSCAP_Value_Each'],
                            "BUSCAP_Value": data['BUSCAP_Value'],
                            "LPFC_Stacks": data['LPFC_Stacks'],
                            "LPFC_Turns": data['LPFC_Turns'],
                            "CMC_CM_L": data['CMC_CM_L'],
                            "CMC_Turns": data['CMC_Turns'],
                            "CM_Choke_Temperature_Rise": data['CM_Choke_Temperature_Rise'],
                            "CMC_Volume": data['CMC_Volume'],
                            
                            }
                           for result_id, data in results_cache.items()]

        return jsonify({
            "results": all_results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@main.route('/pfcresult/Fet', methods=['GET'])
def get_pfcresult_fet():
        try:
            with cache_lock:
                if not results_cache:
                    return jsonify({"error": "Sonuç bulunamadı"}), 404
                
                pfc_results = [{"result_id": result_id,
                                "HFFET_Name": data['HFFET_Name'],
                                "LFFET_Name": data['LFFET_Name'],
                                "HFFET_Loss": data['HFFET_Loss'],
                                "LFFET_Loss": data['LFFET_Loss'],
                                "FET_Achievable_dvdt": data['FET_Achievable_dvdt'],
                                "HFFET_Loss_Cond": data['HFFET_Loss_Cond'],
                                "HFFET_Loss_SW": data['HFFET_Loss_SW'],
                                "fsw_decided": data['fsw_decided'],
                                "HFFET_Number_in_Total": data['HFFET_Number_in_Total'],
                                "HFFET_in_Series": data['HFFET_in_Series'],
                                "HFFET_in_Parallel": data['HFFET_in_Parallel'],
                                "HFFET_Cost": data['HFFET_Cost'],
                                "FET_Achievable_dvdt_per_fet": data['FET_Achievable_dvdt_per_fet'],
                                "FET_RGate_Result": data['FET_RGate_Result'],
                                "HFFET_Loss_IV": data['HFFET_Loss_IV'],
                                "HFFET_Loss_Qoss": data['HFFET_Loss_Qoss'],
                                "HFFET_Loss_DT": data['HFFET_Loss_DT'],
                                "HFFET_Loss_OFF": data['HFFET_Loss_OFF'],
                                "HFFET_Loss_Gate": data['HFFET_Loss_Gate'],
                                "HFFET_Loss_Qrr": data['HFFET_Loss_Qrr'],
                                
                                }
                               for result_id, data in results_cache.items()]

            return jsonify({
                "results": pfc_results
            })
                    
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@main.route('/pfcresult/cmcresult', methods=['GET'])
def get_pfcresult_cmc():
    try:
        with cache_lock:
            if not results_cache:
                return jsonify({"error": "Not results found"}), 404
            
            cmc_results= [{
                "result_id": result_id,
                "DM_Noise_f": data['DM_Noise_f'],
                "DM_Noise_Plot": data['DM_Noise_Plot'],
                "LF_CM_Noise_f": data['LF_CM_Noise_f'],
                "LF_CM_Noise_Plot" : data['LF_CM_Noise_Plot'],
                "CMC_Name": data['CMC_Name'],
                "CMC_Loss": data['CMC_Loss'],
                "CMC_Mu": data['CMC_Mu'],
                "CMC_CM_Noise": data['CMC_CM_Noise'],
                "CMC_CM_L": data['CMC_CM_L'],
                "CMC_CM_C": data['CMC_CM_C'],
                "CM_Choke_Temperature_Rise": data['CM_Choke_Temperature_Rise'],
                "CMC_AWG": data['CMC_AWG'],
                "CMC_Turns_Each": data['CMC_Turns_Each'],
                "CMC_Turns": data['CMC_Turns'],
                "DMC_DM_Noise": data['DMC_DM_Noise'],
                "DMC_DM_L": data['DMC_DM_L'],
                "DMC_DM_C": data['DMC_DM_C'],
                "EMI_Filter_Level": data['EMI_Filter_Level'],
                "EMI_Filter_Volume": data['EMI_Filter_Volume'],
                "EMI_Filter_Volume_Choke": data['EMI_Filter_Volume_Choke'],
                "EMI_Filter_Volume_Cap": data['EMI_Filter_Volume_Cap'],
                "CMC_CM_L_Desired": data['CMC_CM_L_Desired'],
                
            }
                           
            for result_id, data in results_cache.items()]
            
        return jsonify ({
            "results": cmc_results
        })       
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@main.route ('/pfcresult/lpfcresult', methods=['GET'])
def get_pfcresult_lpfc():
    try:
        with cache_lock:
            if not results_cache:
                
                return jsonify({"error": "Not results found"}), 404
        lpfc_results =  [{
            
            "result_id": result_id,
            "t_ripple_plot": data['t_ripple_plot'],
            "Real_Current_Ripple_Waveform": data['Real_Current_Ripple_Waveform'],
            "Real_Input_Current_Waveform": data['Real_Input_Current_Waveform'],
            "LPFC_Name": data['LPFC_Name'],
            "L_decided": data['L_decided'],
            "LPFC_Stacks": data['LPFC_Stacks'],
            "LPFC_AWG": data['LPFC_AWG'],
            "LPFC_Layers": data['LPFC_Layers'],
            "LPFC_Turns": data['LPFC_Turns'],
            "LPFC_Volume": data['LPFC_Volume'],
            "LPFC_Stacks": data['LPFC_Stacks'],
            "LPFC_AWG": data['LPFC_AWG'],
            "LPFC_Layers": data['LPFC_Layers'],
            "LPFC_Turns": data['LPFC_Turns'],
            "LPFC_Loss": data['LPFC_Loss'],
            "LPFC_Loss_Core": data['LPFC_Loss_Core'],
            "LPFC_Loss_Copper": data['LPFC_Loss_Copper'],
            "LPFC_Core_Temperature_Rise": data['LPFC_Core_Temperature_Rise'],
        }
                         
           for result_id, data in results_cache.items()]
        
        return jsonify ({
            "results": lpfc_results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@main.route('/pfcresult/heatsink', methods=['GET'])
def get_pfcresult_heatsink():
    try:
        with cache_lock:
            if not results_cache:
                return jsonify({"error": "Not results found"}), 404
            heatsink_results = [{
                "result_id": result_id,
                "HEATSINK_Name": data['HEATSINK_Name'],
                "HEATSINK_Volume": data['HEATSINK_Volume'],
            } for result_id, data in results_cache.items()]
                               
            return jsonify({
                "results": heatsink_results
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@main.route ('/pfcresult/buscap', methods=['GET'])
def get_pfcresult_buscap():
    try:
        with cache_lock:
            if not results_cache:
                return jsonify({ "error": "Not results found"}), 404
            buscap_results = [{
                "result_id": result_id,
                "BUSCAP_Name": data['BUSCAP_Name'],
                "BUSCAP_Value_Each": data['BUSCAP_Value_Each'],
                "BUSCAP_Number_in_Parallel": data['BUSCAP_Number_in_Parallel'],
                "BUSCAP_Value": data['BUSCAP_Value'],
                "BUSCAP_Volume": data['BUSCAP_Volume'],
                "BUSCAP_Loss": data['BUSCAP_Loss'],
            }for result_id, data in results_cache.items()]
            return jsonify({
                "results": buscap_results,

                
            })
    except Exception as e:
            return jsonify({"error": str(e)}), 500

def check_none_values(data):
    return [key for key, value in data.items() if value is None]
