"""
Pytest configuration and fixtures
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_llc_params():
    """Sample LLC converter parameters for testing"""
    return {
        "V_in": 400,  # Input voltage (V)
        "V_out": 12,  # Output voltage (V)
        "I_out": 10,  # Output current (A)
        "P_out": 120,  # Output power (W)
        "f_sw_min": 80000,  # Min switching frequency (Hz)
        "f_sw_max": 150000,  # Max switching frequency (Hz)
        "T_amb": 25,  # Ambient temperature (°C)
        "eta_target": 0.95  # Target efficiency
    }


@pytest.fixture
def sample_pfc_params():
    """Sample PFC converter parameters for testing"""
    return {
        "V_in_RMS": 230,  # Input RMS voltage (V)
        "V_out": 400,  # Output voltage (V)
        "P_out": 500,  # Output power (W)
        "f_sw": 65000,  # Switching frequency (Hz)
        "T_amb": 25,  # Ambient temperature (°C)
        "eta_eff": 0.96  # Efficiency
    }


@pytest.fixture
def sample_fet():
    """Sample FET data for testing"""
    return {
        "part_number": "IPP60R099C6",
        "V_dss": 600,
        "I_d": 60,
        "R_dson": 0.099,
        "Q_g": 120e-9,
        "Q_rr": 0,
        "C_oss": 380e-12,
        "C_iss": 5200e-12,
        "t_r": 25e-9,
        "t_f": 15e-9
    }


@pytest.fixture
def sample_core():
    """Sample magnetic core data for testing"""
    return {
        "name": "ETD29",
        "type": "ETD",
        "material": "N87",
        "manufacturer": "TDK",
        "Ae": 7.6,  # cm²
        "Aw": 9.7,  # cm²
        "Ve": 5.3,  # cm³
        "le": 6.9,  # cm
        "Al": 610,  # nH/N²
        "MLT": 48,  # mm
        "volume": 5300,  # mm³
        "k": 44.5,
        "alpha": 1.63,
        "beta": 2.62,
        "B_sat": 0.39  # T
    }
