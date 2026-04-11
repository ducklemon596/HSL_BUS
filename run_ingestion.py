"""Entry point for MQTT to Kafka ingestion"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hsl_bus.ingestion import main

if __name__ == "__main__":
    main()
