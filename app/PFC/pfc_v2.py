"""
PFC Blueprint v2 - Python-based simulation (No MATLAB)
Replaces MATLAB engine with pure Python implementation
"""

from flask import Blueprint, request, jsonify
import traceback
import numpy as np
import logging

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
            # Uzun listeleri kısalt
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

# Import Python simulation engine
from app.simulation.pfc.pfc_optimizer import PFCOptimizer

pfc_bp_v2 = Blueprint("pfc_v2", __name__)

# Global result cache (for frontend compatibility)
pfc_results = {}
pfc_inductor_results = {}
pfc_fet_results = {}
pfc_capacitor_results = {}
pfc_cmc_results = {}
pfc_lpfc_results = {}
pfc_heatsink_results = {}
pfc_buscap_results = {}


@pfc_bp_v2.route("/PFC", methods=["POST"])
@pfc_bp_v2.route("/optimizations", methods=["POST"])
def PFC_Organiser():
    """
    PFC Optimization endpoint - PYTHON VERSION (No MATLAB)

    This replaces the MATLAB engine call with pure Python simulation
    """
    try:
        data = request.get_json()
        if data is None:
            logger.error("JSON verisi alınamadı!")
            return jsonify({"error": "No data provided"}), 400

        logger.info("=" * 60)
        logger.info("PFC PYTHON OPTİMİZASYONU BAŞLADI")
        logger.info("=" * 60)

        # Frontend'den gelen tüm veriyi logla
        debug_print("FRONTEND'DEN GELEN VERİ", data, "cyan")

        # Seçilen parçaları özel olarak logla
        selected_components = {
            "selectedFets": data.get("selectedFets", []),
            "selectedLpfc": data.get("selectedLpfc", []),
            "selectedCmc": data.get("selectedCmc", []),
            "selectedBusCaps": data.get("selectedBusCaps", []),
            "selectedHeatsinks": data.get("selectedHeatsinks", []),
        }
        debug_print("SEÇİLEN PARÇALAR", selected_components, "green")

        # Select All parametrelerini logla
        select_all_params = {
            "AllSelectedFets": data.get("AllSelectedFets", "undefined"),
            "Select_All_PFCCores_by_Default": data.get("Select_All_PFCCores_by_Default", "undefined"),
            "selectedAllHeatsinksByDefault": data.get("selectedAllHeatsinksByDefault", "undefined"),
            "Select_All_CMChokes_by_Default": data.get("Select_All_CMChokes_by_Default", "undefined"),
            "Select_All_Buscaps_by_Default": data.get("Select_All_Buscaps_by_Default", "undefined"),
        }
        debug_print("SELECT ALL PARAMETRELERİ (0=Seçilenler, 1=Hepsi)", select_all_params, "magenta")

        # Uyarılar
        if not data.get("selectedFets"):
            logger.warning("⚠️ DİKKAT: selectedFets listesi boş!")
        if not data.get("selectedLpfc"):
            logger.warning("⚠️ DİKKAT: selectedLpfc listesi boş!")
        if not data.get("selectedBusCaps"):
            logger.warning("⚠️ DİKKAT: selectedBusCaps listesi boş!")

        # Initialize Python optimizer (replaces MATLAB engine)
        logger.info("PFCOptimizer başlatılıyor...")
        optimizer = PFCOptimizer()

        # Run optimization (replaces eng.PFC_Organiser_Function())
        logger.info("Optimizasyon çalıştırılıyor...")
        result = optimizer.run_optimization(data)

        print("Optimization completed successfully!")
        print(f"Best Efficiency: {result.get('BestTotalEfficiency', 0):.2f}%")
        print("=" * 60)

        # Extract waveform data
        t = result.get('t', [])
        i_L = result.get('i_L', [])

        # Format results to match MATLAB output structure
        global pfc_results, pfc_inductor_results, pfc_fet_results, pfc_capacitor_results

        # Format results to match frontend expected field names
        # Frontend uses: R_Efficiency, R_Volume, R_Cost, fsw_decided, L_decided, etc.
        pfc_results = {
            # Main metrics (frontend expected names)
            "R_Efficiency_res0": result.get("BestTotalEfficiency", 0),
            "R_Volume_res0": result.get("BestTotalVolume", 0),
            "R_Cost_res0": 50.0,  # Placeholder cost estimate
            "fsw_decided_res0": result.get("Bestfs", 0),  # Hz
            "L_decided_res0": result.get("BestL", 0),  # H
            "R_Power_Density_res0": result.get("BestPowerDensity", 0),
            "ConductionModeDecided_res0": 0,  # 0 = CCM

            # Component names (frontend expected names)
            "HFFET_Name_res0": result.get("BestFet_Name", "Uygun parça bulunamadı"),
            "LFFET_Name_res0": result.get("BestFet_Name", "Uygun parça bulunamadı"),  # Same FET for now
            "LPFC_Name_res0": result.get("BestInd_Name", "Uygun parça bulunamadı"),
            "CMC_Name_res0": result.get("BestCMC_Name", "Uygun parça bulunamadı"),
            "BUSCAP_Name_res0": result.get("BestCap_Name", "Uygun parça bulunamadı"),
            "HEATSINK_Name_res0": result.get("BestHeatsink_Name", "Uygun parça bulunamadı"),

            # Loss breakdown
            "HFFET_Loss_res0": result.get("BestFet_Loss", 0) / 2,
            "LFFET_Loss_res0": result.get("BestFet_Loss", 0) / 2,
            "LPFC_Loss_res0": result.get("BestInd_Loss", 0),
            "CMC_Loss_res0": 0.2,
            "BUSCAP_Loss_res0": 0.5,

            # Legacy field names for compatibility
            "BestFet_Loss_res0": result.get("BestFet_Loss", 0),
            "BestInd_Loss_res0": result.get("BestInd_Loss", 0),
            "BestCap_Loss_res0": 0.5,
            "BestTotalLoss_res0": result.get("BestTotalLoss", 0),
            "BestTotalEfficiency_res0": result.get("BestTotalEfficiency", 0),
            "BestTotalVolume_res0": result.get("BestTotalVolume", 0),
            "BestInd_Volume_res0": result.get("BestInd_Volume", 0),
            "BestFET_Volume_res0": 500,
            "BestPowerDensity_res0": result.get("BestPowerDensity", 0),
            "Bestfs_res0": result.get("Bestfs", 0),
            "BestL_res0": result.get("BestL", 0),
            "BestDeltaI_res0": result.get("BestDeltaI", 0),
            "BestN_res0": result.get("BestN", 0),
            "BestFet_Name_res0": result.get("BestFet_Name", "Uygun parça bulunamadı"),
            "BestFet_Total_res0": result.get("BestFet_Loss", 0),
            "BestFet_Conduction_res0": result.get("BestFet_Conduction", 0),
            "BestFet_Switching_res0": result.get("BestFet_Switching", 0),
            "BestFet_Gate_res0": result.get("BestFet_Gate", 0),
            "BestInd_Name_res0": result.get("BestInd_Name", "Uygun parça bulunamadı"),
            "BestInd_core_res0": result.get("BestInd_CoreLoss", 0),
            "BestInd_cu_res0": result.get("BestInd_CopperLoss", 0),
            "BestInd_Bmax_res0": result.get("BestInd_Bmax", 0),
            "BestHeatsink_Name_res0": result.get("BestHeatsink_Name", "Uygun parça bulunamadı"),
            "BestCap_Name_res0": result.get("BestCap_Name", "Uygun parça bulunamadı"),
            "BestCap_Value_res0": result.get("BestCap_Value", 0),
            "t": t,
            "i_L": i_L,
        }

        # FET results
        pfc_fet_results["pfc_fet_results"] = {
            "BestFet_Name_res0": result.get("BestFet_Name", "Uygun parça bulunamadı"),
            "fs_Best": result.get("Bestfs", 0),
            "BestFet_Total_res0": result.get("BestFet_Loss", 0),
            "BestFet_Conduction_res0": result.get("BestFet_Conduction", 0),
            "BestFet_Switching_res0": result.get("BestFet_Switching", 0),
            "BestFet_Gate_res0": result.get("BestFet_Gate", 0),
        }

        # Inductor results
        pfc_inductor_results["pfc_inductor_results"] = {
            "BestInd_Name_res0": result.get("BestInd_Name", "Uygun parça bulunamadı"),
            "BestL_res0": result.get("BestL", 0),
            "BestInd_Volume_res0": result.get("BestInd_Volume", 0),
            "BestInd_Bmax_res0": result.get("BestInd_Bmax", 0),
            "BestN_res0": result.get("BestN", 0),
            "BestInd_core_res0": result.get("BestInd_CoreLoss", 0),
            "BestInd_cu_res0": result.get("BestInd_CopperLoss", 0),
            "BestInd_Loss_res0": result.get("BestInd_Loss", 0),
            "i_L": i_L,
            "t": t,
        }

        # Capacitor results
        pfc_capacitor_results["pfc_capacitor_results"] = {
            "BestCap_Name_res0": result.get("BestCap_Name", "Uygun parça bulunamadı"),
            "BestCap_Value_res0": result.get("BestCap_Value", 0),
            "BestCap_Voltage_res0": result.get("BestCap_Voltage", 0),
        }

        # CMC (Common Mode Choke) results
        global pfc_cmc_results
        pfc_cmc_results["pfc_cmc_results"] = {
            "BestCMC_Name_res0": result.get("BestCMC_Name", "Uygun parça bulunamadı"),
            "BestCMC_Inductance_res0": result.get("BestCMC_Inductance", 10e-3),
            "BestCMC_Current_res0": result.get("BestCMC_Current", 10),
            "BestCMC_Volume_res0": result.get("BestCMC_Volume", 2000),
            "BestCMC_Loss_res0": result.get("BestCMC_Loss", 0.5),
        }

        # LPFC (PFC Inductor) results
        global pfc_lpfc_results
        pfc_lpfc_results["pfc_lpfc_results"] = {
            "BestLPFC_Name_res0": result.get("BestInd_Name", "Uygun parça bulunamadı"),
            "BestLPFC_Value_res0": result.get("BestL", 0),
            "BestLPFC_Volume_res0": result.get("BestInd_Volume", 0),
            "BestLPFC_CoreLoss_res0": result.get("BestInd_CoreLoss", 0),
            "BestLPFC_CopperLoss_res0": result.get("BestInd_CopperLoss", 0),
            "BestLPFC_TotalLoss_res0": result.get("BestInd_Loss", 0),
            "BestLPFC_Bmax_res0": result.get("BestInd_Bmax", 0),
            "BestLPFC_Turns_res0": result.get("BestN", 0),
            "i_L": i_L,
            "t": t,
        }

        # Heatsink results
        global pfc_heatsink_results
        pfc_heatsink_results["pfc_heatsink_results"] = {
            "BestHeatsink_Name_res0": result.get("BestHeatsink_Name", "Uygun parça bulunamadı"),
            "BestHeatsink_Rth_res0": result.get("BestHeatsink_Rth", 2.5),
            "BestHeatsink_Volume_res0": result.get("BestHeatsink_Volume", 5000),
            "BestHeatsink_Tj_res0": result.get("BestHeatsink_Tj", 85),
        }

        # Bus Capacitor results
        global pfc_buscap_results
        pfc_buscap_results["pfc_buscap_results"] = {
            "BestBusCap_Name_res0": result.get("BestCap_Name", "Uygun parça bulunamadı"),
            "BestBusCap_Value_res0": result.get("BestCap_Value", 0),
            "BestBusCap_Voltage_res0": result.get("BestCap_Voltage", 450),
            "BestBusCap_ESR_res0": result.get("BestCap_ESR", 0.1),
            "BestBusCap_RippleCurrent_res0": result.get("BestCap_RippleCurrent", 2),
            "BestBusCap_Volume_res0": result.get("BestCap_Volume", 3000),
            "BestBusCap_Loss_res0": result.get("BestCap_Loss", 0.3),
        }

        return jsonify({"message": "Success", "result": pfc_results}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "error": str(e)}), 500


