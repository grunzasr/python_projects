import datetime

# --- UPDATE VERSION HERE ---
VERSION_NUMBER = "1.4.2"
# ---------------------------

# This captures the build time when the script is first loaded/compiled
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d")
BUILD_TIME = datetime.datetime.now().strftime("%H:%M:%S")

def get_full_version_string():
    return f"Version: {VERSION_NUMBER} | Built: {BUILD_DATE} at {BUILD_TIME}"