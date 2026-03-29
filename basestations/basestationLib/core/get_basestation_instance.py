
from importlib import import_module
from typing import Optional, Dict, Any
from importlib.resources import files  # Python 3.9+
import json

# Map (country, region) → module path
#
# - Keys are lowercase
# - Values are fully-qualified module paths where `BaseStations` lives
#
# For Belgium we use a nested dict so you can have multiple region/city variants.
def _load_country_module_map() -> Dict[str, Any]:
    # __package__ is "basetationLib.core" here
    json_path = files(__package__) / "country_module_map.json"
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)

COUNTRY_MODULE_MAP = _load_country_module_map()

def get_basestation_instance(country: str, region_city: Optional[str] = None):
    """
    Return a BaseStations instance for the requested country (and region/city).

    Parameters
    ----------
    country : str
        Country name (case-insensitive), e.g. "Poland", "Belgium".
    region_city : str, optional
        Region or city name for countries that need it.
        Currently only required/used for Belgium.
    **kwargs :
        Extra keyword arguments passed to the BaseStations constructor.

    Raises
    ------
    ValueError
        If the (country, region_city) combination is unknown or region_city
        is missing for Belgium.
    ImportError
        If the target module doesn’t expose a `BaseStations` attribute.
    """

    country_key = country.strip().lower()
    if country_key not in COUNTRY_MODULE_MAP.keys():
        module_path = COUNTRY_MODULE_MAP["other"]
    else: 
        # Resolve module path
        if country_key == "belgium":
            if not region_city:
                print(
                    "For Belgium you must specify 'flanders' or 'brussels', 'wallonia' is not implemented" 
                )
                region_city = input("Type flanders or brussels and press ENTER:   ")
            region_key = region_city.strip().lower()
            belgium_map = COUNTRY_MODULE_MAP.get("belgium", {})
            try:
                module_path = belgium_map[region_key]
            except KeyError:
                valid = ", ".join(sorted(belgium_map.keys())) or "<none configured>"
                raise ValueError(
                    f"Unknown Belgian region/city '{region_city}'. "
                    f"Configured options: {valid}"
                )
        else:
            try:
                module_path = COUNTRY_MODULE_MAP[country_key]
            except KeyError:
                valid_countries = [
                    c for c in COUNTRY_MODULE_MAP.keys() if c != "belgium"
                ]
                raise ValueError(
                    f"Unsupported country '{country}'. "
                    f"Configured countries: {', '.join(sorted(valid_countries + ['belgium']))}"
                )

    # Import the module and fetch BaseStations
    module = import_module(module_path)

    try:
        BaseStations = getattr(module, "BaseStations")
    except AttributeError as exc:
        raise ImportError(
            f"Module '{module_path}' does not define 'BaseStations'."
        ) from exc

    # Return an instance; pass through any kwargs for flexibility
    return BaseStations