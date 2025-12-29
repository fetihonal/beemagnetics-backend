"""
LLC Resonant Tank Calculator
Based on LLC converter theory and First Harmonic Approximation (FHA)
"""

import numpy as np
from typing import Dict, Tuple, Optional


class LLCResonantTank:
    """LLC Resonant Converter Tank Calculator"""

    @staticmethod
    def calculate_resonant_frequency(Lr: float, Cr: float) -> float:
        """
        Calculate resonant frequency

        f_o = 1 / (2π√(Lr*Cr))

        Args:
            Lr: Resonant inductance (H)
            Cr: Resonant capacitance (F)

        Returns:
            Resonant frequency (Hz)
        """
        f_o = 1 / (2 * np.pi * np.sqrt(Lr * Cr))
        return f_o

    @staticmethod
    def calculate_quality_factor(Lr: float, Cr: float, R_ac: float) -> float:
        """
        Calculate quality factor

        Q = √(Lr/Cr) / R_ac = (ω_o * Lr) / R_ac

        Args:
            Lr: Resonant inductance (H)
            Cr: Resonant capacitance (F)
            R_ac: AC load resistance reflected to primary (Ω)

        Returns:
            Quality factor (dimensionless)
        """
        if R_ac <= 0:
            return float('inf')

        Q = np.sqrt(Lr / Cr) / R_ac
        return Q

    @staticmethod
    def calculate_inductance_ratio(Lm: float, Lr: float) -> float:
        """
        Calculate inductance ratio

        Ln = Lm / Lr

        Args:
            Lm: Magnetizing inductance (H)
            Lr: Resonant inductance (H)

        Returns:
            Inductance ratio (dimensionless)
        """
        if Lr <= 0:
            return float('inf')

        Ln = Lm / Lr
        return Ln

    @staticmethod
    def calculate_ac_resistance(V_out: float, P_out: float, n: float) -> float:
        """
        Calculate AC load resistance reflected to primary

        R_ac = (8 * n² * V_out²) / (π² * P_out)

        Args:
            V_out: Output voltage (V)
            P_out: Output power (W)
            n: Turns ratio (N_primary / N_secondary)

        Returns:
            AC resistance (Ω)
        """
        if P_out <= 0:
            return float('inf')

        R_ac = (8 * n**2 * V_out**2) / (np.pi**2 * P_out)
        return R_ac

    @staticmethod
    def calculate_voltage_gain_fha(f_sw: float, f_o: float, Q: float, Ln: float,
                                   use_full_equation: bool = True) -> float:
        """
        Calculate LLC voltage gain using First Harmonic Approximation (FHA)

        Full FHA equation (recommended):
        M = (Ln * f_n²) / √[(Ln + 1 - Ln/f_n²)² + Q²*(f_n - 1/f_n)²*(Ln + 1)²]

        Simplified equation (for quick estimation):
        M = 1 / √[(1 - f_n² + f_n²/Ln)² + (Q*f_n*(1/Ln - 1))²]

        where:
        - f_n = f_sw / f_o (normalized frequency)
        - Ln = Lm / Lr (inductance ratio)
        - Q = √(Lr/Cr) / R_ac (quality factor)

        Args:
            f_sw: Switching frequency (Hz)
            f_o: Resonant frequency (Hz)
            Q: Quality factor
            Ln: Inductance ratio (Lm/Lr)
            use_full_equation: Use full FHA equation (default True)

        Returns:
            Voltage gain M (dimensionless)
        """
        if f_o <= 0 or Ln <= 0:
            return 0

        # Normalized frequency
        f_n = f_sw / f_o

        if use_full_equation:
            # Full FHA equation - more accurate across all operating points
            # M = (Ln * f_n²) / √[(Ln + 1 - Ln/f_n²)² + Q²*(f_n - 1/f_n)²*(Ln + 1)²]

            # Avoid division by zero
            if f_n == 0:
                return 0

            numerator = Ln * (f_n ** 2)

            term1 = (Ln + 1 - Ln / (f_n ** 2)) ** 2
            term2 = (Q ** 2) * ((f_n - 1/f_n) ** 2) * ((Ln + 1) ** 2)

            denominator = np.sqrt(term1 + term2)

            if denominator == 0:
                return float('inf')

            M = numerator / denominator
        else:
            # Simplified equation - faster but less accurate at extremes
            term1 = (1 - f_n**2 + (f_n**2 / Ln))**2
            term2 = (Q * f_n * ((1 / Ln) - 1))**2

            denominator = np.sqrt(term1 + term2)

            if denominator == 0:
                return float('inf')

            M = 1 / denominator

        return M

    @staticmethod
    def calculate_voltage_gain_fha_array(f_sw_array: np.ndarray, f_o: float,
                                         Q: float, Ln: float) -> np.ndarray:
        """
        Calculate voltage gain for an array of switching frequencies

        Useful for plotting gain curves.

        Args:
            f_sw_array: Array of switching frequencies (Hz)
            f_o: Resonant frequency (Hz)
            Q: Quality factor
            Ln: Inductance ratio

        Returns:
            Array of voltage gains
        """
        f_n = f_sw_array / f_o

        # Full FHA equation vectorized
        numerator = Ln * (f_n ** 2)
        term1 = (Ln + 1 - Ln / (f_n ** 2)) ** 2
        term2 = (Q ** 2) * ((f_n - 1/f_n) ** 2) * ((Ln + 1) ** 2)
        denominator = np.sqrt(term1 + term2)

        # Handle edge cases
        M = np.where(denominator > 0, numerator / denominator, 0)

        return M

    @staticmethod
    def calculate_switching_frequency_for_gain(M_target: float, f_o: float,
                                              Q: float, Ln: float,
                                              below_resonance: bool = True) -> float:
        """
        Calculate required switching frequency for target gain

        Solves the FHA equation for f_sw given M_target

        Args:
            M_target: Target voltage gain
            f_o: Resonant frequency (Hz)
            Q: Quality factor
            Ln: Inductance ratio
            below_resonance: If True, solve for f_sw < f_o (typical)

        Returns:
            Switching frequency (Hz)
        """
        # This requires solving a quartic equation, use numerical method
        from scipy.optimize import brentq

        def gain_error(f_sw):
            M = LLCResonantTank.calculate_voltage_gain_fha(f_sw, f_o, Q, Ln)
            return M - M_target

        # Search range
        if below_resonance:
            f_min = 0.3 * f_o
            f_max = f_o
        else:
            f_min = f_o
            f_max = 3 * f_o

        try:
            f_sw = brentq(gain_error, f_min, f_max)
            return f_sw
        except:
            # If no solution found, return boundary
            return f_max if below_resonance else f_min

    @staticmethod
    def calculate_magnetizing_current(V_in: float, Lm: float, f_sw: float) -> float:
        """
        Calculate peak magnetizing current

        I_mag_peak ≈ V_in / (4 * f_sw * Lm)

        Args:
            V_in: Input voltage (V)
            Lm: Magnetizing inductance (H)
            f_sw: Switching frequency (Hz)

        Returns:
            Peak magnetizing current (A)
        """
        if Lm <= 0 or f_sw <= 0:
            return float('inf')

        I_mag_peak = V_in / (4 * f_sw * Lm)
        return I_mag_peak

    @staticmethod
    def calculate_resonant_current(P_out: float, V_in: float, M: float) -> float:
        """
        Calculate RMS resonant tank current

        I_r_RMS ≈ P_out / (M * V_in)

        Args:
            P_out: Output power (W)
            V_in: Input voltage (V)
            M: Voltage gain

        Returns:
            RMS resonant current (A)
        """
        if M <= 0 or V_in <= 0:
            return float('inf')

        I_r_RMS = P_out / (M * V_in)
        return I_r_RMS

    @staticmethod
    def design_resonant_tank(V_in_nom: float, V_in_min: float, V_in_max: float,
                            V_out: float, P_out: float, n: float,
                            Q_target: float, Ln_target: float) -> Dict:
        """
        Design LLC resonant tank parameters

        Args:
            V_in_nom: Nominal input voltage (V)
            V_in_min: Minimum input voltage (V)
            V_in_max: Maximum input voltage (V)
            V_out: Output voltage (V)
            P_out: Output power (W)
            n: Turns ratio (N_pri / N_sec)
            Q_target: Target quality factor
            Ln_target: Target inductance ratio

        Returns:
            Dictionary with Lr, Cr, Lm, f_o, Q, Ln, and operating points
        """
        # Calculate AC load resistance
        R_ac = LLCResonantTank.calculate_ac_resistance(V_out, P_out, n)

        # Calculate Lr from Q and R_ac
        # Q = sqrt(Lr/Cr) / R_ac
        # Also need to choose a resonant frequency

        # Typical resonant frequency: 50-200 kHz
        # Let's choose f_o based on power level
        if P_out < 100:
            f_o = 100e3  # 100 kHz for low power
        elif P_out < 500:
            f_o = 150e3  # 150 kHz for medium power
        else:
            f_o = 100e3  # 100 kHz for high power

        # From Q = sqrt(Lr/Cr) / R_ac and f_o = 1/(2π√(Lr*Cr))
        # We get: Lr = Q * R_ac / (2π * f_o)
        Lr = Q_target * R_ac / (2 * np.pi * f_o)

        # From f_o = 1/(2π√(Lr*Cr)), solve for Cr
        Cr = 1 / ((2 * np.pi * f_o)**2 * Lr)

        # From Ln = Lm / Lr
        Lm = Ln_target * Lr

        # Verify Q
        Q_actual = LLCResonantTank.calculate_quality_factor(Lr, Cr, R_ac)

        # Calculate required gains at boundaries
        M_min = (V_out * n) / V_in_max  # Low gain at high input
        M_max = (V_out * n) / V_in_min  # High gain at low input
        M_nom = (V_out * n) / V_in_nom

        # Calculate required switching frequencies
        # At V_in_max (low gain), f_sw should be close to or above f_o
        # At V_in_min (high gain), f_sw should be below f_o

        f_sw_max = LLCResonantTank.calculate_switching_frequency_for_gain(
            M_min, f_o, Q_actual, Ln_target, below_resonance=False
        )

        f_sw_min = LLCResonantTank.calculate_switching_frequency_for_gain(
            M_max, f_o, Q_actual, Ln_target, below_resonance=True
        )

        f_sw_nom = LLCResonantTank.calculate_switching_frequency_for_gain(
            M_nom, f_o, Q_actual, Ln_target, below_resonance=True
        )

        return {
            'Lr': Lr,
            'Cr': Cr,
            'Lm': Lm,
            'f_o': f_o,
            'Q': Q_actual,
            'Ln': Ln_target,
            'R_ac': R_ac,
            'M_min': M_min,
            'M_max': M_max,
            'M_nom': M_nom,
            'f_sw_min': f_sw_min,
            'f_sw_max': f_sw_max,
            'f_sw_nom': f_sw_nom
        }

    @staticmethod
    def generate_waveforms(Lr: float, Cr: float, Lm: float, V_in: float,
                          f_sw: float, n_points: int = 1000) -> Dict:
        """
        Generate simplified LLC waveforms for visualization

        Returns time-domain waveforms: t1, t2, Ilrp, id1

        Args:
            Lr: Resonant inductance (H)
            Cr: Resonant capacitance (F)
            Lm: Magnetizing inductance (H)
            V_in: Input voltage (V)
            f_sw: Switching frequency (Hz)
            n_points: Number of points in waveform

        Returns:
            Dictionary with time arrays and current waveforms
        """
        T_sw = 1 / f_sw
        t = np.linspace(0, T_sw, n_points)

        # Simplified resonant current (sinusoidal approximation)
        f_o = LLCResonantTank.calculate_resonant_frequency(Lr, Cr)
        omega_o = 2 * np.pi * f_o

        # Peak resonant current (rough estimate)
        Z_o = np.sqrt(Lr / Cr)
        I_peak = V_in / Z_o

        # Resonant current (half sine wave)
        Ilrp = I_peak * np.sin(2 * np.pi * f_sw * t)
        Ilrp[Ilrp < 0] = 0  # Rectify

        # Magnetizing current (triangular)
        I_mag_peak = V_in / (4 * f_sw * Lm)
        id1 = I_mag_peak * (2 * (t / T_sw) - 1)

        # Time vectors
        t1 = t
        t2 = t + T_sw / 2  # Second half period

        return {
            't1': t1.tolist(),
            't2': t2.tolist(),
            'Ilrp': Ilrp.tolist(),
            'id1': id1.tolist()
        }
