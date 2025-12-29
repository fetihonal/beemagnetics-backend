"""
LLC FET Loss Calculator
For both primary and secondary side FETs
"""

import numpy as np
from typing import Dict, Any


class LLCFETLosses:
    """LLC Primary and Secondary FET Loss Calculations"""

    @staticmethod
    def calculate_fall_time(R_g: float, R_gext: float, C_iss: float,
                           V_plt: float, V_th: float) -> float:
        """
        Detailed fall time calculation

        t_fall = (R_g + R_gext) * C_iss * log(V_plt / V_th)

        This accounts for gate drive characteristics and FET parameters.
        More accurate than fixed timing assumptions.

        Args:
            R_g: Internal gate resistance (Ω)
            R_gext: External gate resistance (Ω)
            C_iss: Input capacitance (F)
            V_plt: Plateau voltage (V)
            V_th: Threshold voltage (V)

        Returns:
            Fall time (s)
        """
        if V_th <= 0 or V_plt <= V_th:
            return 50e-9  # Default 50ns

        t_fall = (R_g + R_gext) * C_iss * np.log(V_plt / V_th)
        return t_fall

    @staticmethod
    def check_zvs_condition(Lm: float, Lr: float, I_Lr_max: float,
                           C_eq: float, V_dc: float) -> Dict[str, Any]:
        """
        Check ZVS (Zero Voltage Switching) condition

        ZVS requires energy stored in inductors to be greater than
        energy stored in FET output capacitances:

        1/2 * (L_m + L_r) * (I_Lr_max)² ≥ 1/2 * (C_eq) * V_dc²

        Without ZVS, switching losses increase dramatically and
        reliability decreases due to hard switching.

        Args:
            Lm: Magnetizing inductance (H)
            Lr: Resonant inductance (H)
            I_Lr_max: Maximum resonant current (A)
            C_eq: Equivalent output capacitance (F)
            V_dc: DC bus voltage (V)

        Returns:
            Dict with:
              - zvs_ok: bool (True if ZVS achieved)
              - energy_inductor: float (J)
              - energy_capacitor: float (J)
              - margin: float (%)
        """
        E_inductor = 0.5 * (Lm + Lr) * (I_Lr_max ** 2)
        E_capacitor = 0.5 * C_eq * (V_dc ** 2)

        zvs_ok = E_inductor >= E_capacitor
        margin = ((E_inductor - E_capacitor) / E_capacitor) * 100 if E_capacitor > 0 else 0

        return {
            'zvs_ok': zvs_ok,
            'energy_inductor': E_inductor,
            'energy_capacitor': E_capacitor,
            'margin_percent': margin
        }

    @staticmethod
    def calculate_min_dead_time(C_eq: float, V_dc: float, I_mag: float,
                                Lm: float = None, f_r: float = None) -> float:
        """
        Minimum dead time required for ZVS

        Method 1 (preferred): t_dead = (C_eq * V_dc) / I_mag
        Method 2 (if I_mag unknown): t_dead ≈ (π/2) * √(Lm * C_eq)

        Dead time is the period when all switches are off, allowing
        magnetizing current to charge/discharge FET output capacitances for ZVS.

        The dead time must be long enough for the magnetizing current to
        fully charge one FET's Coss and discharge the other's.

        Args:
            C_eq: Equivalent output capacitance (F) - typically 2*Coss for half-bridge
            V_dc: DC bus voltage (V)
            I_mag: Peak magnetizing current (A) at switching instant
            Lm: Magnetizing inductance (H) - optional, for Method 2
            f_r: Resonant frequency (Hz) - optional, for verification

        Returns:
            Minimum dead time (s)
        """
        if I_mag > 0:
            # Method 1: Based on capacitor charging by magnetizing current
            # t_dead = Q / I = (C_eq * V_dc) / I_mag
            t_dead_min = (C_eq * V_dc) / I_mag
        elif Lm is not None and Lm > 0:
            # Method 2: Based on resonant transition
            # t_dead ≈ (π/2) * √(Lm * C_eq)
            t_dead_min = (np.pi / 2) * np.sqrt(Lm * C_eq)
        else:
            # Default: assume 200ns typical dead time
            t_dead_min = 200e-9

        return t_dead_min

    @staticmethod
    def calculate_body_diode_loss_deadtime(V_sd: float, I_sd: float,
                                          t_bdc: float, f_s: float,
                                          num_switches: int = 4) -> float:
        """
        Body diode conduction loss during dead time

        P_bodydiode,FB = num_switches * V_sd * I_sd * t_bdc * f_s

        During dead time, body diodes conduct before the FET channel turns on.
        This is additional loss in synchronous rectification.

        Args:
            V_sd: Body diode forward voltage (V), typically 0.7-1.0V
            I_sd: Body diode current (A)
            t_bdc: Body diode conduction time (s)
            f_s: Switching frequency (Hz)
            num_switches: Number of switches (4 for full-bridge)

        Returns:
            Body diode loss (W)
        """
        P_body_diode = num_switches * V_sd * I_sd * t_bdc * f_s
        return P_body_diode

    @staticmethod
    def calculate_primary_conduction_loss(I_pri_RMS: float, R_dson: float,
                                         n_parallel: int = 2) -> float:
        """
        Calculate primary FET conduction loss

        P_cond = (I_pri_RMS² * R_dson) / n_parallel

        LLC primary has 2 FETs in half-bridge (current shared)

        Args:
            I_pri_RMS: Primary RMS current (A)
            R_dson: On-resistance (Ω)
            n_parallel: Number of parallel FETs per switch

        Returns:
            Total conduction loss for all primary FETs (W)
        """
        # Each FET in half-bridge conducts for half period
        # RMS current per FET = I_pri_RMS / sqrt(2) / n_parallel
        I_per_fet = I_pri_RMS / np.sqrt(2) / n_parallel

        # Loss per FET
        P_per_fet = I_per_fet**2 * R_dson

        # Total for 2 FETs in half-bridge
        P_cond_total = 2 * n_parallel * P_per_fet

        return P_cond_total

    @staticmethod
    def calculate_primary_switching_loss(V_ds: float, I_sw: float,
                                        t_rise: float, t_fall: float,
                                        f_sw: float, n_fets: int = 2) -> float:
        """
        Calculate primary switching loss (ZVS should minimize this)

        P_sw = n_fets * 0.5 * V_ds * I_sw * (t_rise + t_fall) * f_sw

        Note: In proper ZVS operation, this should be near zero

        Args:
            V_ds: Drain-source voltage (V)
            I_sw: Switching current (A)
            t_rise: Rise time (s)
            t_fall: Fall time (s)
            f_sw: Switching frequency (Hz)
            n_fets: Total number of primary FETs

        Returns:
            Switching loss (W)
        """
        P_sw = n_fets * 0.5 * V_ds * I_sw * (t_rise + t_fall) * f_sw
        return P_sw

    @staticmethod
    def calculate_gate_drive_loss(Q_g: float, V_gs: float, f_sw: float,
                                  n_fets: int = 2) -> float:
        """
        Calculate gate drive loss

        P_gate = n_fets * Q_g * V_gs * f_sw

        Args:
            Q_g: Gate charge (C)
            V_gs: Gate-source voltage (V)
            f_sw: Switching frequency (Hz)
            n_fets: Number of FETs

        Returns:
            Gate drive loss (W)
        """
        P_gate = n_fets * Q_g * V_gs * f_sw
        return P_gate

    @staticmethod
    def calculate_output_capacitance_loss(C_oss: float, V_ds: float,
                                         f_sw: float, n_fets: int = 2) -> float:
        """
        Calculate output capacitance related loss

        P_Coss = n_fets * 0.5 * C_oss * V_ds² * f_sw

        Args:
            C_oss: Output capacitance (F)
            V_ds: Drain-source voltage (V)
            f_sw: Switching frequency (Hz)
            n_fets: Number of FETs

        Returns:
            Coss loss (W)
        """
        P_Coss = n_fets * 0.5 * C_oss * (V_ds**2) * f_sw
        return P_Coss

    @staticmethod
    def calculate_body_diode_loss(I_diode_avg: float, V_f: float,
                                  Q_rr: float, f_sw: float) -> float:
        """
        Calculate body diode conduction and reverse recovery loss

        P_diode = I_diode_avg * V_f + Q_rr * V_f * f_sw

        Args:
            I_diode_avg: Average diode current (A)
            V_f: Forward voltage drop (V)
            Q_rr: Reverse recovery charge (C)
            f_sw: Switching frequency (Hz)

        Returns:
            Body diode loss (W)
        """
        P_cond = I_diode_avg * V_f
        P_rr = Q_rr * V_f * f_sw
        return P_cond + P_rr

    def calculate_primary_total_losses(self, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate total primary FET losses

        Args:
            params: Dictionary with all FET parameters

        Returns:
            Breakdown of all primary FET losses
        """
        # Extract parameters
        I_pri_RMS = params['I_pri_RMS']
        R_dson = params['R_dson']
        V_ds = params['V_ds']
        f_sw = params['f_sw']
        n_parallel = params.get('n_parallel', 1)
        n_fets = 4 * n_parallel  # Full-bridge: 4 switches (2 legs × 2 FETs per leg)

        Q_g = params.get('Q_g', 0)
        V_gs = params.get('V_gs', 12)
        C_oss = params.get('C_oss', 0)

        # Switching parameters
        t_rise = params.get('t_rise', 10e-9)
        t_fall = params.get('t_fall', 10e-9)
        I_sw = params.get('I_sw', I_pri_RMS)

        # Body diode (for dead time conduction)
        I_diode_avg = params.get('I_diode_avg', 0)
        V_f = params.get('V_f', 1.0)
        Q_rr = params.get('Q_rr', 0)

        # Calculate individual components
        P_cond = self.calculate_primary_conduction_loss(I_pri_RMS, R_dson, n_parallel)
        P_gate = self.calculate_gate_drive_loss(Q_g, V_gs, f_sw, n_fets)
        P_Coss = self.calculate_output_capacitance_loss(C_oss, V_ds, f_sw, n_fets)

        # Switching loss (should be minimal with ZVS)
        P_sw = self.calculate_primary_switching_loss(V_ds, I_sw, t_rise, t_fall, f_sw, n_fets)

        # Body diode loss
        P_body = self.calculate_body_diode_loss(I_diode_avg, V_f, Q_rr, f_sw) if I_diode_avg > 0 else 0

        # Total
        P_total = P_cond + P_gate + P_Coss + P_sw + P_body

        return {
            'P_conduction': P_cond,
            'P_switching': P_sw,
            'P_gate': P_gate,
            'P_Coss': P_Coss,
            'P_body_diode': P_body,
            'P_total': P_total
        }

    @staticmethod
    def calculate_secondary_conduction_loss(I_sec_RMS: float, R_dson: float,
                                           n_parallel: int = 1) -> float:
        """
        Calculate secondary synchronous rectifier conduction loss

        P_cond = (I_sec_RMS² * R_dson) / n_parallel

        Args:
            I_sec_RMS: Secondary RMS current (A)
            R_dson: On-resistance (Ω)
            n_parallel: Number of parallel FETs per rectifier

        Returns:
            Conduction loss (W)
        """
        # Two rectifiers conduct alternately
        I_per_fet = I_sec_RMS / np.sqrt(2) / n_parallel

        # Loss per FET
        P_per_fet = I_per_fet**2 * R_dson

        # Total for 2 rectifiers
        P_cond_total = 2 * n_parallel * P_per_fet

        return P_cond_total

    @staticmethod
    def calculate_secondary_reverse_recovery(Q_rr: float, V_f: float,
                                            f_sw: float, n_fets: int = 2) -> float:
        """
        Calculate secondary FET body diode reverse recovery loss

        P_rr = n_fets * Q_rr * V_f * f_sw

        Args:
            Q_rr: Reverse recovery charge (C)
            V_f: Forward voltage (V)
            f_sw: Switching frequency (Hz)
            n_fets: Number of secondary FETs

        Returns:
            Reverse recovery loss (W)
        """
        P_rr = n_fets * Q_rr * V_f * f_sw
        return P_rr

    def calculate_secondary_total_losses(self, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate total secondary FET losses

        Args:
            params: Dictionary with all secondary FET parameters

        Returns:
            Breakdown of all secondary FET losses
        """
        # Extract parameters
        I_sec_RMS = params['I_sec_RMS']
        R_dson = params['R_dson']
        f_sw = params['f_sw']
        n_parallel = params.get('n_parallel', 1)
        n_fets = 2 * n_parallel  # Two synchronous rectifiers

        Q_g = params.get('Q_g', 0)
        V_gs = params.get('V_gs', 12)
        Q_rr = params.get('Q_rr', 0)
        V_f = params.get('V_f', 0.7)

        # Body diode parameters (during dead time)
        V_sd = params.get('V_sd', 0.7)  # Body diode forward voltage
        I_sd = params.get('I_sd', I_sec_RMS * 0.5)  # Approximate diode current
        t_bdc = params.get('t_bdc', 50e-9)  # Body diode conduction time (ns)

        # Calculate components
        P_cond = self.calculate_secondary_conduction_loss(I_sec_RMS, R_dson, n_parallel)
        P_gate = self.calculate_gate_drive_loss(Q_g, V_gs, f_sw, n_fets)
        P_rr = self.calculate_secondary_reverse_recovery(Q_rr, V_f, f_sw, n_fets)

        # Body diode loss during dead time (NEW!)
        P_body_diode = self.calculate_body_diode_loss_deadtime(
            V_sd, I_sd, t_bdc, f_sw, n_fets
        )

        # Total
        P_total = P_cond + P_gate + P_rr + P_body_diode

        return {
            'P_conduction': P_cond,
            'P_gate': P_gate,
            'P_reverse_recovery': P_rr,
            'P_body_diode': P_body_diode,
            'P_total': P_total
        }
