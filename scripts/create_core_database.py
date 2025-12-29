#!/usr/bin/env python3
"""
Magnetic Core Database Generator
Creates comprehensive magnetic core databases with Steinmetz parameters
"""

import json
from pathlib import Path


def create_ferrite_core_database():
    """
    Create ferrite core database with common E, EE, ETD, RM cores
    Based on typical manufacturer (TDK, Ferroxcube, EPCOS) datasheets
    """

    # Common ferrite core types with realistic parameters
    cores = [
        # E cores (small)
        {
            "name": "E13",
            "type": "E",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 1.6,  # cm²
            "Aw": 1.5,  # cm²
            "Ve": 0.38,  # cm³
            "le": 2.9,  # cm
            "Al": 250,  # nH/N²
            "MLT": 18,  # mm
            "volume": 380,  # mm³
            # Steinmetz parameters for N87 at 100kHz
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39  # T at 100°C
        },
        {
            "name": "E16",
            "type": "E",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 2.0,
            "Aw": 2.4,
            "Ve": 0.62,
            "le": 3.6,
            "Al": 315,
            "MLT": 22,
            "volume": 620,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        {
            "name": "E20",
            "type": "E",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 3.1,
            "Aw": 4.0,
            "Ve": 1.2,
            "le": 4.3,
            "Al": 400,
            "MLT": 28,
            "volume": 1200,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        # EE cores (medium)
        {
            "name": "EE25",
            "type": "EE",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 5.3,
            "Aw": 6.8,
            "Ve": 2.5,
            "le": 5.7,
            "Al": 500,
            "MLT": 35,
            "volume": 2500,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        {
            "name": "EE32",
            "type": "EE",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 7.6,
            "Aw": 12.5,
            "Ve": 4.8,
            "le": 6.8,
            "Al": 630,
            "MLT": 45,
            "volume": 4800,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        # ETD cores (medium-large)
        {
            "name": "ETD29",
            "type": "ETD",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 7.6,
            "Aw": 9.7,
            "Ve": 5.3,
            "le": 6.9,
            "Al": 610,
            "MLT": 48,
            "volume": 5300,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        {
            "name": "ETD34",
            "type": "ETD",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 9.7,
            "Aw": 14.2,
            "Ve": 7.5,
            "le": 7.7,
            "Al": 710,
            "MLT": 55,
            "volume": 7500,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        # RM cores
        {
            "name": "RM8",
            "type": "RM",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 6.5,
            "Aw": 5.0,
            "Ve": 4.8,
            "le": 1.85,
            "Al": 1900,
            "MLT": 28,
            "volume": 480,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        {
            "name": "RM10",
            "type": "RM",
            "material": "N87",
            "manufacturer": "TDK",
            "Ae": 9.8,
            "Aw": 9.5,
            "Ve": 7.4,
            "le": 2.3,
            "Al": 2350,
            "MLT": 35,
            "volume": 740,
            "k": 44.5,
            "alpha": 1.63,
            "beta": 2.62,
            "B_sat": 0.39
        },
        # High power cores
        {
            "name": "EE42",
            "type": "EE",
            "material": "N97",
            "manufacturer": "TDK",
            "Ae": 18.1,
            "Aw": 31.8,
            "Ve": 15.5,
            "le": 9.8,
            "Al": 1020,
            "MLT": 70,
            "volume": 15500,
            "k": 120,  # N97 has higher losses
            "alpha": 1.41,
            "beta": 2.50,
            "B_sat": 0.47  # Higher saturation
        },
        {
            "name": "ETD49",
            "type": "ETD",
            "material": "N97",
            "manufacturer": "TDK",
            "Ae": 21.1,
            "Aw": 27.4,
            "Ve": 20.1,
            "le": 11.6,
            "Al": 1000,
            "MLT": 85,
            "volume": 20100,
            "k": 120,
            "alpha": 1.41,
            "beta": 2.50,
            "B_sat": 0.47
        }
    ]

    return cores


def create_powder_core_database():
    """
    Create powder core database (for inductors)
    Includes iron powder, Kool Mu, High Flux, MPP cores
    """

    cores = [
        # Iron powder cores (cheap, good for storage inductors)
        {
            "name": "T50-26",
            "type": "Toroid",
            "material": "Iron Powder -26",
            "manufacturer": "Micrometals",
            "Ae": 0.133,  # cm²
            "Aw": 0.200,  # cm² (window area)
            "Ve": 0.71,  # cm³
            "le": 3.31,  # cm
            "Al": 75,  # nH/N²
            "OD": 12.7,  # mm
            "ID": 7.5,  # mm
            "HT": 6.4,  # mm
            "volume": 710,  # mm³
            "mu_i": 75,  # Initial permeability
            "B_sat": 1.5,  # T
            "core_loss_density": 20  # mW/cm³ at 100kHz, 100mT
        },
        {
            "name": "T80-26",
            "type": "Toroid",
            "material": "Iron Powder -26",
            "manufacturer": "Micrometals",
            "Ae": 0.195,
            "Aw": 0.493,
            "Ve": 1.54,
            "le": 5.14,
            "Al": 57,
            "OD": 20.3,
            "ID": 12.5,
            "HT": 7.9,
            "volume": 1540,
            "mu_i": 75,
            "B_sat": 1.5,
            "core_loss_density": 20
        },
        # Kool Mu cores (distributed gap, good for DC bias)
        {
            "name": "77439",
            "type": "Toroid",
            "material": "Kool Mu 60u",
            "manufacturer": "Magnetics",
            "Ae": 1.33,
            "Aw": 2.34,
            "Ve": 8.35,
            "le": 6.27,
            "Al": 127,
            "OD": 38.1,
            "ID": 19.05,
            "HT": 15.9,
            "volume": 8350,
            "mu_i": 60,
            "B_sat": 1.0,
            "core_loss_density": 15
        },
        # High Flux cores (best for high DC bias)
        {
            "name": "58337",
            "type": "Toroid",
            "material": "High Flux 60u",
            "manufacturer": "Magnetics",
            "Ae": 0.354,
            "Aw": 0.535,
            "Ve": 2.21,
            "le": 6.24,
            "Al": 34,
            "OD": 25.4,
            "ID": 14.7,
            "HT": 11.2,
            "volume": 2210,
            "mu_i": 60,
            "B_sat": 1.5,
            "core_loss_density": 25
        }
    ]

    return cores


def main():
    """Generate all core databases"""
    output_dir = Path("../app/data")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Create transformer cores (ferrite)
    print("🔧 Creating transformer core database...")
    transformer_cores = create_ferrite_core_database()
    output_file = output_dir / "transformer_cores.json"
    with open(output_file, 'w') as f:
        json.dump({"cores": transformer_cores}, f, indent=2)
    print(f"✅ Created {output_file} with {len(transformer_cores)} cores")

    # Create inductor cores (powder + ferrite)
    print("\n🔧 Creating inductor core database...")
    inductor_cores = create_ferrite_core_database() + create_powder_core_database()
    output_file = output_dir / "inductor_cores.json"
    with open(output_file, 'w') as f:
        json.dump({"cores": inductor_cores}, f, indent=2)
    print(f"✅ Created {output_file} with {len(inductor_cores)} cores")

    # Create CMC cores (ferrite only)
    print("\n🔧 Creating CMC core database...")
    cmc_cores = [c for c in create_ferrite_core_database() if c['type'] in ['RM', 'ETD']]
    output_file = output_dir / "cmc_cores.json"
    with open(output_file, 'w') as f:
        json.dump({"cores": cmc_cores}, f, indent=2)
    print(f"✅ Created {output_file} with {len(cmc_cores)} cores")

    print("\n✨ All core databases created successfully!")


if __name__ == "__main__":
    main()
