"""
Unit tests for Battery Parameters Module
Tests the batterypar.m formulas implementation
"""
import pytest
import numpy as np
from app.simulation.llc.battery_params import BatteryParameters


class TestBatteryParameters:
    """Test suite for battery/load parameter calculations"""

    def test_calculate_battery_current(self):
        """Test battery current calculation: I_bat = P / V_o"""
        P_out = 100  # W
        V_out = 12   # V

        I_bat = BatteryParameters.calculate_battery_current(P_out, V_out)

        expected = P_out / V_out
        assert abs(I_bat - expected) < 0.001
        assert I_bat > 0

    def test_calculate_load_resistance(self):
        """Test load resistance: R = V_o / I_bat"""
        V_out = 12   # V
        I_bat = 8.33  # A

        R_load = BatteryParameters.calculate_load_resistance(V_out, I_bat)

        expected = V_out / I_bat
        assert abs(R_load - expected) < 0.01
        assert R_load > 0

    def test_calculate_voltage_loss(self):
        """Test voltage loss calculation with efficiency"""
        P_out = 100       # W
        I_bat = 8.33      # A
        efficiency = 95   # %

        V_loss = BatteryParameters.calculate_voltage_loss(P_out, I_bat, efficiency)

        # V_loss = (P_o * (1 - η/100)) / (I_bat * η/100)
        eta = efficiency / 100
        expected = (P_out * (1 - eta)) / (I_bat * eta)

        assert abs(V_loss - expected) < 0.001
        assert V_loss >= 0

    def test_voltage_loss_higher_with_lower_efficiency(self):
        """Voltage loss should increase when efficiency decreases"""
        P_out = 100
        I_bat = 8.33

        V_loss_95 = BatteryParameters.calculate_voltage_loss(P_out, I_bat, 95)
        V_loss_90 = BatteryParameters.calculate_voltage_loss(P_out, I_bat, 90)

        assert V_loss_90 > V_loss_95

    def test_calculate_turns_ratio_corrected(self):
        """Test loss-corrected turns ratio with round()"""
        V_in = 400    # V
        V_out = 48    # V
        V_loss = 2.5  # V

        turns_ratio = BatteryParameters.calculate_turns_ratio_corrected(
            V_in, V_out, V_loss
        )

        # a = round(V_i / (V_o + V_loss))
        expected = round(V_in / (V_out + V_loss))

        assert turns_ratio == expected
        assert isinstance(turns_ratio, int)  # Must be integer

    def test_turns_ratio_uses_round(self):
        """Verify that round() is used, not floor or ceil"""
        V_in = 400
        V_out = 48
        V_loss = 2.5

        # V_in / (V_out + V_loss) = 400 / 50.5 = 7.92...
        # round(7.92) = 8
        # floor(7.92) = 7
        # ceil(7.92) = 8

        turns_ratio = BatteryParameters.calculate_turns_ratio_corrected(
            V_in, V_out, V_loss
        )

        assert turns_ratio == 8  # Should be round(7.92) = 8

    def test_turns_ratio_without_loss_correction(self):
        """Show difference between loss-corrected and simple calculation"""
        V_in = 400
        V_out = 48
        V_loss = 2.5

        # With loss correction
        turns_ratio_corrected = BatteryParameters.calculate_turns_ratio_corrected(
            V_in, V_out, V_loss
        )

        # Without loss correction (old method)
        turns_ratio_simple = round(V_in / V_out)

        # They should be different!
        assert turns_ratio_corrected != turns_ratio_simple
        assert turns_ratio_corrected == 8  # 400 / 50.5 ≈ 7.92 → 8
        assert turns_ratio_simple == 8       # 400 / 48 ≈ 8.33 → 8

    def test_calculate_equivalent_resistance(self):
        """Test equivalent resistance: R_e = (8 * a² * R) / π²"""
        turns_ratio = 8
        R_load = 1.44  # Ω

        R_e = BatteryParameters.calculate_equivalent_resistance(turns_ratio, R_load)

        expected = (8 * turns_ratio**2 * R_load) / (np.pi**2)
        assert abs(R_e - expected) < 0.01
        assert R_e > 0

    def test_equivalent_resistance_scales_with_turns_squared(self):
        """R_e should scale with turns ratio squared"""
        R_load = 1.0

        R_e_4 = BatteryParameters.calculate_equivalent_resistance(4, R_load)
        R_e_8 = BatteryParameters.calculate_equivalent_resistance(8, R_load)

        # R_e ∝ a²
        ratio = R_e_8 / R_e_4
        expected_ratio = (8**2) / (4**2)  # = 4

        assert abs(ratio - expected_ratio) < 0.01

    def test_calculate_voltage_gain_limits(self):
        """Test voltage gain limit calculations"""
        turns_ratio = 8
        V_out = 48
        V_loss = 2.5
        V_in_min = 350
        V_in_max = 450

        result = BatteryParameters.calculate_voltage_gain_limits(
            turns_ratio, V_out, V_loss, V_in_min, V_in_max
        )

        # M_g_max = (a * (V_o + V_loss)) / V_imin
        V_out_corrected = V_out + V_loss
        expected_M_max = (turns_ratio * V_out_corrected) / V_in_min
        expected_M_min = (turns_ratio * V_out_corrected) / V_in_max

        assert abs(result['M_g_max'] - expected_M_max) < 0.01
        assert abs(result['M_g_min'] - expected_M_min) < 0.01
        assert result['V_out_corrected'] == V_out_corrected
        assert result['M_g_max'] > result['M_g_min']  # Max at min input voltage

    def test_voltage_gain_uses_loss_correction(self):
        """Verify voltage gain uses (V_o + V_loss) not just V_o"""
        turns_ratio = 8
        V_out = 48
        V_loss = 2.5
        V_in_min = 350

        result = BatteryParameters.calculate_voltage_gain_limits(
            turns_ratio, V_out, V_loss, V_in_min, V_in_min
        )

        # With loss correction
        M_with_loss = result['M_g_max']

        # Without loss correction would give
        M_without_loss = (turns_ratio * V_out) / V_in_min

        # They should be different
        assert abs(M_with_loss - M_without_loss) > 0.01
        # With loss correction should be higher (larger numerator)
        assert M_with_loss > M_without_loss

    def test_calculate_all_parameters(self):
        """Test complete parameter calculation workflow"""
        V_in_nom = 400
        V_in_min = 350
        V_in_max = 450
        V_out = 48
        P_out = 100
        efficiency = 95

        result = BatteryParameters.calculate_all_parameters(
            V_in_nom, V_in_min, V_in_max, V_out, P_out, efficiency
        )

        # Check all expected keys are present
        assert 'I_bat' in result
        assert 'R_load' in result
        assert 'V_loss' in result
        assert 'turns_ratio' in result
        assert 'R_e' in result
        assert 'M_g_max' in result
        assert 'M_g_min' in result
        assert 'V_out_corrected' in result

        # Check values are reasonable
        assert result['I_bat'] > 0
        assert result['R_load'] > 0
        assert result['V_loss'] >= 0
        assert result['turns_ratio'] > 0
        assert isinstance(result['turns_ratio'], int)
        assert result['R_e'] > 0
        assert result['M_g_max'] > result['M_g_min']

    def test_complete_workflow_example_100W(self):
        """Test realistic 400V → 48V, 100W LLC example"""
        result = BatteryParameters.calculate_all_parameters(
            V_in_nom=400,
            V_in_min=350,
            V_in_max=450,
            V_out=48,
            P_out=100,
            efficiency=95
        )

        # Expected values (approximate)
        assert abs(result['I_bat'] - 2.083) < 0.01  # 100W / 48V
        assert abs(result['R_load'] - 23.04) < 0.1  # 48V / 2.083A
        assert result['V_loss'] > 0  # Should have some loss
        assert result['V_loss'] < 5  # But not too much
        assert result['turns_ratio'] >= 7
        assert result['turns_ratio'] <= 9
        assert result['R_e'] > 10  # Reasonable equivalent resistance

    def test_complete_workflow_example_1kW(self):
        """Test realistic 400V → 48V, 1kW LLC example"""
        result = BatteryParameters.calculate_all_parameters(
            V_in_nom=400,
            V_in_min=350,
            V_in_max=450,
            V_out=48,
            P_out=1000,
            efficiency=95
        )

        # Expected values (approximate)
        assert abs(result['I_bat'] - 20.83) < 0.01  # 1000W / 48V
        assert abs(result['R_load'] - 2.304) < 0.01  # 48V / 20.83A
        assert result['turns_ratio'] >= 7
        assert result['turns_ratio'] <= 9

    def test_edge_case_zero_current(self):
        """Test handling of zero current edge case"""
        V_out = 12
        I_bat = 0

        R_load = BatteryParameters.calculate_load_resistance(V_out, I_bat)
        assert R_load == float('inf')

    def test_edge_case_zero_efficiency(self):
        """Test handling of zero efficiency edge case"""
        P_out = 100
        I_bat = 8.33
        efficiency = 0

        V_loss = BatteryParameters.calculate_voltage_loss(P_out, I_bat, efficiency)
        assert V_loss == 0  # Should return 0 for invalid efficiency

    def test_edge_case_100_percent_efficiency(self):
        """Test 100% efficiency gives zero voltage loss"""
        P_out = 100
        I_bat = 8.33
        efficiency = 100

        V_loss = BatteryParameters.calculate_voltage_loss(P_out, I_bat, efficiency)
        assert V_loss == 0  # No loss at 100% efficiency

    def test_different_power_levels(self):
        """Test battery parameters across different power levels"""
        V_in_nom = 400
        V_out = 48
        efficiency = 95

        powers = [50, 100, 250, 500, 1000]  # W

        for P_out in powers:
            result = BatteryParameters.calculate_all_parameters(
                V_in_nom, V_in_nom, V_in_nom, V_out, P_out, efficiency
            )

            # All should have valid results
            assert result['I_bat'] > 0
            assert result['R_load'] > 0
            assert result['turns_ratio'] > 0
            assert result['R_e'] > 0

            # Current should scale with power
            expected_current = P_out / V_out
            assert abs(result['I_bat'] - expected_current) < 0.01
