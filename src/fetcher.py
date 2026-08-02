"""HTTP fetching, built for government sites that are slow, rate-limited or
carrying an expired certificate."""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urlparse

import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("fetch")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

TIMEOUT = 45
RETRIES = 3

# Government sites routinely answer a missing page with 302 -> /Error/Error
# and 200 OK, so the status code alone says nothing. PESB withdrew its
# Upcoming Vacancies page exactly this way: --check-urls called it reachable
# while the parser found no table. Landing somewhere error-shaped that we did
# not ask for is the tell.
ERROR_LANDING = re.compile(r"/(error|notfound|404|pagenotfound)\b", re.I)


def _redirected_to_error(requested: str, final: str) -> bool:
    if final == requested:
        return False
    return bool(ERROR_LANDING.search(urlparse(final).path)) and \
        not ERROR_LANDING.search(urlparse(requested).path)


def get(url: str) -> tuple[bool, str, str]:
    """Return (ok, html, note). Never raises."""
    last = ""
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            if r.status_code == 200 and _redirected_to_error(url, r.url):
                # No point retrying: the page is gone, not flaky.
                note = f"page withdrawn - redirects to {r.url}"
                log.warning("fetch failed %s -> %s", url, note)
                return False, "", note
            if r.status_code == 200:
                return True, r.text, ""
            last = f"HTTP {r.status_code}"
        except requests.exceptions.SSLError as e:
            last = f"SSL error: {type(e).__name__}"
        except requests.exceptions.Timeout:
            last = f"timed out after {TIMEOUT}s"
        except requests.exceptions.RequestException as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < RETRIES:
            time.sleep(3 * attempt)
    log.warning("fetch failed %s -> %s", url, last)
    return False, "", last
