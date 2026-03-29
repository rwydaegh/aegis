import sys
import os

# Add repo root to path so basestationLib can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from basestationLib.core import run
import traceback

if __name__ == "__main__":
    try:
        run("config.yaml")
    except:
        traceback.print_exc()