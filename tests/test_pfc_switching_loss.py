"""
Unit tests for PFC Switching Loss Calculator
"""
import pytest
from app.simulation.pfc.switching_loss import PFCSwitchingLossCalculator


class TestPFCSwitchingLossCalculator:
    """Test suite for PFC switching loss calculations"""

    def test_conduction_loss(self, sample_fet):
        """Test FET conduction loss calculation"""
        P_cond = PFCSwitchingLossCalculator.calculate_conduction_loss(
            m_FET=1,
            I_sw_RMS=5.0,
            R_dson=sample_fet["R_dson"]
        )

        assert P_cond > 0
        expected = 1 * (5.0 ** 2) * sample_fet["R_dson"]
        assert abs(P_cond - expected) < 0.01

    def test_switching_loss(self, sample_pfc_params, sample_fet):
        """Test FET switching loss calculation"""
        P_sw = PFCSwitchingLossCalculator.calculate_switching_loss(
            m_FET=1,
            V_in=sample_pfc_params["V_out"],  # Drain voltage
            I_sw_avg=3.0,
            f_sw=sample_pfc_params["f_sw"],
            t_r=sample_fet["t_r"],
            t_f=sample_fet["t_f"]
        )

        assert P_sw > 0
        assert P_sw < 50  # Reasonable switching loss

    def test_gate_drive_loss(self, sample_pfc_params, sample_fet):
        """Test gate drive loss calculation"""
        P_gate = PFCSwitchingLossCalculator.calculate_gate_drive_loss(
            m_FET=1,
            Q_g=sample_fet["Q_g"],
            V_gs=12,  # Gate drive voltage
            f_sw=sample_pfc_params["f_sw"]
        )

        assert P_gate > 0
        expected = 1 * sample_fet["Q_g"] * 12 * sample_pfc_params["f_sw"]
        assert abs(P_gate - expected) < 0.01

    def test_output_capacitance_loss(self, sample_pfc_params, sample_fet):
        """Test output capacitance loss calculation"""
        P_oss = PFCSwitchingLossCalculator.calculate_output_capacitance_loss(
            m_FET=1,
            C_oss=sample_fet["C_oss"],
            V_ds=sample_pfc_params["V_out"],
            f_sw=sample_pfc_params["f_sw"]
        )

        assert P_oss > 0
        expected = 1 * 0.5 * sample_fet["C_oss"] * (sample_pfc_params["V_out"] ** 2) * sample_pfc_params["f_sw"]
        assert abs(P_oss - expected) < 0.01

    def test_reverse_recovery_loss(self, sample_pfc_params, sample_fet):
        """Test reverse recovery loss calculation"""
        P_rr = PFCSwitchingLossCalculator.calculate_reverse_recovery_loss(
            m_FET=1,
            Q_rr=100e-9,  # 100nC
            V_ds=sample_pfc_params["V_out"],
            f_sw=sample_pfc_params["f_sw"]
        )

        assert P_rr >= 0  # Can be zero for MOSFETs with no body diode recovery

    def test_total_fet_loss(self, sample_pfc_params, sample_fet):
        """Test total FET loss calculation"""
        result = PFCSwitchingLossCalculator.calculate_total_fet_loss(
            m_FET=1,
            I_sw_RMS=5.0,
            I_sw_avg=3.0,
            V_ds=sample_pfc_params["V_out"],
            f_sw=sample_pfc_params["f_sw"],
            fet_params=sample_fet,
            V_gs=12
        )

        assert "P_conduction" in result
        assert "P_switching" in result
        assert "P_gate" in result
        assert "P_oss" in result
        assert "P_rr" in result
        assert "P_total" in result

        # Total should be sum of all components
        expected_total = (
            result["P_conduction"] +
            result["P_switching"] +
            result["P_gate"] +
            result["P_oss"] +
            result["P_rr"]
        )
        assert abs(result["P_total"] - expected_total) < 0.01
