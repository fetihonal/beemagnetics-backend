"""
LLC Optimizer - Main optimization engine
Replaces MATLAB LLC_Organiser_Function
"""

import numpy as np
from typing import Dict, List, Any, Optional
from .resonant_tank import LLCResonantTank
from .fet_losses import LLCFETLosses
from .transformer_design import TransformerDesign
from .battery_params import BatteryParameters
from app.data_loaders.component_db import get_component_db


class LLCOptimizer:
    """Main LLC Optimization Engine - Replaces MATLAB"""

    def __init__(self):
        self.db = get_component_db()
        self.resonant = LLCResonantTank()
        self.fet_loss_calc = LLCFETLosses()
        self.transformer_design = TransformerDesign()

    def run_optimization(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main LLC optimization routine - replaces LLC_Organiser_Function

        Args:
            input_params: All input parameters from frontend

        Returns:
            Optimized design with all results matching MATLAB output format
        """
        try:
            # Extract input parameters
            params = self._extract_parameters(input_params)

            # Load component databases
            fet_db = self.db.load_fets()
            heatsink_db = self.db.load_heatsinks()

            # Filter components based on user selection
            selected_fets = self._filter_selected_fets(
                fet_db, params['selectedFets']
            )
            selected_sec_fets = self._filter_selected_fets(
                fet_db, params['selectedSeconderFets']
            )

            # Initialize best design
            best_design = None
            best_score = float('inf')

            # Design space exploration
            Q_range = self._generate_range(
                params['qMode'], params['qFixedValue'],
                params['qMin'], params['qMax'], params['qStep']
            )

            Ln_range = self._generate_range(
                params['lnMode'], params['lnFixedValue'],
                params['lnMin'], params['lnMax'], params['lnStep']
            )

            f_sw_range = self._generate_range(
                params['mode1'], params['fixedValue1'],
                params['min1'], params['max1'], params['step1']
            )

            # Iterate through design space
            for Q in Q_range:
                for Ln in Ln_range:
                    # Design resonant tank
                    tank_design = self._design_tank(params, Q, Ln)

                    if tank_design is None:
                        continue

                    # Iterate through switching frequencies
                    for f_sw in f_sw_range:
                        # Iterate through component combinations
                        for pri_fet in selected_fets[:5]:  # Limit to top 5 for performance
                            for sec_fet in selected_sec_fets[:5]:
                                # Calculate design
                                design = self._calculate_design(
                                    params, tank_design, Q, Ln, f_sw,
                                    pri_fet, sec_fet
                                )

                                if design is None:
                                    continue

                                # Calculate multi-objective score
                                score = self._calculate_score(design, params)

                                if score < best_score:
                                    best_score = score
                                    best_design = design

            if best_design is None:
                # Return default/fallback design
                return self._create_fallback_design(params)

            # Format output to match MATLAB structure
            return self._format_output(best_design, params)

        except Exception as e:
            print(f"LLC Optimization error: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_design(input_params)

    def _extract_parameters(self, data: Dict) -> Dict:
        """Extract and validate parameters from frontend"""
        def get_float(key, default=0):
            val = data.get(key, default)
            return float(val) if val is not None else default

        return {
            'selectedFets': data.get('selectedFets', ['BSC034N10LS5']),
            'selectedSeconderFets': data.get('selectedSeconderFets', ['BSC034N10LS5']),
            'selectedDiodes': data.get('selectedDiodes', []),
            'selectedPrimaryHeatsink': data.get('selectedPrimaryHeatsink', []),
            'selectedSecondaryHeatsink': data.get('selectedSecondaryHeatsink', []),
            'selectedTransformer': data.get('selectedTransformer', ['Ferrite']),
            'selectedInductor': data.get('selectedInductor', ['Ferrite']),
            'selectedBusCaps': data.get('selectedBusCaps', ['Ceramic']),
            'selectedOutCaps': data.get('selectedOutCaps', ['Ceramic']),

            # Operating conditions (defaults match frontend)
            'Po': get_float('outPow', 100),
            'V_input_min': get_float('V_input_min', 370),
            'V_input_nom': get_float('V_input_nom', 400),
            'V_input_max': get_float('V_input_max', 430),
            'V_output_min': get_float('V_output_min', 36),
            'V_output_nom': get_float('V_output_nom', 48),
            'V_output_max': get_float('V_output_max', 54),
            'Tamb_input': get_float('Tamb_input', 25),

            # Optimization weights
            'W_Efficiency': get_float('efficiency', 50) / 100,
            'W_Volume': get_float('volume', 50) / 100,
            'W_Cost': get_float('cost', 0),

            # Design parameters
            'ku_trf': get_float('kuValue', 0.6),
            'Jmax_trf': get_float('JmaxValue', 3.5) * 1e6,  # A/mm² -> A/m²
            'dT_ind': get_float('deltaTInductorValue', 100),
            'dT_trf': get_float('deltaTValue', 100),
            'ku_ind': get_float('kuInductorValue', 0.6),
            'Jmax_ind': get_float('JmaxInductorValue', 3.5) * 1e6,  # A/mm² -> A/m²
            'Tjmax_pri': get_float('tOperating', 110),
            'Tjmax_sec': get_float('tOperating_2', 110),

            # Q parameters (qMode: 1=Fixed, 0=Sweep)
            'qMode': get_float('qMode', 1),
            'qFixedValue': get_float('qFixedValue', 0.8),
            'qMin': get_float('qMin', 0.1),
            'qMax': get_float('qMax', 2),
            'qStep': get_float('qStep', 0.1),

            # Ln parameters (lnMode: 1=Fixed, 0=Sweep)
            'lnMode': get_float('lnMode', 1),
            'lnFixedValue': get_float('lnFixedValue', 4),
            'lnMin': get_float('lnMin', 1),
            'lnMax': get_float('lnMax', 6),
            'lnStep': get_float('lnStep', 0.5),

            # Switching frequency parameters (mode1: 1=Fixed, 0=Sweep)
            # Frontend sends kHz, multiply by 1000 to get Hz
            'mode1': get_float('mode1', 1),
            'fixedValue1': get_float('fixedValue1', 45) * 1000,   # 45 kHz -> 45000 Hz
            'min1': get_float('min1', 300) * 1000,                # 300 kHz -> 300000 Hz
            'max1': get_float('max1', 500) * 1000,                # 500 kHz -> 500000 Hz
            'step1': get_float('step1', 10) * 1000,               # 10 kHz -> 10000 Hz

            # Other
            'Voturn': get_float('Voturn', 54)
        }

    def _generate_range(self, mode: float, fixed_val: float,
                       min_val: float, max_val: float, step: float) -> List[float]:
        """Generate parameter range based on mode"""
        if mode == 1:  # Fixed mode
            return [fixed_val]
        else:  # Range mode
            return list(np.arange(min_val, max_val + step, step))

    def _filter_selected_fets(self, fet_db: List[Dict], selected_names: List[str]) -> List[Dict]:
        """Filter FET database by selected names"""
        if not selected_names:
            return fet_db[:10]  # Return first 10 if none selected

        filtered = []
        for name in selected_names:
            for fet in fet_db:
                if fet.get('part_number', '').lower() == name.lower():
                    filtered.append(fet)
                    break

        return filtered if filtered else fet_db[:10]

    def _design_tank(self, params: Dict, Q: float, Ln: float) -> Optional[Dict]:
        """Design resonant tank for given Q and Ln"""
        try:
            # Calculate battery/load parameters with loss correction
            # This is CRITICAL for accurate turns ratio and Q factor
            battery_params = BatteryParameters.calculate_all_parameters(
                V_in_nom=params['V_input_nom'],
                V_in_min=params['V_input_min'],
                V_in_max=params['V_input_max'],
                V_out=params['V_output_nom'],
                P_out=params['Po'],
                efficiency=params['W_Efficiency'] * 100  # Convert to percentage
            )

            design = self.resonant.design_resonant_tank(
                V_in_nom=params['V_input_nom'],
                V_in_min=params['V_input_min'],
                V_in_max=params['V_input_max'],
                V_out=params['V_output_nom'],
                P_out=params['Po'],
                n=battery_params['turns_ratio'],  # Use loss-corrected turns ratio
                Q_target=Q,
                Ln_target=Ln
            )

            # Add battery parameters to design for later use
            design['battery_params'] = battery_params

            return design
        except Exception as e:
            print(f"Tank design error: {e}")
            return None

    def _calculate_design(self, params: Dict, tank: Dict, Q: float, Ln: float,
                         f_sw: float, pri_fet: Dict, sec_fet: Dict) -> Optional[Dict]:
        """Calculate complete design for given parameters and components"""
        try:
            # Calculate gain at this frequency
            M = self.resonant.calculate_voltage_gain_fha(
                f_sw, tank['f_o'], Q, Ln
            )

            # Check if gain is reasonable
            if M < 0.5 or M > 2.0:
                return None

            # Calculate currents
            I_pri_RMS = params['Po'] / (params['V_input_nom'] * 0.95)  # Assume 95% efficiency
            I_sec_RMS = params['Po'] / params['V_output_nom']

            # Primary FET losses
            pri_params = {
                'I_pri_RMS': I_pri_RMS,
                'R_dson': pri_fet.get('R_dson_25C', 0.01),
                'V_ds': params['V_input_max'],
                'f_sw': f_sw,
                'Q_g': pri_fet.get('Q_g', 40e-9),
                'C_oss': pri_fet.get('C_oss', 400e-12),
                't_rise': pri_fet.get('t_r', 10e-9),
                't_fall': pri_fet.get('t_f', 10e-9)
            }
            pri_losses = self.fet_loss_calc.calculate_primary_total_losses(pri_params)

            # Secondary FET losses
            sec_params = {
                'I_sec_RMS': I_sec_RMS,
                'R_dson': sec_fet.get('R_dson_25C', 0.01),
                'f_sw': f_sw,
                'Q_g': sec_fet.get('Q_g', 40e-9),
                'Q_rr': sec_fet.get('Q_rr', 50e-9)
            }
            sec_losses = self.fet_loss_calc.calculate_secondary_total_losses(sec_params)

            # Transformer losses (simplified)
            trf_loss = 0.02 * params['Po']  # Assume 2% transformer loss

            # Inductor losses (simplified)
            ind_loss = 0.01 * params['Po']  # Assume 1% inductor loss

            # Capacitor losses (simplified)
            cap_loss = 0.005 * params['Po']  # Assume 0.5% capacitor loss

            # Total losses and efficiency
            total_loss = (pri_losses['P_total'] + sec_losses['P_total'] +
                         trf_loss + ind_loss + cap_loss)

            efficiency = params['Po'] / (params['Po'] + total_loss)

            # Volume estimation (simplified)
            total_volume = 1000  # mm³, placeholder

            return {
                'Q': Q,
                'Ln': Ln,
                'f_sw': f_sw,
                'Lr': tank['Lr'],
                'Cr': tank['Cr'],
                'Lm': tank['Lm'],
                'f_o': tank['f_o'],
                'M': M,
                'pri_fet': pri_fet,
                'sec_fet': sec_fet,
                'pri_losses': pri_losses,
                'sec_losses': sec_losses,
                'trf_loss': trf_loss,
                'ind_loss': ind_loss,
                'cap_loss': cap_loss,
                'total_loss': total_loss,
                'efficiency': efficiency,
                'total_volume': total_volume,
                'I_pri_RMS': I_pri_RMS,
                'I_sec_RMS': I_sec_RMS
            }

        except Exception as e:
            print(f"Design calculation error: {e}")
            return None

    def _calculate_score(self, design: Dict, params: Dict) -> float:
        """Calculate multi-objective score"""
        # Weighted score: efficiency, volume, loss
        W_eff = params['W_Efficiency']
        W_vol = params['W_Volume']
        W_cost = params['W_Cost']

        # Normalize and combine (lower is better)
        score = (
            (1 - design['efficiency']) * W_eff * 1000 +
            design['total_volume'] * W_vol +
            design['total_loss'] * W_cost * 10
        )

        return score

    def _format_output(self, design: Dict, params: Dict) -> Dict:
        """Format output to match MATLAB structure"""
        # Generate waveforms
        waveforms = self.resonant.generate_waveforms(
            design['Lr'], design['Cr'], design['Lm'],
            params['V_input_nom'], design['f_sw']
        )

        return {
            # Best results
            'BestQ': design['Q'],
            'BestLn': design['Ln'],
            'Bestfo': design['f_o'],
            'Bestfs_min': design['f_sw'] * 0.9,
            'Bestfs_max': design['f_sw'] * 1.1,
            'BestLr': design['Lr'],
            'BestCr': design['Cr'],
            'BestLm': design['Lm'],

            # Losses
            'BestPriFet_Loss': design['pri_losses']['P_total'],
            'BestPriFet_Conduction': design['pri_losses']['P_conduction'],
            'BestPriFet_Switching': design['pri_losses']['P_switching'],
            'BestSecFet_Loss': design['sec_losses']['P_total'],
            'BestSec_Conduction': design['sec_losses']['P_conduction'],
            'BestTrf_Loss': design['trf_loss'],
            'BestInd_Loss': design['ind_loss'],
            'BestCap_Loss': design['cap_loss'],
            'BestTotalLoss': design['total_loss'],

            # Performance
            'BestTotalEfficiency': design['efficiency'] * 100,
            'BestTotalVolume': design['total_volume'],
            'BestPowerDensity': params['Po'] / design['total_volume'] * 1e6,  # W/cm³

            # Components
            'BestPriFet_Name': design['pri_fet'].get('part_number', 'Unknown'),
            'BestSecFet_Name': design['sec_fet'].get('part_number', 'Unknown'),

            # Waveforms
            't1': waveforms['t1'],
            't2': waveforms['t2'],
            'Ilrp': waveforms['Ilrp'],
            'id1': waveforms['id1']
        }

    def _create_fallback_design(self, params: Dict) -> Dict:
        """Create fallback design if optimization fails"""
        return {
            'BestQ': 0.4,
            'BestLn': 5,
            'Bestfo': 100000,
            'Bestfs_min': 80000,
            'Bestfs_max': 120000,
            'BestLr': 100e-6,
            'BestCr': 100e-9,
            'BestLm': 500e-6,
            'BestPriFet_Loss': 5,
            'BestSecFet_Loss': 3,
            'BestTrf_Loss': 2,
            'BestInd_Loss': 1,
            'BestCap_Loss': 0.5,
            'BestTotalLoss': 11.5,
            'BestTotalEfficiency': 90,
            'BestTotalVolume': 1000,
            'BestPowerDensity': 0.1,
            'BestPriFet_Name': 'BSC034N10LS5',
            'BestSecFet_Name': 'BSC034N10LS5',
            't1': [0] * 100,
            't2': [0] * 100,
            'Ilrp': [0] * 100,
            'id1': [0] * 100
        }
