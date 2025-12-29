"""
PFC Thermal Analysis and Heatsink Selection
Based on Equations_PFC.pdf - Heatsink_surface_area.m
"""

import numpy as np
from typing import Dict, List, Optional


class ThermalAnalysis:
    """Heatsink and Thermal Calculations for PFC"""

    @staticmethod
    def calculate_required_thermal_resistance(T_max: float, T_ambient: float,
                                             P_FET: float, R_jc: float) -> float:
        """
        Calculate required heatsink thermal resistance

        From PDF:
        R_sa = (T_max - T_ambient) / P_FET - R_jc

        Args:
            T_max: Maximum junction temperature (°C)
            T_ambient: Ambient temperature (°C)
            P_FET: FET power dissipation (W)
            R_jc: Junction-to-case thermal resistance (°C/W)

        Returns:
            Required sink-to-ambient thermal resistance (°C/W)
        """
        if P_FET <= 0:
            return float('inf')

        R_sa = (T_max - T_ambient) / P_FET - R_jc
        return R_sa

    @staticmethod
    def calculate_thermal_resistance_ja(P_total: float, T_j_max: float,
                                        T_amb: float) -> float:
        """
        Calculate required junction-to-ambient thermal resistance

        R_ja = (T_j_max - T_amb) / P_total

        Args:
            P_total: Total power dissipation (W)
            T_j_max: Maximum junction temperature (°C)
            T_amb: Ambient temperature (°C)

        Returns:
            Required junction-to-ambient thermal resistance (°C/W)
        """
        if P_total <= 0:
            return float('inf')

        R_ja = (T_j_max - T_amb) / P_total
        return R_ja

    @staticmethod
    def calculate_heatsink_area(R_sa: float, a: float, b: float, c: float) -> float:
        """
        Calculate heatsink surface area from thermal resistance

        From PDF:
        Area_HS = a * (R_sa)^b + c

        This is an empirical curve fit for heatsink area vs thermal resistance

        Args:
            R_sa: Required thermal resistance (°C/W)
            a: Curve fit parameter
            b: Curve fit exponent
            c: Curve fit offset

        Returns:
            Heatsink surface area (cm²)
        """
        if R_sa <= 0:
            return float('inf')

        Area_HS = a * (R_sa ** b) + c
        return Area_HS

    @staticmethod
    def calculate_heatsink_volume(dimensions: Dict[str, float]) -> float:
        """
        Calculate heatsink volume from dimensions

        Args:
            dimensions: Dict with x_b, y_b, z_b, x_k, y_k, z_k in mm

        Returns:
            Volume in mm³
        """
        # Base volume
        x_b = dimensions.get('x_b', 0)
        y_b = dimensions.get('y_b', 0)
        z_b = dimensions.get('z_b', 0)

        # Fin volume
        x_k = dimensions.get('x_k', 0)
        y_k = dimensions.get('y_k', 0)
        z_k = dimensions.get('z_k', 0)

        V_base = x_b * y_b * z_b
        V_fins = x_k * y_k * z_k

        total_volume = V_base + V_fins

        return total_volume

    @staticmethod
    def select_heatsink(R_sa_required: float, heatsink_db: List[Dict],
                       mounting_area: Optional[Dict[str, float]] = None) -> Optional[Dict]:
        """
        Select appropriate heatsink from database

        Args:
            R_sa_required: Required thermal resistance (°C/W)
            heatsink_db: List of available heatsinks
            mounting_area: Optional constraint on X, Y dimensions (mm)

        Returns:
            Best heatsink selection, or None if no valid selection
        """
        # Filter heatsinks that meet thermal requirement
        # Note: Heatsink database doesn't have R_sa, so we estimate it
        # from dimensions using empirical formula

        valid_heatsinks = []

        for hs in heatsink_db:
            # Check dimensional constraints if specified
            if mounting_area:
                X_max = mounting_area.get('X_max', float('inf'))
                Y_max = mounting_area.get('Y_max', float('inf'))

                if hs.get('X', 0) > X_max or hs.get('Y', 0) > Y_max:
                    continue

            # Estimate thermal resistance from dimensions
            # Larger heatsinks have lower R_sa
            # Empirical: R_sa ≈ k / (fin_height * surface_area)

            # For U-type heatsinks in database:
            # Surface area estimation
            X = hs.get('X', 30)  # mm
            Y = hs.get('Y', 30)  # mm
            y_b = hs.get('y_b', 10)  # Fin height in mm
            P1 = hs.get('P1', 1)  # Fin thickness
            P2 = hs.get('P2', 1)

            # Rough estimation of thermal resistance
            # Base area
            base_area = X * Y  # mm²

            # Fin area (rough estimate)
            fin_area = 2 * X * y_b * 5  # Assume ~5 fins

            total_area = (base_area + fin_area) / 100  # Convert to cm²

            # Empirical formula: R_sa ≈ 20 / sqrt(total_area) for natural convection
            R_sa_estimated = 20 / np.sqrt(total_area)

            # Add to dict
            hs_copy = hs.copy()
            hs_copy['R_sa_estimated'] = R_sa_estimated

            # Check if meets requirement (with 20% margin)
            if R_sa_estimated <= R_sa_required * 1.2:
                valid_heatsinks.append(hs_copy)

        if not valid_heatsinks:
            return None

        # Select smallest volume that meets requirement
        best_hs = None
        best_volume = float('inf')

        for hs in valid_heatsinks:
            dimensions = {
                'x_b': hs.get('x_b', 0),
                'y_b': hs.get('y_b', 0),
                'z_b': hs.get('z_b', 0),
                'x_k': hs.get('x_k', 0),
                'y_k': hs.get('y_k', 0),
                'z_k': hs.get('z_k', 0)
            }

            volume = ThermalAnalysis.calculate_heatsink_volume(dimensions)

            if volume < best_volume:
                best_volume = volume
                best_hs = hs

        if best_hs is None:
            return None

        return {
            'heatsink': best_hs,
            'name': best_hs.get('name', 'Unknown'),
            'R_sa_estimated': best_hs.get('R_sa_estimated', 0),
            'R_sa_required': R_sa_required,
            'margin': best_hs.get('R_sa_estimated', 0) - R_sa_required,
            'volume': best_volume,
            'X': best_hs.get('X', 0),
            'Y': best_hs.get('Y', 0)
        }

    def calculate_complete(self, params: Dict) -> Dict:
        """
        Complete thermal analysis and heatsink selection

        Args:
            params: Dictionary with parameters

        Returns:
            Thermal analysis results
        """
        T_max = params.get('T_max', 125)  # °C
        T_ambient = params['T_ambient']  # °C
        P_FET = params['P_FET']  # W
        R_jc = params.get('R_jc', 0.5)  # °C/W (typical for TO-220)
        heatsink_db = params['heatsink_db']
        mounting_area = params.get('mounting_area', None)

        # Calculate required thermal resistance
        R_sa_required = self.calculate_required_thermal_resistance(
            T_max, T_ambient, P_FET, R_jc
        )

        # Select heatsink
        selection = self.select_heatsink(R_sa_required, heatsink_db, mounting_area)

        # Calculate actual junction temperature with selected heatsink
        if selection:
            R_sa_actual = selection['R_sa_estimated']
            T_junction = T_ambient + P_FET * (R_jc + R_sa_actual)
        else:
            T_junction = None

        return {
            'R_sa_required': R_sa_required,
            'R_jc': R_jc,
            'T_max': T_max,
            'T_ambient': T_ambient,
            'P_FET': P_FET,
            'selection': selection,
            'T_junction_estimated': T_junction
        }


# Alias for backward compatibility
ThermalCalculator = ThermalAnalysis
