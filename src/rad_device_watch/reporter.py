from __future__ import annotations

from rich.console import Console
from rich.table import Table

from rad_device_watch.database import Database
from rad_device_watch.models import AlertHistory, Device, UptimeReport, UsageSummary

console = Console()


def print_device_table(devices: list[Device]) -> None:
    if not devices:
        console.print("[yellow]No devices found.[/yellow]")
        return
    table = Table(title=f"Devices ({len(devices)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Manufacturer")
    table.add_column("Model")
    table.add_column("Serial #")
    table.add_column("Modality")
    table.add_column("Location")
    table.add_column("Status")

    for d in devices:
        table.add_row(
            str(d.id or ""),
            d.name,
            d.manufacturer or "",
            d.model or "",
            d.serial_number or "",
            d.modality or "",
            d.location or "",
            d.status.value,
        )
    console.print(table)


def print_uptime_table(reports: list[UptimeReport]) -> None:
    if not reports:
        console.print("[yellow]No uptime data.[/yellow]")
        return
    table = Table(title="Uptime Report")
    table.add_column("Device", style="green")
    table.add_column("Period")
    table.add_column("Total (hrs)")
    table.add_column("Downtime (hrs)")
    table.add_column("Uptime %", style="bold")

    for r in reports:
        pct_str = f"{r.uptime_pct:.1f}%"
        if r.uptime_pct >= 99.5:
            pct_str = f"[green]{pct_str}[/green]"
        elif r.uptime_pct < 95:
            pct_str = f"[red]{pct_str}[/red]"

        table.add_row(
            r.device_name,
            f"{r.period_start} to {r.period_end}",
            f"{r.total_minutes / 60:.1f}",
            f"{r.downtime_minutes / 60:.1f}",
            pct_str,
        )
    console.print(table)


def print_usage_table(summaries: list[UsageSummary]) -> None:
    if not summaries:
        console.print("[yellow]No usage data.[/yellow]")
        return
    table = Table(title="Usage Summary")
    table.add_column("Device", style="green")
    table.add_column("Modality")
    table.add_column("Total Procedures")
    table.add_column("Active Days")
    table.add_column("Avg/Day")
    table.add_column("Peak/Day")
    table.add_column("Trend")

    for s in summaries:
        trend = s.trend_direction or "-"
        if s.trend_direction == "increasing":
            trend = f"[green]{trend}[/green]"
        elif s.trend_direction == "decreasing":
            trend = f"[red]{trend}[/red]"

        table.add_row(
            s.device_name,
            s.modality or "",
            str(s.procedure_count),
            str(s.unique_days),
            str(s.avg_daily_volume),
            str(s.peak_daily_volume),
            trend,
        )
    console.print(table)


def print_alert_history(history: list[AlertHistory]) -> None:
    if not history:
        console.print("[yellow]No alert history.[/yellow]")
        return
    table = Table(title="Alert History")
    table.add_column("Time", style="cyan")
    table.add_column("Message")
    table.add_column("Channel")
    table.add_column("Acknowledged")

    for h in history:
        ack = "[green]Yes[/green]" if h.acknowledged else "[red]No[/red]"
        table.add_row(
            h.triggered_at,
            h.message,
            h.channel or "",
            ack,
        )
    console.print(table)


def generate_report_text(
    db: Database,
    devices: list[Device] | None = None,
    uptime: list[UptimeReport] | None = None,
    usage: list[UsageSummary] | None = None,
) -> str:
    lines = ["=" * 60, "rad-device-watch Report", "=" * 60, ""]

    if devices is not None:
        lines.append(f"Devices: {len(devices)}")
        for d in devices:
            lines.append(f"  {d.id}: {d.name} ({d.modality or 'N/A'}) - {d.status.value}")
        lines.append("")

    if uptime is not None:
        lines.append("Uptime:")
        for r in uptime:
            lines.append(
                f"  {r.device_name}: {r.uptime_pct:.1f}% "
                f"(downtime: {r.downtime_minutes / 60:.1f} hrs)"
            )
        lines.append("")

    if usage is not None:
        lines.append("Usage:")
        for s in usage:
            lines.append(
                f"  {s.device_name}: {s.procedure_count} procedures, "
                f"{s.avg_daily_volume}/day avg"
            )
        lines.append("")

    return "\n".join(lines)
