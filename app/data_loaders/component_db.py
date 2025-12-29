"""
Component Database Loader
Loads and caches component databases from JSON files
"""

import json
import os
from typing import Dict, List, Optional
from functools import lru_cache
from pathlib import Path


class ComponentDatabase:
    """Component Database Loader with Caching"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize database loader

        Args:
            data_dir: Directory containing JSON database files
                     If None, uses app/data directory
        """
        if data_dir is None:
            # Get path to app/data directory
            current_dir = Path(__file__).parent
            data_dir = current_dir.parent / 'data'

        self.data_dir = Path(data_dir)

        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

    def _load_json(self, filename: str) -> Dict:
        """Load JSON file from data directory"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            print(f"Warning: {filename} not found, returning empty dict")
            return {}

        with open(filepath, 'r') as f:
            return json.load(f)

    @lru_cache(maxsize=32)
    def load_fets(self) -> List[Dict]:
        """
        Load FET database

        Returns:
            List of FET dictionaries
        """
        data = self._load_json('fets.json')
        return data.get('fets', [])

    @lru_cache(maxsize=32)
    def load_heatsinks(self) -> List[Dict]:
        """
        Load heatsink database

        Returns:
            List of heatsink dictionaries
        """
        data = self._load_json('heatsinks.json')
        return data.get('heatsinks', [])

    @lru_cache(maxsize=32)
    def load_capacitors(self, cap_type: str = 'buscaps') -> List[Dict]:
        """
        Load capacitor database

        Args:
            cap_type: Type of capacitors ('buscaps', 'outcaps', etc.)

        Returns:
            List of capacitor dictionaries
        """
        filename = f'{cap_type}.json'
        data = self._load_json(filename)
        return data.get('capacitors', [])

    @lru_cache(maxsize=32)
    def load_cores(self, core_type: str = 'inductor') -> List[Dict]:
        """
        Load magnetic core database

        Args:
            core_type: Type of cores ('inductor', 'transformer', 'cmc')

        Returns:
            List of core dictionaries
        """
        filename = f'{core_type}_cores.json'
        data = self._load_json(filename)
        return data.get('cores', [])

    def search_fets(self, V_dss_min: float = 0, I_d_min: float = 0,
                   R_dson_max: float = float('inf'),
                   manufacturer: Optional[str] = None) -> List[Dict]:
        """
        Search FETs with filters

        Args:
            V_dss_min: Minimum drain-source voltage (V)
            I_d_min: Minimum drain current (A)
            R_dson_max: Maximum on-resistance (Ω)
            manufacturer: Filter by manufacturer name

        Returns:
            Filtered list of FETs
        """
        fets = self.load_fets()

        filtered = [
            fet for fet in fets
            if (fet.get('V_dss', 0) >= V_dss_min and
                fet.get('I_d', 0) >= I_d_min and
                fet.get('R_dson_25C', float('inf')) <= R_dson_max and
                (manufacturer is None or fet.get('manufacturer', '').lower() == manufacturer.lower()))
        ]

        # Sort by R_dson (lower is better)
        filtered.sort(key=lambda x: x.get('R_dson_25C', float('inf')))

        return filtered

    def search_heatsinks(self, X_max: Optional[float] = None,
                        Y_max: Optional[float] = None,
                        R_sa_max: Optional[float] = None) -> List[Dict]:
        """
        Search heatsinks with dimensional constraints

        Args:
            X_max: Maximum X dimension (mm)
            Y_max: Maximum Y dimension (mm)
            R_sa_max: Maximum thermal resistance (°C/W) - estimated

        Returns:
            Filtered list of heatsinks
        """
        heatsinks = self.load_heatsinks()

        filtered = []
        for hs in heatsinks:
            # Check dimensional constraints
            if X_max is not None and hs.get('X', float('inf')) > X_max:
                continue
            if Y_max is not None and hs.get('Y', float('inf')) > Y_max:
                continue

            # Estimate thermal resistance if needed
            if R_sa_max is not None:
                # Rough estimation: larger heatsinks have lower R_sa
                y_b = hs.get('y_b', 10)
                X = hs.get('X', 30)
                # Empirical: R_sa ≈ 20 / sqrt(area * height)
                R_sa_est = 20 / (X * y_b)**0.5
                if R_sa_est > R_sa_max:
                    continue

            filtered.append(hs)

        return filtered

    def search_capacitors(self, V_rated_min: float, C_min: float = 0,
                         cap_type: str = 'buscaps',
                         manufacturer: Optional[str] = None) -> List[Dict]:
        """
        Search capacitors with filters

        Args:
            V_rated_min: Minimum voltage rating (V)
            C_min: Minimum capacitance (F)
            cap_type: Type of capacitors
            manufacturer: Filter by manufacturer

        Returns:
            Filtered list of capacitors
        """
        caps = self.load_capacitors(cap_type)

        filtered = [
            cap for cap in caps
            if (cap.get('voltage', 0) >= V_rated_min and
                cap.get('capacitance', 0) >= C_min and
                (manufacturer is None or cap.get('manufacturer', '').lower() == manufacturer.lower()))
        ]

        # Sort by capacitance (higher is better for same voltage)
        filtered.sort(key=lambda x: x.get('capacitance', 0), reverse=True)

        return filtered

    def get_fet_by_part_number(self, part_number: str) -> Optional[Dict]:
        """
        Get specific FET by part number

        Args:
            part_number: FET part number

        Returns:
            FET dictionary or None if not found
        """
        fets = self.load_fets()

        for fet in fets:
            if fet.get('part_number', '').lower() == part_number.lower():
                return fet

        return None

    def clear_cache(self):
        """Clear all cached database loads"""
        self.load_fets.cache_clear()
        self.load_heatsinks.cache_clear()
        self.load_capacitors.cache_clear()
        self.load_cores.cache_clear()


# Global instance for easy access
_db_instance = None


def get_component_db() -> ComponentDatabase:
    """
    Get global ComponentDatabase instance (singleton pattern)

    Returns:
        ComponentDatabase instance
    """
    global _db_instance

    if _db_instance is None:
        _db_instance = ComponentDatabase()

    return _db_instance
