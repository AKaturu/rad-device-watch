from pathlib import Path

from streamlit.testing.v1 import AppTest

from rad_device_watch.database import Database

APP_PATH = Path(__file__).parents[1] / "src" / "rad_device_watch" / "dashboard.py"


def test_dashboard_initializes_configured_database(monkeypatch, tmp_path: Path) -> None:
    database = tmp_path / "dashboard.db"
    monkeypatch.setenv("RAD_DEVICE_WATCH_DB", str(database))

    app = AppTest.from_file(str(APP_PATH), default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value.endswith("rad-device-watch")
    assert [tab.label for tab in app.tabs] == [
        "Overview",
        "Devices",
        "Downtime",
        "Usage",
        "Alerts",
    ]
    with Database(database) as db:
        assert db.fetchone("SELECT COUNT(*) AS count FROM devices")["count"] == 0
