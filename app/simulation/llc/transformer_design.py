"""
LLC Transformer Design Calculator
Based on Area Product Method
"""

import numpy as np
from typing import Dict, List, Optional


class TransformerDesign:
    """LLC Transformer Design and Selection"""

    @staticmethod
    def calculate_skin_depth(f_sw: float, conductivity: float = 5.96e7,
                            mu_0: float = 4*np.pi*1e-7) -> float:
        """
        Skin depth calculation

        δ = 1 / sqrt(π * f_s * μ_0 * σ)

        At high frequencies, current concentrates near the conductor surface,
        increasing effective resistance. Skin depth is the depth at which
        current density drops to 1/e (~37%) of surface value.

        Args:
            f_sw: Switching frequency (Hz)
            conductivity: Copper conductivity (S/m), default 5.96e7 at 20°C
            mu_0: Permeability of free space (H/m)

        Returns:
            Skin depth (m)
        """
        delta = 1 / np.sqrt(np.pi * f_sw * mu_0 * conductivity)
        return delta

    @staticmethod
    def calculate_ac_resistance_round_wire(R_dc: float, wire_radius: float,
                                          skin_depth: float) -> float:
        """
        AC resistance for round wire with skin effect

        R_ac = R_dc * [1 + (r/δ)⁴ / (48 + 0.8 * (r/δ)⁴)]

        This formula accounts for skin effect and proximity effect in round wires.
        At high frequencies, AC resistance can be 2-10x higher than DC resistance!

        Args:
            R_dc: DC resistance (Ω)
            wire_radius: Wire radius (m)
            skin_depth: Skin depth at frequency (m)

        Returns:
            AC resistance (Ω)
        """
        ratio = wire_radius / skin_depth
        ratio4 = ratio ** 4

        R_ac = R_dc * (1 + ratio4 / (48 + 0.8 * ratio4))
        return R_ac

    @staticmethod
    def calculate_optimal_wire_diameter(f_sw: float, f_0: float, p: int,
                                       skin_depth: float) -> Dict[str, float]:
        """
        Optimal wire diameter for minimum AC loss

        ψ = (5 * p² - 1) / 15
        Δ_opt = ⁴√((4 * (f_sw/(2*f_0))²) / ψ)
        d_opt = Δ_opt * δ

        Args:
            f_sw: Switching frequency (Hz)
            f_0: Resonant frequency (Hz)
            p: Number of winding layers
            skin_depth: Skin depth (m)

        Returns:
            Dict with d_opt (m), Delta_opt, psi
        """
        psi = (5 * p**2 - 1) / 15

        if psi <= 0:
            psi = 1  # Prevent division by zero

        freq_ratio = f_sw / (2 * f_0)
        Delta_opt = ((4 * freq_ratio**2) / psi) ** (1/4)

        d_opt = Delta_opt * skin_depth

        return {
            'd_opt': d_opt,
            'd_opt_mm': d_opt * 1000,  # Convert to mm
            'Delta_opt': Delta_opt,
            'psi': psi
        }

    @staticmethod
    def calculate_thermal_factor_Kt(h_c: float = 10.0, k_a: float = 4.0,
                                   rho_w: float = 1.72e-8, k_w: float = 400.0) -> float:
        """
        Thermal factor K_t for transformer design

        K_t = sqrt(h_c * k_a / (ρ_w * k_w))

        NOTE: Kt2 = K_t² (as specified in MATLAB formulas)

        Args:
            h_c: Convection coefficient (W/m²·K), default 10 (natural convection)
            k_a: Core thermal conductivity (W/m·K), default 4 (ferrite)
            rho_w: Wire resistivity (Ω·m), default 1.72e-8 (copper at 20°C)
            k_w: Wire thermal conductivity (W/m·K), default 400 (copper)

        Returns:
            K_t thermal factor
        """
        K_t = np.sqrt(h_c * k_a / (rho_w * k_w))
        return K_t

    @staticmethod
    def calculate_current_density_J0(K_t: float, delta_T: float,
                                    k_u: float, gamma: float,
                                    A_p: float) -> float:
        """
        Optimal current density based on thermal constraints

        J_0 = K_t * sqrt(ΔT / (k_u(1+γ)) * A_p^(-1/8))

        This optimizes wire gauge based on allowable temperature rise.

        Args:
            K_t: Thermal factor
            delta_T: Allowable temperature rise (°C)
            k_u: Window utilization factor (0.2-0.5 typical)
            gamma: Winding ratio (N_sec*I_sec)/(N_pri*I_pri)
            A_p: Area product (m⁴)

        Returns:
            Current density (A/m²)
        """
        J_0 = K_t * np.sqrt(delta_T / (k_u * (1 + gamma)) * (A_p ** (-1/8)))
        return J_0

    @staticmethod
    def calculate_turns_ratio(V_in_nom: float, V_out: float, M_nom: float = 1.0) -> float:
        """
        Calculate transformer turns ratio

        n = N_primary / N_secondary = (V_in_nom / M_nom) / V_out

        Args:
            V_in_nom: Nominal input voltage (V)
            V_out: Output voltage (V)
            M_nom: Nominal voltage gain (default 1.0 for operation at resonance)

        Returns:
            Turns ratio n
        """
        if V_out <= 0:
            return float('inf')

        n = (V_in_nom / M_nom) / V_out
        return n

    @staticmethod
    def calculate_magnetizing_inductance(Lr: float, Ln: float) -> float:
        """
        Calculate magnetizing inductance

        Lm = Ln * Lr

        Args:
            Lr: Resonant (leakage) inductance (H)
            Ln: Inductance ratio

        Returns:
            Magnetizing inductance (H)
        """
        return Ln * Lr

    @staticmethod
    def calculate_area_product(P_out: float, B_max: float, J_max: float,
                               ku: float, f_sw: float, efficiency: float = 0.95,
                               K_f: float = 4.0) -> float:
        """
        Calculate required core area product

        AP = P_out / (K_f * K_u * B_max * J_max * f_sw * η) * 10^4

        where K_f is the waveform factor:
        - K_f = 4.0 for square wave (LLC, full-bridge)
        - K_f = 4.44 for sine wave

        Args:
            P_out: Output power (W)
            B_max: Maximum flux density (T)
            J_max: Maximum current density (A/m²)
            ku: Window utilization factor (0.2-0.5 typical)
            f_sw: Switching frequency (Hz)
            efficiency: Converter efficiency (0-1)
            K_f: Waveform factor (4.0 for square wave, 4.44 for sine)

        Returns:
            Area product AP (cm⁴)
        """
        if B_max <= 0 or J_max <= 0 or f_sw <= 0 or K_f <= 0:
            return float('inf')

        # Area product formula with K_f factor
        # AP = P_out / (K_f * K_u * B_max * J_max * f_sw * η)
        # Result in m⁴, multiply by 1e8 to convert to cm⁴
        AP = P_out / (K_f * ku * B_max * J_max * f_sw * efficiency)

        # Convert m⁴ to cm⁴ (1 m⁴ = 10^8 cm⁴)
        AP_cm4 = AP * 1e8

        return AP_cm4

    @staticmethod
    def calculate_primary_turns(Lm: float, I_mag_peak: float, B_max: float,
                               Ae: float) -> int:
        """
        Calculate number of primary turns

        From L = N² * AL and B = (N * I) / (l_m / μ * Ae)

        N_p = (Lm * I_mag_peak) / (B_max * Ae)

        Args:
            Lm: Magnetizing inductance (H)
            I_mag_peak: Peak magnetizing current (A)
            B_max: Maximum flux density (T)
            Ae: Core effective area (m²)

        Returns:
            Number of primary turns
        """
        if B_max <= 0 or Ae <= 0:
            return 0

        N_p = (Lm * I_mag_peak) / (B_max * Ae)
        return int(np.ceil(N_p))

    @staticmethod
    def calculate_wire_gauge(I_RMS: float, J_max: float) -> Dict[str, float]:
        """
        Calculate required wire gauge

        A_wire = I_RMS / J_max
        d_wire = 2 * sqrt(A_wire / π)

        Args:
            I_RMS: RMS current (A)
            J_max: Maximum current density (A/m²)

        Returns:
            Dictionary with wire_area, wire_diameter, AWG_approx
        """
        if J_max <= 0:
            return {'wire_area': 0, 'wire_diameter': 0, 'AWG_approx': 0}

        # Wire area (m²)
        A_wire = I_RMS / J_max

        # Wire diameter (m)
        d_wire = 2 * np.sqrt(A_wire / np.pi)

        # Approximate AWG (rough conversion)
        # AWG = -19.93 * log10(d_mm) + 9.73
        d_mm = d_wire * 1000
        if d_mm > 0:
            AWG_approx = -19.93 * np.log10(d_mm) + 9.73
        else:
            AWG_approx = 50

        return {
            'wire_area': A_wire,
            'wire_diameter': d_wire,
            'wire_diameter_mm': d_mm,
            'AWG_approx': round(AWG_approx)
        }

    @staticmethod
    def calculate_winding_resistance(N: int, MLT: float, wire_area: float,
                                    rho_copper: float = 1.72e-8) -> float:
        """
        Calculate winding resistance

        R = (rho * N * MLT) / A_wire

        Args:
            N: Number of turns
            MLT: Mean Length per Turn (m)
            wire_area: Wire cross-sectional area (m²)
            rho_copper: Copper resistivity (Ω·m), default at 25°C

        Returns:
            Resistance (Ω)
        """
        if wire_area <= 0:
            return float('inf')

        l_wire = N * MLT
        R = (rho_copper * l_wire) / wire_area

        return R

    @staticmethod
    def calculate_copper_loss(I_RMS: float, R: float) -> float:
        """
        Calculate copper loss

        P_cu = I_RMS² * R

        Args:
            I_RMS: RMS current (A)
            R: Winding resistance (Ω)

        Returns:
            Copper loss (W)
        """
        return I_RMS**2 * R

    @staticmethod
    def calculate_core_loss_steinmetz(f_sw: float, B_peak: float, V_core: float,
                                     k: float, alpha: float, beta: float) -> float:
        """
        Calculate core loss using Steinmetz equation

        P_v = k * f^α * B^β (W/m³)
        P_core = P_v * V_core

        Args:
            f_sw: Switching frequency (Hz)
            B_peak: Peak flux density (T)
            V_core: Core volume (m³)
            k: Steinmetz coefficient
            alpha: Frequency exponent
            beta: Flux density exponent

        Returns:
            Core loss (W)
        """
        # Steinmetz equation
        P_v = k * (f_sw ** alpha) * (B_peak ** beta)  # W/m³

        # Total core loss
        P_core = P_v * V_core

        return P_core

    @staticmethod
    def select_core(AP_required: float, core_db: List[Dict]) -> Optional[Dict]:
        """
        Select appropriate core from database

        Args:
            AP_required: Required area product (cm⁴)
            core_db: List of available cores

        Returns:
            Selected core dictionary, or None if no suitable core
        """
        # Filter cores with sufficient area product
        # AP = Ae * Aw (cm⁴)
        suitable_cores = []

        for core in core_db:
            Ae = core.get('Ae', 0)  # cm²
            Aw = core.get('Aw', 0)  # cm²
            AP = Ae * Aw

            if AP >= AP_required:
                core_copy = core.copy()
                core_copy['AP'] = AP
                suitable_cores.append(core_copy)

        if not suitable_cores:
            return None

        # Select smallest suitable core (minimum volume)
        best_core = min(suitable_cores, key=lambda x: x.get('volume', float('inf')))

        return best_core

    def design_complete_transformer(self, params: Dict) -> Dict:
        """
        Complete transformer design

        Args:
            params: Design parameters

        Returns:
            Complete transformer design
        """
        # Extract parameters
        V_in_nom = params['V_in_nom']
        V_out = params['V_out']
        P_out = params['P_out']
        Lr = params['Lr']
        Lm = params['Lm']
        f_sw = params['f_sw']
        I_mag_peak = params['I_mag_peak']

        B_max = params.get('B_max', 0.3)  # T
        J_max = params.get('J_max', 5e6)  # A/m² (5 A/mm²)
        ku = params.get('ku', 0.4)
        efficiency = params.get('efficiency', 0.95)

        core_db = params.get('core_db', [])

        # Calculate turns ratio
        M_nom = params.get('M_nom', 1.0)
        n = self.calculate_turns_ratio(V_in_nom, V_out, M_nom)

        # Calculate area product
        AP_required = self.calculate_area_product(P_out, B_max, J_max, ku, f_sw, efficiency)

        # Select core
        core = self.select_core(AP_required, core_db)

        if core is None:
            return {
                'error': 'No suitable core found',
                'AP_required': AP_required
            }

        Ae = core['Ae'] * 1e-4  # cm² to m²
        Aw = core['Aw'] * 1e-4  # cm² to m²
        V_core = core.get('volume', 0) * 1e-9  # mm³ to m³
        MLT = core.get('MLT', 0) * 1e-3  # mm to m

        # Calculate primary turns
        N_p = self.calculate_primary_turns(Lm, I_mag_peak, B_max, Ae)

        # Calculate secondary turns
        N_s = int(np.ceil(N_p / n))

        # Calculate wire gauges
        I_pri_RMS = params.get('I_pri_RMS', P_out / V_in_nom)
        I_sec_RMS = params.get('I_sec_RMS', P_out / V_out)

        wire_pri = self.calculate_wire_gauge(I_pri_RMS, J_max)
        wire_sec = self.calculate_wire_gauge(I_sec_RMS, J_max)

        # Calculate resistances
        R_pri = self.calculate_winding_resistance(N_p, MLT, wire_pri['wire_area'])
        R_sec = self.calculate_winding_resistance(N_s, MLT, wire_sec['wire_area'])

        # Calculate losses
        P_cu_pri = self.calculate_copper_loss(I_pri_RMS, R_pri)
        P_cu_sec = self.calculate_copper_loss(I_sec_RMS, R_sec)
        P_cu_total = P_cu_pri + P_cu_sec

        # Core loss (need Steinmetz parameters from core data)
        k = core.get('k', 0)
        alpha = core.get('alpha', 1.5)
        beta = core.get('beta', 2.5)

        B_peak = (I_mag_peak * Lm) / (N_p * Ae)
        P_core = self.calculate_core_loss_steinmetz(f_sw, B_peak, V_core, k, alpha, beta)

        # Total loss
        P_total = P_cu_total + P_core

        return {
            'core': core,
            'core_name': core.get('name', 'Unknown'),
            'n_turns_ratio': n,
            'N_primary': N_p,
            'N_secondary': N_s,
            'wire_primary': wire_pri,
            'wire_secondary': wire_sec,
            'R_primary': R_pri,
            'R_secondary': R_sec,
            'B_peak': B_peak,
            'P_copper_primary': P_cu_pri,
            'P_copper_secondary': P_cu_sec,
            'P_copper_total': P_cu_total,
            'P_core': P_core,
            'P_total': P_total,
            'volume': core.get('volume', 0)
        }
