"""Generate safe, successful Meta Marketing API reads for access-tier qualification."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


TOKEN = os.environ.get("META_ACCESS_TOKEN", "").strip()
TARGET = int(os.environ.get("META_QUALIFICATION_CALLS", "500"))
USAGE_CEILING = int(os.environ.get("META_USAGE_CEILING", "80"))
COOLDOWN_SECONDS = int(os.environ.get("META_COOLDOWN_SECONDS", "420"))
GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v26.0")


def request_once() -> int:
    query = urllib.parse.urlencode({
        "fields": "id,name,account_status",
        "limit": "1",
        "access_token": TOKEN,
    })
    request = urllib.request.Request(
        f"https://graph.facebook.com/{GRAPH_VERSION}/me/adaccounts?{query}",
        headers={"User-Agent": "Ads-Wise access qualification"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status}")
        body = json.load(response)
        if not body.get("data"):
            raise RuntimeError("Meta returned no accessible ad account")
        raw_usage = response.headers.get("x-business-use-case-usage", "{}")
        usage = json.loads(raw_usage)
        rows = next(iter(usage.values()), [])
        return max((int(row.get("call_count", 0)) for row in rows), default=0)


def main() -> int:
    if not TOKEN:
        print("META_ACCESS_TOKEN is required", file=sys.stderr)
        return 2
    successful = 0
    while successful < TARGET:
        try:
            usage = request_once()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                ValueError, RuntimeError) as exc:
            print(f"stopped after {successful} successful calls: {type(exc).__name__}", file=sys.stderr)
            return 1
        successful += 1
        if successful == 1 or successful % 25 == 0 or successful == TARGET:
            print(f"successful={successful}/{TARGET} usage={usage}%", flush=True)
        if usage >= USAGE_CEILING and successful < TARGET:
            print(f"usage ceiling reached; cooling down for {COOLDOWN_SECONDS} seconds", flush=True)
            time.sleep(COOLDOWN_SECONDS)
        else:
            time.sleep(0.8)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
