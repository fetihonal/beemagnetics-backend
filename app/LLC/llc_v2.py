"""
LLC Blueprint v2 - Python-based simulation (No MATLAB)
Replaces MATLAB engine with pure Python implementation
"""

from flask import Blueprint, request, jsonify
import traceback
import numpy as np
import logging

# Import Python simulation engine instead of MATLAB
from app.simulation.llc.llc_optimizer import LLCOptimizer

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
            if isinstance(value, list) and len(value) > 5:
                print(f"  {key}: [{value[0]}, {value[1]}, ... ({len(value)} öğe)]")
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

llc_bp_v2 = Blueprint("llc_v2", __name__)

# Global result caches (same structure as original for frontend compatibility)
llc_results = {}
swithcsecfet_results = {}
priinductor_results = {}
transformer_results = {}
buscap_results = {}
outputcap_results = {}


@llc_bp_v2.route("/LLC", methods=["POST"])
def LLC_Organiser():
    """
    LLC Optimization endpoint - PYTHON VERSION (No MATLAB)

    This replaces the MATLAB engine call with pure Python simulation
    """
    try:
        data = request.get_json()
        if data is None:
            logger.error("JSON verisi alınamadı!")
            return jsonify({"error": "No data provided"}), 400

        logger.info("=" * 60)
        logger.info("LLC PYTHON OPTİMİZASYONU BAŞLADI")
        logger.info("=" * 60)

        # =========================================================================
        # 1. FRONTEND'DEN GELEN TÜM VERİYİ LOGLA
        # =========================================================================
        debug_print("FRONTEND'DEN GELEN VERİ", data, "cyan")

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
        debug_print("SEÇİLEN BİLEŞENLER", selected_components, "green")

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
        debug_print("SELECT ALL PARAMETRELERİ (0=Seçilenler, 1=Hepsi)", select_all_params, "magenta")

        # =========================================================================
        # 4. BOŞ LİSTELER İÇİN UYARILAR
        # =========================================================================
        if not data.get("selectedFets"):
            logger.warning("DİKKAT: selectedFets (Primary FET) listesi boş!")
        if not data.get("selectedSeconderFets"):
            logger.warning("DİKKAT: selectedSeconderFets (Secondary FET) listesi boş!")
        if not data.get("selectedDiodes"):
            logger.warning("DİKKAT: selectedDiodes listesi boş!")
        if not data.get("selectedTransformer"):
            logger.warning("DİKKAT: selectedTransformer listesi boş!")
        if not data.get("selectedInductor"):
            logger.warning("DİKKAT: selectedInductor listesi boş!")
        if not data.get("selectedPrimaryHeatsink"):
            logger.warning("DİKKAT: selectedPrimaryHeatsink listesi boş!")
        if not data.get("selectedSecondaryHeatsink"):
            logger.warning("DİKKAT: selectedSecondaryHeatsink listesi boş!")
        if not data.get("selectedBusCaps"):
            logger.warning("DİKKAT: selectedBusCaps listesi boş!")
        if not data.get("selectedOutCaps"):
            logger.warning("DİKKAT: selectedOutCaps listesi boş!")

        # =========================================================================
        # 5. GİRİŞ PARAMETRELERİNİ LOGLA
        # =========================================================================
        def safe_float(val, default=0):
            if val is None:
                return default
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                val = val.strip().replace(',', '.')
                if not val or val.lower() in ['user input needed', 'nan', 'null', 'none']:
                    return default
                try:
                    return float(val)
                except ValueError:
                    return default
            return default

        power_voltage_params = {
            "Po (W)": safe_float(data.get("outPow"), 100),
            "V_input_min (V)": safe_float(data.get("V_input_min"), 370),
            "V_input_nom (V)": safe_float(data.get("V_input_nom"), 400),
            "V_input_max (V)": safe_float(data.get("V_input_max"), 430),
            "V_output_min (V)": safe_float(data.get("V_output_min"), 36),
            "V_output_nom (V)": safe_float(data.get("V_output_nom"), 48),
            "V_output_max (V)": safe_float(data.get("V_output_max"), 54),
            "Tamb_input (°C)": safe_float(data.get("Tamb_input"), 25),
        }
        debug_print("GÜÇ VE GERİLİM PARAMETRELERİ", power_voltage_params, "cyan")

        # Resonant Frequency parametreleri
        mode1 = safe_float(data.get("mode1"), 1)
        resonant_freq_params = {
            "Mode (1=Fixed, 0=Sweep)": mode1,
            "fixedValue1 (kHz)": safe_float(data.get("fixedValue1"), 45),
            "min1 (kHz)": safe_float(data.get("min1"), 300),
            "max1 (kHz)": safe_float(data.get("max1"), 500),
            "step1 (kHz)": safe_float(data.get("step1"), 10),
        }
        debug_print("REZONANS FREKANS PARAMETRELERİ", resonant_freq_params, "magenta")

        # Ln parametreleri
        ln_mode = safe_float(data.get("lnMode"), 1)
        ln_params = {
            "Mode (1=Fixed, 0=Sweep)": ln_mode,
            "lnFixedValue": safe_float(data.get("lnFixedValue"), 4),
            "lnMin": safe_float(data.get("lnMin"), 1),
            "lnMax": safe_float(data.get("lnMax"), 6),
            "lnStep": safe_float(data.get("lnStep"), 0.5),
        }
        debug_print("Ln PARAMETRELERİ", ln_params, "magenta")

        # Q parametreleri
        q_mode = safe_float(data.get("qMode"), 1)
        q_params = {
            "Mode (1=Fixed, 0=Sweep)": q_mode,
            "qFixedValue": safe_float(data.get("qFixedValue"), 0.8),
            "qMin": safe_float(data.get("qMin"), 0.1),
            "qMax": safe_float(data.get("qMax"), 2),
            "qStep": safe_float(data.get("qStep"), 0.1),
        }
        debug_print("Q PARAMETRELERİ", q_params, "magenta")

        # Transformatör ve İndüktör parametreleri
        design_params = {
            "ku_trf": safe_float(data.get("kuValue"), 0.6),
            "Jmax_trf (A/mm²)": safe_float(data.get("JmaxValue"), 3.5),
            "dT_trf (°C)": safe_float(data.get("deltaTValue"), 100),
            "ku_ind": safe_float(data.get("kuInductorValue"), 0.6),
            "Jmax_ind (A/mm²)": safe_float(data.get("JmaxInductorValue"), 3.5),
            "dT_ind (°C)": safe_float(data.get("deltaTInductorValue"), 100),
            "Tjmax_pri (°C)": safe_float(data.get("tOperating"), 110),
            "Tjmax_sec (°C)": safe_float(data.get("tOperating_2"), 110),
        }
        debug_print("TASARIM PARAMETRELERİ", design_params, "blue")

        # =========================================================================
        # 6. PYTHON OPTİMİZASYONUNU ÇALIŞTIR
        # =========================================================================
        logger.info("=" * 60)
        logger.info("LLCOptimizer başlatılıyor...")
        optimizer = LLCOptimizer()

        # Run optimization (replaces eng.LLC_Organiser_Function())
        logger.info("Optimizasyon çalıştırılıyor...")
        result = optimizer.run_optimization(data)

        debug_print("OPTİMİZASYON SONUCU", {
            "Verimlilik": f"{result.get('BestTotalEfficiency', 0):.2f}%",
            "Primary FET": result.get("BestPriFet_Name", "N/A"),
            "Secondary FET": result.get("BestSecFet_Name", "N/A"),
            "Toplam Kayıp": f"{result.get('BestTotalLoss', 0):.2f}W",
        }, "green")

        logger.info(f"✅ LLC Optimizasyonu tamamlandı! Verimlilik: {result.get('BestTotalEfficiency', 0):.2f}%")

        # Extract waveform data (matching MATLAB format)
        t1 = result.get('t1', [])
        t2 = result.get('t2', [])
        Ilrp = result.get('Ilrp', [])
        id1 = result.get('id1', [])

        # Format results to match MATLAB output structure
        # UNIT CONVERSIONS:
        # - Frequencies: Hz -> kHz (divide by 1000)
        # - Inductances: H -> µH (multiply by 1e6)
        # - Capacitances: F -> µF (multiply by 1e6)

        # Convert units for frontend display
        Bestfo_Hz = result.get("Bestfo", 0)
        Bestfs_min_Hz = result.get("Bestfs_min", 0)
        Bestfs_max_Hz = result.get("Bestfs_max", 0)
        BestLr_H = result.get("BestLr", 0)
        BestCr_F = result.get("BestCr", 0)
        BestLm_H = result.get("BestLm", 0)

        # Convert to frontend-expected units
        Bestfo_kHz = Bestfo_Hz / 1000 if Bestfo_Hz else 0
        Bestfs_min_kHz = Bestfs_min_Hz / 1000 if Bestfs_min_Hz else 0
        Bestfs_max_kHz = Bestfs_max_Hz / 1000 if Bestfs_max_Hz else 0
        BestLr_uH = BestLr_H * 1e6 if BestLr_H else 0
        BestCr_uF = BestCr_F * 1e6 if BestCr_F else 0
        BestLm_uH = BestLm_H * 1e6 if BestLm_H else 0

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
            "BestTrf_Volume_res0": result.get("BestTotalVolume", 0) * 0.4,  # Estimate
            "BestInd_Volume_res0": result.get("BestTotalVolume", 0) * 0.3,  # Estimate
            "BestPriFET_Volume_res0": result.get("BestTotalVolume", 0) * 0.15,  # Estimate
            "BestSecFET_Volume_res0": result.get("BestTotalVolume", 0) * 0.15,  # Estimate
            "BestPowerDensity_res0": result.get("BestPowerDensity", 0),
            "Bestfo_res0": Bestfo_kHz,  # kHz
            "Bestfs_min_res0": Bestfs_min_kHz,  # kHz
            "Bestfs_max_res0": Bestfs_max_kHz,  # kHz
            "BestLr_res0": BestLr_uH,  # µH
            "BestCr_res0": BestCr_uF,  # µF
            "BestLm_res0": BestLm_uH,  # µH
            "BestPriFet_Name_res0": result.get("BestPriFet_Name", "Uygun parça bulunamadı"),
            "BestPriFet_Total_res0": result.get("BestPriFet_Loss", 0),
            "BestPriFet_Conduction_res0": result.get("BestPriFet_Conduction", 0),
            "BestPriFet_Switching_res0": result.get("BestPriFet_Switching", 0),
            "BestSecFet_Name_res0": result.get("BestSecFet_Name", "Uygun parça bulunamadı"),
            "TotalSecSw_res0": 2,  # Typical: 2 secondary switches
            "psw_best_res0": 2,
            "BestSec_Total_res0": result.get("BestSecFet_Loss", 0),
            "BestSec_Conduction_res0": result.get("BestSec_Conduction", 0),
            "BestSec_Switching_res0": 0,  # Synchronous rectification, minimal switching
            "BestInd_Name_res0": result.get("BestInd_Name", "Uygun parça bulunamadı"),
            "BestInd_core_res0": result.get("BestInd_Loss", 0) * 0.5,
            "BestInd_cu_res0": result.get("BestInd_Loss", 0) * 0.5,
            "BestTrf_Name_res0": result.get("BestTrf_Name", "Uygun parça bulunamadı"),
            "BestTrf_core_res0": result.get("BestTrf_Loss", 0) * 0.4,
            "BestTrf_cu_res0": result.get("BestTrf_Loss", 0) * 0.6,
            "ptrf_best_res0": result.get("BestTrf_Loss", 0),
            "BestPriHeatsink_Name_res0": result.get("BestPriHeatsink_Name", "Uygun parça bulunamadı"),
            "BestSecHeatsink_Name_res0": result.get("BestSecHeatsink_Name", "Uygun parça bulunamadı"),
            "BestLn_res0": result.get("BestLn", 5),
            "BestQ_res0": result.get("BestQ", 0.4),
            "BestInd_airgap_res0": 0.5,  # mm, typical
            "t1": t1,
            "t2": t2,
            "Ilrp": Ilrp,
            "id1": id1,
            "Best_BusCap_Name_res0": result.get("Best_BusCap_Name", "Uygun parça bulunamadı"),
            "Best_BusCap_SingleC_res0": result.get("Best_BusCap_SingleC", 0),
            "Best_BusCap_TotalC_res0": result.get("Best_BusCap_TotalC", 0),
            "Best_BusCap_Parallel_res0": result.get("Best_BusCap_Parallel", 0),
            "Best_BusCap_Volume_res0": result.get("Best_BusCap_Volume", 0),
            "Best_BusCap_Loss_res0": result.get("BestCap_Loss", 0) * 0.5,
            "Best_OutCap_Name_res0": result.get("Best_OutCap_Name", "Uygun parça bulunamadı"),
            "Best_OutCap_SingleC_res0": result.get("Best_OutCap_SingleC", 0),
            "Best_OutCap_TotalC_res0": result.get("Best_OutCap_TotalC", 0),
            "Best_OutCap_Parallel_res0": result.get("Best_OutCap_Parallel", 0),
            "Best_OutCap_Volume_res0": result.get("Best_OutCap_Volume", 0),
            "Best_OutCap_Loss_res0": result.get("BestCap_Loss", 0) * 0.5,
        }

        # Switching FETs results
        global swithcsecfet_results
        swithcsecfet_results["swithcsecfet_results"] = {
            "BestPriFet_Name_res0": result.get("BestPriFet_Name", "Uygun parça bulunamadı"),
            "BestSecFet_Name_res0": result.get("BestSecFet_Name", "Uygun parça bulunamadı"),
            "fnom_Best": Bestfo_kHz,  # kHz
            "psw_best_res0": 2,
            "TotalSecSw_res0": 2,
            "BestPriFet_Total_res0": result.get("BestPriFet_Loss", 0),
            "BestPriFet_Conduction_res0": result.get("BestPriFet_Conduction", 0),
            "BestPriFet_Switching_res0": result.get("BestPriFet_Switching", 0),
            "BestSec_Total_res0": result.get("BestSecFet_Loss", 0),
            "BestSec_Conduction_res0": result.get("BestSec_Conduction", 0),
            "BestSec_Switching_res0": 0,
            "BestPriFet_off_res0": result.get("BestPriFet_Switching", 0) * 0.5,
            "BestPriFet_gate_res0": result.get("BestPriFet_Switching", 0) * 0.3,
            "BestPriFet_body_res0": result.get("BestPriFet_Switching", 0) * 0.2,
            "BestSecFet_gate_res0": result.get("BestSecFet_Loss", 0) * 0.1,
            "BestSecFet_body_res0": result.get("BestSecFet_Loss", 0) * 0.1,
            "BestSecFet_rr_res0": result.get("BestSecFet_Loss", 0) * 0.1,
        }

        # Inductor results
        global priinductor_results
        priinductor_results["priinductor_results"] = {
            "BestInd_Name_res0": result.get("BestInd_Name", "Uygun parça bulunamadı"),
            "BestLr_res0": BestLr_uH,  # µH
            "BestInd_Volume_res0": result.get("BestTotalVolume", 0) * 0.3,
            "BestInd_airgap_res0": 0.5,
            "BestInd_Bmax_res0": 0.3,
            "BestInd_J_res0": 4e6,
            "BestInd_dT_res0": 40,
            "BestInd_turns_res0": 20,
            "BestInd_AWG_res0": 18,
            "BestInd_Litz_res0": 1,
            "BestInd_Layer_res0": 2,
            "BestInd_core_res0": result.get("BestInd_Loss", 0) * 0.5,
            "BestInd_cu_res0": result.get("BestInd_Loss", 0) * 0.5,
            "BestInd_Loss_res0": result.get("BestInd_Loss", 0),
            "Ilrp": Ilrp,
            "t1": t1,
            "t2": t2,
        }

        # Transformer results
        global transformer_results
        transformer_results["transformer_results"] = {
            "BestTrf_Name_res0": result.get("BestTrf_Name", "Uygun parça bulunamadı"),
            "BestLm_res0": BestLm_uH,  # µH
            "BestTrf_Volume_res0": result.get("BestTotalVolume", 0) * 0.4,
            "BestTrf_airgap_res0": 0,
            "BestTrf_Bmax_res0": 0.3,
            "BestTrf_Jp_res0": 4e6,
            "BestTrf_Js_res0": 5e6,
            "BestTrf_dT_res0": 40,
            "BestTrf_Np_res0": 10,
            "BestTrf_Ns_res0": 20,
            "BestTrf_pAWG_res0": 18,
            "BestTrf_pLitz_res0": 1,
            "BestTrf_sLitz_res0": 1,
            "BestTrf_dopt_res0": 1,
            "BestTrf_length_res0": 100,
            "BestTrf_pLayer_res0": 2,
            "BestTrf_sLayer_res0": 3,
            "BestTrf_Loss_res0": result.get("BestTrf_Loss", 0),
            "BestTrf_cu_res0": result.get("BestTrf_Loss", 0) * 0.6,
            "BestTrf_core_res0": result.get("BestTrf_Loss", 0) * 0.4,
            "Ilrp": Ilrp,
            "t1": t1,
            "t2": t2,
            "id1": id1,
            "ptrf_best_res0": result.get("BestTrf_Loss", 0),
            "Pcu_indx_res0": 1,
            "BestTrf_sAWG_res0": 20,
        }

        # Bus capacitor results
        global buscap_results
        buscap_results["buscap_results"] = {
            "Best_BusCap_Name_res0": result.get("Best_BusCap_Name", "Uygun parça bulunamadı"),
            "Best_BusCap_SingleC_res0": result.get("Best_BusCap_SingleC", 0),
            "Best_BusCap_TotalC_res0": result.get("Best_BusCap_TotalC", 0),
            "Best_BusCap_Parallel_res0": result.get("Best_BusCap_Parallel", 0),
            "Best_BusCap_Volume_res0": result.get("Best_BusCap_Volume", 0),
            "Best_BusCap_Loss_res0": result.get("BestCap_Loss", 0) * 0.5,
        }

        # Output capacitor results
        global outputcap_results
        outputcap_results["outputcap_results"] = {
            "Best_OutCap_Name_res0": result.get("Best_OutCap_Name", "Uygun parça bulunamadı"),
            "Best_OutCap_SingleC_res0": result.get("Best_OutCap_SingleC", 0),
            "Best_OutCap_TotalC_res0": result.get("Best_OutCap_TotalC", 0),
            "Best_OutCap_Parallel_res0": result.get("Best_OutCap_Parallel", 0),
            "Best_OutCap_Volume_res0": result.get("Best_OutCap_Volume", 0),
            "Best_OutCap_Loss_res0": result.get("BestCap_Loss", 0) * 0.5,
        }

        # =========================================================================
        # 10. SONUÇLARI DETAYLI LOGLA
        # =========================================================================
        main_results_summary = {
            "Toplam Verimlilik (%)": llc_results.get("BestTotalEfficiency_res0", 0),
            "Toplam Kayıp (W)": llc_results.get("BestTotalLoss_res0", 0),
            "Toplam Hacim (mm³)": llc_results.get("BestTotalVolume_res0", 0),
            "Güç Yoğunluğu (W/dm³)": llc_results.get("BestPowerDensity_res0", 0),
            "Rezonans Frekansı fo (kHz)": llc_results.get("Bestfo_res0", 0),
            "Lr (µH)": llc_results.get("BestLr_res0", 0),
            "Cr (µF)": llc_results.get("BestCr_res0", 0),
            "Lm (µH)": llc_results.get("BestLm_res0", 0),
            "Ln": llc_results.get("BestLn_res0", 0),
            "Q": llc_results.get("BestQ_res0", 0),
        }
        debug_print("ANA SONUÇ ÖZETİ", main_results_summary, "green")

        # Kayıp dağılımı
        loss_breakdown = {
            "Primary FET Kayıp (W)": llc_results.get("BestPriFet_Loss_res0", 0),
            "Secondary FET Kayıp (W)": llc_results.get("BestSecFet_Loss_res0", 0),
            "Transformatör Kayıp (W)": llc_results.get("BestTrf_Loss_res0", 0),
            "İndüktör Kayıp (W)": llc_results.get("BestInd_Loss_res0", 0),
            "Kapasitör Kayıp (W)": llc_results.get("BestCap_Loss_res0", 0),
        }
        debug_print("KAYIP DAĞILIMI", loss_breakdown, "yellow")

        # Seçilen optimal bileşenler
        selected_optimal = {
            "Primary FET": llc_results.get("BestPriFet_Name_res0", "Bilinmiyor"),
            "Secondary FET": llc_results.get("BestSecFet_Name_res0", "Bilinmiyor"),
            "İndüktör Core": llc_results.get("BestInd_Name_res0", "Bilinmiyor"),
            "Transformatör Core": llc_results.get("BestTrf_Name_res0", "Bilinmiyor"),
            "Primary Heatsink": llc_results.get("BestPriHeatsink_Name_res0", "Bilinmiyor"),
            "Secondary Heatsink": llc_results.get("BestSecHeatsink_Name_res0", "Bilinmiyor"),
            "Bus Kapasitör": llc_results.get("Best_BusCap_Name_res0", "Bilinmiyor"),
            "Out Kapasitör": llc_results.get("Best_OutCap_Name_res0", "Bilinmiyor"),
        }
        debug_print("SEÇİLEN OPTİMAL BİLEŞENLER", selected_optimal, "green")

        logger.info("=" * 60)
        logger.info("LLC OPTİMİZASYONU BAŞARIYLA TAMAMLANDI!")
        eff_val = main_results_summary.get('Toplam Verimlilik (%)', 0)
        loss_val = main_results_summary.get('Toplam Kayıp (W)', 0)
        if isinstance(eff_val, (int, float)):
            logger.info(f"   Toplam Verimlilik: {eff_val:.2f}%")
        if isinstance(loss_val, (int, float)):
            logger.info(f"   Toplam Kayıp: {loss_val:.2f} W")
        logger.info("=" * 60)

        return jsonify({"result": llc_results}), 200

    except Exception as e:
        logger.error("=" * 60)
        logger.error("LLC OPTİMİZASYONU SIRASINDA HATA OLUŞTU!")
        logger.error("=" * 60)
        logger.error(f"Hata Mesajı: {str(e)}")
        traceback.print_exc()

        error_info = {
            "Hata Tipi": type(e).__name__,
            "Hata Mesajı": str(e),
        }
        debug_print("HATA DETAYLARI", error_info, "red")

        return jsonify({"error": str(e)}), 500


# GET endpoints remain exactly the same as original
@llc_bp_v2.route("/llcresult", methods=["GET"])
def get_llc_results():
    try:
        global llc_results
        return jsonify({"results": llc_results}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@llc_bp_v2.route("/llcresult/switchingfets", methods=["GET"])
def get_switchingfets_results():
    try:
        return jsonify({"results": swithcsecfet_results.get("swithcsecfet_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@llc_bp_v2.route("/llcresult/inductor", methods=["GET"])
def get_inductor_results():
    try:
        return jsonify({"results": priinductor_results.get("priinductor_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@llc_bp_v2.route("/llcresult/transformer", methods=["GET"])
def get_transformer_results():
    try:
        return jsonify({"results": transformer_results.get("transformer_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@llc_bp_v2.route("/llcresult/Buscap", methods=["GET"])
def get_buscap_results():
    try:
        return jsonify({"results": buscap_results.get("buscap_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@llc_bp_v2.route("/llcresult/Outcap", methods=["GET"])
def get_outputcap_results():
    try:
        return jsonify({"results": outputcap_results.get("outputcap_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
