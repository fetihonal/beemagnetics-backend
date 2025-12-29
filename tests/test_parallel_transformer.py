"""
Unit tests for Parallel Transformer Module
Tests the currentcalc.m parallel transformer corrections
"""
import pytest
import numpy as np
from app.simulation.llc.parallel_transformer import ParallelTransformerCalculator


class TestParallelTransformerCalculator:
    """Test suite for parallel transformer calculations"""

    def test_corrected_turns_ratio_single_transformer(self):
        """Test turns ratio with single transformer (ptrf=1)"""
        a = 8
        ptrf = 1

        n_corrected = ParallelTransformerCalculator.calculate_corrected_turns_ratio(a, ptrf)

        # With single transformer, should be same as original
        assert n_corrected == round(a / ptrf)
        assert n_corrected == 8

    def test_corrected_turns_ratio_two_transformers(self):
        """Test turns ratio with two parallel transformers"""
        a = 8
        ptrf = 2

        n_corrected = ParallelTransformerCalculator.calculate_corrected_turns_ratio(a, ptrf)

        # round(8 / 2) = round(4) = 4
        assert n_corrected == 4

    def test_corrected_turns_ratio_uses_round(self):
        """Verify round() is used for turns ratio correction"""
        a = 9
        ptrf = 2

        n_corrected = ParallelTransformerCalculator.calculate_corrected_turns_ratio(a, ptrf)

        # round(9 / 2) = round(4.5) = 4 (banker's rounding in Python 3)
        # Actually Python 3 uses round-half-to-even, so 4.5 → 4
        assert n_corrected == 4

    def test_corrected_turns_ratio_minimum_value(self):
        """Turns ratio should be at least 1"""
        a = 1
        ptrf = 10  # Many transformers

        n_corrected = ParallelTransformerCalculator.calculate_corrected_turns_ratio(a, ptrf)

        # Should not go below 1
        assert n_corrected >= 1

    def test_corrected_magnetizing_inductance_single(self):
        """Test Lm correction with single transformer"""
        Lm = 500e-6  # 500µH
        ptrf = 1

        Lm_corrected = ParallelTransformerCalculator.calculate_corrected_magnetizing_inductance(Lm, ptrf)

        # With single transformer, no change
        assert abs(Lm_corrected - Lm) < 1e-9

    def test_corrected_magnetizing_inductance_parallel(self):
        """Test Lm correction with parallel transformers"""
        Lm = 500e-6  # 500µH total
        ptrf = 2

        Lm_corrected = ParallelTransformerCalculator.calculate_corrected_magnetizing_inductance(Lm, ptrf)

        # Lm / ptrf = 500 / 2 = 250µH per transformer
        expected = Lm / ptrf
        assert abs(Lm_corrected - expected) < 1e-9
        assert abs(Lm_corrected - 250e-6) < 1e-9

    def test_parallel_currents_distribution(self):
        """Test current distribution between parallel transformers"""
        I_Lr_rms = 10  # A total
        I_sec_rms = 20  # A total
        I_Lm_max = 5   # A per transformer
        I_Lr_max = 15  # A total
        ptrf = 2

        result = ParallelTransformerCalculator.calculate_parallel_currents(
            I_Lr_rms, I_sec_rms, I_Lm_max, I_Lr_max, ptrf
        )

        # Each transformer should carry half
        assert abs(result['I_Lr_rms_each'] - 5) < 0.01  # 10/2
        assert abs(result['I_sec_rms_each'] - 10) < 0.01  # 20/2
        assert abs(result['I_Lm_max_each'] - I_Lm_max) < 0.01  # Same flux
        assert abs(result['I_Lr_max_each'] - 7.5) < 0.01  # 15/2
        assert result['total_transformers'] == ptrf

    def test_I_Lm_max_parallel_single_transformer(self):
        """Test I_Lm_max with single transformer"""
        n = 8
        V_o = 48
        L_m = 500e-6
        f_s = 100e3
        ptrf = 1

        I_Lm_max = ParallelTransformerCalculator.calculate_I_Lm_max_parallel(
            n, V_o, L_m, f_s, ptrf
        )

        # I_Lm_max = (n * V_o) / (4 * Lm * f_s)
        expected = (n * V_o) / (4 * L_m * f_s)
        assert abs(I_Lm_max - expected) < 0.01

    def test_I_Lm_max_parallel_two_transformers(self):
        """Test I_Lm_max with two parallel transformers"""
        n = 8
        V_o = 48
        L_m = 500e-6  # Total
        f_s = 100e3
        ptrf = 2

        I_Lm_max = ParallelTransformerCalculator.calculate_I_Lm_max_parallel(
            n, V_o, L_m, f_s, ptrf
        )

        # With corrections: n→4, Lm→250µH
        # I_Lm_max = (4 * 48) / (4 * 250e-6 * 100e3) = 192 / 100 = 1.92A
        n_corrected = round(n / ptrf)
        Lm_corrected = L_m / ptrf
        expected = (n_corrected * V_o) / (4 * Lm_corrected * f_s)

        assert abs(I_Lm_max - expected) < 0.01
        assert abs(I_Lm_max - 1.92) < 0.01

    def test_I_Lr_rms_parallel_calculation(self):
        """Test resonant current RMS with parallel transformers"""
        n = 8
        V_o = 48
        f_s = 100e3
        L_m = 500e-6
        I_o = 20
        f_0 = 100e3
        ptrf = 2

        I_Lr_rms = ParallelTransformerCalculator.calculate_I_Lr_rms_parallel(
            n, V_o, f_s, L_m, I_o, f_0, ptrf
        )

        # Should return positive value
        assert I_Lr_rms > 0
        # For two transformers, should be less than total
        assert I_Lr_rms < I_o

    def test_I_sec_rms_parallel_calculation(self):
        """Test secondary RMS current with parallel transformers"""
        I_o = 20  # A total
        f_0 = 100e3
        f_s = 100e3  # At resonance
        ptrf = 2

        I_sec_rms = ParallelTransformerCalculator.calculate_I_sec_rms_parallel(
            I_o, f_0, f_s, ptrf
        )

        # I_sec_rms = (sqrt(2) * π * I_o/ptrf) / 4 * sqrt(f_0/f_s)
        # At resonance: sqrt(f_0/f_s) = 1
        # I_sec_rms = (sqrt(2) * π * 10) / 4 ≈ 11.1A per transformer
        expected = (np.sqrt(2) * np.pi * (I_o/ptrf) / 4) * np.sqrt(f_0 / f_s)

        assert abs(I_sec_rms - expected) < 0.01
        assert I_sec_rms > 0

    def test_I_Lr_max_parallel_calculation(self):
        """Test maximum resonant current with parallel transformers"""
        I_o = 20
        f_o = 100e3
        f_s = 100e3
        n = 8
        I_Lm_max = 2
        ptrf = 2

        I_Lr_max = ParallelTransformerCalculator.calculate_I_Lr_max_parallel(
            I_o, f_o, f_s, n, I_Lm_max, ptrf
        )

        # Should return positive value
        assert I_Lr_max > 0
        # Should be greater than I_Lm_max
        assert I_Lr_max > I_Lm_max

    def test_calculate_all_currents_parallel_complete(self):
        """Test complete parallel current calculation workflow"""
        params = {
            'n': 8,
            'V_o': 48,
            'I_o': 20,
            'L_m': 500e-6,
            'f_s': 100e3,
            'f_0': 100e3,
            'ptrf': 2
        }

        result = ParallelTransformerCalculator.calculate_all_currents_parallel(params)

        # Check all expected keys
        assert 'n_corrected' in result
        assert 'Lm_corrected' in result
        assert 'I_Lm_max' in result
        assert 'I_Lr_rms' in result
        assert 'I_sec_rms' in result
        assert 'I_Lr_max' in result
        assert 'ptrf' in result
        assert 'I_o_per_transformer' in result
        assert 'power_per_transformer' in result

        # Verify corrections applied
        assert result['n_corrected'] == round(8 / 2)  # 4
        assert abs(result['Lm_corrected'] - 250e-6) < 1e-9  # 500/2
        assert result['ptrf'] == 2

        # Verify current distribution
        assert abs(result['I_o_per_transformer'] - 10) < 0.01  # 20/2

        # Verify power distribution
        expected_power = (48 * 20) / 2  # 480W per transformer
        assert abs(result['power_per_transformer'] - expected_power) < 1

    def test_determine_optimal_ptrf_low_power(self):
        """Test optimal transformer count for low power"""
        P_out = 500  # W
        P_max = 1000  # W per transformer

        ptrf = ParallelTransformerCalculator.determine_optimal_ptrf(P_out, P_max)

        # 500W < 1000W → Need only 1 transformer
        assert ptrf == 1

    def test_determine_optimal_ptrf_high_power(self):
        """Test optimal transformer count for high power"""
        P_out = 2500  # W
        P_max = 1000  # W per transformer

        ptrf = ParallelTransformerCalculator.determine_optimal_ptrf(P_out, P_max)

        # 2500W / 1000W = 2.5 → Need 3 transformers
        assert ptrf == 3

    def test_determine_optimal_ptrf_exact_multiple(self):
        """Test optimal transformer count when power is exact multiple"""
        P_out = 2000  # W
        P_max = 1000  # W per transformer

        ptrf = ParallelTransformerCalculator.determine_optimal_ptrf(P_out, P_max)

        # 2000W / 1000W = 2.0 → Need exactly 2 transformers
        assert ptrf == 2

    def test_realistic_example_1kW_single_transformer(self):
        """Test realistic 1kW design with single transformer"""
        params = {
            'n': 8,
            'V_o': 48,
            'I_o': 1000 / 48,  # ~20.83A
            'L_m': 500e-6,
            'f_s': 100e3,
            'f_0': 100e3,
            'ptrf': 1
        }

        result = ParallelTransformerCalculator.calculate_all_currents_parallel(params)

        # Verify single transformer operation
        assert result['ptrf'] == 1
        assert result['n_corrected'] == 8
        assert abs(result['Lm_corrected'] - 500e-6) < 1e-9
        assert abs(result['power_per_transformer'] - 1000) < 1

    def test_realistic_example_3kW_parallel_transformers(self):
        """Test realistic 3kW design with parallel transformers"""
        P_out = 3000  # W
        V_o = 48     # V
        I_o = P_out / V_o  # ~62.5A

        # Determine optimal number of transformers
        ptrf = ParallelTransformerCalculator.determine_optimal_ptrf(P_out, 1000)
        assert ptrf == 3  # Need 3 transformers for 3kW

        params = {
            'n': 8,
            'V_o': V_o,
            'I_o': I_o,
            'L_m': 500e-6,
            'f_s': 100e3,
            'f_0': 100e3,
            'ptrf': ptrf
        }

        result = ParallelTransformerCalculator.calculate_all_currents_parallel(params)

        # Verify parallel operation
        assert result['ptrf'] == 3
        assert result['n_corrected'] == round(8 / 3)  # ~3
        assert abs(result['Lm_corrected'] - 500e-6/3) < 1e-9
        assert abs(result['I_o_per_transformer'] - I_o/3) < 0.01
        assert abs(result['power_per_transformer'] - 1000) < 1

    def test_current_balance_between_transformers(self):
        """Test that currents are balanced between transformers"""
        I_total = 30  # A
        ptrf = 3

        result = ParallelTransformerCalculator.calculate_parallel_currents(
            I_Lr_rms=I_total,
            I_sec_rms=I_total,
            I_Lm_max=2,
            I_Lr_max=I_total,
            ptrf=ptrf
        )

        # Each should carry equal share
        assert abs(result['I_Lr_rms_each'] - 10) < 0.01
        assert abs(result['I_sec_rms_each'] - 10) < 0.01
        assert abs(result['I_Lr_max_each'] - 10) < 0.01

    def test_edge_case_zero_transformers(self):
        """Test handling of invalid ptrf=0"""
        a = 8
        ptrf = 0

        n_corrected = ParallelTransformerCalculator.calculate_corrected_turns_ratio(a, ptrf)

        # Should default to ptrf=1
        assert n_corrected == 8

    def test_edge_case_negative_transformers(self):
        """Test handling of invalid ptrf<0"""
        Lm = 500e-6
        ptrf = -2

        Lm_corrected = ParallelTransformerCalculator.calculate_corrected_magnetizing_inductance(Lm, ptrf)

        # Should default to ptrf=1
        assert abs(Lm_corrected - Lm) < 1e-9

    def test_power_scaling_with_transformers(self):
        """Test that total power scales correctly with number of transformers"""
        P_total = 5000  # W
        V_o = 48

        for ptrf in [1, 2, 3, 5]:
            params = {
                'n': 8,
                'V_o': V_o,
                'I_o': P_total / V_o,
                'L_m': 500e-6,
                'f_s': 100e3,
                'f_0': 100e3,
                'ptrf': ptrf
            }

            result = ParallelTransformerCalculator.calculate_all_currents_parallel(params)

            # Power per transformer should be total / ptrf
            expected_power_per_trf = P_total / ptrf
            assert abs(result['power_per_transformer'] - expected_power_per_trf) < 1

    def test_frequency_variation_with_parallel(self):
        """Test parallel operation at different frequencies"""
        params_base = {
            'n': 8,
            'V_o': 48,
            'I_o': 20,
            'L_m': 500e-6,
            'f_s': None,  # Will vary
            'f_0': 100e3,
            'ptrf': 2
        }

        frequencies = [80e3, 100e3, 120e3]

        for f_s in frequencies:
            params = params_base.copy()
            params['f_s'] = f_s

            result = ParallelTransformerCalculator.calculate_all_currents_parallel(params)

            # Should work at all frequencies
            assert result['I_Lr_rms'] > 0
            assert result['I_sec_rms'] > 0
            assert result['I_Lr_max'] > 0
