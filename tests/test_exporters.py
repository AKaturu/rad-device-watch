from pathlib import Path

from rad_device_watch.exporters.csv_exporter import export_devices, export_to_csv


def test_export_to_csv(tmp_path: Path):
    data = [{"id": 1, "name": "CT1"}, {"id": 2, "name": "MRI1"}]
    out = export_to_csv(data, tmp_path / "out.csv")
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "id,name" in content
    assert "1,CT1" in content
    assert "2,MRI1" in content


def test_export_to_csv_empty(tmp_path: Path):
    out = export_to_csv([], tmp_path / "empty.csv")
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


def test_export_devices(tmp_path: Path):
    rows = [
        {
            "id": 1,
            "name": "CT1",
            "manufacturer": "Siemens",
            "model": "SOMATOM",
            "serial_number": "SN1",
            "station_name": "CT1",
            "modality": "CT",
            "location": "Room 1",
            "department": "Radiology",
            "software_version": "VA60",
            "install_date": "2025-01-01",
            "manufacture_date": "2024-06-01",
            "status": "active",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
    ]
    out = export_devices(rows, tmp_path / "devices.csv")
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "CT1" in content
    assert "Siemens" in content
