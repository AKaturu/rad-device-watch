from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from rad_device_watch.alerts.engine import AlertEngine
from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.downtime import DowntimeTracker
from rad_device_watch.maintenance import MaintenanceManager
from rad_device_watch.models import (
    AlertChannel,
    AlertCondition,
    AlertMetric,
    AlertRule,
    CauseCategory,
    Device,
    DeviceStatus,
    DowntimeEvent,
    ImpactLevel,
    MaintenanceRecord,
    MaintenanceType,
    UsageRecord,
)
from rad_device_watch.reporter import (
    print_alert_history,
    print_device_table,
    print_uptime_table,
    print_usage_table,
)
from rad_device_watch.usage import UsageAnalyzer

app = typer.Typer(
    name="rad-device-watch",
    help="Radiology device monitoring — inventory, uptime, usage, alerts.",
    no_args_is_help=True,
)
console = Console()

_DEFAULT_DB = "rad_device_watch.db"


def _get_db(db_path: str | None) -> Database:
    path = db_path or _DEFAULT_DB
    db = Database(path)
    db.connect()
    db.init_schema()
    return db


# ── init ───────────────────────────────────────────────────────────────


@app.command()
def init(
    db_path: str = typer.Option(_DEFAULT_DB, "--db", help="Path to SQLite database file"),
):
    """Initialize a new rad-device-watch database."""
    db = _get_db(db_path)
    console.print(f"[green]Database initialized at {db.path}[/green]")
    db.close()


# ── device ──────────────────────────────────────────────────────────────


