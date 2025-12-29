"""
Unit tests for Component Database Loader
"""
import pytest
from app.data_loaders.component_db import ComponentDatabase


class TestComponentDatabase:
    """Test suite for component database loader"""

    def test_load_fets(self):
        """Test loading FET database"""
        fets = ComponentDatabase.load_fets()

        assert isinstance(fets, list)
        assert len(fets) > 0

        # Check first FET has required fields
        fet = fets[0]
        assert "part_number" in fet
        assert "V_dss" in fet
        assert "I_d" in fet
        assert "R_dson" in fet

    def test_load_heatsinks(self):
        """Test loading heatsink database"""
        heatsinks = ComponentDatabase.load_heatsinks()

        assert isinstance(heatsinks, list)
        assert len(heatsinks) > 0

        # Check first heatsink has required fields
        hs = heatsinks[0]
        assert "name" in hs
        assert "X" in hs
        assert "Y" in hs

    def test_load_capacitors(self):
        """Test loading capacitor database"""
        caps = ComponentDatabase.load_capacitors()

        assert isinstance(caps, list)
        assert len(caps) > 0

        # Check first capacitor has required fields
        cap = caps[0]
        assert "part_number" in cap
        assert "capacitance" in cap
        assert "voltage" in cap

    def test_load_transformer_cores(self):
        """Test loading transformer core database"""
        cores = ComponentDatabase.load_cores(core_type="transformer")

        assert isinstance(cores, list)
        assert len(cores) > 0

        # Check first core has required fields
        core = cores[0]
        assert "name" in core
        assert "Ae" in core
        assert "Ve" in core
        assert "k" in core  # Steinmetz parameter

    def test_load_inductor_cores(self):
        """Test loading inductor core database"""
        cores = ComponentDatabase.load_cores(core_type="inductor")

        assert isinstance(cores, list)
        assert len(cores) > 0

    def test_search_fet_by_voltage(self):
        """Test searching FETs by voltage rating"""
        fets = ComponentDatabase.search_fets(min_voltage=600)

        assert isinstance(fets, list)
        for fet in fets:
            assert fet["V_dss"] >= 600

    def test_search_fet_by_current(self):
        """Test searching FETs by current rating"""
        fets = ComponentDatabase.search_fets(min_current=30)

        assert isinstance(fets, list)
        for fet in fets:
            assert fet["I_d"] >= 30

    def test_search_fet_by_rdson(self):
        """Test searching FETs by on-resistance"""
        fets = ComponentDatabase.search_fets(max_rdson=0.1)

        assert isinstance(fets, list)
        for fet in fets:
            assert fet["R_dson"] <= 0.1

    def test_search_core_by_volume(self):
        """Test searching cores by volume"""
        cores = ComponentDatabase.search_cores(
            core_type="transformer",
            min_volume=1000
        )

        assert isinstance(cores, list)
        for core in cores:
            assert core["volume"] >= 1000

    def test_caching_works(self):
        """Test that caching improves performance"""
        import time

        # First load (not cached)
        start = time.time()
        fets1 = ComponentDatabase.load_fets()
        time1 = time.time() - start

        # Second load (cached)
        start = time.time()
        fets2 = ComponentDatabase.load_fets()
        time2 = time.time() - start

        # Cached load should be much faster
        assert time2 < time1
        # Results should be identical
        assert fets1 == fets2
