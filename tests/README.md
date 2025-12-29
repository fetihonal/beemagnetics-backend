# Test Suite

Comprehensive unit tests for the Python-based power electronics simulation backend.

## Running Tests

### Install pytest

```bash
pip install pytest pytest-cov
```

### Run all tests

```bash
cd backend-main
pytest tests/
```

### Run with coverage report

```bash
pytest tests/ --cov=app --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`

### Run specific test file

```bash
pytest tests/test_llc_optimizer.py
```

### Run specific test

```bash
pytest tests/test_llc_optimizer.py::TestLLCOptimizer::test_run_optimization
```

## Test Structure

```
tests/
├── __init__.py                      # Package initialization
├── conftest.py                      # Pytest fixtures and configuration
├── test_pfc_core_loss.py           # PFC core loss calculations
├── test_pfc_switching_loss.py      # PFC switching loss calculations
├── test_llc_resonant_tank.py       # LLC resonant tank design
├── test_llc_optimizer.py           # LLC optimization engine
└── test_component_db.py            # Component database loader
```

## Test Coverage

The test suite covers:

- **PFC Simulations**
  - Inductor current calculations
  - Ripple current calculations
  - Copper and core loss calculations (Steinmetz equation)
  - FET switching and conduction losses
  - Gate drive losses
  - Reverse recovery losses

- **LLC Simulations**
  - Resonant frequency calculations
  - Quality factor and inductance ratio
  - Voltage gain (First Harmonic Approximation)
  - Resonant tank design
  - Multi-objective optimization

- **Component Database**
  - FET database loading and searching
  - Heatsink database
  - Capacitor database
  - Magnetic core database
  - Database caching

## Fixtures

Common test fixtures are defined in `conftest.py`:

- `sample_llc_params`: LLC converter parameters
- `sample_pfc_params`: PFC converter parameters
- `sample_fet`: Sample FET specifications
- `sample_core`: Sample magnetic core specifications

## Performance Tests

To verify the performance improvement over MATLAB:

```bash
# Run LLC optimization benchmark
pytest tests/test_llc_optimizer.py -v --durations=10
```

Expected performance:
- Python simulation: 2-5 seconds
- MATLAB simulation: 30-60 seconds
- **Speedup: 10-30x faster**

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ --cov=app
```