@app.command()
def device_add(
    name: str = typer.Argument(..., help="Device name"),
    manufacturer: str | None = typer.Option(None, "--manufacturer", "-m"),
    model: str | None = typer.Option(None, "--model"),
    serial: str | None = typer.Option(None, "--serial", "-s"),
    station: str | None = typer.Option(None, "--station"),
    modality: str | None = typer.Option(None, "--modality"),
    location: str | None = typer.Option(None, "--location", "-l"),
    department: str | None = typer.Option(None, "--department", "-d"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Add a device to inventory."""
    db = _get_db(db_path)
    dm = DeviceManager(db)
    dev = Device(
        name=name,
        manufacturer=manufacturer,
        model=model,
        serial_number=serial,
        station_name=station,
        modality=modality,
        location=location,
        department=department,
    )
    dev_id = dm.add(dev)
    console.print(f"[green]Device added with ID {dev_id}[/green]")
    db.close()


@app.command()
def device_update(
    device_id: int = typer.Argument(..., help="Device ID"),
    name: str | None = typer.Option(None, "--name"),
    manufacturer: str | None = typer.Option(None, "--manufacturer", "-m"),
    model: str | None = typer.Option(None, "--model"),
    serial: str | None = typer.Option(None, "--serial", "-s"),
    station: str | None = typer.Option(None, "--station"),
    modality: str | None = typer.Option(None, "--modality"),
    location: str | None = typer.Option(None, "--location", "-l"),
    department: str | None = typer.Option(None, "--department", "-d"),
    status: str | None = typer.Option(None, "--status"),
    notes: str | None = typer.Option(None, "--notes"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Update supplied fields on an existing device."""
    parsed_status: DeviceStatus | None = None
    if status is not None:
        try:
            parsed_status = DeviceStatus(status)
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/red]")
            raise typer.Exit(1) from None

    db = _get_db(db_path)
    manager = DeviceManager(db)
    device = manager.get(device_id)
    if device is None:
        db.close()
        console.print(f"[red]Device {device_id} not found[/red]")
        raise typer.Exit(1)

    updates = {
        "name": name,
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": serial,
        "station_name": station,
        "modality": modality,
        "location": location,
        "department": department,
        "status": parsed_status,
        "notes": notes,
    }
    for field, value in updates.items():
        if value is not None:
            setattr(device, field, value)
    manager.update(device)
    db.close()
    console.print(f"[green]Device {device_id} updated[/green]")


@app.command()
def device_list(
    modality: str | None = typer.Option(None, "--modality", "-m"),
    status: str | None = typer.Option(None, "--status"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """List devices in inventory."""
    db = _get_db(db_path)
    dm = DeviceManager(db)
    if modality:
        devices = dm.list_by_modality(modality)
    elif status:
        try:
            s = DeviceStatus(status)
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/red]")
            return
        devices = dm.list_by_status(s)
    else:
        devices = dm.list_all()
    print_device_table(devices)
    db.close()


@app.command()
def device_get(
    device_id: int = typer.Argument(..., help="Device ID"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Show details for a device."""
    db = _get_db(db_path)
    dm = DeviceManager(db)
    dev = dm.get(device_id)
    if not dev:
        console.print(f"[red]Device {device_id} not found[/red]")
    else:
        print_device_table([dev])
    db.close()


@app.command()
def device_delete(
    device_id: int = typer.Argument(..., help="Device ID"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Delete a device from inventory."""
    db = _get_db(db_path)
    dm = DeviceManager(db)
    if dm.delete(device_id):
        console.print(f"[green]Device {device_id} deleted[/green]")
    else:
        console.print(f"[red]Device {device_id} not found[/red]")
    db.close()


# ── import ──────────────────────────────────────────────────────────────


@app.command()
def import_cmd(
    devices: str | None = typer.Option(None, "--devices", help="CSV/Excel file for device import"),
    downtime: str | None = typer.Option(
        None, "--downtime", help="CSV/Excel file for downtime import"
    ),
    usage: str | None = typer.Option(None, "--usage", help="CSV/Excel file for usage import"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Import data from CSV/Excel files."""
    from rad_device_watch.importers import csv_importer

    db = _get_db(db_path)
    dm = DeviceManager(db)
    dt = DowntimeTracker(db)
    ua = UsageAnalyzer(db)

    if devices:
        with Progress() as progress:
            task = progress.add_task("Importing devices...", total=None)
            devs = csv_importer.import_devices(devices)
            added = 0
            for d in devs:
                existing = dm.get_by_serial(d.serial_number) if d.serial_number else None
                if not existing:
                    dm.add(d)
                    added += 1
            progress.update(task, completed=True)
        console.print(f"[green]Imported {added} devices from {devices}[/green]")

    if downtime:
        with Progress() as progress:
            task = progress.add_task("Importing downtime...", total=None)
            events = csv_importer.import_downtime(downtime)
            for e in events:
                dt.log_event(e)
            progress.update(task, completed=True)
        console.print(f"[green]Imported {len(events)} downtime events from {downtime}[/green]")

    if usage:
        with Progress() as progress:
            task = progress.add_task("Importing usage...", total=None)
            records = csv_importer.import_usage(usage)
            ua.add_records(records)
            progress.update(task, completed=True)
        console.print(f"[green]Imported {len(records)} usage records from {usage}[/green]")

    db.close()


@app.command()
def import_dicom(
    directory: str = typer.Argument(..., help="Directory of DICOM files"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Extract device info from DICOM files."""
    from rad_device_watch.importers.dicom_importer import (
        extract_devices_from_directory,
    )

    db = _get_db(db_path)
    dm = DeviceManager(db)

    with Progress() as progress:
        task = progress.add_task("Scanning DICOM files...", total=None)
        devices = extract_devices_from_directory(directory, recursive=recursive)
        progress.update(task, completed=True)

    added = 0
    for d in devices:
        existing = dm.get_by_serial(d.serial_number) if d.serial_number else None
        if not existing:
            dm.add(d)
            added += 1

    console.print(f"[green]Extracted and added {added} devices from DICOM directory[/green]")
    db.close()


# ── downtime ────────────────────────────────────────────────────────────


@app.command()
def downtime_log(
    device_id: int = typer.Argument(..., help="Device ID"),
    start: str = typer.Option(..., "--start", "-s", help="Start time (YYYY-MM-DD HH:MM:SS)"),
    end: str | None = typer.Option(None, "--end", "-e", help="End time"),
    cause: str | None = typer.Option(None, "--cause", "-c", help="Cause category"),
    detail: str | None = typer.Option(None, "--detail", help="Cause detail"),
    impact: str | None = typer.Option(None, "--impact", "-i", help="Impact level"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Log a downtime event."""
    db = _get_db(db_path)
    dt = DowntimeTracker(db)

    cause_cat = None
    if cause:
        try:
            cause_cat = CauseCategory(cause)
        except ValueError:
            console.print(f"[red]Invalid cause: {cause}[/red]")
            return

    impact_lvl = None
    if impact:
        try:
            impact_lvl = ImpactLevel(impact)
        except ValueError:
            console.print(f"[red]Invalid impact: {impact}[/red]")
            return

    event = DowntimeEvent(
        device_id=device_id,
        start_time=start,
        end_time=end,
        cause_category=cause_cat,
        cause_detail=detail,
        impact_level=impact_lvl,
    )
    event_id = dt.log_event(event)
    console.print(f"[green]Downtime event {event_id} logged[/green]")
    db.close()


@app.command()
def downtime_list(
    device_id: int | None = typer.Option(None, "--device", "-d"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """List downtime events."""
    db = _get_db(db_path)
    dt = DowntimeTracker(db)
    events = dt.list_events(device_id=device_id)

    if not events:
        console.print("[yellow]No downtime events found.[/yellow]")
    else:
        from rich.table import Table

        table = Table(title=f"Downtime Events ({len(events)})")
        table.add_column("ID", style="cyan")
        table.add_column("Device ID")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Duration (min)")
        table.add_column("Cause")
        table.add_column("Impact")

        for e in events:
            table.add_row(
                str(e.id or ""),
                str(e.device_id),
                e.start_time,
                e.end_time or "",
                f"{e.duration_minutes:.0f}" if e.duration_minutes else "",
                e.cause_category.value if e.cause_category else "",
                e.impact_level.value if e.impact_level else "",
            )
        console.print(table)

    db.close()


@app.command()
def downtime_delete(
    event_id: int = typer.Argument(..., help="Downtime event ID"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Delete a downtime event."""
    db = _get_db(db_path)
    deleted = DowntimeTracker(db).delete_event(event_id)
    db.close()
    if not deleted:
        console.print(f"[red]Downtime event {event_id} not found[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Downtime event {event_id} deleted[/green]")


# ── uptime ──────────────────────────────────────────────────────────────


@app.command()
def uptime(
    period_start: str = typer.Argument(
        ..., help="Period start (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
    ),
    period_end: str = typer.Argument(..., help="Period end"),
    device_id: int | None = typer.Option(None, "--device", "-d"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Calculate uptime for one or all devices."""
    db = _get_db(db_path)
    dt = DowntimeTracker(db)

    if device_id:
        reports = [dt.compute_uptime(device_id, period_start, period_end)]
    else:
        reports = dt.uptime_for_all_devices(period_start, period_end)

    print_uptime_table(reports)
    db.close()


# ── usage ───────────────────────────────────────────────────────────────


@app.command()
def usage_add(
    device_id: int = typer.Argument(..., help="Device ID"),
    date: str = typer.Option(..., "--date", "-d", help="Procedure date (YYYY-MM-DD)"),
    count: int = typer.Option(1, "--count", "-c", help="Procedure count"),
    modality: str | None = typer.Option(None, "--modality", "-m"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Add a usage record."""
    db = _get_db(db_path)
    ua = UsageAnalyzer(db)
    rec = UsageRecord(
        device_id=device_id,
        procedure_date=date,
        procedure_count=count,
        modality=modality,
    )
    rec_id = ua.add_record(rec)
    console.print(f"[green]Usage record {rec_id} added[/green]")
    db.close()


@app.command()
def usage_report(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="End date (YYYY-MM-DD)"),
    device_id: int | None = typer.Option(None, "--device", "-d"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Generate usage summary report."""
    db = _get_db(db_path)
    ua = UsageAnalyzer(db)

    if device_id:
        summary = ua.summarize_device(device_id, start_date, end_date)
        summaries = [summary] if summary else []
    else:
        summaries = ua.summarize_all(start_date, end_date)

    print_usage_table(summaries)
    total = ua.total_procedures(start_date, end_date)
    console.print(f"\nTotal procedures across all devices: [bold]{total}[/bold]")
    db.close()


# ── maintenance ─────────────────────────────────────────────────────────


@app.command()
def maintenance_add(
    device_id: int = typer.Argument(..., help="Device ID"),
    maintenance_type: str = typer.Option(
        ..., "--type", help="preventive, corrective, or calibration"
    ),
    scheduled_date: str | None = typer.Option(None, "--scheduled"),
    completed_date: str | None = typer.Option(None, "--completed"),
    description: str | None = typer.Option(None, "--description"),
    vendor: str | None = typer.Option(None, "--vendor"),
    cost: float | None = typer.Option(None, "--cost"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Add a maintenance record for a device."""
    try:
        parsed_type = MaintenanceType(maintenance_type)
    except ValueError:
        console.print(f"[red]Invalid maintenance type: {maintenance_type}[/red]")
        raise typer.Exit(1) from None

    db = _get_db(db_path)
    manager = MaintenanceManager(db)
    try:
        record_id = manager.add(
            MaintenanceRecord(
                device_id=device_id,
                maintenance_type=parsed_type,
                scheduled_date=scheduled_date,
                completed_date=completed_date,
                description=description,
                vendor=vendor,
                cost=cost,
            )
        )
    except ValueError as exc:
        db.close()
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    db.close()
    console.print(f"[green]Maintenance record {record_id} added[/green]")


@app.command()
def maintenance_list(
    device_id: int | None = typer.Option(None, "--device", "-d"),
    pending: bool = typer.Option(False, "--pending", help="Show incomplete records only"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """List maintenance records."""
    from rich.table import Table

    db = _get_db(db_path)
    records = MaintenanceManager(db).list_records(device_id=device_id, pending_only=pending)
    db.close()

    table = Table(title=f"Maintenance Records ({len(records)})")
    for heading in ("ID", "Device", "Type", "Scheduled", "Completed", "Vendor", "Cost"):
        table.add_column(heading)
    for record in records:
        table.add_row(
            str(record.id or ""),
            str(record.device_id),
            record.maintenance_type.value,
            record.scheduled_date or "",
            record.completed_date or "",
            record.vendor or "",
            f"{record.cost:.2f}" if record.cost is not None else "",
        )
    console.print(table)


@app.command()
def maintenance_complete(
    record_id: int = typer.Argument(..., help="Maintenance record ID"),
    completed_date: str | None = typer.Option(None, "--date"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Mark a maintenance record complete."""
    date = completed_date or datetime.now().strftime("%Y-%m-%d")
    db = _get_db(db_path)
    completed = MaintenanceManager(db).complete(record_id, date)
    db.close()
    if not completed:
        console.print(f"[red]Maintenance record {record_id} not found[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Maintenance record {record_id} completed[/green]")


@app.command()
def maintenance_delete(
    record_id: int = typer.Argument(..., help="Maintenance record ID"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Delete a maintenance record."""
    db = _get_db(db_path)
    deleted = MaintenanceManager(db).delete(record_id)
    db.close()
    if not deleted:
        console.print(f"[red]Maintenance record {record_id} not found[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Maintenance record {record_id} deleted[/green]")


# ── alert ───────────────────────────────────────────────────────────────


@app.command()
def alert_add(
    name: str = typer.Argument(..., help="Alert rule name"),
    metric: str = typer.Option(
        ..., "--metric", "-m", help="Metric: downtime_duration, uptime_pct, usage_volume"
    ),
    condition: str = typer.Option(..., "--condition", "-c", help="Condition: gt, lt, eq"),
    threshold: float = typer.Option(..., "--threshold", "-t", help="Threshold value"),
    channel: str = typer.Option(
        "console", "--channel", help="Channel: console, email, slack, webhook"
    ),
    channel_config: str | None = typer.Option(
        None, "--config", help="Channel configuration as a JSON object"
    ),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Add an alert rule."""
    try:
        am = AlertMetric(metric)
    except ValueError:
        console.print(f"[red]Invalid metric: {metric}[/red]")
        return
    try:
        ac = AlertCondition(condition)
    except ValueError:
        console.print(f"[red]Invalid condition: {condition}[/red]")
        return
    try:
        ach = AlertChannel(channel)
    except ValueError:
        console.print(f"[red]Invalid channel: {channel}[/red]")
        return

    db = _get_db(db_path)
    engine = AlertEngine(db)
    rule = AlertRule(
        name=name,
        metric=am,
        condition=ac,
        threshold=threshold,
        channel=ach,
        channel_config=channel_config,
    )
    try:
        rule_id = engine.add_rule(rule)
    except ValueError as exc:
        db.close()
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[green]Alert rule '{name}' added with ID {rule_id}[/green]")
    db.close()


@app.command()
def alert_check(
    db_path: str | None = typer.Option(None, "--db"),
):
    """Evaluate all alert rules and dispatch notifications."""
    db = _get_db(db_path)
    engine = AlertEngine(db)
    triggered = engine.poll()
    console.print(f"[green]Alert check complete. {len(triggered)} alerts triggered.[/green]")

    if triggered:
        for t in triggered:
            console.print(f"  [yellow]{t.triggered_at}[/yellow] {t.message}")

    db.close()


@app.command()
def alert_history(
    device_id: int | None = typer.Option(None, "--device", "-d"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Show alert history."""
    db = _get_db(db_path)
    engine = AlertEngine(db)
    history = engine.get_history(device_id=device_id)
    print_alert_history(history)
    db.close()


@app.command()
def alert_acknowledge(
    history_id: int = typer.Argument(..., help="Alert history ID"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Acknowledge a triggered alert."""
    db = _get_db(db_path)
    acknowledged = AlertEngine(db).acknowledge(history_id)
    db.close()
    if not acknowledged:
        console.print(f"[red]Alert history {history_id} not found[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Alert history {history_id} acknowledged[/green]")


@app.command()
def alert_delete(
    rule_id: int = typer.Argument(..., help="Alert rule ID"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Delete an alert rule."""
    db = _get_db(db_path)
    deleted = AlertEngine(db).delete_rule(rule_id)
    db.close()
    if not deleted:
        console.print(f"[red]Alert rule {rule_id} not found[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Alert rule {rule_id} deleted[/green]")


# ── export ──────────────────────────────────────────────────────────────


@app.command()
def export(
    output_dir: str = typer.Argument(".", help="Output directory for CSV files"),
    device: bool = typer.Option(True, "--device/--no-device"),
    downtime: bool = typer.Option(True, "--downtime/--no-downtime"),
    usage: bool = typer.Option(True, "--usage/--no-usage"),
    db_path: str | None = typer.Option(None, "--db"),
):
    """Export database tables to CSV."""
    from rad_device_watch.exporters.csv_exporter import (
        export_devices,
        export_downtime,
        export_usage,
    )

    db = _get_db(db_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if device:
        rows = db.rows_to_dicts(db.fetchall("SELECT * FROM devices"))
        path = export_devices(rows, out / "devices.csv")
        console.print(f"[green]Exported {len(rows)} devices to {path}[/green]")

    if downtime:
        rows = db.rows_to_dicts(db.fetchall("SELECT * FROM downtime_events"))
        path = export_downtime(rows, out / "downtime_events.csv")
        console.print(f"[green]Exported {len(rows)} downtime events to {path}[/green]")

    if usage:
        rows = db.rows_to_dicts(db.fetchall("SELECT * FROM usage_records"))
        path = export_usage(rows, out / "usage_records.csv")
        console.print(f"[green]Exported {len(rows)} usage records to {path}[/green]")

    db.close()


# ── serve (dashboard) ──────────────────────────────────────────────────


@app.command()
def serve(
    db_path: str | None = typer.Option(None, "--db"),
    port: int = typer.Option(8501, "--port", "-p", help="Streamlit port"),
):
    """Launch the Streamlit dashboard."""
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(__file__).parent / "dashboard.py"),
        "--server.port",
        str(port),
    ]
    env = {**os.environ, "RAD_DEVICE_WATCH_DB": db_path or _DEFAULT_DB}

    console.print(f"[green]Launching dashboard on port {port}...[/green]")
    subprocess.run(cmd, check=True, env=env)
