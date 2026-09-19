from pathlib import Path
from smartgrid_mlops.data_audit.validation import sha256

def checksums(paths: list[Path]) -> dict[str, str]: return {str(path): sha256(path) for path in paths}
