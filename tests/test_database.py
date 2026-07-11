from rad_device_watch.database import Database


def test_init_schema_creates_tables(db: Database):
    tables = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    names = [r["name"] for r in tables]
    assert "devices" in names
    assert "downtime_events" in names
    assert "usage_records" in names
    assert "maintenance_records" in names
    assert "alert_rules" in names
    assert "alert_history" in names


def test_insert_and_query(db: Database):
    db.execute(
        "INSERT INTO devices (name, manufacturer) VALUES (?, ?)",
        ("CT1", "Siemens"),
    )
    db.commit()
    row = db.fetchone("SELECT * FROM devices WHERE name = ?", ("CT1",))
    assert row is not None
    assert row["manufacturer"] == "Siemens"


def test_row_to_dict(db: Database):
    db.execute("INSERT INTO devices (name) VALUES (?)", ("MRI1",))
    db.commit()
    row = db.fetchone("SELECT * FROM devices WHERE name = ?", ("MRI1",))
    assert row is not None
    d = db.row_to_dict(row)
    assert d is not None
    assert d["name"] == "MRI1"


def test_row_to_dict_none(db: Database):
    assert db.row_to_dict_or_none(None) is None


def test_commit(db: Database):
    db.execute("INSERT INTO devices (name) VALUES (?)", ("XRAY1",))
    db.commit()
    row = db.fetchone("SELECT COUNT(*) as cnt FROM devices")
    assert row is not None
    assert row["cnt"] == 1


def test_schema_redacts_legacy_plaintext_smtp_password(db: Database):
    db.execute(
        """INSERT INTO alert_rules
           (name, metric, condition, threshold, channel, channel_config)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "Legacy email",
            "usage_volume",
            "gt",
            10,
            "email",
            '{"username":"alerts","password":"secret"}',
        ),
    )
    db.commit()

    db.init_schema()

    row = db.fetchone("SELECT channel_config FROM alert_rules WHERE name = ?", ("Legacy email",))
    assert row is not None
    assert "secret" not in row["channel_config"]
    assert "RAD_DEVICE_WATCH_SMTP_PASSWORD" in row["channel_config"]
