from pathlib import Path

import pandas as pd
import pytest

from rad_device_watch.importers.csv_importer import import_devices


def test_import_devices_csv(tmp_path: Path):
    csv_path = tmp_path / "test_devices.csv"
    pd.DataFrame(
        {
            "name": ["CT1", "MRI1"],
            "manufacturer": ["Siemens", "GE"],
            "modality": ["CT", "MR"],
            "serial_number": ["SN001", "SN002"],
        }
    ).to_csv(csv_path, index=False)

    devices = import_devices(str(csv_path))
    assert len(devices) == 2
    assert devices[0].name == "CT1"
    assert devices[0].manufacturer == "Siemens"
    assert devices[0].modality == "CT"
    assert devices[1].name == "MRI1"
    assert devices[1].serial_number == "SN002"


def test_import_devices_missing_column(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"modality": ["CT"]}).to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="Missing required columns"):
        import_devices(str(csv_path))


def test_import_devices_empty(tmp_path: Path):
    csv_path = tmp_path / "empty.csv"
    pd.DataFrame({"name": []}).to_csv(csv_path, index=False)
    devices = import_devices(str(csv_path))
    assert devices == []


def test_import_devices_file_not_found():
    with pytest.raises(FileNotFoundError):
        import_devices("nonexistent.csv")


def test_import_devices_xlsx(tmp_path: Path):
    pytest.importorskip("openpyxl")
    xlsx_path = tmp_path / "test.xlsx"
    pd.DataFrame({"name": ["X1"], "manufacturer": ["Philips"]}).to_excel(
        xlsx_path, index=False
    )
    devices = import_devices(str(xlsx_path))
    assert len(devices) == 1
    assert devices[0].name == "X1"
