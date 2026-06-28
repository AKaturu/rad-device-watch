from __future__ import annotations

import sys

import streamlit as st

from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.downtime import DowntimeTracker
from rad_device_watch.models import Device, DeviceStatus, DowntimeEvent, UsageRecord
from rad_device_watch.usage import UsageAnalyzer


def _get_db() -> Database:
    db_arg = None
    if len(sys.argv) > 1 and sys.argv[-2] == "--db":
        db_arg = sys.argv[-1]
    path = db_arg or "rad_device_watch.db"
    db = Database(path)
    db.connect()
    db.init_schema()
    return db


st.set_page_config(
    page_title="rad-device-watch",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 rad-device-watch")
st.markdown("Radiology device monitoring dashboard")

db = _get_db()
dm = DeviceManager(db)
dt = DowntimeTracker(db)
ua = UsageAnalyzer(db)

tab_overview, tab_devices, tab_downtime, tab_usage, tab_alerts = st.tabs(
    ["Overview", "Devices", "Downtime", "Usage", "Alerts"]
)

with tab_overview:
    col1, col2, col3, col4 = st.columns(4)
    devices = dm.list_all()
    col1.metric("Total Devices", len(devices))

    active = [d for d in devices if d.status == DeviceStatus.active]
    col2.metric("Active Devices", len(active))

    modalities = dm.modalities()
    col3.metric("Modalities", len(modalities))

    events = dt.list_events(limit=10)
    col4.metric("Recent Downtime Events", len(events))

    if devices:
        st.subheader("Device Inventory")
        data = []
        for d in devices:
            data.append(
                {
                    "ID": d.id,
                    "Name": d.name,
                    "Modality": d.modality or "",
                    "Manufacturer": d.manufacturer or "",
                    "Location": d.location or "",
                    "Status": d.status.value,
                }
            )
        st.dataframe(data, use_container_width=True, hide_index=True)

with tab_devices:
    st.subheader("Add Device")
    with st.form("add_device_form"):
        cols = st.columns(2)
        name = cols[0].text_input("Name *")
        manufacturer = cols[1].text_input("Manufacturer")
        model = cols[0].text_input("Model")
        serial = cols[1].text_input("Serial Number")
        station = cols[0].text_input("Station Name")
        modality = cols[1].text_input("Modality")
        location = cols[0].text_input("Location")
        department = cols[1].text_input("Department")
        submitted = st.form_submit_button("Add Device")
        if submitted and name:
            dm.add(
                Device(
                    name=name,
                    manufacturer=manufacturer or None,
                    model=model or None,
                    serial_number=serial or None,
                    station_name=station or None,
                    modality=modality or None,
                    location=location or None,
                    department=department or None,
                )
            )
            st.success(f"Device '{name}' added")
            st.rerun()

    st.subheader("Import from DICOM Directory")
    dicom_dir = st.text_input("DICOM directory path")
    if st.button("Scan DICOM Directory") and dicom_dir:
        from rad_device_watch.importers.dicom_importer import (
            extract_devices_from_directory,
        )

        with st.spinner("Scanning..."):
            extracted = extract_devices_from_directory(dicom_dir)
            added = 0
            for d in extracted:
                existing = (
                    dm.get_by_serial(d.serial_number) if d.serial_number else None
                )
                if not existing:
                    dm.add(d)
                    added += 1
        st.success(f"Added {added} devices from {dicom_dir}")

    st.subheader("All Devices")
    all_devices = dm.list_all()
    if all_devices:
        device_data = [
            {
                "ID": d.id,
                "Name": d.name,
                "Manufacturer": d.manufacturer or "",
                "Model": d.model or "",
                "Serial": d.serial_number or "",
                "Modality": d.modality or "",
                "Status": d.status.value,
            }
            for d in all_devices
        ]
        st.dataframe(device_data, use_container_width=True, hide_index=True)

        device_names = {d.id: d.name for d in all_devices}
        del_id = st.selectbox(
            "Delete device",
            options=list(device_names.keys()),
            format_func=lambda x: f"{x}: {device_names[x]}",
        )
        if st.button("Delete Selected Device"):
            dm.delete(del_id)
            st.success(f"Device {del_id} deleted")
            st.rerun()

with tab_downtime:
    st.subheader("Log Downtime Event")
    with st.form("downtime_form"):
        dev_options = {d.id: d.name for d in dm.list_all()}
        if dev_options:
            dev_id = st.selectbox(
                "Device",
                options=list(dev_options.keys()),
                format_func=lambda x: f"{x}: {dev_options[x]}",
            )
            start = st.text_input("Start Time (YYYY-MM-DD HH:MM:SS)")
            end = st.text_input("End Time (YYYY-MM-DD HH:MM:SS)", value="")
            cause = st.selectbox(
                "Cause Category",
                ["", "hardware", "software", "calibration", "network", "power", "other"],
            )
            detail = st.text_area("Cause Detail")
            impact = st.selectbox("Impact Level", ["", "low", "medium", "high", "critical"])
            if st.form_submit_button("Log Event") and start and dev_id:
                event = DowntimeEvent(
                    device_id=dev_id,
                    start_time=start,
                    end_time=end or None,
                    cause_category=cause or None,
                    cause_detail=detail or None,
                    impact_level=impact or None,
                )
                dt.log_event(event)
                st.success("Downtime event logged")
                st.rerun()

    st.subheader("Recent Downtime Events")
    events = dt.list_events(limit=50)
    if events:
        ev_data = [
            {
                "ID": e.id,
                "Device ID": e.device_id,
                "Start": e.start_time,
                "End": e.end_time or "",
                "Duration (min)": f"{e.duration_minutes:.0f}" if e.duration_minutes else "",
                "Cause": e.cause_category.value if e.cause_category else "",
                "Impact": e.impact_level.value if e.impact_level else "",
            }
            for e in events
        ]
        st.dataframe(ev_data, use_container_width=True, hide_index=True)

with tab_usage:
    st.subheader("Add Usage Record")
    with st.form("usage_form"):
        dev_options = {d.id: d.name for d in dm.list_all()}
        if dev_options:
            dev_id = st.selectbox(
                "Device",
                options=list(dev_options.keys()),
                format_func=lambda x: f"{x}: {dev_options[x]}",
                key="usage_dev",
            )
            proc_date = st.date_input("Procedure Date")
            count = st.number_input("Procedure Count", min_value=1, value=1)
            if st.form_submit_button("Add Record"):
                ua.add_record(
                    UsageRecord(
                        device_id=dev_id,
                        procedure_date=str(proc_date),
                        procedure_count=count,
                    )
                )
                st.success("Usage record added")
                st.rerun()

    st.subheader("Usage Summary")
    from datetime import datetime, timedelta
    end_default = datetime.now().strftime("%Y-%m-%d")
    start_default = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    col1, col2 = st.columns(2)
    start_date = col1.text_input("Start Date", value=start_default)
    end_date = col2.text_input("End Date", value=end_default)
    if st.button("Generate Report"):
        summaries = ua.summarize_all(start_date, end_date)
        if summaries:
            s_data = [
                {
                    "Device": s.device_name,
                    "Modality": s.modality or "",
                    "Procedures": s.procedure_count,
                    "Active Days": s.unique_days,
                    "Avg/Day": s.avg_daily_volume,
                    "Peak/Day": s.peak_daily_volume,
                    "Trend": s.trend_direction or "-",
                }
                for s in summaries
            ]
            st.dataframe(s_data, use_container_width=True, hide_index=True)
            total = ua.total_procedures(start_date, end_date)
            st.metric("Total Procedures", total)

with tab_alerts:
    from rad_device_watch.alerts.engine import AlertEngine

    engine = AlertEngine(db)
    st.subheader("Alert Rules")
    rules = engine.list_rules()
    if rules:
        rule_data = [
            {
                "ID": r.id,
                "Name": r.name,
                "Metric": r.metric.value,
                "Condition": r.condition.value,
                "Threshold": r.threshold,
                "Channel": r.channel.value,
                "Enabled": "Yes" if r.enabled else "No",
            }
            for r in rules
        ]
        st.dataframe(rule_data, use_container_width=True, hide_index=True)

    if st.button("Run Alert Check"):
        triggered = engine.poll()
        if triggered:
            st.warning(f"{len(triggered)} alerts triggered")
            for t in triggered:
                st.text(f"{t.triggered_at} - {t.message}")
        else:
            st.success("No alerts triggered")

    st.subheader("Alert History")
    history = engine.get_history(limit=50)
    if history:
        h_data = [
            {
                "Time": h.triggered_at,
                "Message": h.message,
                "Channel": h.channel or "",
                "Acknowledged": "Yes" if h.acknowledged else "No",
            }
            for h in history
        ]
        st.dataframe(h_data, use_container_width=True, hide_index=True)

db.close()
