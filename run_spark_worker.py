"""Entry point for Spark streaming worker"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hsl_bus.workers.spark_worker import main

if __name__ == "__main__":
    main()
