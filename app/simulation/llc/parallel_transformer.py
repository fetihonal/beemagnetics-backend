"""
Parallel Transformer Support for LLC Converter
For high-power designs (>1kW) requiring multiple transformers

Implements the parallel transformer corrections from currentcalc.m:
- n → round(a/ptrf)
- Lm → Lm/ptrf

This is critical for multi-kW LLC designs where a single transformer
cannot handle the power requirement.
"""

import numpy as np
from typing import Dict, Any


class ParallelTransformerCalculator:
    """
    Parallel transformer calculations for high-power LLC designs

    When power requirements exceed single transformer capability,
    multiple transformers are connected in parallel. This requires
    specific corrections to turns ratio and magnetizing inductance.
    """

    @staticmethod
    def calculate_corrected_turns_ratio(a: float, ptrf: int) -> int:
        """
        Corrected turns ratio for parallel transformers

        n_corrected = round(a / ptrf)

        Each transformer in parallel configuration has reduced
        turns ratio to maintain proper voltage transformation.

        Args:
            a: Original turns ratio (from battery_params)
            ptrf: Number of parallel transformers

        Returns:
            Corrected turns ratio per transformer (integer)
        """
        if ptrf <= 0:
            ptrf = 1  # Safety check

        n_corrected = round(a / ptrf)
        return max(1, n_corrected)  # Ensure at least 1

    @staticmethod
    def calculate_corrected_magnetizing_inductance(Lm: float,
                                                   ptrf: int) -> float:
        """
        Corrected magnetizing inductance for parallel transformers

        Lm_corrected = Lm / ptrf

        When transformers are in parallel, effective magnetizing
        inductance per transformer is divided by number of transformers.

        Args:
            Lm: Total magnetizing inductance (H)
            ptrf: Number of parallel transformers

        Returns:
            Magnetizing inductance per transformer (H)
        """
        if ptrf <= 0:
            ptrf = 1  # Safety check

        Lm_per_transformer = Lm / ptrf
        return Lm_per_transformer

    @staticmethod
    def calculate_parallel_currents(I_Lr_rms: float, I_sec_rms: float,
                                   I_Lm_max: float, I_Lr_max: float,
                                   ptrf: int) -> Dict[str, float]:
        """
        Current distribution in parallel transformers

        Each transformer carries approximately I_total / ptrf
        (assuming balanced current sharing)

        Args:
            I_Lr_rms: Total resonant current RMS (A)
            I_sec_rms: Total secondary current RMS (A)
            I_Lm_max: Maximum magnetizing current per transformer (A)
            I_Lr_max: Total maximum resonant current (A)
            ptrf: Number of parallel transformers

        Returns:
            Dict with per-transformer currents
        """
        if ptrf <= 0:
            ptrf = 1

        return {
            'I_Lr_rms_each': I_Lr_rms / ptrf,
            'I_sec_rms_each': I_sec_rms / ptrf,
            'I_Lm_max_each': I_Lm_max,  # Same flux density in each
            'I_Lr_max_each': I_Lr_max / ptrf,
            'total_transformers': ptrf
        }

    @staticmethod
    def calculate_I_Lm_max_parallel(n: int, V_o: float, L_m: float,
                                   f_s: float, ptrf: int) -> float:
        """
        Maximum magnetizing current with parallel transformer correction

        I_Lm_max = (n_corrected * V_o) / (4 * Lm_corrected * f_s)

        Where:
        - n_corrected = round(n / ptrf)
        - Lm_corrected = Lm / ptrf

        From currentcalc.m: "n yerine round(a/ptrf) ve Lm yerine Lm/ptrf"

        Args:
            n: Original turns ratio
            V_o: Output voltage (V)
            L_m: Total magnetizing inductance (H)
            f_s: Switching frequency (Hz)
            ptrf: Number of parallel transformers

        Returns:
            Maximum magnetizing current per transformer (A)
        """
        if ptrf <= 0:
            ptrf = 1

        # Apply parallel transformer corrections
        n_corrected = round(n / ptrf) if ptrf > 1 else n
        n_corrected = max(1, n_corrected)  # Ensure at least 1

        Lm_corrected = L_m / ptrf if ptrf > 1 else L_m

        # Calculate I_Lm_max with corrected values
        I_Lm_max = (n_corrected * V_o) / (4 * Lm_corrected * f_s)

        return I_Lm_max

    @staticmethod
    def calculate_I_Lr_rms_parallel(n: int, V_o: float, f_s: float,
                                   L_m: float, I_o: float, f_0: float,
                                   ptrf: int) -> float:
        """
        Resonant current RMS with parallel transformer correction

        I_Lr_rms = sqrt(
            1/48 * (n*V_o/(f_s*Lm))² +
            π²/8 * (I_o/n * sqrt(f_0/f_s))² -
            I_o*V_o/Lm * 1/2 * (1/f_s - 1/f_0)
        )

        Where n → round(n/ptrf) and Lm → Lm/ptrf

        Args:
            n: Original turns ratio
            V_o: Output voltage (V)
            f_s: Switching frequency (Hz)
            L_m: Total magnetizing inductance (H)
            I_o: Output current (A)
            f_0: Resonant frequency (Hz)
            ptrf: Number of parallel transformers

        Returns:
            RMS resonant current per transformer (A)
        """
        if ptrf <= 0:
            ptrf = 1

        # Apply parallel transformer corrections
        n_corrected = round(n / ptrf) if ptrf > 1 else n
        n_corrected = max(1, n_corrected)

        Lm_corrected = L_m / ptrf if ptrf > 1 else L_m
        I_o_per_trf = I_o / ptrf  # Current per transformer

        # Calculate I_Lr_rms with corrected values
        term1 = (1/48) * ((n_corrected * V_o) / (f_s * Lm_corrected))**2

        term2 = (np.pi**2 / 8) * ((I_o_per_trf / n_corrected) * np.sqrt(f_0 / f_s))**2

        term3 = (I_o_per_trf * V_o / Lm_corrected) * 0.5 * (1/f_s - 1/f_0)

        I_Lr_rms = np.sqrt(term1 + term2 - term3)

        return I_Lr_rms

    @staticmethod
    def calculate_I_sec_rms_parallel(I_o: float, f_0: float, f_s: float,
                                    ptrf: int) -> float:
        """
        Secondary RMS current with parallel transformers

        I_sec_rms = (sqrt(2) * π * I_o) / 4 * sqrt(f_0/f_s)

        Then divided by ptrf for per-transformer current

        Args:
            I_o: Total output current (A)
            f_0: Resonant frequency (Hz)
            f_s: Switching frequency (Hz)
            ptrf: Number of parallel transformers

        Returns:
            RMS secondary current per transformer (A)
        """
        if ptrf <= 0:
            ptrf = 1

        I_o_per_trf = I_o / ptrf

        I_sec_rms = (np.sqrt(2) * np.pi * I_o_per_trf / 4) * np.sqrt(f_0 / f_s)

        return I_sec_rms

    @staticmethod
    def calculate_I_Lr_max_parallel(I_o: float, f_o: float, f_s: float,
                                   n: int, I_Lm_max: float, ptrf: int) -> float:
        """
        Maximum resonant current with parallel transformers

        I_Lr_max = sqrt(
            (π * I_o * f_0 / (2 * n * f_s))² + I_Lm_max²
        )

        Where n → round(n/ptrf) and currents per transformer

        Args:
            I_o: Total output current (A)
            f_o: Resonant frequency (Hz)
            f_s: Switching frequency (Hz)
            n: Original turns ratio
            I_Lm_max: Maximum magnetizing current per transformer (A)
            ptrf: Number of parallel transformers

        Returns:
            Maximum resonant current per transformer (A)
        """
        if ptrf <= 0:
            ptrf = 1

        # Apply corrections
        n_corrected = round(n / ptrf) if ptrf > 1 else n
        n_corrected = max(1, n_corrected)

        I_o_per_trf = I_o / ptrf

        # Calculate I_Lr_max
        term1 = (np.pi * I_o_per_trf * f_o / (2 * n_corrected * f_s))**2
        term2 = I_Lm_max**2

        I_Lr_max = np.sqrt(term1 + term2)

        return I_Lr_max

    @classmethod
    def calculate_all_currents_parallel(cls, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate all currents for parallel transformer configuration

        This is the main method to use for complete parallel transformer
        current calculations. It applies all necessary corrections.

        Args:
            params: Dictionary with:
                - n: Turns ratio
                - V_o: Output voltage (V)
                - I_o: Output current (A)
                - L_m: Total magnetizing inductance (H)
                - f_s: Switching frequency (Hz)
                - f_0: Resonant frequency (Hz)
                - ptrf: Number of parallel transformers

        Returns:
            Dict with all calculated currents per transformer
        """
        n = params['n']
        V_o = params['V_o']
        I_o = params['I_o']
        L_m = params['L_m']
        f_s = params['f_s']
        f_0 = params['f_0']
        ptrf = params.get('ptrf', 1)

        # Calculate corrected values
        n_corrected = cls.calculate_corrected_turns_ratio(n, ptrf)
        Lm_corrected = cls.calculate_corrected_magnetizing_inductance(L_m, ptrf)

        # Calculate all currents with corrections
        I_Lm_max = cls.calculate_I_Lm_max_parallel(n, V_o, L_m, f_s, ptrf)

        I_Lr_rms = cls.calculate_I_Lr_rms_parallel(
            n, V_o, f_s, L_m, I_o, f_0, ptrf
        )

        I_sec_rms = cls.calculate_I_sec_rms_parallel(I_o, f_0, f_s, ptrf)

        I_Lr_max = cls.calculate_I_Lr_max_parallel(
            I_o, f_0, f_s, n, I_Lm_max, ptrf
        )

        return {
            'n_corrected': n_corrected,
            'Lm_corrected': Lm_corrected,
            'I_Lm_max': I_Lm_max,
            'I_Lr_rms': I_Lr_rms,
            'I_sec_rms': I_sec_rms,
            'I_Lr_max': I_Lr_max,
            'ptrf': ptrf,
            'I_o_per_transformer': I_o / ptrf,
            'power_per_transformer': (V_o * I_o) / ptrf
        }

    @staticmethod
    def determine_optimal_ptrf(P_out: float, P_max_per_transformer: float = 1000) -> int:
        """
        Determine optimal number of parallel transformers

        Based on power requirement and maximum power per transformer

        Args:
            P_out: Total output power (W)
            P_max_per_transformer: Maximum power per transformer (W), default 1kW

        Returns:
            Optimal number of parallel transformers
        """
        if P_max_per_transformer <= 0:
            P_max_per_transformer = 1000

        ptrf = int(np.ceil(P_out / P_max_per_transformer))
        return max(1, ptrf)  # At least 1 transformer
