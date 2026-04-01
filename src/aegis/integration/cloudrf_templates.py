"""Convert CloudRF JSON templates to AEGIS scenario configs."""

import json
import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)


def cloudrf_template_to_scenario(template_path: str) -> dict:
    """Convert a CloudRF JSON template to an AEGIS scenario dict."""
    with open(template_path) as f:
        t = json.load(f)

    name = t.get("template", {}).get("name", Path(template_path).stem)
    freq_mhz = t["transmitter"]["frq"]
    freq_ghz = freq_mhz / 1000
    power_w = t["transmitter"]["txw"]
    gain_dbi = t["antenna"]["txg"]

    # EIRP in dBm = 10*log10(power_W * 1000) + gain_dBi
    power_dbm = round(10 * math.log10(max(power_w, 1e-10) * 1000) + gain_dbi, 1)

    label = name.replace("-", " ").replace("_", " ")

    return {
        "description": f"{label} ({freq_mhz} MHz, {gain_dbi} dBi, {power_dbm} dBm EIRP)",
        "label": label,
        "icon": "radio",
        "instant": True,
        "autoCompute": True,
        "hidden": False,
        "webState": {
            "freqGhz": freq_ghz,
            "powerDbm": power_dbm,
            "mode": "spatial",
        },
    }


# Key templates to convert
SELECTED_TEMPLATES = [
    "5G-CBand-sector.json",
    "LTE-eNodeB-B3-RSRP.json",
    "LoRa-GW-EU.json",
    "WiFi-2.4G-AP-Omni.json",
    "PMR446-Mobile.json",
    "MOTO-DMR-470M.json",
    "Starlink_12GHz_UE.json",
]


def generate_all_presets(templates_dir: str, output_dir: str) -> int:
    """Convert selected CloudRF templates to AEGIS scenario JSON files."""
    templates_path = Path(templates_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    count = 0
    for template_name in SELECTED_TEMPLATES:
        template_file = templates_path / template_name
        if not template_file.exists():
            logger.warning("Template not found: %s", template_file)
            continue
        try:
            scenario = cloudrf_template_to_scenario(str(template_file))
            # Write as AEGIS scenario config
            out_name = template_name.replace(".json", "").lower().replace("-", "_") + ".json"
            out_file = output_path / out_name
            config = {
                "default_scenario": None,
                "scenarios": {out_name.replace(".json", ""): scenario},
            }
            with open(out_file, "w") as f:
                json.dump(config, f, indent=2)
            count += 1
            logger.info("Generated %s", out_file)
        except Exception as e:
            logger.warning("Failed to convert %s: %s", template_name, e)

    return count
