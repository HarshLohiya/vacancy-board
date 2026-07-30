"""Delivery channels. Each reads its own credentials from the environment and
stays silent if they are absent, so you can switch a channel on or off just by
adding or removing a secret."""

from __future__ import annotations

import html as htmllib
import logging
import os
import re
import smtplib
import time
from email.message import EmailMessage

import requests

log = logging.getLogger("notify")


def _plain(body: str) -> str:
    """Strip the small HTML subset back to readable plain text."""
    body = re.sub(r'<a href="([^"]+)">([^<]*)</a>', r"\2: \1", body)
    body = re.sub(r"</?b>", "", body)
    return htmllib.unescape(body)


# --------------------------------------------------------------------------
# Telegram
# --------------------------------------------------------------------------
def telegram(subject: str, body: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    text = f"{body}"
    chunks = _chunk(text, 3800)
    ok = True
    for chunk in chunks:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": chunk,
                      "parse_mode": "HTML",
                      "disable_web_page_preview": "true"},
                timeout=30)
            if r.status_code != 200:
                log.error("telegram: %s %s", r.status_code, r.text[:200])
                ok = False
        except requests.RequestException as e:
            log.error("telegram: %s", e)
            ok = False
        time.sleep(1)
    return ok


def _chunk(text: str, limit: int) -> list[str]:
    out, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            out.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        out.append(current)
    return out or [text]


# --------------------------------------------------------------------------
# E-mail
# --------------------------------------------------------------------------
def email(subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to_addr = os.getenv("EMAIL_TO")
    if not all([host, user, password, to_addr]):
        return False
    port = int(os.getenv("SMTP_PORT", "465"))

    msg = EmailMessage()
    msg["Subject"] = f"[Vacancy board] {subject}"
    msg["From"] = os.getenv("EMAIL_FROM", user)
    msg["To"] = to_addr
    msg.set_content(_plain(body))
    msg.add_alternative(
        "<div style=\"font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;"
        "color:#14181c\">" + body.replace("\n", "<br>") + "</div>",
        subtype="html")

    try:
        if port == 587:
            with smtplib.SMTP(host, port, timeout=40) as s:
                s.starttls()
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=40) as s:
                s.login(user, password)
                s.send_message(msg)
        return True
    except Exception as e:                      # noqa: BLE001
        log.error("email: %s", e)
        return False


# --------------------------------------------------------------------------
# WhatsApp
# --------------------------------------------------------------------------
def whatsapp(subject: str, body: str) -> bool:
    """Sends a short summary, not the full board - WhatsApp is the nudge,
    the dashboard is the detail.

    Two providers are supported. CallMeBot is free and takes two minutes to
    set up but is a personal-use service. Meta's WhatsApp Cloud API is the
    supported route if you would rather not depend on it.
    """
    text = _plain(body)
    if len(text) > 900:
        text = text[:880].rsplit("\n", 1)[0] + "\n…full board in the link above."

    phone = os.getenv("WHATSAPP_PHONE")

    # Meta WhatsApp Cloud API
    meta_token = os.getenv("WHATSAPP_TOKEN")
    meta_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if meta_token and meta_id and phone:
        try:
            r = requests.post(
                f"https://graph.facebook.com/v20.0/{meta_id}/messages",
                headers={"Authorization": f"Bearer {meta_token}"},
                json={"messaging_product": "whatsapp", "to": phone,
                      "type": "text", "text": {"body": text}},
                timeout=30)
            if r.status_code < 300:
                return True
            log.error("whatsapp (meta): %s %s", r.status_code, r.text[:200])
        except requests.RequestException as e:
            log.error("whatsapp (meta): %s", e)
        return False

    # CallMeBot
    key = os.getenv("CALLMEBOT_APIKEY")
    if key and phone:
        try:
            r = requests.get("https://api.callmebot.com/whatsapp.php",
                             params={"phone": phone, "text": text,
                                     "apikey": key},
                             timeout=40)
            if r.status_code == 200:
                return True
            log.error("whatsapp (callmebot): %s %s", r.status_code,
                      r.text[:200])
        except requests.RequestException as e:
            log.error("whatsapp (callmebot): %s", e)
    return False


def send_all(subject: str, body: str, quiet: bool) -> dict[str, bool]:
    if quiet:
        log.info("dry run - nothing sent")
        return {}
    return {"telegram": telegram(subject, body),
            "email": email(subject, body),
            "whatsapp": whatsapp(subject, body)}
