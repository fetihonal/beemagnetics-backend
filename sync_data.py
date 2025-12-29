#!/usr/bin/env python3
"""
Data Sync Script - Frontend TypeScript verilerini Backend JSON'a dönüştürür
"""

import json
import re
import os

# Paths
FRONTEND_PATH = "../Frontend-main/src/components/UIComponents"
BACKEND_DATA_PATH = "app/data"

def parse_ts_array(ts_content: str, variable_name: str) -> list:
    """TypeScript array'ini Python listesine dönüştür"""
    # Find the array definition
    pattern = rf'const\s+{variable_name}\s*[:\s\w\[\]]*=\s*\['
    match = re.search(pattern, ts_content)
    if not match:
        return []

    start = match.end() - 1
    bracket_count = 0
    end = start

    for i, char in enumerate(ts_content[start:]):
        if char == '[':
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end = start + i + 1
                break

    array_str = ts_content[start:end]

    # Clean up TypeScript syntax
    array_str = re.sub(r'//.*$', '', array_str, flags=re.MULTILINE)  # Remove comments
    array_str = re.sub(r'/\*.*?\*/', '', array_str, flags=re.DOTALL)  # Remove block comments
    array_str = re.sub(r'(\w+):', r'"\1":', array_str)  # Quote keys
    array_str = re.sub(r',\s*}', '}', array_str)  # Remove trailing commas in objects
    array_str = re.sub(r',\s*]', ']', array_str)  # Remove trailing commas in arrays
    array_str = array_str.replace("'", '"')  # Replace single quotes

    # Handle special values
    array_str = re.sub(r'"NA"', 'null', array_str)
    array_str = re.sub(r': NA\b', ': null', array_str)

    try:
        return json.loads(array_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing {variable_name}: {e}")
        return []


def sync_heatsinks():
    """Heatsink verilerini senkronize et"""
    print("📦 Syncing Heatsinks...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/HeatsinksModal/_components/HeatsinksData.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    heatsinks = parse_ts_array(content, "HeatsinskData")

    if heatsinks:
        output = {"heatsinks": heatsinks}
        with open(os.path.join(BACKEND_DATA_PATH, "heatsinks.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(heatsinks)} heatsinks synced")
    else:
        print("   ❌ Failed to parse heatsinks")


def sync_buscaps():
    """Bus Capacitor verilerini senkronize et"""
    print("📦 Syncing Bus Capacitors...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/BusCapsModal/_components/BusCaps.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    caps = parse_ts_array(content, "BusCapsData")

    if caps:
        # Convert to backend format
        formatted_caps = []
        for cap in caps:
            formatted_cap = {
                "part_number": cap.get("id", cap.get("name", "")),
                "manufacturer": cap.get("manufacturer", ""),
                "type": cap.get("type", "Al"),
                "voltage": cap.get("voltage", 450),
                "capacitance": cap.get("capacitance", 0),
                "ESR": cap.get("ESR", 0),
                "I_ripple": cap.get("I_AC_Ripple") if cap.get("I_AC_Ripple") != "NA" else 0,
                "diameter": cap.get("diameter", 0),
                "height": cap.get("height", 0),
                "cost": cap.get("cost") if cap.get("cost") != "NA" else 0
            }
            formatted_caps.append(formatted_cap)

        output = {"capacitors": formatted_caps}
        with open(os.path.join(BACKEND_DATA_PATH, "buscaps.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(formatted_caps)} capacitors synced")
    else:
        print("   ❌ Failed to parse capacitors")


def sync_lpfc_cores():
    """LPFC Core verilerini senkronize et"""
    print("📦 Syncing LPFC Cores...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/LpfcModal/_components/lpfc.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    cores = parse_ts_array(content, "lpfcData")

    if cores:
        # Convert to backend format with Steinmetz parameters
        formatted_cores = []
        for core in cores:
            formatted_core = {
                "name": core.get("name", core.get("id", "")),
                "manufacturer": core.get("manufacturer", ""),
                "type": core.get("type", "Core"),
                "cost": core.get("cost", 0),
                # Frequency range
                "f_min": core.get("fmin", 25000),
                "f_max": core.get("fmax", 300000),
                # Steinmetz parameters (frontend format)
                "steinmetz": {
                    "aB": core.get("aB", 0),
                    "bB": core.get("bB", 0),
                    "cB": core.get("cB", 0),
                    "dB": core.get("dB", 0)
                },
                # Magnetic properties
                "B_sat": core.get("Bsat", 0.5),
                "Ve": core.get("ve", 0),
                "Ae": core.get("ae", 0),
                "Wa": core.get("wa", 0),
                "MLT": core.get("MLT", 0),
                "Al": core.get("Al", 0),
                "Ap": core.get("Ap", 0),
                "le": core.get("le", 0),
                # Dimensions
                "A": core.get("A", 0),
                "B": core.get("B", 0),
                "C": core.get("C", 0),
                "has_model": core.get("haveModel", 0) == 1
            }
            formatted_cores.append(formatted_core)

        output = {"cores": formatted_cores}
        with open(os.path.join(BACKEND_DATA_PATH, "inductor_cores.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(formatted_cores)} inductor cores synced")
    else:
        print("   ❌ Failed to parse cores")


def sync_llc_buscaps():
    """LLC Bus Capacitor verilerini senkronize et"""
    print("📦 Syncing LLC Bus Capacitors...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/LLCModal/BuscapModal/_components/BuscapLLCdata.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    caps = parse_ts_array(content, "BusCapsLlcData")

    if caps:
        output = {"capacitors": caps}
        os.makedirs(os.path.join(BACKEND_DATA_PATH, "llc"), exist_ok=True)
        with open(os.path.join(BACKEND_DATA_PATH, "llc/buscaps.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(caps)} LLC bus capacitors synced")
    else:
        print("   ❌ Failed to parse LLC bus capacitors")


def sync_llc_outcaps():
    """LLC Output Capacitor verilerini senkronize et"""
    print("📦 Syncing LLC Output Capacitors...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/LLCModal/OutcapModal/_components/OutcapsLlcData.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    caps = parse_ts_array(content, "OutCapsLlcData")

    if caps:
        output = {"capacitors": caps}
        os.makedirs(os.path.join(BACKEND_DATA_PATH, "llc"), exist_ok=True)
        with open(os.path.join(BACKEND_DATA_PATH, "llc/outcaps.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(caps)} LLC output capacitors synced")
    else:
        print("   ❌ Failed to parse LLC output capacitors")


def sync_primary_fets():
    """Primary FET verilerini senkronize et"""
    print("📦 Syncing Primary FETs...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/LLCModal/PrimaryFet/_components/primaryFetData.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    fets = parse_ts_array(content, "primaryFetData")

    if fets:
        output = {"fets": fets}
        os.makedirs(os.path.join(BACKEND_DATA_PATH, "llc"), exist_ok=True)
        with open(os.path.join(BACKEND_DATA_PATH, "llc/primary_fets.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(fets)} primary FETs synced")
    else:
        print("   ❌ Failed to parse primary FETs")


def sync_secondary_fets():
    """Secondary FET verilerini senkronize et"""
    print("📦 Syncing Secondary FETs...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/LLCModal/SecondaryFet/_components/secondaryFetData.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    fets = parse_ts_array(content, "secondaryFetData")

    if fets:
        output = {"fets": fets}
        os.makedirs(os.path.join(BACKEND_DATA_PATH, "llc"), exist_ok=True)
        with open(os.path.join(BACKEND_DATA_PATH, "llc/secondary_fets.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(fets)} secondary FETs synced")
    else:
        print("   ❌ Failed to parse secondary FETs")


def sync_transformer_cores():
    """Transformer Core verilerini senkronize et"""
    print("📦 Syncing Transformer Cores...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/LLCModal/Tranformer/_components/transformer.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    cores = parse_ts_array(content, "Transformers")

    if cores:
        output = {"cores": cores}
        with open(os.path.join(BACKEND_DATA_PATH, "transformer_cores.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(cores)} transformer cores synced")
    else:
        print("   ❌ Failed to parse transformer cores")


def sync_cmc_cores():
    """CMC Core verilerini senkronize et"""
    print("📦 Syncing CMC Cores...")

    ts_file = os.path.join(FRONTEND_PATH, "BeeModal/CmcModal/_components/CmcData.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    cores = parse_ts_array(content, "cmcData")

    if cores:
        output = {"cores": cores}
        with open(os.path.join(BACKEND_DATA_PATH, "cmc_cores.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(cores)} CMC cores synced")
    else:
        print("   ❌ Failed to parse CMC cores")


def sync_pfc_fets():
    """PFC FET verilerini senkronize et"""
    print("📦 Syncing PFC FETs...")

    ts_file = os.path.join(FRONTEND_PATH, "FetList/FetData.ts")
    with open(ts_file, 'r') as f:
        content = f.read()

    fets = parse_ts_array(content, "fetData")

    if fets:
        # Format for backend
        formatted_fets = []
        for fet in fets:
            formatted_fet = {
                "part_number": fet.get("id", fet.get("name", "")),
                "manufacturer": fet.get("manufacturer", ""),
                "type": fet.get("type", "MOSFET"),
                "V_dss": fet.get("Vds_max", 0),
                "Rdson": fet.get("Rdson", 0),
                "Rdson_max": fet.get("Rdson_max", 0),
                "Rdson_temp_coeff": fet.get("Rdson_max_temp", 0),
                "T_max": fet.get("Max_temp", 150),
                "cost": fet.get("cost", 0),
                "Vth": fet.get("Vth", 0),
                "Vplt": fet.get("Vplt", 0),
                "Rg_int": fet.get("Rint", 0),
                "Vg_drive": fet.get("Vg_recommended", 10),
                # Capacitance curves
                "Ciss": fet.get("Ciss", []),
                "Coss": fet.get("Coss", []),
                "Crss": fet.get("Crss", []),
                "V_curve": fet.get("V", []),
                # Charge
                "Qg": fet.get("Qg", 0),
                "Qgs": fet.get("Qgs", 0),
                "Qgd": fet.get("Qgd", 0),
                "Qgth": fet.get("Qgth", 0),
                "Qoss": fet.get("Qoss", 0),
                "Qrr": fet.get("Qrr", 0) if fet.get("Qrr") != "NA" else 0
            }
            formatted_fets.append(formatted_fet)

        output = {"fets": formatted_fets}
        with open(os.path.join(BACKEND_DATA_PATH, "fets.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"   ✅ {len(formatted_fets)} PFC FETs synced")
    else:
        print("   ❌ Failed to parse PFC FETs")


def main():
    print("=" * 50)
    print("🔄 Frontend → Backend Data Sync")
    print("=" * 50)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    sync_heatsinks()
    sync_buscaps()
    sync_lpfc_cores()
    sync_pfc_fets()
    sync_llc_buscaps()
    sync_llc_outcaps()
    sync_primary_fets()
    sync_secondary_fets()
    sync_transformer_cores()
    sync_cmc_cores()

    print("=" * 50)
    print("✅ Sync complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
