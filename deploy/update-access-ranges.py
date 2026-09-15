"""Refresh password-gated IP ranges from IPdeny's IPv4 and IPv6 country lists."""

import argparse
import ipaddress
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("countries", nargs="+")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    countries = sorted({country.lower() for country in args.countries})
    if any(not re.fullmatch(r"[a-z]{2}", country) for country in countries):
        parser.error("Countries must be two-letter codes")

    ranges = []
    for country in countries:
        for version, base in (
            (4, "https://www.ipdeny.com/ipblocks/data/aggregated"),
            (6, "https://www.ipdeny.com/ipv6/ipaddresses/aggregated"),
        ):
            with urlopen(f"{base}/{country}-aggregated.zone", timeout=60) as response:
                lines = response.read(2_000_000).decode("ascii").splitlines()
            networks = [ipaddress.ip_network(line.strip()) for line in lines if line.strip()]
            if not networks or any(n.version != version or n.prefixlen == 0 for n in networks):
                raise ValueError(f"Invalid IPv{version} range list for {country}")
            ranges.extend(str(n) for n in networks)

    path = args.env_file.resolve()
    original = path.read_text()
    key = "AEGIS_PASSWORD_IP_RANGES="
    lines = [line for line in original.splitlines() if not line.startswith(key)]
    updated = "\n".join([*lines, key + " ".join(ranges), ""])
    if updated != original:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as tmp:
            tmp.write(updated)
            temp_path = Path(tmp.name)
        temp_path.chmod(path.stat().st_mode & 0o777)
        os.replace(temp_path, path)
    if args.reload:
        # Validate using the new environment before recreating the live proxy.
        subprocess.run(
            [
                "docker",
                "compose",
                "run",
                "--rm",
                "--no-deps",
                "caddy",
                "caddy",
                "validate",
                "--config",
                "/etc/caddy/Caddyfile",
                "--adapter",
                "caddyfile",
            ],
            cwd=path.parent,
            check=True,
        )
        subprocess.run(
            ["docker", "compose", "up", "-d", "--no-deps", "caddy"],
            cwd=path.parent,
            check=True,
        )
    print(f"Loaded {len(ranges)} IPv4 and IPv6 ranges")


if __name__ == "__main__":
    main()
