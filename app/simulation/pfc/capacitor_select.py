"""
PFC Capacitor Selection
Based on Equations_PFC.pdf - Capacitor_selection_function.m
"""

import numpy as np
from typing import Dict, List, Optional


class CapacitorSelection:
    """Bus Capacitor Selection for PFC"""

    @staticmethod
    def calculate_holdup_capacitance(P_o: float, T_hold: float,
                                    V_out: float, V_out_MIN: float) -> float:
        """
        Calculate minimum capacitance for holdup time

        From PDF:
        C_Bus > (2 * P_o * T_hold) / (V_out² - V_out_MIN²)

        Args:
            P_o: Output power (W)
            T_hold: Holdup time (s)
            V_out: Output voltage (V)
            V_out_MIN: Minimum output voltage (V)

        Returns:
            Minimum capacitance (F)
        """
        C_min = (2 * P_o * T_hold) / (V_out**2 - V_out_MIN**2)
        return C_min

    @staticmethod
    def calculate_ripple_capacitance(P_out: float, f_in: float,
                                    Delta_V_out: float, V_out: float) -> float:
        """
        Calculate minimum capacitance for output ripple

        From PDF:
        C_Bus > P_out / (2 * π * f_in * ΔV_CBus * V_out)

        Which leads to:
        C_o = P_out / (2 * π * f * ΔV_out * V_out)

        Args:
            P_out: Output power (W)
            f_in: Input frequency (Hz)
            Delta_V_out: Maximum output ripple voltage (V)
            V_out: Output voltage (V)

        Returns:
            Minimum capacitance (F)
        """
        C_min = P_out / (2 * np.pi * f_in * Delta_V_out * V_out)
        return C_min

    @staticmethod
    def calculate_capacitor_rms_current(P_out: float, V_out: float,
                                        f_sw: float, f_in: float = 50) -> float:
        """
        Calculate RMS ripple current through bus capacitor

        The bus capacitor RMS current in a PFC has two components:
        1. Low frequency (2*f_in) component from AC rectification
        2. High frequency (f_sw) component from switching

        Approximate formula:
        I_cap_RMS ≈ I_out * √((π²/8 - 1) + (D*(1-D)/12))

        Simplified for typical PFC:
        I_cap_RMS ≈ 0.5 * I_out (conservative estimate)

        Args:
            P_out: Output power (W)
            V_out: Output voltage (V)
            f_sw: Switching frequency (Hz)
            f_in: Input frequency (Hz), default 50Hz

        Returns:
            RMS ripple current (A)
        """
        # Output current
        I_out = P_out / V_out

        # Low frequency component (dominant in PFC)
        # I_LF_RMS ≈ I_out * sqrt(π²/8 - 1) ≈ 0.48 * I_out
        I_LF_RMS = I_out * np.sqrt(np.pi**2 / 8 - 1)

        # High frequency component (depends on duty cycle)
        # Assume average duty cycle D ≈ 0.5 for estimation
        D_avg = 0.5
        I_HF_RMS = I_out * np.sqrt(D_avg * (1 - D_avg) / 12)

        # Total RMS (RSS of components)
        I_cap_RMS = np.sqrt(I_LF_RMS**2 + I_HF_RMS**2)

        return I_cap_RMS

    @staticmethod
    def select_capacitors(C_required: float, capacitor_db: List[Dict],
                         V_rated_min: float, I_ripple_RMS: float = 0) -> Optional[Dict]:
        """
        Select optimal capacitor configuration from database

        Args:
            C_required: Required total capacitance (F)
            capacitor_db: List of available capacitors
            V_rated_min: Minimum voltage rating required (V)
            I_ripple_RMS: RMS ripple current (A), optional

        Returns:
            Best capacitor selection with parallel count, or None if no valid selection
        """
        valid_caps = [
            cap for cap in capacitor_db
            if cap.get('voltage', 0) >= V_rated_min
        ]

        if not valid_caps:
            return None

        best_selection = None
        best_score = float('inf')

        for cap in valid_caps:
            # Calculate number of parallel caps needed for capacitance
            C_single = cap.get('capacitance', 0)
            if C_single <= 0:
                continue

            n_parallel_C = int(np.ceil(C_required / C_single))

            # Check ripple current capability if specified
            n_parallel_I = 1
            if I_ripple_RMS > 0:
                I_cap_max = cap.get('I_AC_Ripple', float('inf'))
                if isinstance(I_cap_max, str) or I_cap_max == 0:
                    I_cap_max = float('inf')
                if I_cap_max < float('inf'):
                    n_parallel_I = int(np.ceil(I_ripple_RMS / I_cap_max))

            # Take maximum of both requirements
            n_parallel = max(n_parallel_C, n_parallel_I)

            # Calculate volume (cylinder: π * (d/2)² * h)
            diameter = cap.get('diameter', 0) / 1000  # mm to m
            height = cap.get('height', 0) / 1000  # mm to m
            single_volume = np.pi * (diameter/2)**2 * height  # m³

            total_volume = single_volume * n_parallel * 1e6  # Convert to mm³

            # Calculate cost
            cost = cap.get('cost', 0)
            if isinstance(cost, str) or cost == 0:
                cost = 100  # Penalty for unknown cost
            total_cost = cost * n_parallel

            # Calculate ESR and losses
            ESR = cap.get('ESR', 0)
            if ESR > 0 and I_ripple_RMS > 0:
                # ESR reduces with parallel caps
                ESR_total = ESR / n_parallel
                P_loss = I_ripple_RMS**2 * ESR_total
            else:
                P_loss = 0

            # Multi-objective score (weighted sum)
            # Prioritize: volume (40%), cost (30%), loss (30%)
            score = 0.4 * total_volume + 0.3 * total_cost + 0.3 * P_loss * 1000

            if score < best_score:
                best_score = score
                best_selection = {
                    'capacitor': cap,
                    'part_number': cap.get('name', cap.get('id', 'Unknown')),
                    'manufacturer': cap.get('manufacturer', 'Unknown'),
                    'n_parallel': n_parallel,
                    'C_single': C_single,
                    'total_C': C_single * n_parallel,
                    'V_rated': cap.get('voltage', 0),
                    'ESR_single': ESR,
                    'ESR_total': ESR / n_parallel if ESR > 0 else 0,
                    'total_volume': total_volume,
                    'total_cost': total_cost,
                    'P_loss': P_loss,
                    'score': score
                }

        return best_selection

    def calculate_complete(self, params: Dict) -> Dict:
        """
        Complete capacitor selection calculation

        Args:
            params: Dictionary with parameters

        Returns:
            Selection results
        """
        P_out = params['P_out']
        V_out = params['V_out']
        V_out_min = params.get('V_out_min', 0.9 * V_out)
        T_hold = params.get('T_hold', 0.02)  # 20ms default
        f_in = params.get('f_in', 50)  # 50Hz default
        Delta_V_out = params.get('Delta_V_out', 0.05 * V_out)  # 5% ripple
        capacitor_db = params['capacitor_db']
        I_ripple_RMS = params.get('I_ripple_RMS', 0)

        # Calculate required capacitance (take max of both criteria)
        C_holdup = self.calculate_holdup_capacitance(P_out, T_hold, V_out, V_out_min)
        C_ripple = self.calculate_ripple_capacitance(P_out, f_in, Delta_V_out, V_out)

        C_required = max(C_holdup, C_ripple)

        # Voltage derating (use 80% of rated voltage)
        V_rated_min = V_out / 0.8

        # Select capacitors
        selection = self.select_capacitors(C_required, capacitor_db, V_rated_min, I_ripple_RMS)

        return {
            'C_holdup_required': C_holdup,
            'C_ripple_required': C_ripple,
            'C_required': C_required,
            'V_rated_min': V_rated_min,
            'selection': selection
        }


# Alias for backward compatibility
PFCCapacitorSelector = CapacitorSelection
