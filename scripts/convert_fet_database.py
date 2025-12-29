#!/usr/bin/env python3
"""
FET Database Converter
Converts TypeScript FET database to JSON format for backend use
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


def parse_typescript_array(content: str) -> str:
    """
    Extract the fetData array from TypeScript content
    """
    # Find the fetData array
    pattern = r'const\s+fetData:\s*FETData\[\]\s*=\s*(\[.*?\]);'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        return match.group(1)

    return None


def convert_typescript_value(value: str) -> Any:
    """
    Convert TypeScript value to Python value
    """
    value = value.strip()

    # Remove trailing comma
    if value.endswith(','):
        value = value[:-1].strip()

    # Handle "NA" strings
    if value == '"NA"' or value == "'NA'":
        return None

    # Handle strings
    if value.startswith('"') or value.startswith("'"):
        return value.strip('"').strip("'")

    # Handle booleans
    if value == 'true':
        return True
    if value == 'false':
        return False

    # Handle arrays
    if value.startswith('['):
        # Simple array parsing
        value = value.strip('[]')
        if not value:
            return []

        # Split by comma and convert each element
        elements = []
        bracket_depth = 0
        current = ""

        for char in value + ',':
            if char == '[':
                bracket_depth += 1
                current += char
            elif char == ']':
                bracket_depth -= 1
                current += char
            elif char == ',' and bracket_depth == 0:
                if current.strip():
                    try:
                        # Try to convert to float
                        elements.append(float(current.strip()))
                    except ValueError:
                        elements.append(current.strip())
                current = ""
            else:
                current += char

        return elements

    # Handle numbers
    try:
        # Try scientific notation or regular number
        if 'e' in value.lower():
            return float(value)
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    return value


def parse_fet_object(obj_str: str) -> Dict[str, Any]:
    """
    Parse a single FET object from TypeScript
    """
    fet = {}

    # Split into lines
    lines = obj_str.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        # Skip empty lines and brackets
        if not line or line in ['{', '}', ',']:
            continue

        # Parse key: value pairs
        if ':' in line:
            # Find the first colon
            colon_idx = line.index(':')
            key = line[:colon_idx].strip()
            value_str = line[colon_idx + 1:].strip()

            # Handle multi-line arrays
            if value_str.startswith('[') and not (value_str.endswith(']') or value_str.endswith('],')):
                # Multi-line array - collect all lines until closing bracket
                array_content = value_str
                while i < len(lines):
                    next_line = lines[i].strip()
                    array_content += ' ' + next_line
                    i += 1
                    if ']' in next_line:
                        break
                value_str = array_content

            # Remove trailing comma
            if value_str.endswith(','):
                value_str = value_str[:-1].strip()

            # Convert value
            try:
                value = convert_typescript_value(value_str)
                fet[key] = value
            except Exception as e:
                print(f"  Warning: Could not parse {key}: {e}")

    return fet


def extract_fets_improved(content: str) -> List[Dict[str, Any]]:
    """
    Extract FETs using improved parsing
    """
    fets = []

    # Find the array content
    array_match = re.search(r'const\s+fetData:\s*FETData\[\]\s*=\s*\[(.*)\];', content, re.DOTALL)

    if not array_match:
        print("Could not find fetData array")
        return []

    array_content = array_match.group(1)

    # Split by objects - find balanced braces
    current_obj = ""
    brace_count = 0
    in_object = False

    for char in array_content:
        if char == '{':
            brace_count += 1
            in_object = True
            current_obj += char
        elif char == '}':
            brace_count -= 1
            current_obj += char

            if brace_count == 0 and in_object:
                # Object complete
                try:
                    fet = parse_fet_object(current_obj)
                    if fet and 'label' in fet:
                        fets.append(fet)
                        print(f"  ✓ Parsed: {fet.get('label', 'Unknown')}")
                except Exception as e:
                    print(f"  ✗ Error parsing object: {e}")

                current_obj = ""
                in_object = False
        elif in_object:
            current_obj += char

    return fets


def convert_to_backend_format(fets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert frontend FET format to backend format
    """
    backend_fets = []

    for fet in fets:
        # Map frontend fields to backend fields
        backend_fet = {
            "part_number": fet.get("label", fet.get("id", "Unknown")),
            "manufacturer": fet.get("manufacturer", "Unknown"),
            "type": fet.get("type", "MOSFET"),

            # Voltage and current ratings
            "V_dss": fet.get("Vds_max", 0),
            "I_d": 100,  # Not in frontend data, use default

            # Resistance
            "R_dson": fet.get("Rdson", 0),
            "R_dson_max": fet.get("Rdson_max", fet.get("Rdson", 0)),
            "R_dson_max_temp": fet.get("Rdson_max_temp", fet.get("Rdson", 0) * 1.5),

            # Temperature
            "T_j_max": fet.get("Max_temp", 150),

            # Gate charge
            "Q_g": fet.get("Qg", 0),
            "Q_gs": fet.get("Qgs", 0),
            "Q_gd": fet.get("Qgd", 0),
            "Q_oss": fet.get("Qoss", 0),
            "Q_rr": fet.get("Qrr", 0) if fet.get("Qrr") is not None else 0,

            # Capacitances
            "C_iss": fet.get("Ciss", []),
            "C_oss": fet.get("Coss", []),
            "C_rss": fet.get("Crss", []),
            "V_array": fet.get("V", []),  # Voltage points for capacitance

            # Gate threshold
            "V_th": fet.get("Vth", 2.5),
            "V_gs_recommended": fet.get("Vg_recommended", 10),

            # Cost
            "cost": fet.get("cost", 0),
            "cost_die": fet.get("costdie", 0),

            # Additional
            "V_plateau": fet.get("Vplt", 0),
            "R_int": fet.get("Rint", 0),
        }

        # Add switching times if not in data
        if "t_r" not in backend_fet:
            backend_fet["t_r"] = 20e-9  # 20ns default
        if "t_f" not in backend_fet:
            backend_fet["t_f"] = 15e-9  # 15ns default

        backend_fets.append(backend_fet)

    return backend_fets


