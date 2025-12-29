"""
LLC Blueprint - MATLAB-based LLC Converter Simulation
Detaylı debug ve loglama yapısı ile
"""

from flask import Blueprint, request, jsonify
import matlab.engine
import os
import threading
import numpy as np
import traceback
import matlab
import logging

# =============================================================================
# LOGGING YAPILANDIRMASI
# =============================================================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# DEBUG YARDIMCI FONKSİYONLARI
# =============================================================================
def debug_print(title, data, color="blue"):
    """
    Debug bilgisi yazdır - Renkli konsol çıktısı

    Renkler:
    - blue: Genel bilgi
    - green: Başarılı işlemler
    - yellow: Uyarılar
    - red: Hatalar
    - cyan: Veri gösterimi
    - magenta: Parametre bilgileri
    """
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
            # Uzun listeleri kısalt
            if isinstance(value, list) and len(value) > 5:
                print(f"  {key}: [{value[0]}, {value[1]}, ... ({len(value)} öğe)]")
            elif isinstance(value, (int, float)):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
    elif isinstance(data, list):
        if len(data) > 10:
            for item in data[:5]:
                print(f"  - {item}")
            print(f"  ... ve {len(data)-5} öğe daha")
        else:
            for item in data:
                print(f"  - {item}")
    else:
        print(f"  {data}")
    print(f"{c}{'='*60}{r}\n")


def log_parameter_conversion(param_name, original_value, converted_value, unit_info=""):
    """Parametre dönüşümlerini logla"""
    logger.debug(f"  {param_name}: {original_value} -> {converted_value} {unit_info}")


llc_bp = Blueprint("llc", __name__)
result_cache = {}
cache_lock = threading.Lock()
llc_results = {}
swithcsecfet_results = {}
priinductor_results = {}
transformer_results= {}
buscap_results = {}
outputcap_results = {}


def safe_float(value, default=0.0):
    """
    Güvenli float dönüşümü - virgül/nokta sorunlarını ve geçersiz değerleri ele alır.
    - None, boş string, "User input needed" gibi değerler için default döndürür
    - Virgüllü sayıları noktaya çevirir (Türkçe lokalizasyon desteği)
    """
    if value is None:
        return float(default)

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Boş veya geçersiz string kontrolü
        value = value.strip()
        if not value or value.lower() in ['user input needed', 'nan', 'null', 'none', '']:
            return float(default)

        # Virgülü noktaya çevir (Türkçe lokalizasyon)
        value = value.replace(',', '.')

        try:
            return float(value)
        except ValueError:
            return float(default)

    return float(default)


def convert_matlab_data(obj):
    """
    Rekürsif olarak matlab.double tipindeki verileri JSON serileştirilebilir forma dönüştürür.
    Eğer obj matlab.double ise:
      - Tek elemanlı ise float, 
      - Birden fazla eleman varsa numpy array ile listeye dönüştürür.
    Eğer obj bir dict veya liste ise, içindeki elemanları da dönüştürür.
    """
    if isinstance(obj, matlab.double):
        arr = np.array(obj)
        if arr.size == 1:
            return float(arr)
        return arr.tolist()
    elif isinstance(obj, dict):
        return {k: convert_matlab_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_matlab_data(item) for item in obj]
    return obj

def check_none_values(data):
    return [key for key, value in data.items() if value is None]

