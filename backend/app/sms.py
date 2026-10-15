"""Sends sign-in codes. 'console' logs the code (development). For production, add a class for
your SMS gateway (MSG91, Twilio, Gupshup...) with the same send() method; Indian SMS also needs
a DLT-registered sender ID and message template."""
from __future__ import annotations

import logging

log = logging.getLogger("studio.sms")


class ConsoleSms:
    def send(self, phone: str, text: str) -> None:
        log.warning("SMS to %s: %s", phone, text)


def get_sms(provider: str):
    if provider == "console":
        return ConsoleSms()
    raise RuntimeError(f"SMS_PROVIDER {provider!r} is not implemented yet; see app/sms.py")
