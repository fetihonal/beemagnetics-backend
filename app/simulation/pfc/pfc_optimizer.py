"""
PFC Optimizer - Multi-objective optimization for PFC boost converter

Replaces MATLAB PFC optimization with pure Python implementation
Optimizes for: efficiency, volume, cost
"""

import numpy as np
import logging
from typing import Dict, List, Any, Tuple
from app.simulation.pfc.core_loss import PFCCoreLossCalculator
from app.simulation.pfc.switching_loss import PFCSwitchingLossCalculator
from app.simulation.pfc.capacitor_select import PFCCapacitorSelector
from app.simulation.pfc.thermal import ThermalCalculator
from app.data_loaders.component_db import get_component_db

# Logging yapılandırması
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


class PFCOptimizer:
    """
    PFC Boost Converter Optimizer

    Searches design space to find optimal component selection:
    - Inductance value
    - Switching frequency
    - FET selection
    - Core selection
    - Capacitor selection
    - Heatsink selection
    """

    def __init__(self):
        """Initialize optimizer with component databases"""
        db = get_component_db()
        self.all_fets = db.load_fets()
        self.all_cores = db.load_cores(core_type="inductor")
        self.all_capacitors = db.load_capacitors()
        self.all_heatsinks = db.load_heatsinks()

        logger.info(f"Veritabanından yüklenen parçalar:")
        logger.info(f"  - FET'ler: {len(self.all_fets)} adet")
        logger.info(f"  - Core'lar: {len(self.all_cores)} adet")
        logger.info(f"  - Kapasitörler: {len(self.all_capacitors)} adet")
        logger.info(f"  - Heatsink'ler: {len(self.all_heatsinks)} adet")

    def _filter_components(self, input_params: Dict[str, Any]) -> Dict[str, List]:
        """
        Frontend seçimlerine göre parçaları filtrele

        Args:
            input_params: Frontend'den gelen parametreler

        Returns:
            Filtrelenmiş parça listeleri
        """
        # Select All parametrelerini al (0 = seçilenler, 1 = hepsi)
        all_fets_flag = input_params.get("AllSelectedFets", 0)
        all_cores_flag = input_params.get("Select_All_PFCCores_by_Default", 0)
        all_caps_flag = input_params.get("Select_All_Buscaps_by_Default", 0)
        all_heatsinks_flag = input_params.get("selectedAllHeatsinksByDefault", 0)

        # Frontend'den seçilen parça listelerini al
        selected_fets = input_params.get("selectedFets", [])
        selected_lpfc = input_params.get("selectedLpfc", [])
        selected_buscaps = input_params.get("selectedBusCaps", [])
        selected_heatsinks = input_params.get("selectedHeatsinks", [])

        debug_print("PARÇA FİLTRELEME PARAMETRELERİ", {
            "AllSelectedFets": all_fets_flag,
            "Select_All_PFCCores_by_Default": all_cores_flag,
            "Select_All_Buscaps_by_Default": all_caps_flag,
            "selectedAllHeatsinksByDefault": all_heatsinks_flag,
            "selectedFets": selected_fets,
            "selectedLpfc": selected_lpfc,
            "selectedBusCaps": selected_buscaps,
            "selectedHeatsinks": selected_heatsinks,
        }, "yellow")

        # FET filtreleme
        if all_fets_flag == 1 or not selected_fets:
            fets = self.all_fets
            if all_fets_flag == 1:
                logger.warning("⚠️ AllSelectedFets=1 → TÜM FET'ler kullanılıyor!")
            elif not selected_fets:
                logger.warning("⚠️ selectedFets boş → TÜM FET'ler kullanılıyor!")
        else:
            # Seçilen FET'leri filtrele
            fets = [f for f in self.all_fets if f.get("part_number") in selected_fets]
            if not fets:
                logger.warning(f"⚠️ Seçilen FET'ler veritabanında bulunamadı: {selected_fets}")
                fets = self.all_fets
            else:
                logger.info(f"✅ {len(fets)} FET seçildi: {[f.get('part_number') for f in fets]}")

        # Core filtreleme
        if all_cores_flag == 1 or not selected_lpfc:
            cores = self.all_cores
            if all_cores_flag == 1:
                logger.warning("⚠️ Select_All_PFCCores_by_Default=1 → TÜM Core'lar kullanılıyor!")
            elif not selected_lpfc:
                logger.warning("⚠️ selectedLpfc boş → TÜM Core'lar kullanılıyor!")
        else:
            # Seçilen Core'ları filtrele
            cores = [c for c in self.all_cores if c.get("name") in selected_lpfc]
            if not cores:
                logger.warning(f"⚠️ Seçilen Core'lar veritabanında bulunamadı: {selected_lpfc}")
                cores = self.all_cores
            else:
                logger.info(f"✅ {len(cores)} Core seçildi: {[c.get('name') for c in cores]}")

        # Kapasitör filtreleme
        if all_caps_flag == 1 or not selected_buscaps:
            capacitors = self.all_capacitors
            if all_caps_flag == 1:
                logger.warning("⚠️ Select_All_Buscaps_by_Default=1 → TÜM Kapasitörler kullanılıyor!")
            elif not selected_buscaps:
                logger.warning("⚠️ selectedBusCaps boş → TÜM Kapasitörler kullanılıyor!")
        else:
            # Seçilen Kapasitörleri filtrele
            capacitors = [c for c in self.all_capacitors if c.get("part_number") in selected_buscaps]
            if not capacitors:
                logger.warning(f"⚠️ Seçilen Kapasitörler veritabanında bulunamadı: {selected_buscaps}")
                capacitors = self.all_capacitors
            else:
                logger.info(f"✅ {len(capacitors)} Kapasitör seçildi")

        # Heatsink filtreleme
        if all_heatsinks_flag == 1 or not selected_heatsinks:
            heatsinks = self.all_heatsinks
            if all_heatsinks_flag == 1:
                logger.warning("⚠️ selectedAllHeatsinksByDefault=1 → TÜM Heatsink'ler kullanılıyor!")
            elif not selected_heatsinks:
                logger.warning("⚠️ selectedHeatsinks boş → TÜM Heatsink'ler kullanılıyor!")
        else:
            # Seçilen Heatsink'leri filtrele
            heatsinks = [h for h in self.all_heatsinks if h.get("name") in selected_heatsinks]
            if not heatsinks:
                logger.warning(f"⚠️ Seçilen Heatsink'ler veritabanında bulunamadı: {selected_heatsinks}")
                heatsinks = self.all_heatsinks
            else:
                logger.info(f"✅ {len(heatsinks)} Heatsink seçildi")

        debug_print("FİLTRELENMİŞ PARÇA SAYILARI", {
            "FET'ler": f"{len(fets)} / {len(self.all_fets)}",
            "Core'lar": f"{len(cores)} / {len(self.all_cores)}",
            "Kapasitörler": f"{len(capacitors)} / {len(self.all_capacitors)}",
            "Heatsink'ler": f"{len(heatsinks)} / {len(self.all_heatsinks)}",
        }, "green")

        return {
            "fets": fets,
            "cores": cores,
            "capacitors": capacitors,
            "heatsinks": heatsinks
        }

    def run_optimization(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run multi-objective PFC optimization

        Args:
            input_params: Dictionary from frontend containing:
                - vin / V_in_RMS: Input voltage RMS (V)
                - outVol / V_out: Output voltage (V)
                - outPow / P_out: Output power (W)
                - Tamb_input / T_amb: Ambient temperature (°C)
                - mode1, fixedValue1, min1, max1, step1: Switching frequency (kHz)
                - mode2, fixedValue2, min2, max2, step2: Inductance (µH)
                - efficiency: Expected efficiency (%)

        Returns:
            Dictionary with best design parameters and performance metrics
        """

        # Helper function to safely parse values (handles "User input needed" strings)
        def safe_float(key, default, alt_keys=None):
            """Safely extract float value from input params"""
            val = input_params.get(key)

            # Try alternate keys if primary key not found
            if val is None and alt_keys:
                for alt_key in alt_keys:
                    val = input_params.get(alt_key)
                    if val is not None:
                        break

            if val is None:
                return default
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                val = val.strip()
                # Handle "User input needed" and similar strings
                if not val or val.lower() in ['user input needed', 'nan', 'null', 'none', '']:
                    return default
                val = val.replace(',', '.')  # Handle Turkish decimal separator
                try:
                    return float(val)
                except ValueError:
                    return default
            return default

        # Extract input parameters with frontend name mapping
        # Frontend sends: vin, outVol, outPow, Tamb_input
        # Backend expects: V_in_RMS, V_out, P_out, T_amb
        V_in_RMS = safe_float("vin", 230, ["V_in_RMS", "V_in"])
        V_out = safe_float("outVol", 400, ["V_out"])
        P_out = safe_float("outPow", 500, ["P_out"])
        T_amb = safe_float("Tamb_input", 25, ["T_amb"])

        # Calculate V_in_min and V_in_max from V_in_RMS (±15% typical range)
        V_in_min = V_in_RMS * 0.85
        V_in_max = V_in_RMS * 1.15

        # Efficiency from frontend (percentage to decimal)
        efficiency_pct = safe_float("efficiency", 96)
        eta_eff = efficiency_pct / 100 if efficiency_pct > 1 else efficiency_pct

        T_hold = safe_float("T_hold", 20)  # ms

        # Switching frequency range (frontend sends kHz, convert to Hz)
        mode1 = safe_float("mode1", 1)  # 1 = Fixed, 0 = Sweep
        if mode1 == 1:
            # Fixed mode - use fixedValue1 (kHz → Hz)
            f_sw_fixed = safe_float("fixedValue1", 45) * 1000  # kHz to Hz
            f_sw_range = [f_sw_fixed]
        else:
            # Sweep mode (kHz → Hz)
            f_min = safe_float("min1", 45) * 1000
            f_max = safe_float("max1", 90) * 1000
            f_step = safe_float("step1", 5) * 1000
            f_sw_range = np.arange(f_min, f_max + f_step, f_step)

        # Inductance range (frontend sends µH, convert to H)
        mode2 = safe_float("mode2", 1)  # 1 = Fixed, 0 = Sweep
        if mode2 == 1:
            # Fixed mode - use fixedValue2 (µH → H)
            L_fixed = safe_float("fixedValue2", 100) * 1e-6  # µH to H
            L_range = np.array([L_fixed])
        else:
            # Sweep mode (µH → H)
            L_min = safe_float("min2", 100) * 1e-6
            L_max = safe_float("max2", 300) * 1e-6
            L_step = safe_float("step2", 10) * 1e-6
            L_range = np.arange(L_min, L_max + L_step, L_step)

        # Parçaları frontend seçimlerine göre filtrele
        filtered = self._filter_components(input_params)
        fets = filtered["fets"]
        cores = filtered["cores"]
        self.filtered_capacitors = filtered["capacitors"]
        self.filtered_heatsinks = filtered["heatsinks"]

        # Best design tracking
        best_design = None
        best_score = float('inf')  # Lower is better

        debug_print("OPTİMİZASYON ARAMA ALANI", {
            "Frekanslar": f"{len(f_sw_range)} seçenek ({f_sw_range[0]/1000:.0f}kHz - {f_sw_range[-1]/1000:.0f}kHz)" if len(f_sw_range) > 1 else f"{f_sw_range[0]/1000:.0f}kHz (sabit)",
            "İndüktanslar": f"{len(L_range)} seçenek ({L_range[0]*1e6:.0f}µH - {L_range[-1]*1e6:.0f}µH)" if len(L_range) > 1 else f"{L_range[0]*1e6:.0f}µH (sabit)",
            "FET'ler": f"{len(fets)} adet",
            "Core'lar": f"{len(cores)} adet",
            "Toplam kombinasyon": f"{len(f_sw_range) * len(L_range) * len(fets) * len(cores)} adet"
        }, "cyan")

        print(f"🔍 PFC tasarım alanı taranıyor:")
        print(f"   Frekanslar: {len(f_sw_range)} seçenek")
        print(f"   İndüktanslar: {len(L_range)} seçenek")
        print(f"   FET'ler: {len(fets)} seçenek")
        print(f"   Core'lar: {len(cores)} seçenek")

        valid_designs_count = 0
        skipped_voltage = 0
        skipped_turns = 0
        skipped_flux = 0
        skipped_efficiency = 0

        # Iterate through design space
        for f_sw in f_sw_range:
            for L in L_range:
                # Calculate inductor currents
                currents = PFCCoreLossCalculator.calculate_inductor_currents(
                    P_out, eta_eff, V_in_RMS
                )

                delta_I = PFCCoreLossCalculator.calculate_ripple_current(
                    V_in_RMS, V_out, f_sw, L
                )

                # Switch current calculations
                I_sw_RMS = currents["I_in_RMS"]
                I_sw_avg = P_out / (eta_eff * V_in_RMS)

                # Try each FET
                for fet in fets:
                    # Check if FET voltage rating is sufficient
                    if fet["V_dss"] < V_out * 1.2:  # 20% margin
                        skipped_voltage += 1
                        continue

                    # Calculate FET losses
                    fet_losses = PFCSwitchingLossCalculator.calculate_total_fet_loss(
                        m_FET=1,
                        I_sw_RMS=I_sw_RMS,
                        I_sw_avg=I_sw_avg,
                        V_ds=V_out,
                        f_sw=f_sw,
                        fet_params=fet,
                        V_gs=12
                    )

                    # Try each core
                    for core in cores:
                        # Calculate number of turns
                        N = PFCCoreLossCalculator.calculate_turns(
                            L=L,
                            I_peak=currents["I_lf_PEAK"] + delta_I/2,
                            B_max=0.3,  # Conservative flux density
                            Ae=core["Ae"]
                        )

                        if N > 200:  # Too many turns
                            skipped_turns += 1
                            continue

                        # Calculate inductor losses
                        inductor_losses = PFCCoreLossCalculator.calculate_total_inductor_loss(
                            V_in_RMS=V_in_RMS,
                            V_out=V_out,
                            P_out=P_out,
                            f_sw=f_sw,
                            eta_eff=eta_eff,
                            L=L,
                            core=core,
                            N=N,
                            wire_diameter=1.0  # Will optimize later
                        )

                        # Check if flux density is acceptable
                        if inductor_losses["B_max"] > core.get("B_sat", 0.5) * 0.8:
                            skipped_flux += 1
                            continue

                        # Calculate total losses
                        total_loss = fet_losses["P_total"] + inductor_losses["P_total"]

                        # Calculate efficiency
                        P_in = P_out + total_loss
                        efficiency = (P_out / P_in) * 100 if P_in > 0 else 0

                        # Skip if efficiency is too low
                        if efficiency < 85:
                            skipped_efficiency += 1
                            continue

                        valid_designs_count += 1

                        # Calculate volume (rough estimate)
                        fet_volume = 500  # mm³, typical TO-220
                        # Core volume: JSON uses "Ve" in m³, convert to mm³
                        core_ve = core.get("Ve", core.get("volume", 5e-6))
                        if core_ve < 1:  # If in m³, convert to mm³
                            core_volume = core_ve * 1e9
                        else:
                            core_volume = core_ve
                        total_volume = fet_volume + core_volume

                        # Multi-objective score
                        # Weight: 60% efficiency, 30% volume, 10% cost
                        efficiency_score = (100 - efficiency) * 0.6
                        volume_score = (total_volume / 10000) * 0.3
                        cost_score = 0.1  # Placeholder

                        score = efficiency_score + volume_score + cost_score

                        # Update best design
                        if score < best_score:
                            best_score = score
                            best_design = {
                                "f_sw": f_sw,
                                "L": L,
                                "N": N,
                                "delta_I": delta_I,
                                "fet": fet,
                                "core": core,
                                "fet_losses": fet_losses,
                                "inductor_losses": inductor_losses,
                                "total_loss": total_loss,
                                "efficiency": efficiency,
                                "total_volume": total_volume,
                                "currents": currents
                            }

        # Tarama istatistiklerini yazdır
        debug_print("TARAMA İSTATİSTİKLERİ", {
            "Geçerli tasarım sayısı": valid_designs_count,
            "Atlanan (düşük gerilim)": skipped_voltage,
            "Atlanan (çok fazla sarım)": skipped_turns,
            "Atlanan (yüksek B_max)": skipped_flux,
            "Atlanan (düşük verim)": skipped_efficiency,
        }, "magenta")

        if best_design is None:
            logger.error("❌ Hiçbir geçerli tasarım bulunamadı!")
            debug_print("HATA: GEÇERLİ TASARIM YOK", {
                "Sebepler": [
                    f"Gerilim marjı karşılanmadı: {skipped_voltage}",
                    f"Sarım sayısı >200: {skipped_turns}",
                    f"B_max aşıldı: {skipped_flux}",
                    f"Verim <%85: {skipped_efficiency}",
                ],
                "Öneri": "Tasarım kısıtlamalarını gevşetmeyi deneyin"
            }, "red")
            raise ValueError("No valid PFC design found. Try relaxing constraints.")

        # Select capacitors
        C_bus = PFCCapacitorSelector.calculate_holdup_capacitance(
            P_o=P_out,
            T_hold=T_hold / 1000,  # Convert ms to s
            V_out=V_out,
            V_out_MIN=V_out * 0.9
        )

        I_rms_cap = PFCCapacitorSelector.calculate_capacitor_rms_current(
            P_out=P_out,
            V_out=V_out,
            f_sw=best_design["f_sw"]
        )

        # Find suitable capacitor
        best_cap = self._select_capacitor(C_bus, V_out, I_rms_cap)

        # Thermal calculations
        R_th_ja = ThermalCalculator.calculate_thermal_resistance_ja(
            P_total=best_design["fet_losses"]["P_total"],
            T_j_max=150,
            T_amb=T_amb
        )

        best_heatsink = self._select_heatsink(R_th_ja)

        # Format output (compatible with frontend API)
        result = self._format_result(best_design, best_cap, best_heatsink, input_params)

        # En iyi tasarım detaylarını yazdır
        debug_print("EN İYİ TASARIM BULUNDU", {
            "FET": best_design['fet'].get('part_number', 'Unknown'),
            "Core": best_design['core'].get('name', 'Unknown'),
            "Frekans": f"{best_design['f_sw']/1000:.0f} kHz",
            "İndüktans": f"{best_design['L']*1e6:.0f} µH",
            "Sarım sayısı": f"{best_design['N']:.0f}",
            "Verimlilik": f"{best_design['efficiency']:.2f}%",
            "Toplam kayıp": f"{best_design['total_loss']:.2f} W",
            "FET kaybı": f"{best_design['fet_losses']['P_total']:.2f} W",
            "İndüktör kaybı": f"{best_design['inductor_losses']['P_total']:.2f} W",
            "Toplam hacim": f"{best_design['total_volume']:.0f} mm³",
        }, "green")

        debug_print("SEÇİLEN PARÇALAR", {
            "FET": best_design['fet'].get('part_number', 'Unknown'),
            "Core": best_design['core'].get('name', 'Unknown'),
            "Kapasitör": best_cap.get('part_number', 'Unknown'),
            "Heatsink": best_heatsink.get('name', 'Unknown'),
        }, "cyan")

        print(f"✅ PFC Optimizasyonu tamamlandı!")
        print(f"   Verimlilik: {best_design['efficiency']:.2f}%")
        print(f"   Toplam kayıp: {best_design['total_loss']:.2f}W")
        print(f"   İndüktör: {best_design['L']*1e6:.0f}µH @ {best_design['f_sw']/1000:.0f}kHz")

        return result

    def _select_capacitor(self, C_min: float, V_rated: float, I_rms: float) -> Dict:
        """Select best capacitor from filtered database"""
        # Filtrelenmiş kapasitör listesini kullan (varsa)
        cap_list = getattr(self, 'filtered_capacitors', self.all_capacitors)

        logger.info(f"Kapasitör seçimi: C_min={C_min*1e6:.1f}µF, V_rated={V_rated:.0f}V")
        logger.info(f"  Aday kapasitör sayısı: {len(cap_list)}")

        suitable_caps = [
            cap for cap in cap_list
            if cap["capacitance"] >= C_min and cap["voltage"] >= V_rated * 1.2
        ]

        logger.info(f"  Uygun kapasitör sayısı: {len(suitable_caps)}")

        if not suitable_caps:
            logger.warning("⚠️ Uygun kapasitör bulunamadı!")
            return {
                "part_number": "Uygun parça bulunamadı",
                "capacitance": 0,
                "voltage": 0,
                "ESR": 0,
                "I_ripple_rated": 0
            }

        # Select smallest suitable capacitor
        selected = min(suitable_caps, key=lambda c: c["capacitance"])
        logger.info(f"  ✅ Seçilen kapasitör: {selected.get('part_number', 'Unknown')}")
        return selected

    def _select_heatsink(self, R_th_required: float) -> Dict:
        """Select best heatsink from filtered database"""
        # Filtrelenmiş heatsink listesini kullan (varsa)
        heatsink_list = getattr(self, 'filtered_heatsinks', self.all_heatsinks)

        logger.info(f"Heatsink seçimi: R_th_required={R_th_required:.2f} °C/W")
        logger.info(f"  Aday heatsink sayısı: {len(heatsink_list)}")

        if len(heatsink_list) > 0:
            # En küçük termal dirençli heatsink'i seç
            selected = min(heatsink_list, key=lambda h: h.get("R_th_sa", 999))
            logger.info(f"  ✅ Seçilen heatsink: {selected.get('name', 'Unknown')}")
            return selected

        logger.warning("⚠️ Uygun heatsink bulunamadı!")
        return {
            "name": "Uygun parça bulunamadı",
            "X": 0,
            "Y": 0,
            "R_th_sa": 0
        }

    def _format_result(self, design: Dict, capacitor: Dict,
                      heatsink: Dict, input_params: Dict) -> Dict[str, Any]:
        """Format optimization result for API response"""

        # Generate waveforms (simplified)
        T = 1 / design["f_sw"]
        t = np.linspace(0, 2*T, 200)

        # Inductor current waveform (triangular approximation)
        I_avg = design["currents"]["I_in_RMS"]
        I_ripple = design["delta_I"]
        i_L = I_avg + (I_ripple/2) * np.sin(2*np.pi*design["f_sw"]*t)

        return {
            # Overall metrics
            "BestTotalEfficiency": design["efficiency"],
            "BestTotalLoss": design["total_loss"],
            "BestTotalVolume": design["total_volume"],
            "BestPowerDensity": input_params.get("P_out", 0) / (design["total_volume"] / 1000),

            # Design parameters
            "BestL": design["L"],
            "BestN": design["N"],
            "Bestfs": design["f_sw"],
            "BestDeltaI": design["delta_I"],

            # FET results
            "BestFet_Name": design["fet"]["part_number"],
            "BestFet_Loss": design["fet_losses"]["P_total"],
            "BestFet_Conduction": design["fet_losses"]["P_conduction"],
            "BestFet_Switching": design["fet_losses"]["P_switching"],
            "BestFet_Gate": design["fet_losses"]["P_gate"],

            # Inductor results
            "BestInd_Name": design["core"]["name"],
            "BestInd_Loss": design["inductor_losses"]["P_total"],
            "BestInd_CoreLoss": design["inductor_losses"]["P_core"],
            "BestInd_CopperLoss": design["inductor_losses"]["P_copper"],
            "BestInd_Bmax": design["inductor_losses"]["B_max"],
            "BestInd_Volume": design["total_volume"] - 500,  # Total - FET volume

            # Capacitor results
            "BestCap_Name": capacitor["part_number"],
            "BestCap_Value": capacitor["capacitance"],
            "BestCap_Voltage": capacitor["voltage"],

            # Heatsink results
            "BestHeatsink_Name": heatsink["name"],

            # Waveforms
            "t": t.tolist(),
            "i_L": i_L.tolist(),
        }