# GET endpoints
@pfc_bp_v2.route("/pfcresult", methods=["GET"])
def get_pfc_results():
    try:
        global pfc_results
        return jsonify({"results": pfc_results}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/fet", methods=["GET"])
@pfc_bp_v2.route("/pfcresult/Fet", methods=["GET"])  # Frontend uses capital F
def get_fet_results():
    try:
        return jsonify({"results": pfc_fet_results.get("pfc_fet_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/inductor", methods=["GET"])
def get_inductor_results():
    try:
        return jsonify({"results": pfc_inductor_results.get("pfc_inductor_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/capacitor", methods=["GET"])
def get_capacitor_results():
    try:
        return jsonify({"results": pfc_capacitor_results.get("pfc_capacitor_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/cmcresult", methods=["GET"])
def get_cmc_results():
    """CMC (Common Mode Choke) results endpoint"""
    try:
        return jsonify({"results": pfc_cmc_results.get("pfc_cmc_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/lpfcresult", methods=["GET"])
def get_lpfc_results():
    """LPFC (PFC Inductor) results endpoint"""
    try:
        return jsonify({"results": pfc_lpfc_results.get("pfc_lpfc_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/heatsink", methods=["GET"])
def get_heatsink_results():
    """Heatsink results endpoint"""
    try:
        return jsonify({"results": pfc_heatsink_results.get("pfc_heatsink_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@pfc_bp_v2.route("/pfcresult/buscap", methods=["GET"])
def get_buscap_results():
    """Bus Capacitor results endpoint"""
    try:
        return jsonify({"results": pfc_buscap_results.get("pfc_buscap_results", {})}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
