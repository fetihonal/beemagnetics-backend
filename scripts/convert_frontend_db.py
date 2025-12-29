#!/usr/bin/env python3
"""
Frontend Database Converter
Converts TypeScript database files to JSON format
"""

import json
import re
from pathlib import Path
from typing import Dict, List


class FrontendDBConverter:
    """Convert TypeScript component databases to JSON"""

    def __init__(self, frontend_path: str, output_path: str):
        self.frontend_path = Path(frontend_path)
        self.output_path = Path(output_path)

    def convert_fet_database(self):
        """
        Convert FetData.ts to JSON

        Reads: Frontend-main/src/components/UIComponents/FetList/FetData.ts
        Writes: backend-main/app/data/fets.json
        """
        # Read TypeScript file
        fet_data_path = (self.frontend_path /
                        "src/components/UIComponents/FetList/FetData.ts")

        if not fet_data_path.exists():
            print(f"❌ File not found: {fet_data_path}")
            return

        print(f"📖 Reading {fet_data_path}")

        with open(fet_data_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract FET objects using regex
        # This is a simplified parser - may need adjustments
        fets = []

        # Find all FET objects between { and }
        pattern = r'\{[^}]+\}'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            obj_str = match.group(0)
            try:
                # Convert TypeScript to Python dict (simplified)
                # Replace TypeScript syntax with JSON-compatible syntax
                obj_str = obj_str.replace("'", '"')
                obj_str = re.sub(r'(\w+):', r'"\1":', obj_str)  # Add quotes to keys

                # This is a simplified conversion
                # For production, use a proper TS parser

                print(f"  Found FET object: {obj_str[:50]}...")

            except Exception as e:
                print(f"  ⚠️  Could not parse: {e}")
                continue

        print(f"✅ Extracted {len(fets)} FETs")

        # Write to JSON
        output_file = self.output_path / "fets_complete.json"
        with open(output_file, 'w') as f:
            json.dump({"fets": fets}, f, indent=2)

        print(f"✅ Written to {output_file}")

    def convert_heatsink_database(self):
        """
        Convert HeatsinksData.ts to JSON (already done, but complete it)
        """
        heatsink_path = (self.frontend_path /
                        "src/components/UIComponents/BeeModal/HeatsinksModal/_components/HeatsinksData.ts")

        if not heatsink_path.exists():
            print(f"❌ File not found: {heatsink_path}")
            return

        print(f"📖 Reading {heatsink_path}")

        # Read file
        with open(heatsink_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract array content between [ and ]
        array_match = re.search(r'const\s+HeatsinskData.*?=\s*\[(.*?)\];',
                               content, re.DOTALL)

        if not array_match:
            print("❌ Could not find array")
            return

        array_content = array_match.group(1)

        # Split by object boundaries
        heatsinks = []
        current_obj = {}

        # Parse each object
        for line in array_content.split('\n'):
            line = line.strip()

            if line.startswith('{'):
                current_obj = {}
            elif line.startswith('}'):
                if current_obj:
                    heatsinks.append(current_obj.copy())
                current_obj = {}
            elif ':' in line:
                # Parse key: value
                key_val = line.rstrip(',').split(':', 1)
                if len(key_val) == 2:
                    key = key_val[0].strip().strip('"')
                    val = key_val[1].strip().rstrip(',')

                    # Try to parse value
                    try:
                        if val.startswith('"'):
                            current_obj[key] = val.strip('"')
                        else:
                            current_obj[key] = float(val)
                    except:
                        current_obj[key] = val

        print(f"✅ Extracted {len(heatsinks)} heatsinks")

        # Write to JSON
        output_file = self.output_path / "heatsinks_complete.json"
        with open(output_file, 'w') as f:
            json.dump({"heatsinks": heatsinks}, f, indent=2)

        print(f"✅ Written to {output_file}")

    def convert_all(self):
        """Convert all databases"""
        print("=" * 60)
        print("Frontend Database Converter")
        print("=" * 60)

        # self.convert_fet_database()  # Needs proper TS parser
        self.convert_heatsink_database()

        print("\n✅ Conversion complete!")
        print(f"📁 Output directory: {self.output_path}")


def main():
    """Main entry point"""
    import sys

    # Get paths from command line or use defaults
    frontend_path = sys.argv[1] if len(sys.argv) > 1 else "../Frontend-main"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "../backend-main/app/data"

    converter = FrontendDBConverter(frontend_path, output_path)
    converter.convert_all()


if __name__ == "__main__":
    main()
