import os
import platform
from pathlib import Path

def get_default_zotero_path() -> Path:
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Zotero"
    elif system == "Windows":
        return Path(os.environ.get("USERPROFILE", Path.home())) / "Zotero"
    elif system == "Linux":
        return Path.home() / "Zotero"
    else:
        raise RuntimeError("Unsupported operating system")

# Example usage
ZOTERO_FOLDER = get_default_zotero_path()

#COLLECTION_NAME = "myrtle_rust" # Replace with your actual collection name

ZOTERO_DB_PATH = os.path.join(ZOTERO_FOLDER, "zotero.sqlite")
ZOTERO_STORAGE_PATH = os.path.join(ZOTERO_FOLDER, "storage")
BTEX_DB_PATH = os.path.join(ZOTERO_FOLDER, "better-bibtex.sqlite")


# Specify path to store annotated figures
IMAGES_OUTPUT_DIR = "images" 

# Optional paths for temporary files
DB_COPY_PATH = "/tmp/zotero_copy.sqlite"
BTEX_DB_COPY_PATH = "/tmp/better-bibtex.sqlite"