def main():
    """Convert FET database from TypeScript to JSON"""

    # Paths
    frontend_path = Path("../Frontend-main/src/components/UIComponents/FetList/FetData.ts")
    output_path = Path("../backend-main/app/data/fets_complete.json")

    print("=" * 60)
    print("FET Database Converter")
    print("=" * 60)

    # Check if file exists
    if not frontend_path.exists():
        print(f"❌ Frontend file not found: {frontend_path}")
        # Try from current directory
        frontend_path = Path("/Volumes/AED/Downloads - Geçici/wetransfer_backend-main-zip_2025-08-11_1327 (1)/Frontend-main/src/components/UIComponents/FetList/FetData.ts")
        output_path = Path("/Volumes/AED/Downloads - Geçici/wetransfer_backend-main-zip_2025-08-11_1327 (1)/backend-main/app/data/fets_complete.json")

        if not frontend_path.exists():
            print(f"❌ Still not found: {frontend_path}")
            return

    print(f"📖 Reading: {frontend_path}")

    # Read TypeScript file
    with open(frontend_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"📄 File size: {len(content)} bytes")

    # Extract FETs
    print("\n🔍 Extracting FETs...")
    fets = extract_fets_improved(content)

    print(f"\n✅ Extracted {len(fets)} FETs")

    if len(fets) == 0:
        print("❌ No FETs extracted. Check parsing logic.")
        return

    # Convert to backend format
    print("\n🔄 Converting to backend format...")
    backend_fets = convert_to_backend_format(fets)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    print(f"\n💾 Writing to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"fets": backend_fets}, f, indent=2)

    print(f"✅ Successfully converted {len(backend_fets)} FETs")

    # Show statistics
    print("\n📊 Statistics:")
    voltage_classes = {}
    for fet in backend_fets:
        v_class = f"{fet['V_dss']}V"
        voltage_classes[v_class] = voltage_classes.get(v_class, 0) + 1

    print(f"   Total FETs: {len(backend_fets)}")
    print(f"   Voltage classes:")
    for v_class, count in sorted(voltage_classes.items()):
        print(f"      {v_class}: {count} FETs")

    # Show sample
    print("\n📝 Sample FET:")
    if backend_fets:
        sample = backend_fets[0]
        print(f"   Part Number: {sample['part_number']}")
        print(f"   Manufacturer: {sample['manufacturer']}")
        print(f"   V_dss: {sample['V_dss']}V")
        print(f"   R_dson: {sample['R_dson']*1000:.1f}mΩ")
        print(f"   Cost: ${sample['cost']:.2f}")

    print("\n✨ Conversion complete!")


if __name__ == "__main__":
    main()