@llc_bp.route("/LLC", methods=["POST"])
def LLC_Organiser():
    try:
        data = request.get_json()
        if data is None:
            logger.error("❌ JSON verisi alınamadı!")
            return jsonify({"error": "No data provided"}), 400

        logger.info("=" * 60)
        logger.info("🔋 LLC MATLAB OPTİMİZASYONU BAŞLADI")
        logger.info("=" * 60)

        # =========================================================================
        # 1. FRONTEND'DEN GELEN TÜM VERİYİ LOGLA
        # =========================================================================
        debug_print("📥 FRONTEND'DEN GELEN TÜM VERİ", data, "cyan")

        none_keys = check_none_values(data)
        if none_keys:
            debug_print("⚠️ NONE DEĞERE SAHİP ANAHTARLAR", none_keys, "yellow")

        # =========================================================================
        # 2. SEÇİLEN BİLEŞENLERİ LOGLA
        # =========================================================================
        selected_components = {
            "selectedFets (Primary)": data.get("selectedFets", []),
            "selectedSeconderFets (Secondary)": data.get("selectedSeconderFets", []),
            "selectedDiodes": data.get("selectedDiodes", []),
            "selectedTransformer": data.get("selectedTransformer", []),
            "selectedInductor": data.get("selectedInductor", []),
            "selectedPrimaryHeatsink": data.get("selectedPrimaryHeatsink", []),
            "selectedSecondaryHeatsink": data.get("selectedSecondaryHeatsink", []),
            "selectedBusCaps": data.get("selectedBusCaps", []),
            "selectedOutCaps": data.get("selectedOutCaps", []),
        }
        debug_print("🔧 SEÇİLEN BİLEŞENLER", selected_components, "green")

        # =========================================================================
        # 3. SELECT ALL PARAMETRELERİNİ LOGLA
        # =========================================================================
        select_all_params = {
            "selectedAllFetsDefault": data.get("selectedAllFetsDefault", "undefined"),
            "selectedAllSeconderFetsDefault": data.get("selectedAllSeconderFetsDefault", "undefined"),
            "selectedAllDiodesDefault": data.get("selectedAllDiodesDefault", "undefined"),
            "selectedAllTransformerDefault": data.get("selectedAllTransformerDefault", "undefined"),
            "selectedAllInductorDefault": data.get("selectedAllInductorDefault", "undefined"),
            "selectedAllPrimaryHeatsink": data.get("selectedAllPrimaryHeatsink", "undefined"),
            "selectedAllSecondaryHeatsink": data.get("selectedAllSecondaryHeatsink", "undefined"),
            "selectedAllBusCaps": data.get("selectedAllBusCaps", "undefined"),
            "selectedAllOutCaps": data.get("selectedAllOutCaps", "undefined"),
        }
        debug_print("🎯 SELECT ALL PARAMETRELERİ (0=Seçilenler, 1=Hepsi)", select_all_params, "magenta")

        # =========================================================================
        # 4. BOŞ LİSTELER İÇİN UYARILAR
        # =========================================================================
        if not data.get("selectedFets"):
            logger.warning("⚠️ DİKKAT: selectedFets (Primary FET) listesi boş!")
        if not data.get("selectedSeconderFets"):
            logger.warning("⚠️ DİKKAT: selectedSeconderFets (Secondary FET) listesi boş!")
        if not data.get("selectedDiodes"):
            logger.warning("⚠️ DİKKAT: selectedDiodes listesi boş!")
        if not data.get("selectedTransformer"):
            logger.warning("⚠️ DİKKAT: selectedTransformer listesi boş!")
        if not data.get("selectedInductor"):
            logger.warning("⚠️ DİKKAT: selectedInductor listesi boş!")
        if not data.get("selectedPrimaryHeatsink"):
            logger.warning("⚠️ DİKKAT: selectedPrimaryHeatsink listesi boş!")
        if not data.get("selectedSecondaryHeatsink"):
            logger.warning("⚠️ DİKKAT: selectedSecondaryHeatsink listesi boş!")
        if not data.get("selectedBusCaps"):
            logger.warning("⚠️ DİKKAT: selectedBusCaps listesi boş!")
        if not data.get("selectedOutCaps"):
            logger.warning("⚠️ DİKKAT: selectedOutCaps listesi boş!")

        # =========================================================================
        # 5. MATLAB ENGINE BAŞLATMA
        # =========================================================================
        logger.info("🔄 MATLAB Engine başlatılıyor...")
        eng = matlab.engine.start_matlab()
        matlab_folder_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'matlab',
            'LLC'
        )
        eng.cd(matlab_folder_path)
        logger.info(f"📂 MATLAB çalışma dizini: {matlab_folder_path}")

        logger.info("📚 MATLAB veritabanları yükleniyor...")
        eng.run('FET_Database.m', nargout=0)
        logger.debug("  ✓ FET_Database.m yüklendi")
        eng.run('Heatsink_Database.m', nargout=0)
        logger.debug("  ✓ Heatsink_Database.m yüklendi")
        eng.run('core_geometries.m', nargout=0)
        logger.debug("  ✓ core_geometries.m yüklendi")
        eng.run('SECSW_Database.m', nargout=0)
        logger.debug("  ✓ SECSW_Database.m yüklendi")
        eng.run('SECFET_Database.m', nargout=0)
        logger.debug("  ✓ SECFET_Database.m yüklendi")
        eng.run('Diode_Database.m', nargout=0)
        logger.debug("  ✓ Diode_Database.m yüklendi")
        eng.run('Cap_Database.m', nargout=0)
        logger.debug("  ✓ Cap_Database.m yüklendi")
        logger.info("✅ Tüm MATLAB veritabanları yüklendi")

        # =========================================================================
        # 6. BİLEŞEN LİSTELERİNİ HAZIRLA
        # =========================================================================
        logger.info("📋 Bileşen listeleri hazırlanıyor...")

        # Component lists
        Checked_MosFET_List = [str(fet) for fet in (data.get("selectedFets") or ["BSC034N10LS5"])]
        Custom_MosFET_Created = safe_float(data.get("customFetCreated"), 0)
        Checked_SecFET_List = [str(fet) for fet in (data.get("selectedSeconderFets") or ["BSC034N10LS5"])]
        Checked_SecDiode_List = [str(fet) for fet in (data.get("selectedDiodes") or ["BSC034N10LS5"])]
        Checked_Heatsink_pri_List = [str(fet) for fet in (data.get("selectedPrimaryHeatsink") or ["HS-002"])]
        Checked_Heatsink_sec_List = [str(fet) for fet in (data.get("selectedSecondaryHeatsink") or ["HS-002"])]
        Checked_Material_trf_List = [str(fet) for fet in (data.get("selectedTransformer") or ["Aluminium"])]
        Checked_Material_ind_List = [str(fet) for fet in (data.get("selectedInductor") or ["Ferrite"])]
        Checked_BusCap_List = [str(fet) for fet in (data.get("selectedBusCaps") or ["Ceramic"])]
        Checked_OutputCap_List = [str(fet) for fet in (data.get("selectedOutCaps") or ["Ceramic"])]

        component_lists_debug = {
            "Checked_MosFET_List": Checked_MosFET_List,
            "Checked_SecFET_List": Checked_SecFET_List,
            "Checked_SecDiode_List": Checked_SecDiode_List,
            "Checked_Heatsink_pri_List": Checked_Heatsink_pri_List,
            "Checked_Heatsink_sec_List": Checked_Heatsink_sec_List,
            "Checked_Material_trf_List": Checked_Material_trf_List,
            "Checked_Material_ind_List": Checked_Material_ind_List,
            "Checked_BusCap_List": Checked_BusCap_List,
            "Checked_OutputCap_List": Checked_OutputCap_List,
        }
        debug_print("📦 MATLAB'A GÖNDERİLECEK BİLEŞEN LİSTELERİ", component_lists_debug, "blue")

        # =========================================================================
        # 7. PARAMETRE DÖNÜŞÜMLERİ VE LOGLAMA
        # =========================================================================
        logger.info("🔢 Parametreler dönüştürülüyor...")

        # Resonant Frequency Selection (mode1: 1=Fixed, 0=Sweep)
        # Frontend sends values in kHz, MATLAB expects Hz
        # Conversion: kHz * 1000 = Hz
        Fixed_FSW_Option = safe_float(data.get("mode1"), 1)
        rsw_step = safe_float(data.get("step1"), 10) * 1000          # kHz -> Hz
        rsw_Min_Fixed_by_User = safe_float(data.get("min1"), 300) * 1000   # kHz -> Hz
        rsw_Max_Fixed_by_User = safe_float(data.get("max1"), 500) * 1000   # kHz -> Hz
        fsw_Fixed_by_User = safe_float(data.get("fixedValue1"), 45) * 1000  # kHz -> Hz (was *10000, FIXED)

        resonant_freq_params = {
            "Fixed_FSW_Option (1=Fixed, 0=Sweep)": Fixed_FSW_Option,
            "rsw_step (Hz)": rsw_step,
            "rsw_Min_Fixed_by_User (Hz)": rsw_Min_Fixed_by_User,
            "rsw_Max_Fixed_by_User (Hz)": rsw_Max_Fixed_by_User,
            "fsw_Fixed_by_User (Hz)": fsw_Fixed_by_User,
        }
        debug_print("📡 REZONANS FREKANS PARAMETRELERİ", resonant_freq_params, "magenta")

        # Power and Voltage Parameters
        Po = safe_float(data.get("outPow"), 100)
        V_input_min = safe_float(data.get("V_input_min"), 370)
        V_input_nom = safe_float(data.get("V_input_nom"), 400)
        V_input_max = safe_float(data.get("V_input_max"), 430)
        V_output_min = safe_float(data.get("V_output_min"), 36)
        V_output_nom = safe_float(data.get("V_output_nom"), 48)
        V_output_max = safe_float(data.get("V_output_max"), 54)

        power_voltage_params = {
            "Po (W)": Po,
            "V_input_min (V)": V_input_min,
            "V_input_nom (V)": V_input_nom,
            "V_input_max (V)": V_input_max,
            "V_output_min (V)": V_output_min,
            "V_output_nom (V)": V_output_nom,
            "V_output_max (V)": V_output_max,
        }
        debug_print("⚡ GÜÇ VE GERİLİM PARAMETRELERİ", power_voltage_params, "cyan")

        # Temperature and Weight Parameters
        Tamb_input = safe_float(data.get("Tamb_input"), 25)
        W_Efficiency = safe_float(data.get("efficiency"), 50) / 100
        W_Volume = safe_float(data.get("volume"), 50) / 100
        W_Cost = safe_float(data.get("cost"), 0)

        weight_params = {
            "Tamb_input (°C)": Tamb_input,
            "W_Efficiency (ağırlık)": W_Efficiency,
            "W_Volume (ağırlık)": W_Volume,
            "W_Cost (ağırlık)": W_Cost,
        }
        debug_print("⚖️ SICAKLIK VE AĞIRLIK PARAMETRELERİ", weight_params, "blue")

        # Transformer Parameters
        ku_trf_input = safe_float(data.get("kuValue"), 0.6)
        Jmax_trf_input = safe_float(data.get("JmaxValue"), 3.5) * 1000000
        dT_trf_input = safe_float(data.get("deltaTValue"), 100)

        transformer_params = {
            "ku_trf_input": ku_trf_input,
            "Jmax_trf_input (A/m²)": Jmax_trf_input,
            "dT_trf_input (°C)": dT_trf_input,
        }
        debug_print("🔄 TRANSFORMATÖR PARAMETRELERİ", transformer_params, "green")

        # Inductor Parameters
        ku_ind_input = safe_float(data.get("kuInductorValue"), 0.6)
        Jmax_ind_input = safe_float(data.get("JmaxInductorValue"), 3.5) * 1000000
        dT_ind_input = safe_float(data.get("deltaTInductorValue"), 100)

        inductor_params = {
            "ku_ind_input": ku_ind_input,
            "Jmax_ind_input (A/m²)": Jmax_ind_input,
            "dT_ind_input (°C)": dT_ind_input,
        }
        debug_print("🔌 İNDÜKTÖR PARAMETRELERİ", inductor_params, "green")

        # Operating Temperatures
        Tjmax_pri_input = safe_float(data.get("tOperating"), 110)
        Tjmax_sec_input = safe_float(data.get("tOperating_2"), 110)

        operating_temp_params = {
            "Tjmax_pri_input (°C)": Tjmax_pri_input,
            "Tjmax_sec_input (°C)": Tjmax_sec_input,
        }
        debug_print("🌡️ ÇALIŞMA SICAKLIKLARI", operating_temp_params, "yellow")

        # Ln Parameters (lnMode: 1=Fixed, 0=Sweep)
        Fixed_Ln_Option = safe_float(data.get("lnMode"), 1)
        ln_Fixed_by_User = safe_float(data.get("lnFixedValue"), 4)
        ln_Min_Fixed_by_User = safe_float(data.get("lnMin"), 1)
        ln_Max_Fixed_by_User = safe_float(data.get("lnMax"), 6)
        ln_step = safe_float(data.get("lnStep"), 0.5)

        ln_params = {
            "Fixed_Ln_Option (1=Fixed, 0=Sweep)": Fixed_Ln_Option,
            "ln_Fixed_by_User": ln_Fixed_by_User,
            "ln_Min_Fixed_by_User": ln_Min_Fixed_by_User,
            "ln_Max_Fixed_by_User": ln_Max_Fixed_by_User,
            "ln_step": ln_step,
        }
        debug_print("📐 Ln PARAMETRELERİ", ln_params, "magenta")

        # Q Parameters (qMode: 1=Fixed, 0=Sweep)
        Fixed_Q_Option = safe_float(data.get("qMode"), 1)
        q_Fixed_by_User = safe_float(data.get("qFixedValue"), 0.8)
        q_Min_Fixed_by_User = safe_float(data.get("qMin"), 0.1)
        q_Max_Fixed_by_User = safe_float(data.get("qMax"), 2)
        q_step = safe_float(data.get("qStep"), 0.1)

        q_params = {
            "Fixed_Q_Option (1=Fixed, 0=Sweep)": Fixed_Q_Option,
            "q_Fixed_by_User": q_Fixed_by_User,
            "q_Min_Fixed_by_User": q_Min_Fixed_by_User,
            "q_Max_Fixed_by_User": q_Max_Fixed_by_User,
            "q_step": q_step,
        }
        debug_print("📊 Q PARAMETRELERİ", q_params, "magenta")

        # Voturn
        Voturn = safe_float(data.get("Voturn"), 54)
        logger.info(f"🔧 Voturn: {Voturn}")


        # =========================================================================
        # 8. MATLAB FONKSİYONU ÇAĞRISI
        # =========================================================================
        logger.info("=" * 60)
        logger.info("🚀 MATLAB LLC_Organiser_Function ÇAĞRILIYOR...")
        logger.info("=" * 60)

        # Tüm parametreleri özetleyen debug çıktısı
        all_params_summary = {
            "Bileşen Listeleri": f"{len(Checked_MosFET_List)} Primary FET, {len(Checked_SecFET_List)} Secondary FET, {len(Checked_SecDiode_List)} Diode",
            "Rezonans Frekans": f"{'Fixed' if Fixed_FSW_Option == 1 else 'Sweep'} - {fsw_Fixed_by_User/1000:.1f} kHz",
            "Ln": f"{'Fixed' if Fixed_Ln_Option == 1 else 'Sweep'} - {ln_Fixed_by_User}",
            "Q": f"{'Fixed' if Fixed_Q_Option == 1 else 'Sweep'} - {q_Fixed_by_User}",
            "Çıkış Gücü": f"{Po} W",
            "Giriş Gerilimi": f"{V_input_min}-{V_input_max} V",
            "Çıkış Gerilimi": f"{V_output_min}-{V_output_max} V",
        }
        debug_print("📋 MATLAB'A GÖNDERİLECEK PARAMETRE ÖZETİ", all_params_summary, "cyan")

        result = eng.LLC_Organiser_Function(
            Checked_MosFET_List,
            Custom_MosFET_Created,
            Checked_SecFET_List,
            Checked_SecDiode_List,
            Checked_Heatsink_pri_List,
            Checked_Heatsink_sec_List,
            Checked_Material_trf_List,
            Checked_Material_ind_List,  
            Checked_BusCap_List,
            Checked_OutputCap_List,  
            Fixed_FSW_Option,
            rsw_step,
            rsw_Min_Fixed_by_User,
            rsw_Max_Fixed_by_User,
            fsw_Fixed_by_User,
            Po,
            V_input_min,
            V_input_nom,
            V_input_max,
            V_output_min,
            V_output_nom,
            V_output_max,
            Tamb_input,
            W_Efficiency,
            W_Volume,
            W_Cost,
            ku_trf_input,
            Jmax_trf_input,
            dT_ind_input,
            dT_trf_input,
            ku_ind_input,
            Jmax_ind_input,
            Tjmax_pri_input,
            Tjmax_sec_input,
            Fixed_Ln_Option,
            ln_Fixed_by_User,
            ln_Min_Fixed_by_User,
            ln_Max_Fixed_by_User,
            ln_step,
            Fixed_Q_Option,
            q_Fixed_by_User,
            q_Min_Fixed_by_User,
            q_Max_Fixed_by_User,
            q_step,
            Voturn,
        )

        logger.info("✅ MATLAB fonksiyonu başarıyla tamamlandı!")

        # =========================================================================
        # 9. MATLAB SONUÇLARINI İŞLE VE LOGLA
        # =========================================================================
        logger.info("📊 MATLAB sonuçları işleniyor...")

        # Waveform verilerini çıkar
        t1 = np.array(result["t1"]).flatten().tolist() if "t1" in result else []
        t2 = np.array(result["t2"]).flatten().tolist() if "t2" in result else []
        Ilrp = np.array(result["Ilrp"]).flatten().tolist() if "Ilrp" in result else []
        id1 = np.array(result["id1"]).flatten().tolist() if "id1" in result else []

        waveform_info = {
            "t1 uzunluğu": len(t1),
            "t2 uzunluğu": len(t2),
            "Ilrp uzunluğu": len(Ilrp),
            "id1 uzunluğu": len(id1),
        }
        debug_print("📈 WAVEFORM VERİ BİLGİSİ", waveform_info, "blue")

        # MATLAB verilerini JSON formatına dönüştür
        result = convert_matlab_data(result)
        logger.info("✓ MATLAB verileri JSON formatına dönüştürüldü")

        global llc_results
        llc_results = {
            "BestPriFet_Loss_res0": result.get("BestPriFet_Loss", 0),
            "BestSecFet_Loss_res0": result.get("BestSecFet_Loss", 0),
            "BestTrf_Loss_res0": result.get("BestTrf_Loss", 0),
            "BestInd_Loss_res0": result.get("BestInd_Loss", 0),
            "BestCap_Loss_res0": result.get("BestCap_Loss", 0),
            "BestTotalLoss_res0": result.get("BestTotalLoss", 0),
            "BestTotalEfficiency_res0": result.get("BestTotalEfficiency", 0),
            "BestTotalVolume_res0": result.get("BestTotalVolume", 0),
            "BestTrf_Volume_res0": result.get("BestTrf_Volume", 0),
            "BestInd_Volume_res0": result.get("BestInd_Volume", 0),
            "BestPriFET_Volume_res0": result.get("BestPriFET_Volume", 0),
            "BestSecFET_Volume_res0": result.get("BestSecFET_Volume", 0),
            "BestPowerDensity_res0": result.get("BestPowerDensity", 0),
            "Bestfo_res0": result.get("Bestfo", 0),
            "Bestfs_min_res0": result.get("Bestfs_min", 0),
            "Bestfs_max_res0": result.get("Bestfs_max", 0),
            "BestLr_res0": result.get("BestLr", 0),
            "BestCr_res0": result.get("BestCr", 0),
            "BestLm_res0": result.get("BestLm", 0),
            "BestPriFet_Name_res0": result.get("BestPriFet_Name", 0),
            "BestPriFet_Total_res0": result.get("BestPriFet_Total", 0),
            "BestPriFet_Conduction_res0": result.get("BestPriFet_Conduction", 0),
            "BestPriFet_Switching_res0": result.get("BestPriFet_Switching", 0),
            "BestSecFet_Name_res0": result.get("BestSecFet_Name", 0),
            "TotalSecSw_res0": result.get("TotalSecSw", 0),
            "psw_best_res0": result.get("psw_best", 0),
            "BestSec_Total_res0": result.get("BestSec_Total", 0),
            "BestSec_Conduction_res0": result.get("BestSec_Conduction", 0),
            "BestSec_Switching_res0": result.get("BestSec_Switching", 0),
            "BestInd_Name_res0": result.get("BestInd_Name", 0),
            "BestInd_core_res0": result.get("BestInd_core", 0),
            "BestInd_cu_res0": result.get("BestInd_cu", 0),
            "BestTrf_Name_res0": result.get("BestTrf_Name", 0),
            "BestTrf_core_res0": result.get("BestTrf_core", 0),
            "BestTrf_cu_res0": result.get("BestTrf_cu", 0),
            "ptrf_best_res0": result.get("ptrf_best", 0),
            "BestPriHeatsink_Name_res0": result.get("BestPriHeatsink_Name", 0),
            "BestSecHeatsink_Name_res0": result.get("BestSecHeatsink_Name", 0),
            "BestLn_res0": result.get("BestLn", 0),
            "BestQ_res0": result.get("BestQ", 0),
            "BestInd_airgap_res0": result.get("BestInd_airgap", 0),
            "t1": t1,
            "t2": t2,
            "Ilrp": Ilrp,
            "id1": id1,
            
            "Best_BusCap_Name_res0": result.get("Best_BusCap_Name", 0),
            "Best_BusCap_SingleC_res0": result.get("Best_BusCap_SingleC", 0),
            "Best_BusCap_TotalC_res0": result.get("Best_BusCap_TotalC", 0),
            "Best_BusCap_Parallel_res0": result.get("Best_BusCap_Parallel", 0),
            "Best_BusCap_Volume_res0": result.get("Best_BusCap_Volume", 0),
            "Best_BusCap_Loss_res0": result.get("Best_BusCap_Loss", 0),
            
            "Best_OutCap_Name_res0": result.get("Best_OutCap_Name", 0),
            "Best_OutCap_SingleC_res0": result.get("Best_OutCap_SingleC", 0),
            "Best_OutCap_TotalC_res0": result.get("Best_OutCap_TotalC", 0),
            "Best_OutCap_Parallel_res0": result.get("Best_OutCap_Parallel", 0),
            "Best_OutCap_Volume_res0": result.get("Best_OutCap_Volume", 0),
            "Best_OutCap_Loss_res0": result.get("Best_OutCap_Loss", 0),
            
            
            
        }
        swithcsecfet_results["swithcsecfet_results"] = {
            "BestPriFet_Name_res0": result.get("BestPriFet_Name", 0),
            "BestSecFet_Name_res0": result.get("BestSecFet_Name", 0),
            "fnom_Best": result.get("fnom_Best", 0),
            "psw_best_res0": result.get("psw_best", 0),
            "TotalSecSw_res0": result.get("TotalSecSw", 0),
            "BestPriFet_Total_res0": result.get("BestPriFet_Total", 0),
            "BestPriFet_Conduction_res0": result.get("BestPriFet_Conduction", 0),
            "BestPriFet_Switching_res0": result.get("BestPriFet_Switching", 0),
            "BestSec_Total_res0": result.get("BestSec_Total", 0),
            "BestSec_Conduction_res0": result.get("BestSec_Conduction", 0),
            "BestSec_Switching_res0": result.get("BestSec_Switching", 0),
            "BestPriFet_off_res0": result.get("BestPriFet_off", 0),
            "BestPriFet_gate_res0": result.get("BestPriFet_gate", 0),
            "BestPriFet_body_res0": result.get("BestPriFet_body", 0),
            "BestSecFet_gate_res0": result.get("BestSecFet_gate", 0),
            "BestSecFet_body_res0": result.get("BestSecFet_body", 0),
            "BestSecFet_rr_res0": result.get("BestSecFet_rr", 0),
}
        
        priinductor_results["priinductor_results"] = {
            
            "BestInd_Name_res0": result.get("BestInd_Name", 0),
            "BestLr_res0": result.get("BestLr",0),
            "BestInd_Volume_res0": result.get("BestInd_Volume", 0),
            "BestInd_airgap_res0": result.get("BestInd_airgap", 0),
            "BestInd_Bmax_res0": result.get("BestInd_Bmax", 0),
            
            "BestInd_J_res0":result.get("BestInd_J", 0),
            
            "BestInd_dT_res0": result.get("BestInd_dT", 0),
            
            "BestInd_turns_res0": result.get("BestInd_turns", 0),
            "BestInd_AWG_res0": result.get("BestInd_AWG", 0),
            "BestInd_Litz_res0": result.get("BestInd_Litz", 0),
            "BestInd_Layer_res0": result.get("BestInd_Layer", 0),
            "BestInd_core_res0": result.get("BestInd_core", 0),
            "BestInd_cu_res0": result.get("BestInd_cu", 0),
            "BestInd_Loss_res0": result.get("BestInd_Loss", 0),
            "Ilrp": Ilrp,
            "t1": t1,
            "t2": t2,
        }

        transformer_results["transformer_results"] = {
            
            "BestTrf_Name_res0": result.get("BestTrf_Name", 0),
            "BestLm_res0": result.get("BestLm", 0),
            "BestTrf_Volume_res0": result.get("BestTrf_Volume", 0),
            "BestTrf_airgap_res0": result.get("BestTrf_airgap", 0),
            
            "BestTrf_Bmax_res0": result.get("BestTrf_Bmax", 0),
            "BestTrf_Jp_res0": result.get("BestTrf_Jp", 0),
            "BestTrf_Js_res0": result.get("BestTrf_Js", 0),
            
            "BestTrf_dT_res0": result.get("BestTrf_dT", 0),
            
            "BestTrf_Np_res0": result.get("BestTrf_Np", 0),
            "BestTrf_Ns_res0": result.get("BestTrf_Ns", 0),
            "BestTrf_pAWG_res0": result.get("BestTrf_pAWG", 0),
            "BestTrf_pLitz_res0": result.get("BestTrf_pLitz", 0),
            "BestTrf_sLitz_res0": result.get("BestTrf_sLitz", 0),
            "BestTrf_sLitz_res0":result.get("BestTrf_sLitz", 0),
            "BestTrf_dopt_res0": result.get("BestTrf_dopt", 0),
            "BestTrf_length_res0": result.get("BestTrf_length", 0),
            "BestTrf_pLayer_res0": result.get("BestTrf_pLayer", 0),
            "BestTrf_sLayer_res0": result.get("BestTrf_sLayer", 0),
            "BestTrf_Loss_res0":result.get("BestTrf_Loss", 0),
            "BestTrf_cu_res0": result.get("BestTrf_cu", 0),
            "BestTrf_core_res0": result.get("BestTrf_core", 0),
            "Ilrp": Ilrp,
            "t1": t1,
            "t2": t2,
            "id1": id1,
            "ptrf_best_res0": result.get("ptrf_best", 0),
            "Pcu_indx_res0": result.get("Pcu_indx", 0),
            "BestTrf_sAWG_res0": result.get("BestTrf_sAWG", 0),
            "BestTrf_sLitz_res0": result.get("BestTrf_sLitz", 0),
            
        }   
        buscap_results["buscap_results"] = {
            "Best_BusCap_Name_res0": result.get("Best_BusCap_Name", 0),
            "Best_BusCap_SingleC_res0": result.get("Best_BusCap_SingleC", 0),
            "Best_BusCap_TotalC_res0": result.get("Best_BusCap_TotalC", 0),
            "Best_BusCap_Parallel_res0": result.get("Best_BusCap_Parallel", 0),
            "Best_BusCap_Volume_res0": result.get("Best_BusCap_Volume", 0),
            "Best_BusCap_Loss_res0": result.get("Best_BusCap_Loss", 0),
        } 
        outputcap_results["outputcap_results"] = {
            "Best_OutCap_Name_res0": result.get("Best_OutCap_Name", 0),
            "Best_OutCap_SingleC_res0": result.get("Best_OutCap_SingleC", 0),
            "Best_OutCap_TotalC_res0": result.get("Best_OutCap_TotalC", 0),
            "Best_OutCap_Parallel_res0": result.get("Best_OutCap_Parallel", 0),
            "Best_OutCap_Volume_res0": result.get("Best_OutCap_Volume", 0),
            "Best_OutCap_Loss_res0": result.get("Best_OutCap_Loss", 0),
        }

        # =========================================================================
        # 10. SONUÇLARI DETAYLI LOGLA
        # =========================================================================

        # Ana sonuç özeti
        main_results_summary = {
            "Toplam Verimlilik (%)": llc_results.get("BestTotalEfficiency_res0", 0),
            "Toplam Kayıp (W)": llc_results.get("BestTotalLoss_res0", 0),
            "Toplam Hacim (mm³)": llc_results.get("BestTotalVolume_res0", 0),
            "Güç Yoğunluğu (W/dm³)": llc_results.get("BestPowerDensity_res0", 0),
            "Rezonans Frekansı fo (Hz)": llc_results.get("Bestfo_res0", 0),
            "Min Anahtarlama fs_min (Hz)": llc_results.get("Bestfs_min_res0", 0),
            "Max Anahtarlama fs_max (Hz)": llc_results.get("Bestfs_max_res0", 0),
            "Lr (H)": llc_results.get("BestLr_res0", 0),
            "Cr (F)": llc_results.get("BestCr_res0", 0),
            "Lm (H)": llc_results.get("BestLm_res0", 0),
            "Ln": llc_results.get("BestLn_res0", 0),
            "Q": llc_results.get("BestQ_res0", 0),
        }
        debug_print("🏆 ANA SONUÇ ÖZETİ", main_results_summary, "green")

        # Kayıp dağılımı
        loss_breakdown = {
            "Primary FET Kayıp (W)": llc_results.get("BestPriFet_Loss_res0", 0),
            "Secondary FET Kayıp (W)": llc_results.get("BestSecFet_Loss_res0", 0),
            "Transformatör Kayıp (W)": llc_results.get("BestTrf_Loss_res0", 0),
            "İndüktör Kayıp (W)": llc_results.get("BestInd_Loss_res0", 0),
            "Kapasitör Kayıp (W)": llc_results.get("BestCap_Loss_res0", 0),
            "Bus Cap Kayıp (W)": llc_results.get("Best_BusCap_Loss_res0", 0),
            "Out Cap Kayıp (W)": llc_results.get("Best_OutCap_Loss_res0", 0),
        }
        debug_print("📉 KAYIP DAĞILIMI", loss_breakdown, "yellow")

        # Seçilen bileşenler
        selected_components_result = {
            "Primary FET": llc_results.get("BestPriFet_Name_res0", "Bilinmiyor"),
            "Secondary FET": llc_results.get("BestSecFet_Name_res0", "Bilinmiyor"),
            "İndüktör Core": llc_results.get("BestInd_Name_res0", "Bilinmiyor"),
            "Transformatör Core": llc_results.get("BestTrf_Name_res0", "Bilinmiyor"),
            "Primary Heatsink": llc_results.get("BestPriHeatsink_Name_res0", "Bilinmiyor"),
            "Secondary Heatsink": llc_results.get("BestSecHeatsink_Name_res0", "Bilinmiyor"),
            "Bus Kapasitör": llc_results.get("Best_BusCap_Name_res0", "Bilinmiyor"),
            "Out Kapasitör": llc_results.get("Best_OutCap_Name_res0", "Bilinmiyor"),
        }
        debug_print("✅ SEÇİLEN OPTİMAL BİLEŞENLER", selected_components_result, "green")

        # Hacim dağılımı
        volume_breakdown = {
            "Transformatör Hacim (mm³)": llc_results.get("BestTrf_Volume_res0", 0),
            "İndüktör Hacim (mm³)": llc_results.get("BestInd_Volume_res0", 0),
            "Primary FET Hacim (mm³)": llc_results.get("BestPriFET_Volume_res0", 0),
            "Secondary FET Hacim (mm³)": llc_results.get("BestSecFET_Volume_res0", 0),
            "Bus Cap Hacim (mm³)": llc_results.get("Best_BusCap_Volume_res0", 0),
            "Out Cap Hacim (mm³)": llc_results.get("Best_OutCap_Volume_res0", 0),
        }
        debug_print("📦 HACİM DAĞILIMI", volume_breakdown, "cyan")

        logger.info("=" * 60)
        logger.info("✅ LLC OPTİMİZASYONU BAŞARIYLA TAMAMLANDI!")
        logger.info(f"   Toplam Verimlilik: {main_results_summary['Toplam Verimlilik (%)']:.2f}%")
        logger.info(f"   Toplam Kayıp: {main_results_summary['Toplam Kayıp (W)']:.2f} W")
        logger.info("=" * 60)

        return jsonify({"result": result}), 200

    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ LLC OPTİMİZASYONU SIRASINDA HATA OLUŞTU!")
        logger.error("=" * 60)
        logger.error(f"Hata Mesajı: {str(e)}")
        logger.error("Detaylı Hata:")
        traceback.print_exc()

        # Hata detaylarını debug_print ile göster
        error_info = {
            "Hata Tipi": type(e).__name__,
            "Hata Mesajı": str(e),
        }
        debug_print("❌ HATA DETAYLARI", error_info, "red")

        return jsonify({"error": str(e)}), 500

@llc_bp.route("/llcresult", methods=["GET"])
def get_llc_results():
    try:
        global llc_results
        return jsonify({"results": llc_results}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@llc_bp.route("/llcresult/switchingfets", methods=["GET"])
def get_switchingfets_results():
    try:
        return jsonify({"results": swithcsecfet_results.get("swithcsecfet_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@llc_bp.route("/llcresult/inductor", methods=["GET"])
def get_inductor_results():
    try:
        return jsonify({"results": priinductor_results.get("priinductor_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@llc_bp.route("/llcresult/transformer", methods=["GET"])
def get_transformer_results():
    try:
        return jsonify({"results": transformer_results.get("transformer_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@llc_bp.route("/llcresult/Buscap", methods=["GET"])
def get_buscap_results():
    try:
        return jsonify({"results": buscap_results.get("buscap_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@llc_bp.route("/llcresult/Outcap", methods=["GET"])
def get_outputcap_results():
    try:
        return jsonify({"results": outputcap_results.get("outputcap_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500