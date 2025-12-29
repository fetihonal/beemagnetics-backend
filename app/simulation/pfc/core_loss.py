"""
PFC Core Loss Calculator
Based on Equations_PFC.pdf - PFC_Core_Loss_Function.m
"""

import numpy as np
from typing import Dict, Any, Optional
from scipy.integrate import quad


class PFCCoreLoss:
    """PFC Inductor Core Loss and Winding Loss Calculator"""

    @staticmethod
    def calculate_inductor_currents(P_out: float, eta_eff: float,
                                   V_in_RMS: float) -> Dict[str, float]:
        """
        Calculate PFC inductor currents

        From PDF:
        I_in_RMS = P_out / (η_eff * V_in_RMS)
        I_lf_PEAK = √2 * I_in_RMS
        I_in_MAX = I_lf_PEAK + ΔI_in_PEAK

        Args:
            P_out: Output power (W)
            eta_eff: Efficiency (0-1)
            V_in_RMS: Input RMS voltage (V)

        Returns:
            Dictionary with current values
        """
        # I_in_RMS = P_out / (η_eff * V_in_RMS)
        I_in_RMS = P_out / (eta_eff * V_in_RMS)

        # I_lf_PEAK = √2 * I_in_RMS
        I_lf_PEAK = np.sqrt(2) * I_in_RMS

        return {
            'I_in_RMS': I_in_RMS,
            'I_lf_PEAK': I_lf_PEAK
        }

    @staticmethod
    def calculate_ripple_current(V_in_RMS: float, V_out: float, f_sw: float,
                                 L: float, D: float = None) -> float:
        """
        Calculate inductor ripple current for PFC Boost Converter

        For PFC boost converter:
        ΔI_L = (V_in_peak * D * (1-D)) / (L * f_sw)

        At peak of sine wave (worst case):
        D = 1 - (V_in_peak / V_out)
        ΔI_L_max = (V_in_peak * D) / (L * f_sw)

        Simplified for CCM operation:
        ΔI_L ≈ (V_out - V_in_peak) * D / (L * f_sw)
             ≈ V_in_peak * (V_out - V_in_peak) / (V_out * L * f_sw)

        Args:
            V_in_RMS: Input RMS voltage (V)
            V_out: Output DC voltage (V)
            f_sw: Switching frequency (Hz)
            L: Inductance (H)
            D: Duty cycle (optional, calculated if not provided)

        Returns:
            Peak-to-peak ripple current (A)
        """
        # Calculate peak input voltage
        V_in_peak = V_in_RMS * np.sqrt(2)

        # Calculate duty cycle at peak of sine wave (worst case for ripple)
        if D is None:
            if V_out > V_in_peak:
                D = 1 - (V_in_peak / V_out)
            else:
                D = 0.5  # Default for invalid case

        # Ripple current formula for boost converter
        # ΔI_L = (V_in * D) / (L * f_sw) during switch ON
        # This is maximum at peak of input sine wave
        if L > 0 and f_sw > 0:
            Delta_I_L = (V_in_peak * D) / (L * f_sw)
        else:
            Delta_I_L = 0

        return Delta_I_L

    @staticmethod
    def calculate_ripple_current_simple(V_in: float, D: float, L: float,
                                        f_sw: float) -> float:
        """
        Simple ripple current calculation (original formula)

        ΔI_L = (V_in * D) / (L * f_sw)

        Args:
            V_in: Input voltage (V)
            D: Duty cycle (0-1)
            L: Inductance (H)
            f_sw: Switching frequency (Hz)

        Returns:
            Ripple current (A)
        """
        if L <= 0 or f_sw <= 0:
            return 0
        Delta_I_L = (V_in * D) / (L * f_sw)
        return Delta_I_L

    @staticmethod
    def calculate_max_current(I_lf_PEAK: float, I_hf_PEAK: float) -> float:
        """
        Calculate maximum inductor current

        From PDF:
        I_in_MAX = I_lf_PEAK + I_hf_PEAK

        Args:
            I_lf_PEAK: Low frequency peak current (A)
            I_hf_PEAK: High frequency peak current (A)

        Returns:
            Maximum current (A)
        """
        return I_lf_PEAK + I_hf_PEAK

    @staticmethod
    def calculate_turns(L: float = None, I_peak: float = None,
                       B_max: float = None, Ae: float = None,
                       Al: float = None) -> int:
        """
        Calculate number of turns using one of two methods:

        Method 1 (from flux density): N = (L * I_peak) / (B_max * Ae)
        Method 2 (from AL value): N = √(L / Al)

        Args:
            L: Inductance (H)
            I_peak: Peak inductor current (A) - for Method 1
            B_max: Maximum flux density (T) - for Method 1
            Ae: Core effective area (m²) - for Method 1
            Al: Core AL value (H/turn²) - for Method 2

        Returns:
            Number of turns (integer, rounded up)
        """
        # Method 1: Based on flux density (preferred for PFC)
        if L is not None and I_peak is not None and B_max is not None and Ae is not None:
            if B_max > 0 and Ae > 0:
                # N = (L * I_peak) / (B_max * Ae)
                # This ensures B_max is not exceeded at peak current
                N = (L * I_peak) / (B_max * Ae)
                return int(np.ceil(N))

        # Method 2: Based on AL value
        if L is not None and Al is not None and Al > 0:
            # N = √(L / Al)
            N = np.sqrt(L / Al)
            return int(np.ceil(N))

        # Fallback
        return 1

    @staticmethod
    def calculate_turns_from_al(L_PFC: float, Al: float) -> int:
        """
        Calculate number of turns from AL value (original formula)

        N = √(L_PFC / Al)

        Args:
            L_PFC: PFC inductance (H)
            Al: Core AL value (H/turn²)

        Returns:
            Number of turns
        """
        if Al <= 0:
            return 1
        N = np.sqrt(L_PFC / Al)
        return int(np.ceil(N))

    @staticmethod
    def calculate_max_flux_density(I_in_MAX: float, L_PFC: float,
                                   N: int, Ae_core: float) -> float:
        """
        Calculate maximum flux density

        From PDF:
        B_MAX = (I_in_MAX * L_PFC) / (N * Ae_core)

        Args:
            I_in_MAX: Maximum inductor current (A)
            L_PFC: PFC inductance (H)
            N: Number of turns
            Ae_core: Core effective area (m²)

        Returns:
            Maximum flux density (T)
        """
        B_MAX = (I_in_MAX * L_PFC) / (N * Ae_core)
        return B_MAX

    @staticmethod
    def calculate_wire_length(MLT_w: float, N: int, extra: float = 0.06) -> float:
        """
        Calculate wire length

        From PDF:
        l_wire = MLT_w * N + 2 * 0.03

        Args:
            MLT_w: Mean Length per Turn (m)
            N: Number of turns
            extra: Extra wire length (m), default 0.06m (2 * 0.03)

        Returns:
            Wire length (m)
        """
        return MLT_w * N + extra

    @staticmethod
    def calculate_copper_resistivity(T_o: float, T_a: float = 25.0) -> float:
        """
        Calculate copper resistivity at temperature

        From PDF:
        ρ_copper(T) = 1.72 × 10^-8 [1 + 0.00393 * (T_o - T_a)]

        Args:
            T_o: Operating temperature (°C)
            T_a: Ambient temperature (°C), default 25°C

        Returns:
            Resistivity (Ω·m)
        """
        rho_copper = 1.72e-8 * (1 + 0.00393 * (T_o - T_a))
        return rho_copper

    @staticmethod
    def calculate_dc_resistance(l_wire: float, rho_copper: float,
                               r_wire: float) -> float:
        """
        Calculate DC resistance

        From PDF:
        R_DC = (l_wire * ρ_copper) / (π * r_wire²)

        Args:
            l_wire: Wire length (m)
            rho_copper: Copper resistivity (Ω·m)
            r_wire: Wire radius (m)

        Returns:
            DC resistance (Ω)
        """
        R_DC = (l_wire * rho_copper) / (np.pi * r_wire**2)
        return R_DC

    @staticmethod
    def calculate_ac_resistance(R_DC: float, r_wire: float,
                               skin_depth: float) -> float:
        """
        Calculate AC resistance with skin effect

        From PDF:
        R_AC = R_DC * [1 + (r_wire/skindepth)^4 / (48+0.8*(r_wire/skindepth)^4)]

        Args:
            R_DC: DC resistance (Ω)
            r_wire: Wire radius (m)
            skin_depth: Skin depth at frequency (m)

        Returns:
            AC resistance (Ω)
        """
        ratio = r_wire / skin_depth
        ratio_4 = ratio**4
        R_AC = R_DC * (1 + ratio_4 / (48 + 0.8 * ratio_4))
        return R_AC

    @staticmethod
    def calculate_copper_loss(I_in_RMS: float, I_hf_RMS: float,
                             R_DC: float, R_AC: float) -> float:
        """
        Calculate copper (winding) loss

        From PDF:
        P_copper = I_in_RMS² * R_DC + I_hf_RMS² * R_AC

        Args:
            I_in_RMS: Low frequency RMS current (A)
            I_hf_RMS: High frequency RMS current (A)
            R_DC: DC resistance (Ω)
            R_AC: AC resistance (Ω)

        Returns:
            Copper loss (W)
        """
        P_copper = I_in_RMS**2 * R_DC + I_hf_RMS**2 * R_AC
        return P_copper

    @staticmethod
    def calculate_core_loss_steinmetz(B_ripple: float, f_eff: float,
                                     core_params: Dict[str, float],
                                     V_core: float) -> float:
        """
        Calculate core loss using Steinmetz equation

        From PDF:
        P_core = (1/T_in) * ∫[0 to T_in] func_loss(B_ripple(t), f_eff) dt

        Steinmetz: P_v = k * f^α * B^β

        Args:
            B_ripple: Ripple flux density (T)
            f_eff: Effective frequency (Hz)
            core_params: Dict with 'k', 'alpha', 'beta' Steinmetz parameters
            V_core: Core volume (m³)

        Returns:
            Core loss (W)
        """
        k = core_params.get('k', 0.0)
        alpha = core_params.get('alpha', 1.5)
        beta = core_params.get('beta', 2.5)

        # Steinmetz equation: P_v = k * f^α * B^β
        P_v = k * (f_eff ** alpha) * (B_ripple ** beta)  # W/m³

        # Total core loss
        P_core = P_v * V_core

        return P_core

    @staticmethod
    def calculate_ripple_flux_density(I_in_MAX: float, L_PFC: float,
                                     N: int, Ae_core: float) -> float:
        """
        Calculate ripple flux density

        From PDF:
        B_ripple(t) = (I_ripple(t) * L_PFC) / (2 * N * Ae_core)

        Args:
            I_in_MAX: Maximum inductor current (A)
            L_PFC: Inductance (H)
            N: Number of turns
            Ae_core: Core area (m²)

        Returns:
            Ripple flux density (T)
        """
        B_ripple = (I_in_MAX * L_PFC) / (2 * N * Ae_core)
        return B_ripple

    @staticmethod
    def calculate_inductor_volume(OD_core: float, HT_core: float,
                                 r_wire: float) -> float:
        """
        Calculate inductor volume

        From PDF:
        V_ind = (4 + r_wire + OD_core)² * (4 + r_wire + HT_core)

        Args:
            OD_core: Core outer diameter (mm)
            HT_core: Core height (mm)
            r_wire: Wire radius (mm)

        Returns:
            Inductor volume (mm³)
        """
        V_ind = (4 + r_wire + OD_core)**2 * (4 + r_wire + HT_core)
        return V_ind

    @staticmethod
    def calculate_pfc_score(V_ind: float, P_ind: float) -> float:
        """
        Calculate PFC score

        From PDF:
        Score_PFC = Volume_inductor * Loss_inductor

        Args:
            V_ind: Inductor volume (mm³)
            P_ind: Total inductor loss (W)

        Returns:
            PFC score (lower is better)
        """
        return V_ind * P_ind

    @staticmethod
    def calculate_total_inductor_loss(V_in_RMS: float, V_out: float, P_out: float,
                                      f_sw: float, eta_eff: float, L: float,
                                      core: Dict[str, Any], N: int,
                                      wire_diameter: float = 1.0,
                                      T_operating: float = 80.0) -> Dict[str, Any]:
        """
        Calculate total inductor losses for PFC optimizer

        This is a convenience method that calculates all inductor losses
        in one call, compatible with pfc_optimizer.py interface.

        Args:
            V_in_RMS: Input RMS voltage (V)
            V_out: Output DC voltage (V)
            P_out: Output power (W)
            f_sw: Switching frequency (Hz)
            eta_eff: Expected efficiency (0-1)
            L: Inductance (H)
            core: Core dictionary with Ae, volume, MLT, etc.
            N: Number of turns
            wire_diameter: Wire diameter (mm)
            T_operating: Operating temperature (°C)

        Returns:
            Dictionary with P_total, P_core, P_copper, B_max, etc.
        """
        # Extract core parameters (handle both JSON field names and expected names)
        Ae = core.get("Ae", 100e-6)  # m² (default 100mm²)
        if Ae > 1:  # If in mm², convert to m²
            Ae = Ae * 1e-6

        # Volume: JSON uses "Ve" (effective volume in m³), fallback to "volume"
        V_core = core.get("Ve", core.get("volume", 5000))
        if V_core > 1:  # If > 1, assume mm³, convert to m³
            V_core_m3 = V_core * 1e-9
        else:
            V_core_m3 = V_core  # Already in m³

        MLT = core.get("MLT", 50)  # mm or m
        if MLT > 1:  # If > 1, assume mm, convert to m
            MLT_m = MLT * 1e-3
        else:
            MLT_m = MLT

        # Steinmetz parameters - JSON uses nested "steinmetz" object with aB, bB, cB, dB
        # Some cores (like ICERGICORE1) use a different loss equation format
        # where aB, bB, cB, dB are polynomial coefficients, not standard Steinmetz params
        steinmetz = core.get("steinmetz", {})
        use_polynomial_model = False

        if steinmetz:
            aB = steinmetz.get("aB", 0.0002)
            bB = steinmetz.get("bB", 1.5)
            cB = steinmetz.get("cB", 2.5)
            dB = steinmetz.get("dB", 0)

            # Check if this is a polynomial model (very large aB/bB values)
            # Standard Steinmetz: k < 100, alpha < 5, beta < 5
            # Polynomial model: coefficients can be billions
            if aB > 1000 or bB > 10:
                use_polynomial_model = True
                # Polynomial model coefficients
                poly_a = aB
                poly_b = bB
                poly_c = cB
                poly_d = dB
                # Use defaults for standard calculation fallback
                k = 0.0002
                alpha = 1.5
                beta = 2.5
            else:
                # Standard Steinmetz parameters
                k = aB
                alpha = bB
                beta = cB
        else:
            # Fallback to direct parameters
            k = core.get("k", 0.0002)
            alpha = core.get("alpha", 1.5)
            beta = core.get("beta", 2.5)

        # Calculate currents
        I_in_RMS = P_out / (eta_eff * V_in_RMS)
        I_lf_PEAK = np.sqrt(2) * I_in_RMS

        # Calculate ripple current
        V_in_peak = V_in_RMS * np.sqrt(2)
        if V_out > V_in_peak:
            D = 1 - (V_in_peak / V_out)
        else:
            D = 0.5

        if L > 0 and f_sw > 0:
            delta_I = (V_in_peak * D) / (L * f_sw)
        else:
            delta_I = 0

        I_peak = I_lf_PEAK + delta_I / 2
        I_hf_RMS = delta_I / (2 * np.sqrt(3))  # Triangular waveform RMS

        # Calculate B_max
        if N > 0 and Ae > 0:
            B_max = (L * I_peak) / (N * Ae)
        else:
            B_max = 0

        # Calculate B_ripple (for core loss)
        if N > 0 and Ae > 0:
            B_ripple = (L * delta_I) / (2 * N * Ae)
        else:
            B_ripple = 0

        # Wire calculations
        r_wire = (wire_diameter / 2) * 1e-3  # Convert mm to m
        A_wire = np.pi * r_wire**2

        # Wire length
        l_wire = MLT_m * N + 0.06  # Extra 6cm for leads

        # DC Resistance (temperature corrected)
        rho_copper = 1.72e-8 * (1 + 0.00393 * (T_operating - 25))
        if A_wire > 0:
            R_DC = (l_wire * rho_copper) / A_wire
        else:
            R_DC = 0

        # Skin depth at switching frequency
        mu_0 = 4 * np.pi * 1e-7
        sigma_copper = 5.96e7  # S/m at 20°C
        if f_sw > 0:
            skin_depth = 1 / np.sqrt(np.pi * f_sw * mu_0 * sigma_copper)
        else:
            skin_depth = r_wire  # No skin effect

        # AC Resistance
        if skin_depth > 0:
            ratio = r_wire / skin_depth
            ratio_4 = ratio**4
            R_AC = R_DC * (1 + ratio_4 / (48 + 0.8 * ratio_4))
        else:
            R_AC = R_DC

        # Copper loss: P_cu = I_lf²*R_DC + I_hf²*R_AC
        P_copper = I_in_RMS**2 * R_DC + I_hf_RMS**2 * R_AC

        # Core loss calculation
        if use_polynomial_model and B_ripple > 0:
            # Polynomial loss model: P_v = a*B^4 + b*B^3 + c*B^2 + d*B (mW/cm³)
            # B_ripple is in Tesla, need to convert to appropriate unit if needed
            B_mT = B_ripple * 1000  # Tesla to mT
            # Core loss density (mW/cm³)
            P_v = poly_a * (B_mT**4) + poly_b * (B_mT**3) + poly_c * (B_mT**2) + poly_d * B_mT
            # Convert to Watts: V_core is in m³, need cm³
            V_core_cm3 = V_core_m3 * 1e6
            P_core = abs(P_v) * V_core_cm3 / 1000  # mW to W
            # Sanity check: limit core loss to reasonable value
            if P_core > P_out * 0.5:  # More than 50% of output power is unreasonable
                P_core = P_out * 0.02  # Fallback to 2% estimate
        elif k > 0 and B_ripple > 0:
            # Standard Steinmetz: P_core = k * f^α * B^β * V_core
            try:
                P_core = k * (f_sw**alpha) * (B_ripple**beta) * V_core_m3
                # Sanity check
                if P_core > P_out * 0.5 or not np.isfinite(P_core):
                    P_core = P_out * 0.02
            except (OverflowError, ValueError):
                # Fallback if calculation overflows
                P_core = P_out * 0.02
        else:
            # Simplified core loss estimate: 1-2% of output power
            P_core = 0.01 * P_out

        # Total loss
        P_total = P_copper + P_core

        return {
            "P_total": P_total,
            "P_core": P_core,
            "P_copper": P_copper,
            "B_max": B_max,
            "B_ripple": B_ripple,
            "R_DC": R_DC,
            "R_AC": R_AC,
            "I_peak": I_peak,
            "delta_I": delta_I,
            "skin_depth": skin_depth
        }

    def calculate_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete PFC inductor calculation

        Args:
            params: Dictionary with all required parameters

        Returns:
            Complete results dictionary
        """
        # Extract parameters
        P_out = params['P_out']
        eta_eff = params['eta_eff']
        V_in_RMS = params['V_in_RMS']
        L_PFC = params['L_PFC']
        Al = params['Al']
        f_sw = params['f_sw']
        Ae_core = params['Ae_core']
        V_core = params['V_core']
        MLT_w = params['MLT_w']
        r_wire = params['r_wire']
        skin_depth = params['skin_depth']
        T_o = params['T_o']
        core_params = params.get('core_params', {'k': 0, 'alpha': 1.5, 'beta': 2.5})
        OD_core = params.get('OD_core', 0)
        HT_core = params.get('HT_core', 0)

        # Calculate currents
        currents = self.calculate_inductor_currents(P_out, eta_eff, V_in_RMS)
        I_in_RMS = currents['I_in_RMS']
        I_lf_PEAK = currents['I_lf_PEAK']

        # Assume ripple current (30% of average as typical)
        I_avg = P_out / V_in_RMS
        Delta_I = 0.3 * I_avg
        I_hf_PEAK = Delta_I / 2
        I_hf_RMS = Delta_I / (2 * np.sqrt(3))  # Triangular waveform

        I_in_MAX = I_lf_PEAK + I_hf_PEAK

        # Calculate turns
        N = self.calculate_turns(L_PFC, Al)

        # Calculate flux density
        B_MAX = self.calculate_max_flux_density(I_in_MAX, L_PFC, N, Ae_core)
        B_ripple = self.calculate_ripple_flux_density(I_hf_PEAK, L_PFC, N, Ae_core)

        # Calculate winding losses
        l_wire = self.calculate_wire_length(MLT_w, N)
        rho_copper = self.calculate_copper_resistivity(T_o)
        R_DC = self.calculate_dc_resistance(l_wire, rho_copper, r_wire)
        R_AC = self.calculate_ac_resistance(R_DC, r_wire, skin_depth)
        P_copper = self.calculate_copper_loss(I_in_RMS, I_hf_RMS, R_DC, R_AC)

        # Calculate core loss
        P_core = self.calculate_core_loss_steinmetz(B_ripple, f_sw, core_params, V_core)

        # Total loss
        P_ind = P_copper + P_core

        # Volume
        V_ind = self.calculate_inductor_volume(OD_core, HT_core, r_wire * 1000)  # Convert to mm

        # Score
        Score_PFC = self.calculate_pfc_score(V_ind, P_ind)

        return {
            'I_in_RMS': I_in_RMS,
            'I_lf_PEAK': I_lf_PEAK,
            'I_in_MAX': I_in_MAX,
            'N': N,
            'B_MAX': B_MAX,
            'B_ripple': B_ripple,
            'l_wire': l_wire,
            'R_DC': R_DC,
            'R_AC': R_AC,
            'P_copper': P_copper,
            'P_core': P_core,
            'P_ind': P_ind,
            'V_ind': V_ind,
            'Score_PFC': Score_PFC
        }


# Alias for backward compatibility
PFCCoreLossCalculator = PFCCoreLoss
