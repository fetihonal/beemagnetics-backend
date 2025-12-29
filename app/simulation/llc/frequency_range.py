"""
Automatic Frequency Range Calculation for LLC Converter
Implements rangeoffreq.m - 6th order polynomial solver

This module automatically calculates the optimal switching frequency range
for LLC converters based on design parameters, eliminating the need for
manual frequency range input.
"""

import numpy as np
from typing import Dict, Tuple, Optional


class FrequencyRangeSolver:
    """
    Automatic frequency range calculation using 6th order polynomial
    Implements rangeoffreq.m from MATLAB

    The polynomial represents the LLC voltage gain equation solved for
    frequency ratio F = f_s / f_0 at different operating conditions.
    """

    @staticmethod
    def solve_frequency_polynomial(Q: float, Ln: float, M: float) -> Optional[float]:
        """
        Solve 6th order polynomial for frequency range

        The polynomial equation is:
        Q² * F⁶ + ((1 + 1/Ln)² - 2*Q² - 1/M²) * F⁴ +
          ((-2/Ln) * (1 + 1/Ln) + Q²) * F² + 1/Ln² = 0

        Where F = f_s / f_0 (normalized switching frequency)

        This equation comes from the LLC voltage gain FHA (First Harmonic
        Approximation) rearranged to solve for frequency.

        Args:
            Q: Quality factor
            Ln: Inductance ratio
            M: Voltage gain (desired)

        Returns:
            Maximum F (largest real positive root), or None if no valid solution
        """
        if Q <= 0 or Ln <= 0 or M <= 0:
            return None

        # Coefficients for polynomial: Q² * F⁶ + ... = 0
        # This is a 6th order polynomial in F
        c6 = Q**2
        c5 = 0  # No F⁵ term
        c4 = (1 + 1/Ln)**2 - 2*Q**2 - 1/M**2
        c3 = 0  # No F³ term
        c2 = (-2/Ln) * (1 + 1/Ln) + Q**2
        c1 = 0  # No F term
        c0 = 1 / (Ln**2)

        # Polynomial coefficients array (highest to lowest order)
        coeffs = [c6, c5, c4, c3, c2, c1, c0]

        # Solve polynomial
        roots = np.roots(coeffs)

        # Filter: only real positive roots
        real_roots = roots[np.abs(roots.imag) < 1e-10].real
        positive_roots = real_roots[real_roots > 0]

        if len(positive_roots) == 0:
            return None

        # Return largest positive root (maximum frequency)
        F_max = np.max(positive_roots)
        return F_max

    @staticmethod
    def calculate_frequency_range_at_voltage_gain(Q: float, Ln: float,
                                                   M_max: float, M_min: float,
                                                   f_0: float) -> Dict[str, float]:
        """
        Calculate switching frequency range for voltage gain limits

        LLC operates with variable frequency to regulate output voltage:
        - At max input voltage (min gain needed) → frequency is maximum
        - At min input voltage (max gain needed) → frequency is minimum

        Args:
            Q: Quality factor
            Ln: Inductance ratio
            M_max: Maximum voltage gain (at minimum input voltage)
            M_min: Minimum voltage gain (at maximum input voltage)
            f_0: Resonant frequency (Hz)

        Returns:
            Dict with f_sw_min, f_sw_max, F_min, F_max, f_0
        """
        # Solve for max frequency (at min gain)
        F_max = FrequencyRangeSolver.solve_frequency_polynomial(Q, Ln, M_min)

        # Solve for min frequency (at max gain)
        F_min = FrequencyRangeSolver.solve_frequency_polynomial(Q, Ln, M_max)

        # Handle cases where polynomial has no solution
        if F_max is None:
            F_max = 1.5  # Default: 50% above resonance

        if F_min is None:
            F_min = 0.8  # Default: 20% below resonance

        # Ensure F_max > F_min
        if F_max < F_min:
            F_max, F_min = F_min, F_max

        # Convert to absolute frequencies
        f_sw_max = F_max * f_0
        f_sw_min = F_min * f_0

        return {
            'f_sw_min': f_sw_min,
            'f_sw_max': f_sw_max,
            'f_0': f_0,
            'F_min': F_min,
            'F_max': F_max,
            'frequency_range': f_sw_max - f_sw_min,
            'frequency_range_percent': ((f_sw_max - f_sw_min) / f_0) * 100
        }

    @staticmethod
    def calculate_frequency_range_for_llc(V_in_min: float, V_in_max: float,
                                          V_out: float, n: float,
                                          Q: float, Ln: float,
                                          f_0: float) -> Dict[str, float]:
        """
        Complete frequency range calculation for LLC converter

        Calculates voltage gain limits from input/output voltages,
        then solves for corresponding frequency range.

        Args:
            V_in_min: Minimum input voltage (V)
            V_in_max: Maximum input voltage (V)
            V_out: Output voltage (V)
            n: Transformer turns ratio
            Q: Quality factor
            Ln: Inductance ratio
            f_0: Resonant frequency (Hz)

        Returns:
            Dict with complete frequency range analysis
        """
        # Calculate voltage gain limits
        # M = (V_out * n) / V_in
        M_max = (V_out * n) / V_in_min  # Max gain at min input
        M_min = (V_out * n) / V_in_max  # Min gain at max input

        # Calculate frequency range
        result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M_max, M_min, f_0
        )

        # Add voltage gain info
        result['M_max'] = M_max
        result['M_min'] = M_min
        result['V_in_min'] = V_in_min
        result['V_in_max'] = V_in_max
        result['V_out'] = V_out
        result['n'] = n

        return result

    @staticmethod
    def validate_frequency_range(f_sw_min: float, f_sw_max: float,
                                 f_0: float) -> Dict[str, any]:
        """
        Validate calculated frequency range for practical operation

        Checks if frequency range is reasonable and provides warnings
        if design may have issues.

        Args:
            f_sw_min: Minimum switching frequency (Hz)
            f_sw_max: Maximum switching frequency (Hz)
            f_0: Resonant frequency (Hz)

        Returns:
            Dict with validation results and warnings
        """
        warnings = []
        is_valid = True

        # Check 1: Frequency range should span resonance
        if f_sw_min > f_0:
            warnings.append("WARNING: Minimum frequency above resonance - may lose ZVS")
            is_valid = False

        if f_sw_max < f_0:
            warnings.append("WARNING: Maximum frequency below resonance - unusual operation")

        # Check 2: Frequency range should not be too narrow
        range_percent = ((f_sw_max - f_sw_min) / f_0) * 100
        if range_percent < 10:
            warnings.append(f"WARNING: Narrow frequency range ({range_percent:.1f}%) - limited regulation")

        # Check 3: Frequency range should not be too wide
        if range_percent > 100:
            warnings.append(f"WARNING: Very wide frequency range ({range_percent:.1f}%) - may be impractical")

        # Check 4: Frequencies should be positive
        if f_sw_min <= 0 or f_sw_max <= 0:
            warnings.append("ERROR: Invalid frequencies (negative or zero)")
            is_valid = False

        # Check 5: Max should be greater than min
        if f_sw_max <= f_sw_min:
            warnings.append("ERROR: Max frequency not greater than min frequency")
            is_valid = False

        return {
            'is_valid': is_valid,
            'warnings': warnings,
            'range_percent': range_percent,
            'spans_resonance': f_sw_min <= f_0 <= f_sw_max
        }

    @staticmethod
    def recommend_resonant_frequency(f_sw_desired: float,
                                     operating_point: str = 'resonance') -> float:
        """
        Recommend resonant frequency based on desired switching frequency

        Args:
            f_sw_desired: Desired nominal switching frequency (Hz)
            operating_point: Where to operate relative to resonance
                'resonance': f_0 = f_sw (nominal at resonance)
                'below': f_0 = 1.2 * f_sw (operate below resonance)
                'above': f_0 = 0.8 * f_sw (operate above resonance)

        Returns:
            Recommended resonant frequency (Hz)
        """
        if operating_point == 'resonance':
            return f_sw_desired
        elif operating_point == 'below':
            return f_sw_desired * 1.2  # Resonance 20% above nominal
        elif operating_point == 'above':
            return f_sw_desired * 0.8  # Resonance 20% below nominal
        else:
            return f_sw_desired  # Default to resonance

    @classmethod
    def quick_frequency_range(cls, V_in_nom: float, V_in_range_percent: float,
                              V_out: float, n: float, Q: float, Ln: float,
                              f_sw_desired: float) -> Dict[str, float]:
        """
        Quick frequency range calculation with minimal inputs

        Simplified interface for common use case where input voltage
        range is specified as percentage variation.

        Args:
            V_in_nom: Nominal input voltage (V)
            V_in_range_percent: Input voltage variation (%), e.g., 20 for ±20%
            V_out: Output voltage (V)
            n: Transformer turns ratio
            Q: Quality factor
            Ln: Inductance ratio
            f_sw_desired: Desired nominal switching frequency (Hz)

        Returns:
            Dict with frequency range and recommendations
        """
        # Calculate input voltage range
        V_in_min = V_in_nom * (1 - V_in_range_percent / 100)
        V_in_max = V_in_nom * (1 + V_in_range_percent / 100)

        # Use desired frequency as resonant frequency (operate at resonance nominally)
        f_0 = f_sw_desired

        # Calculate frequency range
        result = cls.calculate_frequency_range_for_llc(
            V_in_min, V_in_max, V_out, n, Q, Ln, f_0
        )

        # Validate
        validation = cls.validate_frequency_range(
            result['f_sw_min'], result['f_sw_max'], f_0
        )
        result['validation'] = validation

        return result
