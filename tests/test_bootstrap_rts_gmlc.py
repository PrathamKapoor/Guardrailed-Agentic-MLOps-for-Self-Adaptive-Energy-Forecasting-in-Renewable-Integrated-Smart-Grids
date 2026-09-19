import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_rts_gmlc.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_rts_gmlc", SCRIPT)
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BOOTSTRAP)


def _write_minimal_rts_archive(path: Path, unsafe: bool = False) -> None:
    files = {
        "RTS-GMLC-master/README.md": "RTS-GMLC\n",
        "RTS-GMLC-master/RTS_Data/SourceData/gen.csv": "GEN UID\nG1\n",
        "RTS-GMLC-master/RTS_Data/SourceData/bus.csv": "Bus ID\n1\n",
        "RTS-GMLC-master/RTS_Data/SourceData/timeseries_pointers.csv": "Object,Category\nG1,WIND\n",
        "RTS-GMLC-master/RTS_Data/timeseries_data_files/Load/DAY_AHEAD_regional_Load.csv": "Year,Month,Day,Period,R1\n2020,1,1,1,1\n",
        "RTS-GMLC-master/RTS_Data/timeseries_data_files/WIND/DAY_AHEAD_wind.csv": "Year,Month,Day,Period,G1\n2020,1,1,1,1\n",
        "RTS-GMLC-master/RTS_Data/timeseries_data_files/PV/DAY_AHEAD_pv.csv": "Year,Month,Day,Period,G2\n2020,1,1,1,1\n",
        "RTS-GMLC-master/RTS_Data/timeseries_data_files/RTPV/DAY_AHEAD_rtpv.csv": "Year,Month,Day,Period,G3\n2020,1,1,1,1\n",
    }
    with zipfile.ZipFile(path, "w") as zipped:
        for name, content in files.items():
            zipped.writestr(name, content)
        if unsafe:
            zipped.writestr("../../file.txt", "unsafe")


def test_valid_zip_and_required_structure_are_recognized() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "RTS-GMLC-master.zip"
        _write_minimal_rts_archive(archive)
        assert BOOTSTRAP.validate_zip(archive)
        destination = Path(temporary) / "RTS-GMLC"
        BOOTSTRAP.extract_archive(archive, destination)
        assert BOOTSTRAP.validate_structure(destination)["required"] == "PASS"


def test_unsafe_zip_path_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "RTS-GMLC-master.zip"
        _write_minimal_rts_archive(archive, unsafe=True)
        try:
            BOOTSTRAP.validate_zip(archive)
        except BOOTSTRAP.DatasetValidationError:
            pass
        else:
            raise AssertionError("unsafe path was accepted")


def test_checksums_are_deterministic_and_extraction_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "project"
        archive = Path(temporary) / "RTS-GMLC-master.zip"
        _write_minimal_rts_archive(archive)
        destination = project / "data/external/RTS-GMLC"
        original_root = BOOTSTRAP.PROJECT_ROOT
        original_dataset = BOOTSTRAP.DATASET_ROOT
        original_manifest = BOOTSTRAP.MANIFEST_PATH
        original_checksums = BOOTSTRAP.CHECKSUM_PATH
        try:
            BOOTSTRAP.PROJECT_ROOT = project
            BOOTSTRAP.DATASET_ROOT = destination
            BOOTSTRAP.MANIFEST_PATH = project / "data/manifests/rts_gmlc_manifest.yaml"
            BOOTSTRAP.CHECKSUM_PATH = project / "data/manifests/rts_gmlc_checksums.sha256"
            assert BOOTSTRAP.main(["--archive", str(archive)]) == 0
            assert BOOTSTRAP.main(["--archive", str(archive)]) == 0
        finally:
            BOOTSTRAP.PROJECT_ROOT = original_root
            BOOTSTRAP.DATASET_ROOT = original_dataset
            BOOTSTRAP.MANIFEST_PATH = original_manifest
            BOOTSTRAP.CHECKSUM_PATH = original_checksums
        target = destination / "RTS_Data/SourceData/gen.csv"
        before = BOOTSTRAP.sha256_file(target)
        assert before == BOOTSTRAP.sha256_file(target)
        assert BOOTSTRAP.sha256_file(target) == before


def test_manifest_generation_required_fields() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "RTS-GMLC-master.zip"
        _write_minimal_rts_archive(archive)
        destination = Path(temporary) / "RTS-GMLC"
        BOOTSTRAP.extract_archive(archive, destination)
        structure = BOOTSTRAP.validate_structure(destination)
        original_manifest = BOOTSTRAP.MANIFEST_PATH
        try:
            BOOTSTRAP.MANIFEST_PATH = Path(temporary) / "manifest.yaml"
            BOOTSTRAP.write_manifest(destination, archive, BOOTSTRAP.sha256_file(archive), structure)
            manifest = json.loads(BOOTSTRAP.MANIFEST_PATH.read_text())
        finally:
            BOOTSTRAP.MANIFEST_PATH = original_manifest
        assert {"dataset_id", "dataset_name", "official_repository", "key_files", "integrity"} <= manifest.keys()
        assert manifest["dataset_id"] == "RTS-GMLC"


def test_verify_only_logic_does_not_mutate_a_dataset_file() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "project"
        archive = Path(temporary) / "RTS-GMLC-master.zip"
        _write_minimal_rts_archive(archive)
        destination = project / "data/external/RTS-GMLC"
        original_root = BOOTSTRAP.PROJECT_ROOT
        original_dataset = BOOTSTRAP.DATASET_ROOT
        original_manifest = BOOTSTRAP.MANIFEST_PATH
        original_checksums = BOOTSTRAP.CHECKSUM_PATH
        try:
            BOOTSTRAP.PROJECT_ROOT = project
            BOOTSTRAP.DATASET_ROOT = destination
            BOOTSTRAP.MANIFEST_PATH = project / "data/manifests/rts_gmlc_manifest.yaml"
            BOOTSTRAP.CHECKSUM_PATH = project / "data/manifests/rts_gmlc_checksums.sha256"
            assert BOOTSTRAP.main(["--archive", str(archive)]) == 0
            source = destination / "RTS_Data/SourceData/gen.csv"
            before = BOOTSTRAP.sha256_file(source)
            assert BOOTSTRAP.main(["--verify-only"]) == 0
            assert BOOTSTRAP.sha256_file(source) == before
        finally:
            BOOTSTRAP.PROJECT_ROOT = original_root
            BOOTSTRAP.DATASET_ROOT = original_dataset
            BOOTSTRAP.MANIFEST_PATH = original_manifest
            BOOTSTRAP.CHECKSUM_PATH = original_checksums
