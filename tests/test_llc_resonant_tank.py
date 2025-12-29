"""
Unit tests for LLC Resonant Tank Calculator
"""
import pytest
import numpy as np
from app.simulation.llc.resonant_tank import LLCResonantTank


class TestLLCResonantTank:
    """Test suite for LLC resonant tank calculations"""

    def test_resonant_frequency(self):
        """Test resonant frequency calculation"""
        Lr = 100e-6  # 100 µH
        Cr = 100e-9  # 100 nF

        f_o = LLCResonantTank.calculate_resonant_frequency(Lr, Cr)

        expected = 1 / (2 * np.pi * np.sqrt(Lr * Cr))
        assert abs(f_o - expected) < 1  # Within 1Hz

    def test_quality_factor(self):
        """Test quality factor calculation"""
        Lr = 100e-6
        Cr = 100e-9
        R_ac = 10  # 10Ω

        Q = LLCResonantTank.calculate_quality_factor(Lr, Cr, R_ac)

        f_o = 1 / (2 * np.pi * np.sqrt(Lr * Cr))
        Z_o = np.sqrt(Lr / Cr)
        expected = Z_o / R_ac
        assert abs(Q - expected) < 0.01

    def test_inductance_ratio(self):
        """Test inductance ratio calculation"""
        Lr = 100e-6
        Lm = 500e-6

        Ln = LLCResonantTank.calculate_inductance_ratio(Lr, Lm)

        expected = (Lr + Lm) / Lr
        assert abs(Ln - expected) < 0.01

    def test_voltage_gain_fha(self):
        """Test voltage gain using First Harmonic Approximation"""
        f_sw = 100000  # 100kHz
        f_o = 100000   # 100kHz (at resonance)
        Q = 0.5
        Ln = 5

        M = LLCResonantTank.calculate_voltage_gain_fha(f_sw, f_o, Q, Ln)

        # At resonance (f_sw = f_o), gain should be close to 1
        assert M > 0
        assert M < 2  # Reasonable gain range

    def test_voltage_gain_below_resonance(self):
        """Test voltage gain below resonant frequency"""
        f_sw = 80000   # 80kHz
        f_o = 100000   # 100kHz
        Q = 0.5
        Ln = 5

        M = LLCResonantTank.calculate_voltage_gain_fha(f_sw, f_o, Q, Ln)

        assert M > 1  # Below resonance, gain should be higher

    def test_voltage_gain_above_resonance(self):
        """Test voltage gain above resonant frequency"""
        f_sw = 150000  # 150kHz
        f_o = 100000   # 100kHz
        Q = 0.5
        Ln = 5

        M = LLCResonantTank.calculate_voltage_gain_fha(f_sw, f_o, Q, Ln)

        assert M < 1  # Above resonance, gain should be lower

    def test_equivalent_load_resistance(self, sample_llc_params):
        """Test equivalent AC load resistance calculation"""
        n = sample_llc_params["V_in"] / (2 * sample_llc_params["V_out"])  # Turns ratio

        R_ac = LLCResonantTank.calculate_equivalent_load_resistance(
            V_out=sample_llc_params["V_out"],
            I_out=sample_llc_params["I_out"],
            n=n
        )

        assert R_ac > 0
        # R_ac = (8 * n^2 / π^2) * R_load
        R_load = sample_llc_params["V_out"] / sample_llc_params["I_out"]
        expected = (8 * n**2 / (np.pi**2)) * R_load
        assert abs(R_ac - expected) < 0.1

    def test_design_resonant_tank(self, sample_llc_params):
        """Test complete resonant tank design"""
        n = sample_llc_params["V_in"] / (2 * sample_llc_params["V_out"])

        result = LLCResonantTank.design_resonant_tank(
            V_in=sample_llc_params["V_in"],
            V_out=sample_llc_params["V_out"],
            I_out=sample_llc_params["I_out"],
            n=n,
            f_o=100000,  # 100kHz
            Q=0.5,
            Ln=5
        )

        assert "Lr" in result
        assert "Cr" in result
        assert "Lm" in result
        assert "R_ac" in result
        assert "f_o" in result
        assert "Q" in result
        assert "Ln" in result

        assert result["Lr"] > 0
        assert result["Cr"] > 0
        assert result["Lm"] > result["Lr"]  # Lm should be larger than Lr
