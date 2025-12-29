"""
Unit tests for PFC Core Loss Calculator
"""
import pytest
import numpy as np
from app.simulation.pfc.core_loss import PFCCoreLossCalculator


class TestPFCCoreLossCalculator:
    """Test suite for PFC core loss calculations"""

    def test_inductor_currents(self, sample_pfc_params):
        """Test inductor current calculations"""
        result = PFCCoreLossCalculator.calculate_inductor_currents(
            P_out=sample_pfc_params["P_out"],
            eta_eff=sample_pfc_params["eta_eff"],
            V_in_RMS=sample_pfc_params["V_in_RMS"]
        )

        assert "I_in_RMS" in result
        assert "I_lf_PEAK" in result
        assert result["I_in_RMS"] > 0
        assert result["I_lf_PEAK"] > result["I_in_RMS"]  # Peak should be higher

    def test_ripple_current(self, sample_pfc_params):
        """Test ripple current calculation"""
        delta_I = PFCCoreLossCalculator.calculate_ripple_current(
            V_in_RMS=sample_pfc_params["V_in_RMS"],
            V_out=sample_pfc_params["V_out"],
            f_sw=sample_pfc_params["f_sw"],
            L=500e-6  # 500 µH
        )

        assert delta_I > 0
        assert delta_I < 10  # Reasonable ripple current

    def test_turns_calculation(self, sample_core):
        """Test number of turns calculation"""
        N = PFCCoreLossCalculator.calculate_turns(
            L=500e-6,  # 500 µH
            I_peak=5,  # 5A
            B_max=0.3,  # 0.3T
            Ae=sample_core["Ae"]
        )

        assert N > 0
        assert isinstance(N, int)
        assert N < 200  # Reasonable number of turns

    def test_flux_density(self, sample_core):
        """Test maximum flux density calculation"""
        B_max = PFCCoreLossCalculator.calculate_max_flux_density(
            L=500e-6,
            I_peak=5,
            N=50,
            Ae=sample_core["Ae"]
        )

        assert B_max > 0
        assert B_max < sample_core["B_sat"]  # Must be below saturation

    def test_copper_loss(self):
        """Test copper loss calculation"""
        P_cu = PFCCoreLossCalculator.calculate_copper_loss(
            I_rms=2.5,
            N=50,
            MLT=0.048,  # 48mm
            wire_diameter=1.0  # 1mm
        )

        assert P_cu > 0
        assert P_cu < 50  # Reasonable copper loss

    def test_core_loss_steinmetz(self, sample_core):
        """Test Steinmetz core loss calculation"""
        P_core = PFCCoreLossCalculator.calculate_core_loss_steinmetz(
            k=sample_core["k"],
            alpha=sample_core["alpha"],
            beta=sample_core["beta"],
            f=65000,  # 65kHz
            B_peak=0.3,  # 0.3T
            Ve=sample_core["Ve"]
        )

        assert P_core > 0
        assert P_core < 20  # Reasonable core loss for this size

    def test_total_inductor_loss(self, sample_pfc_params, sample_core):
        """Test total inductor loss calculation"""
        result = PFCCoreLossCalculator.calculate_total_inductor_loss(
            V_in_RMS=sample_pfc_params["V_in_RMS"],
            V_out=sample_pfc_params["V_out"],
            P_out=sample_pfc_params["P_out"],
            f_sw=sample_pfc_params["f_sw"],
            eta_eff=sample_pfc_params["eta_eff"],
            L=500e-6,
            core=sample_core,
            N=50,
            wire_diameter=1.0
        )

        assert "P_copper" in result
        assert "P_core" in result
        assert "P_total" in result
        assert "B_max" in result
        assert result["P_total"] == result["P_copper"] + result["P_core"]
        assert result["B_max"] < sample_core["B_sat"]
