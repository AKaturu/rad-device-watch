from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate README demo media from real CLI output.")
    parser.add_argument("--output", type=Path, default=Path("outputs/demo-media"))
    parser.add_argument("--assets", type=Path, default=Path("docs/assets"))
    parser.add_argument("--skip-run", action="store_true")
    return parser.parse_args()


def font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str] = []
    if os.name == "nt":
        candidates.extend(
            [
                "C:/Windows/Fonts/consola.ttf" if mono else "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
        )
    candidates.extend(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
            if mono
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Menlo.ttc" if mono else "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def clean(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r\n", "\n").strip()


def run_cli(args: list[str], db_path: Path) -> str:
    command = [
        sys.executable,
        "-c",
        "from rad_device_watch.cli import app; app()",
        *args,
        "--db",
        str(db_path),
    ]
    env = {
        **os.environ,
        "NO_COLOR": "1",
        "PYTHONUTF8": "1",
        "PYTHONPATH": os.pathsep.join(
            part for part in (str(ROOT / "src"), os.environ.get("PYTHONPATH")) if part
        ),
    }
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )
    return clean(result.stdout)


def wrap_line(
    draw: ImageDraw.ImageDraw, text: str, max_width: int, fnt: ImageFont.ImageFont
) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    max_width: int,
    fnt: ImageFont.ImageFont,
    fill: str,
    line_height: int,
) -> int:
    x, y = xy
    for raw in text.splitlines():
        for line in wrap_line(draw, raw, max_width, fnt):
            draw.text((x, y), line, font=fnt, fill=fill)
            y += line_height
    return y


def make_frame(
    title: str, command: str, body: list[str], stats: list[tuple[str, str]], footer: str
) -> Image.Image:
    image = Image.new("RGB", (1280, 720), "#101419")
    draw = ImageDraw.Draw(image)
    title_font = font(42)
    body_font = font(22, mono=True)
    small_font = font(20)
    stat_font = font(26)

    draw.rectangle((0, 0, 1280, 88), fill="#1f2933")
    draw.rectangle((0, 88, 1280, 96), fill="#38bdf8")
    draw.text((40, 24), title, font=title_font, fill="#f8fafc")
    draw.text((40, 675), footer, font=small_font, fill="#a8b3bd")

    draw.rounded_rectangle(
        (40, 130, 780, 630), radius=14, fill="#0b0f14", outline="#314154", width=2
    )
    draw_wrapped(draw, (70, 158), f"$ {command}", 660, body_font, "#bae6fd", 30)
    y = 218
    for line in body:
        y = draw_wrapped(draw, (70, y), line, 660, body_font, "#d9e2ec", 30) + 4

    draw.rounded_rectangle(
        (820, 130, 1240, 630), radius=14, fill="#111827", outline="#344052", width=2
    )
    draw.text((850, 160), "Monitoring snapshot", font=stat_font, fill="#f8fafc")
    y = 220
    for label, value in stats:
        draw.text((850, y), label, font=small_font, fill="#9fb0c0")
        draw.text((850, y + 28), value, font=stat_font, fill="#facc15")
        y += 78
    return image


def query_count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def run_demo(output: Path) -> dict[str, str]:
    db_path = output / "rad_device_watch_demo.db"
    export_dir = output / "exports"
    today = date.today()
    day_1 = today - timedelta(days=1)
    day_2 = today - timedelta(days=2)
    period_start = (today - timedelta(days=30)).isoformat()
    period_end = today.isoformat()
    if db_path.exists():
        db_path.unlink()
    export_dir.mkdir(parents=True, exist_ok=True)

    transcripts: dict[str, str] = {}
    transcripts["init"] = run_cli(["init"], db_path)
    device_specs = [
        [
            "device-add",
            "CT Bay 1",
            "--manufacturer",
            "Siemens",
            "--model",
            "SOMATOM Force",
            "--serial",
            "CT-001",
            "--station",
            "CTBAY1",
            "--modality",
            "CT",
            "--location",
            "Room 101",
            "--department",
            "Radiology",
        ],
        [
            "device-add",
            "MR Suite 2",
            "--manufacturer",
            "GE",
            "--model",
            "SIGNA Architect",
            "--serial",
            "MR-002",
            "--station",
            "MRSUITE2",
            "--modality",
            "MR",
            "--location",
            "Room 202",
            "--department",
            "Radiology",
        ],
        [
            "device-add",
            "XR Room 3",
            "--manufacturer",
            "Canon",
            "--model",
            "RadPRO",
            "--serial",
            "XR-003",
            "--station",
            "XRROOM3",
            "--modality",
            "XR",
            "--location",
            "Room 303",
            "--department",
            "Radiology",
        ],
    ]
    for spec in device_specs:
        run_cli(spec, db_path)
    transcripts["devices"] = run_cli(["device-list"], db_path)

    run_cli(
        [
            "downtime-log",
            "1",
            "--start",
            f"{day_2.isoformat()} 08:00:00",
            "--end",
            f"{day_2.isoformat()} 10:30:00",
            "--cause",
            "hardware",
            "--impact",
            "high",
            "--detail",
            "Tube cooling alarm",
        ],
        db_path,
    )
    run_cli(
        [
            "downtime-log",
            "2",
            "--start",
            f"{day_1.isoformat()} 13:00:00",
            "--end",
            f"{day_1.isoformat()} 13:45:00",
            "--cause",
            "software",
            "--impact",
            "low",
            "--detail",
            "Protocol workstation reboot",
        ],
        db_path,
    )
    transcripts["downtime"] = run_cli(["downtime-list"], db_path)
    transcripts["uptime"] = run_cli(["uptime", period_start, period_end], db_path)

    usage_rows = [
        ("1", day_2.isoformat(), "42", "CT"),
        ("1", day_1.isoformat(), "39", "CT"),
        ("2", day_2.isoformat(), "28", "MR"),
        ("2", day_1.isoformat(), "31", "MR"),
        ("3", day_2.isoformat(), "76", "XR"),
        ("3", day_1.isoformat(), "82", "XR"),
    ]
    for device_id, procedure_date, count, modality in usage_rows:
        run_cli(
            [
                "usage-add",
                device_id,
                "--date",
                procedure_date,
                "--count",
                count,
                "--modality",
                modality,
            ],
            db_path,
        )
    transcripts["usage"] = run_cli(["usage-report", period_start, period_end], db_path)

    run_cli(
        [
            "alert-add",
            "High weekly usage",
            "--metric",
            "usage_volume",
            "--condition",
            "gt",
            "--threshold",
            "75",
        ],
        db_path,
    )
    transcripts["alerts"] = run_cli(["alert-check"], db_path)
    transcripts["export"] = run_cli(["export", str(export_dir)], db_path)
    return transcripts


def csv_summary(output: Path) -> dict[str, list[str]]:
    devices = pd.read_csv(output / "exports" / "devices.csv")
    downtime = pd.read_csv(output / "exports" / "downtime_events.csv")
    usage = pd.read_csv(output / "exports" / "usage_records.csv")

    device_lines = [
        f"{row.name}: {row.manufacturer} {row.model} ({row.modality}) - {row.location}"
        for row in devices[["name", "manufacturer", "model", "modality", "location"]].itertuples(
            index=False
        )
    ]
    downtime_lines = [
        f"Device {int(row.device_id)}: {int(row.duration_minutes)} min {row.cause_category} downtime ({row.impact_level})"
        for row in downtime[
            ["device_id", "duration_minutes", "cause_category", "impact_level"]
        ].itertuples(index=False)
    ]
    usage_totals = usage.groupby("modality", as_index=False)["procedure_count"].sum()
    usage_lines = [
        f"{row.modality}: {int(row.procedure_count)} procedures"
        for row in usage_totals.itertuples(index=False)
    ]
    return {"devices": device_lines, "downtime": downtime_lines, "usage": usage_lines}


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.assets.mkdir(parents=True, exist_ok=True)

    transcripts = {} if args.skip_run else run_demo(args.output)
    db_path = args.output / "rad_device_watch_demo.db"
    devices = query_count(db_path, "devices")
    downtime = query_count(db_path, "downtime_events")
    usage = query_count(db_path, "usage_records")
    alerts = query_count(db_path, "alert_history")
    exported_usage = pd.read_csv(args.output / "exports" / "usage_records.csv")
    total_procedures = int(exported_usage["procedure_count"].sum())
    summaries = csv_summary(args.output)

    stats = [
        ("Devices tracked", str(devices)),
        ("Downtime events", str(downtime)),
        ("Usage records", str(usage)),
        ("Total procedures", str(total_procedures)),
        ("Alerts triggered", str(alerts)),
    ]
    frames = [
        make_frame(
            "rad-device-watch",
            "rad-device-watch device-list",
            summaries["devices"],
            stats,
            "Real CLI output from a synthetic monitoring database.",
        ),
        make_frame(
            "Uptime and downtime tracking",
            "rad-device-watch downtime-list && uptime",
            summaries["downtime"]
            + [
                "",
                "Uptime report generated across all tracked devices.",
                "Downtime minutes roll into device availability percentages.",
            ],
            stats,
            "Downtime events roll up into period uptime percentages.",
        ),
        make_frame(
            "Usage auditing and alerts",
            "rad-device-watch usage-report && alert-check",
            summaries["usage"] + [""] + transcripts.get("alerts", "").splitlines()[:2],
            stats,
            "Inventory, uptime, usage, alerts, and CSV export are exercised in one run.",
        ),
    ]

    poster = args.assets / "demo-poster.png"
    gif = args.assets / "demo.gif"
    mp4 = args.assets / "demo.mp4"
    frames[0].save(poster)
    # Hold each real CLI-derived scene long enough to read, then encode the same
    # three-step sequence as the full browser-playable walkthrough.
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=3000, loop=0)
    with imageio.get_writer(
        mp4, fps=6, codec="libx264", quality=8, macro_block_size=None
    ) as writer:
        for frame in frames:
            for _ in range(18):
                writer.append_data(np.asarray(frame))
    print(f"Wrote {poster}")
    print(f"Wrote {gif}")
    print(f"Wrote {mp4}")


if __name__ == "__main__":
    main()
