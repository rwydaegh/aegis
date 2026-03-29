# Contributing to BaseStationLib

Thank you for your interest in contributing! This document provides guidelines for contributions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

   ```bash
   git clone https://github.com/mattleem/basestations.git
   cd BaseStationLib
   ```

3. **Create a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install development dependencies**:
   ```bash
   pip install -e .
   pip install pytest black flake8
   ```

## Development Workflow

### Before You Start

- Check existing [issues](https://github.com/mattleem/basestations/issues) and [pull requests](https://github.com/mattleem/basestations/pulls)
- Create an issue first for significant changes

### Making Changes

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the style guidelines (see below)

3. **Test your changes**:

   ```bash
   pytest tests/
   ```

4. **Format your code**:

   ```bash
   black basestationlib/
   flake8 basestationlib/
   ```

5. **Commit with clear messages**:

   ```bash
   git commit -m "Add: brief description of changes"
   git commit -m "Fix: fix description"
   git commit -m "Docs: documentation updates"
   ```

6. **Push to your fork**:

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request** on GitHub with:
   - Clear title and description
   - Reference to related issues
   - Summary of changes

## Code Style Guidelines

- **Python**: Follow PEP 8

  - Use 4 spaces for indentation
  - Max line length: 100 characters
  - Use type hints where practical

- **Documentation**:

  - Docstrings for all public functions/classes
  - Use triple quotes with clear descriptions
  - Include parameter and return type information

- **Naming**:
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`

Example function docstring:

```python
def extract_antennas(self):
    """
    Extract base station antennas for configured region.

    Returns:
        pd.DataFrame: DataFrame with standardized antenna columns

    Raises:
        ValueError: If bounding box is not configured
    """
```

## Adding a New Country Adapter

1. **Create directory structure**:

   ```
   basestationlib/Countries/{CountryName}/
   ├── __init__.py
   ├── basestations.py
   └── [optional: sparql.py, patterns.py, etc.]
   ```

2. **Implement BaseStations class** in `basestations.py`:

   ```python
   class BaseStations:
       def __init__(self, operator=None, technology=None,
                    bounding_box=None, **kwargs):
           """Initialize adapter with standard parameters."""

       def extract_antennas(self):
           """Fetch and process antenna data."""

       def extract_patterns(self):
           """Extract antenna patterns (optional)."""
   ```

3. **Register in country_module_map.json**:

   ```json
   {
     "country_name": "basestationlib.Countries.CountryName.basestations"
   }
   ```

4. **Add tests** in `tests/test_countrynamme.py`

5. **Update README.md** with country info and usage examples

## Testing

- Write tests for new functionality
- Use pytest for test framework
- Aim for >80% code coverage

```bash
pytest tests/ -v --cov=basestationlib
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings for code changes
- Update examples if API changes

## Pull Request Process

1. Ensure all tests pass
2. Update documentation as needed
3. Add entry to CHANGELOG (if exists)
4. Respond to review feedback
5. Squash commits before merge (if requested)

## Reporting Issues

When reporting bugs, include:

- Python version and OS
- Full error traceback
- Config file (remove sensitive info)
- Steps to reproduce
- Expected vs actual behavior

## Feature Requests

Describe:

- Use case and motivation
- Proposed API/interface
- Examples of usage

## Questions?

Feel free to open an issue with the `question` label.

## Code of Conduct

- Be respectful and inclusive
- No harassment or discrimination
- Professional communication
- Focus on issues, not people

## License

By contributing, you agree your contributions will be licensed under the MIT License.

Thank you for helping improve basestations.git! 🎉
