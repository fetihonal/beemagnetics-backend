"""
Unit tests for LLC Optimizer
"""
import pytest
from app.simulation.llc.llc_optimizer import LLCOptimizer


class TestLLCOptimizer:
    """Test suite for LLC optimizer"""

    def test_optimizer_initialization(self):
        """Test optimizer can be initialized"""
        optimizer = LLCOptimizer()
        assert optimizer is not None

    def test_run_optimization(self, sample_llc_params):
        """Test LLC optimization runs successfully"""
        optimizer = LLCOptimizer()

        input_data = {
            "V_in": sample_llc_params["V_in"],
            "V_out": sample_llc_params["V_out"],
            "I_out": sample_llc_params["I_out"],
            "P_out": sample_llc_params["P_out"],
            "f_sw_min": sample_llc_params["f_sw_min"],
            "f_sw_max": sample_llc_params["f_sw_max"],
            "T_amb": sample_llc_params["T_amb"],
        }

        result = optimizer.run_optimization(input_data)

        # Verify result structure
        assert "BestTotalEfficiency" in result
        assert "BestTotalLoss" in result
        assert "BestTotalVolume" in result
        assert "BestPowerDensity" in result
        assert "BestLr" in result
        assert "BestCr" in result
        assert "BestLm" in result
        assert "Bestfo" in result
        assert "BestQ" in result
        assert "BestLn" in result

    def test_optimization_results_validity(self, sample_llc_params):
        """Test that optimization results are physically valid"""
        optimizer = LLCOptimizer()

        input_data = {
            "V_in": sample_llc_params["V_in"],
            "V_out": sample_llc_params["V_out"],
            "I_out": sample_llc_params["I_out"],
            "P_out": sample_llc_params["P_out"],
            "f_sw_min": sample_llc_params["f_sw_min"],
            "f_sw_max": sample_llc_params["f_sw_max"],
            "T_amb": sample_llc_params["T_amb"],
        }

        result = optimizer.run_optimization(input_data)

        # Check efficiency is reasonable
        assert 0 < result["BestTotalEfficiency"] <= 100

        # Check losses are positive
        assert result["BestTotalLoss"] > 0
        assert result["BestPriFet_Loss"] >= 0
        assert result["BestSecFet_Loss"] >= 0
        assert result["BestTrf_Loss"] >= 0
        assert result["BestInd_Loss"] >= 0

        # Check component values are positive
        assert result["BestLr"] > 0
        assert result["BestCr"] > 0
        assert result["BestLm"] > 0
        assert result["Bestfo"] > 0
        assert result["BestQ"] > 0
        assert result["BestLn"] > 1  # Ln should be > 1

    def test_waveform_generation(self, sample_llc_params):
        """Test that waveforms are generated"""
        optimizer = LLCOptimizer()

        input_data = {
            "V_in": sample_llc_params["V_in"],
            "V_out": sample_llc_params["V_out"],
            "I_out": sample_llc_params["I_out"],
            "P_out": sample_llc_params["P_out"],
            "f_sw_min": sample_llc_params["f_sw_min"],
            "f_sw_max": sample_llc_params["f_sw_max"],
            "T_amb": sample_llc_params["T_amb"],
        }

        result = optimizer.run_optimization(input_data)

        # Check waveforms are present
        assert "t1" in result
        assert "t2" in result
        assert "Ilrp" in result
        assert "id1" in result

        # Waveforms should be lists
        assert isinstance(result["t1"], list)
        assert isinstance(result["Ilrp"], list)
