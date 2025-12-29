"""
Component Database API Endpoints
Provides REST API access to component databases for frontend
"""

from flask import Blueprint, jsonify, request
from app.data_loaders.component_db import get_component_db

components_bp = Blueprint("components", __name__, url_prefix="/api/components")


@components_bp.route("/fets", methods=["GET"])
def get_fets():
    """
    Get all FETs or filter by parameters

    Query params:
        - V_dss_min: Minimum voltage rating
        - manufacturer: Filter by manufacturer
        - type: Filter by FET type (pfc, llc_primary, llc_secondary)
    """
    try:
        db = get_component_db()

        # Check for special types
        fet_type = request.args.get("type", "pfc")

        if fet_type == "llc_primary":
            fets = db._load_json("llc/primary_fets.json").get("fets", [])
        elif fet_type == "llc_secondary":
            fets = db._load_json("llc/secondary_fets.json").get("fets", [])
        else:
            fets = db.load_fets()

        # Apply filters
        manufacturer = request.args.get("manufacturer")
        if manufacturer:
            fets = [f for f in fets if f.get("manufacturer", "").lower() == manufacturer.lower()]

        V_dss_min = request.args.get("V_dss_min", type=float)
        if V_dss_min:
            fets = [f for f in fets if f.get("V_dss", f.get("Vds_max", 0)) >= V_dss_min]

        return jsonify({"fets": fets, "count": len(fets)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@components_bp.route("/heatsinks", methods=["GET"])
def get_heatsinks():
    """
    Get all heatsinks or filter by dimensions

    Query params:
        - X_max: Maximum X dimension (mm)
        - Y_max: Maximum Y dimension (mm)
    """
    try:
        db = get_component_db()
        heatsinks = db.load_heatsinks()

        # Apply filters
        X_max = request.args.get("X_max", type=float)
        if X_max:
            heatsinks = [h for h in heatsinks if h.get("X", 0) <= X_max]

        Y_max = request.args.get("Y_max", type=float)
        if Y_max:
            heatsinks = [h for h in heatsinks if h.get("Y", 0) <= Y_max]

        return jsonify({"heatsinks": heatsinks, "count": len(heatsinks)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@components_bp.route("/capacitors", methods=["GET"])
def get_capacitors():
    """
    Get capacitors by type

    Query params:
        - type: Capacitor type (buscaps, llc_buscaps, llc_outcaps)
        - V_min: Minimum voltage rating
        - manufacturer: Filter by manufacturer
    """
    try:
        db = get_component_db()

        cap_type = request.args.get("type", "buscaps")

        if cap_type == "llc_buscaps":
            caps = db._load_json("llc/buscaps.json").get("capacitors", [])
        elif cap_type == "llc_outcaps":
            caps = db._load_json("llc/outcaps.json").get("capacitors", [])
        else:
            caps = db.load_capacitors()

        # Apply filters
        manufacturer = request.args.get("manufacturer")
        if manufacturer:
            caps = [c for c in caps if c.get("manufacturer", "").lower() == manufacturer.lower()]

        V_min = request.args.get("V_min", type=float)
        if V_min:
            caps = [c for c in caps if c.get("voltage", 0) >= V_min]

        return jsonify({"capacitors": caps, "count": len(caps)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@components_bp.route("/cores", methods=["GET"])
def get_cores():
    """
    Get magnetic cores by type

    Query params:
        - type: Core type (inductor, transformer, cmc)
        - manufacturer: Filter by manufacturer
    """
    try:
        db = get_component_db()

        core_type = request.args.get("type", "inductor")
        cores = db.load_cores(core_type=core_type)

        # Apply filters
        manufacturer = request.args.get("manufacturer")
        if manufacturer:
            cores = [c for c in cores if c.get("manufacturer", "").lower() == manufacturer.lower()]

        return jsonify({"cores": cores, "count": len(cores)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@components_bp.route("/manufacturers", methods=["GET"])
def get_manufacturers():
    """
    Get list of all manufacturers across all component types
    """
    try:
        db = get_component_db()

        manufacturers = set()

        # Collect manufacturers from all databases
        for fet in db.load_fets():
            if "manufacturer" in fet:
                manufacturers.add(fet["manufacturer"])

        for hs in db.load_heatsinks():
            if "manufacturer" in hs:
                manufacturers.add(hs["manufacturer"])

        for cap in db.load_capacitors():
            if "manufacturer" in cap:
                manufacturers.add(cap["manufacturer"])

        for core in db.load_cores("inductor"):
            if "manufacturer" in core:
                manufacturers.add(core["manufacturer"])

        return jsonify({"manufacturers": sorted(list(manufacturers))}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@components_bp.route("/summary", methods=["GET"])
def get_summary():
    """
    Get summary of all available components
    """
    try:
        db = get_component_db()

        summary = {
            "fets": {
                "pfc": len(db.load_fets()),
                "llc_primary": len(db._load_json("llc/primary_fets.json").get("fets", [])),
                "llc_secondary": len(db._load_json("llc/secondary_fets.json").get("fets", []))
            },
            "heatsinks": len(db.load_heatsinks()),
            "capacitors": {
                "pfc_buscaps": len(db.load_capacitors()),
                "llc_buscaps": len(db._load_json("llc/buscaps.json").get("capacitors", [])),
                "llc_outcaps": len(db._load_json("llc/outcaps.json").get("capacitors", []))
            },
            "cores": {
                "inductor": len(db.load_cores("inductor")),
                "transformer": len(db.load_cores("transformer")),
                "cmc": len(db.load_cores("cmc"))
            }
        }

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
