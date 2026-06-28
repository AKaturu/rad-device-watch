from __future__ import annotations

import json
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class AlertChannel(Protocol):
    def send(self, message: str, config: dict | None = None) -> bool: ...


class ConsoleChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        logger.warning("ALERT: %s", message)
        print(f"[ALERT] {message}")
        return True


class EmailChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        cfg = config or {}
        smtp_server = cfg.get("smtp_server", "localhost")
        smtp_port = cfg.get("smtp_port", 587)
        sender = cfg.get("sender", "rad-device-watch@localhost")
        recipients = cfg.get("recipients", [])
        username = cfg.get("username")
        password = cfg.get("password")
        use_tls = cfg.get("use_tls", True)

        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(",")]

        if not recipients:
            logger.warning("Email alert skipped: no recipients configured")
            return False

        msg = EmailMessage()
        msg["Subject"] = "[rad-device-watch] Alert"
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.set_content(message)

        try:
            context = ssl.create_default_context() if use_tls else None
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls(context=context)
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            logger.info("Email alert sent to %s", recipients)
            return True
        except Exception as exc:
            logger.error("Failed to send email alert: %s", exc)
            return False


class SlackChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        cfg = config or {}
        webhook_url = cfg.get("webhook_url", "")
        if not webhook_url:
            logger.warning("Slack alert skipped: no webhook_url configured")
            return False
        try:
            resp = httpx.post(webhook_url, json={"text": message}, timeout=10)
            resp.raise_for_status()
            logger.info("Slack alert sent")
            return True
        except Exception as exc:
            logger.error("Failed to send Slack alert: %s", exc)
            return False


class WebhookChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        cfg = config or {}
        url = cfg.get("url", "")
        if not url:
            logger.warning("Webhook alert skipped: no url configured")
            return False
        headers = cfg.get("headers", {"Content-Type": "application/json"})
        payload = cfg.get("payload_template", {"text": message})
        rendered = json.loads(
            json.dumps(payload).replace("{{message}}", message)
        )
        try:
            resp = httpx.post(url, json=rendered, headers=headers, timeout=10)
            resp.raise_for_status()
            logger.info("Webhook alert sent to %s", url)
            return True
        except Exception as exc:
            logger.error("Failed to send webhook alert: %s", exc)
            return False


def get_channel(name: str) -> AlertChannel:
    mapping: dict[str, AlertChannel] = {
        "console": ConsoleChannel(),
        "email": EmailChannel(),
        "slack": SlackChannel(),
        "webhook": WebhookChannel(),
    }
    return mapping.get(name, ConsoleChannel())
