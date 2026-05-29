"""pytest config for Nexus Knowledge Engine tests."""
import os

# If running against a live API, set this env var
NEXUS_API_URL = os.environ.get("NEXUS_API_URL", "http://localhost:8002")
