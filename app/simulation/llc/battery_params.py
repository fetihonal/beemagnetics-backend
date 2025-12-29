"""
Battery/Output Stage Parameters for LLC Converter
Implements batterypar.m formulas from MATLAB

This module calculates battery/load parameters with loss correction,
which is critical for accurate turns ratio and Q factor calculations.
"""

import numpy as np
from typing import Dict


class BatteryParameters:
    """
    Battery/Output stage parameters with loss correction
    Implements batterypar.m formulas
    """

    @staticmethod
    def calculate_load_resistance(V_out: float, I_bat: float) -> float:
        """
        Calculate load resistance

        R = V_o / I_bat

        Args:
            V_out: Output voltage (V)
            I_bat: Battery/load current (A)

        Returns:
            Load resistance (Ω)
        """
        if I_bat <= 0:
            return float('inf')

        R = V_out / I_bat
        return R

    @staticmethod
    def calculate_battery_current(P_out: float, V_out: float) -> float:
        """
        Calculate battery/load current

        I_bat = P / V_o

        Args:
            P_out: Output power (W)
            V_out: Output voltage (V)

        Returns:
            Battery current (A)
        """
        if V_out <= 0:
            return 0

        I_bat = P_out / V_out
        return I_bat

    @staticmethod
    def calculate_voltage_loss(P_out: float, I_bat: float,
                               efficiency: float) -> float:
        """
        Calculate voltage loss due to converter losses

        V_loss = (P_o * (1 - η/100)) / (I_bat * η/100)

        This accounts for the voltage drop across the converter due to losses.
        Critical for accurate turns ratio calculation.

        Args:
            P_out: Output power (W)
            I_bat: Battery/load current (A)
            efficiency: Converter efficiency (%)

        Returns:
            Voltage loss (V)
        """
        if efficiency <= 0 or I_bat <= 0:
            return 0

        # Convert efficiency from percentage
        eta = efficiency / 100.0

        V_loss = (P_out * (1 - eta)) / (I_bat * eta)
        return V_loss

    @staticmethod
    def calculate_turns_ratio_corrected(V_in: float, V_out: float,
                                       V_loss: float) -> int:
        """
        Calculate loss-corrected turns ratio

        a = round(V_i / (V_o + V_loss))

        IMPORTANT: Must use round() as specified in MATLAB formulas!
        This ensures integer turns ratio for practical transformer design.

        Args:
            V_in: Input voltage (V)
            V_out: Output voltage (V)
            V_loss: Voltage loss (V)

        Returns:
            Turns ratio (integer)
        """
        if (V_out + V_loss) <= 0:
            return 1

        a = V_in / (V_out + V_loss)
        return round(a)  # CRITICAL: Use round() as per MATLAB spec

    @staticmethod
    def calculate_equivalent_resistance(turns_ratio: int,
                                       R_load: float) -> float:
        """
        Calculate equivalent resistance referred to primary

        R_e = (8 * a² * R) / π²

        This is critical for LLC Q factor calculation:
        Q = sqrt(Lr/Cr) / R_e

        Args:
            turns_ratio: Transformer turns ratio (a = N_pri / N_sec)
            R_load: Load resistance (Ω)

        Returns:
            Equivalent resistance (Ω)
        """
        R_e = (8 * turns_ratio**2 * R_load) / (np.pi**2)
        return R_e

    @staticmethod
    def calculate_voltage_gain_limits(turns_ratio: int, V_out: float,
                                      V_loss: float, V_in_min: float,
                                      V_in_max: float) -> Dict[str, float]:
        """
        Calculate voltage gain limits

        M_g_max = (a * (V_o + V_loss)) / V_imin
        M_g_min = (a * (V_o + V_loss)) / V_imax

        IMPORTANT: Use (V_o + V_loss) instead of just V_o as per MATLAB spec!

        Args:
            turns_ratio: Transformer turns ratio
            V_out: Output voltage (V)
            V_loss: Voltage loss (V)
            V_in_min: Minimum input voltage (V)
            V_in_max: Maximum input voltage (V)

        Returns:
            Dict with M_g_max, M_g_min, V_out_corrected
        """
        V_out_corrected = V_out + V_loss

        if V_in_min <= 0 or V_in_max <= 0:
            return {
                'M_g_max': 1.0,
                'M_g_min': 1.0,
                'V_out_corrected': V_out_corrected
            }

        M_g_max = (turns_ratio * V_out_corrected) / V_in_min
        M_g_min = (turns_ratio * V_out_corrected) / V_in_max

        return {
            'M_g_max': M_g_max,
            'M_g_min': M_g_min,
            'V_out_corrected': V_out_corrected
        }

    @classmethod
    def calculate_all_parameters(cls, V_in_nom: float, V_in_min: float,
                                 V_in_max: float, V_out: float, P_out: float,
                                 efficiency: float = 95.0) -> Dict[str, float]:
        """
        Calculate all battery/load parameters in one call

        This is a convenience method that calculates all parameters
        following the complete batterypar.m workflow.

        Args:
            V_in_nom: Nominal input voltage (V)
            V_in_min: Minimum input voltage (V)
            V_in_max: Maximum input voltage (V)
            V_out: Output voltage (V)
            P_out: Output power (W)
            efficiency: Converter efficiency (%), default 95%

        Returns:
            Dict with all calculated parameters
        """
        # Step 1: Calculate battery current
        I_bat = cls.calculate_battery_current(P_out, V_out)

        # Step 2: Calculate load resistance
        R_load = cls.calculate_load_resistance(V_out, I_bat)

        # Step 3: Calculate voltage loss
        V_loss = cls.calculate_voltage_loss(P_out, I_bat, efficiency)

        # Step 4: Calculate loss-corrected turns ratio
        turns_ratio = cls.calculate_turns_ratio_corrected(V_in_nom, V_out, V_loss)

        # Step 5: Calculate equivalent resistance
        R_e = cls.calculate_equivalent_resistance(turns_ratio, R_load)

        # Step 6: Calculate voltage gain limits
        gain_limits = cls.calculate_voltage_gain_limits(
            turns_ratio, V_out, V_loss, V_in_min, V_in_max
        )

        return {
            'I_bat': I_bat,
            'R_load': R_load,
            'V_loss': V_loss,
            'turns_ratio': turns_ratio,
            'R_e': R_e,
            'M_g_max': gain_limits['M_g_max'],
            'M_g_min': gain_limits['M_g_min'],
            'V_out_corrected': gain_limits['V_out_corrected']
        }
