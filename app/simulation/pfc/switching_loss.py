"""
PFC Switching Loss Model
Based on Equations_PFC.pdf - Switching_Loss_Model.m
"""

import numpy as np
from typing import Dict, Any


class SwitchingLossModel:
    """FET Switching and Conduction Loss Calculator for PFC"""

    @staticmethod
    def calculate_fet_score(v_ds: float, P_FET: float) -> float:
        """
        Calculate FET score

        From PDF:
        Score_FET = v_ds * P_FET

        Args:
            v_ds: Drain-source voltage (V)
            P_FET: FET power dissipation (W)

        Returns:
            FET score
        """
        return v_ds * P_FET

    @staticmethod
    def calculate_conduction_loss(m_FET: int, I_sw_RMS: float,
                                  R_dson: float) -> float:
        """
        Calculate conduction loss

        From PDF:
        P_cond = m_FET * (I_sw_RMS)² * R_dson(T)

        Args:
            m_FET: Number of FETs in parallel
            I_sw_RMS: RMS current through switch (A)
            R_dson: Drain-source on-resistance at temperature (Ω)

        Returns:
            Conduction loss (W)
        """
        P_cond = m_FET * (I_sw_RMS ** 2) * R_dson
        return P_cond

    @staticmethod
    def calculate_gate_drive_loss(m_FET: int, Q_gate: float,
                                  V_gate: float, f_sw: float) -> float:
        """
        Calculate gate drive loss

        P_gate = m_FET * Q_gate * V_gate * f_sw

        Args:
            m_FET: Number of FETs
            Q_gate: Gate charge (C)
            V_gate: Gate drive voltage (V)
            f_sw: Switching frequency (Hz)

        Returns:
            Gate drive loss (W)
        """
        P_gate = m_FET * Q_gate * V_gate * f_sw
        return P_gate

    @staticmethod
    def calculate_switching_loss_from_energy(E_on: float, E_off: float,
                                            f_sw: float, m_FET: int = 1) -> Dict[str, float]:
        """
        Calculate switching loss from switching energies

        Args:
            E_on: Turn-on energy (J)
            E_off: Turn-off energy (J)
            f_sw: Switching frequency (Hz)
            m_FET: Number of FETs in parallel

        Returns:
            Dictionary with P_on, P_off, P_sw_total
        """
        P_on = E_on * f_sw
        P_off = E_off * f_sw
        P_sw_total = (P_on + P_off) * m_FET

        return {
            'P_on': P_on,
            'P_off': P_off,
            'P_sw_total': P_sw_total
        }

    @staticmethod
    def calculate_switching_loss_linear(V_ds: float, I_sw: float,
                                       t_rise: float, t_fall: float,
                                       f_sw: float, m_FET: int = 1) -> float:
        """
        Calculate switching loss using linear approximation

        P_sw = m_FET * 0.5 * V_ds * I_sw * (t_rise + t_fall) * f_sw

        Args:
            V_ds: Drain-source voltage (V)
            I_sw: Switching current (A)
            t_rise: Rise time (s)
            t_fall: Fall time (s)
            f_sw: Switching frequency (Hz)
            m_FET: Number of FETs

        Returns:
            Switching loss (W)
        """
        P_sw = m_FET * 0.5 * V_ds * I_sw * (t_rise + t_fall) * f_sw
        return P_sw

    @staticmethod
    def calculate_output_capacitance_loss(C_oss: float, V_ds: float,
                                         f_sw: float, m_FET: int = 1) -> float:
        """
        Calculate output capacitance related loss

        P_Coss = m_FET * 0.5 * C_oss * V_ds² * f_sw

        Args:
            C_oss: Output capacitance (F)
            V_ds: Drain-source voltage (V)
            f_sw: Switching frequency (Hz)
            m_FET: Number of FETs

        Returns:
            Coss loss (W)
        """
        P_Coss = m_FET * 0.5 * C_oss * (V_ds ** 2) * f_sw
        return P_Coss

    @staticmethod
    def calculate_diode_reverse_recovery(Q_rr: float, V_f: float,
                                        f_sw: float) -> float:
        """
        Calculate diode reverse recovery loss

        P_rr = Q_rr * V_f * f_sw

        Args:
            Q_rr: Reverse recovery charge (C)
            V_f: Forward voltage drop (V)
            f_sw: Switching frequency (Hz)

        Returns:
            Reverse recovery loss (W)
        """
        P_rr = Q_rr * V_f * f_sw
        return P_rr

    def calculate_total_fet_losses(self, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate total FET losses

        From PDF page 3:
        P_Qoss, P_gate, P_off, P_IV, P_DF components
        P_sw = P_Qoss + P_gate + P_off + P_IV + P_DF
        P_FET = P_sw + P_cond

        Args:
            params: Dictionary with FET parameters

        Returns:
            Complete FET loss breakdown
        """
        m_FET = params.get('m_FET', 1)
        I_sw_RMS = params['I_sw_RMS']
        R_dson = params['R_dson']
        Q_g = params.get('Q_g', 0)
        V_gate = params.get('V_gate', 12)
        f_sw = params['f_sw']
        V_ds = params['V_ds']
        I_sw = params.get('I_sw', I_sw_RMS)
        C_oss = params.get('C_oss', 0)

        # Conduction loss
        P_cond = self.calculate_conduction_loss(m_FET, I_sw_RMS, R_dson)

        # Gate drive loss
        P_gate = self.calculate_gate_drive_loss(m_FET, Q_g, V_gate, f_sw)

        # Coss loss
        P_Coss = self.calculate_output_capacitance_loss(C_oss, V_ds, f_sw, m_FET)

        # Switching loss (if energies provided)
        E_on = params.get('E_on', 0)
        E_off = params.get('E_off', 0)
        if E_on > 0 or E_off > 0:
            sw_losses = self.calculate_switching_loss_from_energy(E_on, E_off, f_sw, m_FET)
            P_sw = sw_losses['P_sw_total']
        else:
            # Use linear approximation
            t_rise = params.get('t_rise', 10e-9)
            t_fall = params.get('t_fall', 10e-9)
            P_sw = self.calculate_switching_loss_linear(V_ds, I_sw, t_rise, t_fall, f_sw, m_FET)

        # Body diode losses (if applicable)
        Q_rr = params.get('Q_rr', 0)
        V_f = params.get('V_f', 1.0)
        P_rr = self.calculate_diode_reverse_recovery(Q_rr, V_f, f_sw) if Q_rr > 0 else 0

        # Total switching losses
        P_sw_total = P_gate + P_Coss + P_sw + P_rr

        # Total FET loss
        P_FET = P_cond + P_sw_total

        return {
            'P_cond': P_cond,
            'P_gate': P_gate,
            'P_Coss': P_Coss,
            'P_sw': P_sw,
            'P_rr': P_rr,
            'P_sw_total': P_sw_total,
            'P_FET': P_FET
        }


# Static method wrapper for pfc_optimizer.py compatibility
class PFCSwitchingLossCalculator:
    """Wrapper class with static methods for PFC optimizer compatibility"""

    _instance = SwitchingLossModel()

    @staticmethod
    def calculate_total_fet_loss(m_FET: int, I_sw_RMS: float, I_sw_avg: float,
                                 V_ds: float, f_sw: float, fet_params: Dict[str, Any],
                                 V_gs: float = 12) -> Dict[str, float]:
        """
        Calculate total FET losses for PFC optimizer

        Args:
            m_FET: Number of FETs in parallel
            I_sw_RMS: RMS switch current (A)
            I_sw_avg: Average switch current (A)
            V_ds: Drain-source voltage (V)
            f_sw: Switching frequency (Hz)
            fet_params: FET parameters dictionary
            V_gs: Gate-source voltage (V)

        Returns:
            Dictionary with P_total, P_conduction, P_switching, P_gate
        """
        # Extract FET parameters (handle both JSON field names and expected names)
        # Use 'or' to handle None values from JSON null
        R_dson = fet_params.get("Rdson") or fet_params.get("R_dson_25C") or fet_params.get("R_dson") or 0.01
        Q_g = fet_params.get("Qg") or fet_params.get("Q_g") or 40e-9

        # C_oss might be an array - get first value or average
        C_oss_raw = fet_params.get("Coss") or fet_params.get("C_oss") or 100e-12
        if isinstance(C_oss_raw, list):
            C_oss = C_oss_raw[0] if len(C_oss_raw) > 0 else 100e-12
        else:
            C_oss = C_oss_raw if C_oss_raw else 100e-12

        t_rise = fet_params.get("t_r") or fet_params.get("t_rise") or 15e-9
        t_fall = fet_params.get("t_f") or fet_params.get("t_fall") or 15e-9
        Q_rr = fet_params.get("Qrr") or fet_params.get("Q_rr") or 50e-9

        # Temperature correction for R_dson (assume 100°C junction)
        R_dson_hot = R_dson * 1.5  # ~50% increase at 100°C

        # Conduction loss
        P_conduction = m_FET * (I_sw_RMS ** 2) * R_dson_hot

        # Gate drive loss
        P_gate = m_FET * Q_g * V_gs * f_sw

        # Switching loss (linear approximation)
        P_switching = m_FET * 0.5 * V_ds * I_sw_avg * (t_rise + t_fall) * f_sw

        # Output capacitance loss
        P_coss = m_FET * 0.5 * C_oss * (V_ds ** 2) * f_sw

        # Reverse recovery loss (body diode)
        P_rr = Q_rr * V_ds * f_sw

        # Total
        P_total = P_conduction + P_gate + P_switching + P_coss + P_rr

        return {
            "P_total": P_total,
            "P_conduction": P_conduction,
            "P_switching": P_switching + P_coss + P_rr,
            "P_gate": P_gate,
            "P_coss": P_coss,
            "P_rr": P_rr
        }

    @staticmethod
    def calculate_conduction_loss(m_FET: int, I_sw_RMS: float, R_dson: float) -> float:
        return SwitchingLossModel.calculate_conduction_loss(m_FET, I_sw_RMS, R_dson)

    @staticmethod
    def calculate_gate_drive_loss(m_FET: int, Q_gate: float, V_gate: float, f_sw: float) -> float:
        return SwitchingLossModel.calculate_gate_drive_loss(m_FET, Q_gate, V_gate, f_sw)

    @staticmethod
    def calculate_switching_loss_linear(V_ds: float, I_sw: float, t_rise: float,
                                        t_fall: float, f_sw: float, m_FET: int = 1) -> float:
        return SwitchingLossModel.calculate_switching_loss_linear(V_ds, I_sw, t_rise, t_fall, f_sw, m_FET)
