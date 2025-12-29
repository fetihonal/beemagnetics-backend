"""
Unit tests for Frequency Range Solver Module
Tests the rangeoffreq.m polynomial solver implementation
"""
import pytest
import numpy as np
from app.simulation.llc.frequency_range import FrequencyRangeSolver


class TestFrequencyRangeSolver:
    """Test suite for automatic frequency range calculation"""

    def test_polynomial_solver_basic(self):
        """Test basic polynomial solving"""
        Q = 0.5
        Ln = 5
        M = 1.0  # Unity gain at resonance

        F = FrequencyRangeSolver.solve_frequency_polynomial(Q, Ln, M)

        # Should return a positive value
        assert F is not None
        assert F > 0

    def test_polynomial_solver_above_resonance(self):
        """Test polynomial solver for operation above resonance"""
        Q = 0.5
        Ln = 5
        M = 0.8  # Gain < 1 → frequency above resonance

        F = FrequencyRangeSolver.solve_frequency_polynomial(Q, Ln, M)

        # For M < 1, F should be > 1 (above resonance)
        assert F > 1

    def test_polynomial_solver_below_resonance(self):
        """Test polynomial solver for operation below resonance"""
        Q = 0.5
        Ln = 5
        M = 1.2  # Gain > 1 → frequency below resonance

        F = FrequencyRangeSolver.solve_frequency_polynomial(Q, Ln, M)

        # For M > 1, F should be < 1 (below resonance)
        assert F < 1

    def test_polynomial_solver_invalid_inputs(self):
        """Test polynomial solver with invalid inputs"""
        # Negative Q
        F = FrequencyRangeSolver.solve_frequency_polynomial(-0.5, 5, 1.0)
        assert F is None

        # Zero Ln
        F = FrequencyRangeSolver.solve_frequency_polynomial(0.5, 0, 1.0)
        assert F is None

        # Negative M
        F = FrequencyRangeSolver.solve_frequency_polynomial(0.5, 5, -1.0)
        assert F is None

    def test_frequency_range_at_voltage_gain(self):
        """Test frequency range calculation from voltage gain limits"""
        Q = 0.5
        Ln = 5
        M_max = 1.2  # At min input
        M_min = 0.8  # At max input
        f_0 = 100e3  # 100kHz resonance

        result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M_max, M_min, f_0
        )

        # Check all expected keys
        assert 'f_sw_min' in result
        assert 'f_sw_max' in result
        assert 'f_0' in result
        assert 'F_min' in result
        assert 'F_max' in result

        # Verify frequencies are reasonable
        assert result['f_sw_min'] > 0
        assert result['f_sw_max'] > result['f_sw_min']
        assert result['f_0'] == f_0

        # F_min should be < 1 (below resonance for higher gain)
        assert result['F_min'] < 1

        # F_max should be > 1 (above resonance for lower gain)
        assert result['F_max'] > 1

    def test_frequency_range_spans_resonance(self):
        """Test that frequency range typically spans resonant frequency"""
        Q = 0.5
        Ln = 5
        M_max = 1.2
        M_min = 0.8
        f_0 = 100e3

        result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M_max, M_min, f_0
        )

        # Frequency range should span resonance
        assert result['f_sw_min'] < f_0 < result['f_sw_max']

    def test_calculate_frequency_range_for_llc_complete(self):
        """Test complete LLC frequency range calculation"""
        V_in_min = 350
        V_in_max = 450
        V_out = 48
        n = 8
        Q = 0.5
        Ln = 5
        f_0 = 100e3

        result = FrequencyRangeSolver.calculate_frequency_range_for_llc(
            V_in_min, V_in_max, V_out, n, Q, Ln, f_0
        )

        # Check voltage gain calculations
        assert 'M_max' in result
        assert 'M_min' in result

        # M_max at min input
        expected_M_max = (V_out * n) / V_in_min
        assert abs(result['M_max'] - expected_M_max) < 0.01

        # M_min at max input
        expected_M_min = (V_out * n) / V_in_max
        assert abs(result['M_min'] - expected_M_min) < 0.01

        # Verify frequencies
        assert result['f_sw_min'] > 0
        assert result['f_sw_max'] > result['f_sw_min']

    def test_realistic_example_400V_to_48V(self):
        """Test realistic 400V → 48V LLC converter"""
        V_in_min = 350
        V_in_max = 450
        V_in_nom = 400
        V_out = 48
        n = 8  # Turns ratio
        Q = 0.4
        Ln = 5
        f_0 = 100e3

        result = FrequencyRangeSolver.calculate_frequency_range_for_llc(
            V_in_min, V_in_max, V_out, n, Q, Ln, f_0
        )

        # At 400V nominal, gain should be close to 1
        M_nom = (V_out * n) / V_in_nom
        assert abs(M_nom - 0.96) < 0.05  # Should be close to 1

        # Frequency range should be reasonable (±20-30%)
        range_percent = result['frequency_range_percent']
        assert 10 < range_percent < 50

        # Should operate around resonance
        assert result['f_sw_min'] < f_0 < result['f_sw_max']

    def test_validate_frequency_range_good(self):
        """Test frequency range validation with good design"""
        f_sw_min = 80e3
        f_sw_max = 120e3
        f_0 = 100e3

        validation = FrequencyRangeSolver.validate_frequency_range(
            f_sw_min, f_sw_max, f_0
        )

        assert validation['is_valid'] is True
        assert validation['spans_resonance'] is True
        assert len(validation['warnings']) == 0

    def test_validate_frequency_range_narrow(self):
        """Test frequency range validation with narrow range"""
        f_sw_min = 95e3
        f_sw_max = 105e3
        f_0 = 100e3

        validation = FrequencyRangeSolver.validate_frequency_range(
            f_sw_min, f_sw_max, f_0
        )

        # Should warn about narrow range
        assert any('Narrow' in w for w in validation['warnings'])

    def test_validate_frequency_range_above_resonance(self):
        """Test frequency range validation when operating above resonance"""
        f_sw_min = 110e3  # Both above resonance
        f_sw_max = 150e3
        f_0 = 100e3

        validation = FrequencyRangeSolver.validate_frequency_range(
            f_sw_min, f_sw_max, f_0
        )

        # Should warn about losing ZVS
        assert any('ZVS' in w for w in validation['warnings'])
        assert validation['spans_resonance'] is False

    def test_validate_frequency_range_invalid_order(self):
        """Test frequency range validation with max < min"""
        f_sw_min = 120e3
        f_sw_max = 80e3  # Wrong order!
        f_0 = 100e3

        validation = FrequencyRangeSolver.validate_frequency_range(
            f_sw_min, f_sw_max, f_0
        )

        assert validation['is_valid'] is False
        assert any('not greater than min' in w for w in validation['warnings'])

    def test_recommend_resonant_frequency_at_resonance(self):
        """Test resonant frequency recommendation for operation at resonance"""
        f_sw_desired = 100e3

        f_0 = FrequencyRangeSolver.recommend_resonant_frequency(
            f_sw_desired, 'resonance'
        )

        assert f_0 == f_sw_desired

    def test_recommend_resonant_frequency_below(self):
        """Test resonant frequency recommendation for operation below resonance"""
        f_sw_desired = 100e3

        f_0 = FrequencyRangeSolver.recommend_resonant_frequency(
            f_sw_desired, 'below'
        )

        # Resonance should be higher to operate below it
        assert f_0 > f_sw_desired
        assert abs(f_0 - 120e3) < 1

    def test_recommend_resonant_frequency_above(self):
        """Test resonant frequency recommendation for operation above resonance"""
        f_sw_desired = 100e3

        f_0 = FrequencyRangeSolver.recommend_resonant_frequency(
            f_sw_desired, 'above'
        )

        # Resonance should be lower to operate above it
        assert f_0 < f_sw_desired
        assert abs(f_0 - 80e3) < 1

    def test_quick_frequency_range_simple_input(self):
        """Test quick frequency range with simplified inputs"""
        V_in_nom = 400
        V_in_range_percent = 20  # ±20%
        V_out = 48
        n = 8
        Q = 0.4
        Ln = 5
        f_sw_desired = 100e3

        result = FrequencyRangeSolver.quick_frequency_range(
            V_in_nom, V_in_range_percent, V_out, n, Q, Ln, f_sw_desired
        )

        # Check all expected data
        assert 'f_sw_min' in result
        assert 'f_sw_max' in result
        assert 'validation' in result

        # Input voltage range should be correctly calculated
        expected_V_min = V_in_nom * 0.8  # -20%
        expected_V_max = V_in_nom * 1.2  # +20%
        assert abs(result['V_in_min'] - expected_V_min) < 0.1
        assert abs(result['V_in_max'] - expected_V_max) < 0.1

        # Should use desired frequency as resonance
        assert result['f_0'] == f_sw_desired

    def test_different_Q_factors(self):
        """Test frequency range variation with different Q factors"""
        Ln = 5
        M_max = 1.2
        M_min = 0.8
        f_0 = 100e3

        Q_values = [0.2, 0.4, 0.6, 0.8]
        ranges = []

        for Q in Q_values:
            result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
                Q, Ln, M_max, M_min, f_0
            )
            ranges.append(result['frequency_range'])

        # All should produce valid ranges
        for r in ranges:
            assert r > 0

    def test_different_Ln_ratios(self):
        """Test frequency range variation with different Ln ratios"""
        Q = 0.4
        M_max = 1.2
        M_min = 0.8
        f_0 = 100e3

        Ln_values = [3, 5, 7, 10]
        ranges = []

        for Ln in Ln_values:
            result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
                Q, Ln, M_max, M_min, f_0
            )
            ranges.append(result['frequency_range'])

        # All should produce valid ranges
        for r in ranges:
            assert r > 0

    def test_voltage_gain_relationship(self):
        """Test that voltage gain and frequency have inverse relationship"""
        Q = 0.5
        Ln = 5
        f_0 = 100e3

        # High gain → Low frequency
        M_high = 1.5
        result_high = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M_high, M_high, f_0
        )

        # Low gain → High frequency
        M_low = 0.7
        result_low = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M_low, M_low, f_0
        )

        # Higher gain should give lower frequency
        assert result_high['f_sw_min'] < result_low['f_sw_min']

    def test_frequency_range_percentage_calculation(self):
        """Test frequency range percentage calculation"""
        Q = 0.5
        Ln = 5
        M_max = 1.3
        M_min = 0.7
        f_0 = 100e3

        result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M_max, M_min, f_0
        )

        # Verify percentage calculation
        expected_percent = ((result['f_sw_max'] - result['f_sw_min']) / f_0) * 100
        assert abs(result['frequency_range_percent'] - expected_percent) < 0.1

    def test_edge_case_unity_gain(self):
        """Test edge case where gain is unity (M=1)"""
        Q = 0.5
        Ln = 5
        M = 1.0  # Unity gain
        f_0 = 100e3

        result = FrequencyRangeSolver.calculate_frequency_range_at_voltage_gain(
            Q, Ln, M, M, f_0
        )

        # At unity gain, should be close to resonance
        assert abs(result['f_sw_min'] - f_0) < f_0 * 0.1  # Within 10%
        assert abs(result['f_sw_max'] - f_0) < f_0 * 0.1

    def test_wide_input_voltage_range(self):
        """Test with wide input voltage range (±30%)"""
        V_in_nom = 400
        V_in_range_percent = 30  # ±30%
        V_out = 48
        n = 8
        Q = 0.4
        Ln = 5
        f_sw_desired = 100e3

        result = FrequencyRangeSolver.quick_frequency_range(
            V_in_nom, V_in_range_percent, V_out, n, Q, Ln, f_sw_desired
        )

        # Wide voltage range → Wide frequency range
        assert result['frequency_range_percent'] > 30

    def test_narrow_input_voltage_range(self):
        """Test with narrow input voltage range (±5%)"""
        V_in_nom = 400
        V_in_range_percent = 5  # ±5%
        V_out = 48
        n = 8
        Q = 0.4
        Ln = 5
        f_sw_desired = 100e3

        result = FrequencyRangeSolver.quick_frequency_range(
            V_in_nom, V_in_range_percent, V_out, n, Q, Ln, f_sw_desired
        )

        # Narrow voltage range → Narrow frequency range
        assert result['frequency_range_percent'] < 20

    def test_multiple_operating_points(self):
        """Test frequency calculation at multiple operating points"""
        Q = 0.5
        Ln = 5
        f_0 = 100e3

        gains = [0.6, 0.8, 1.0, 1.2, 1.4]
        frequencies = []

        for M in gains:
            F = FrequencyRangeSolver.solve_frequency_polynomial(Q, Ln, M)
            if F is not None:
                frequencies.append(F * f_0)

        # Should have solution for all gains
        assert len(frequencies) == len(gains)

        # Frequencies should decrease as gain increases
        for i in range(len(frequencies) - 1):
            assert frequencies[i] >= frequencies[i + 1]
