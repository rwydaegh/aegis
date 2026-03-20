"""CLI entry when running ``python -m aegis``."""

from __future__ import annotations


def main() -> None:
    from aegis import __version__

    print(f"AEGIS {__version__}")
    print("Geometric dosimetry for wireless exposure.")
    print("Run the 3D viewer with: py -3.12 -m aegis.viewer")


if __name__ == "__main__":
    main()
