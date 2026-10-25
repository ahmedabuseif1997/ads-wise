#!/bin/sh
set -eu

endpoint="https://ads-wise.com/mcp/developer"
service="ads-wise-mcp-token"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
config_file="${CODEX_HOME:-$HOME/.codex}/config.toml"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer currently supports macOS only." >&2
  exit 1
fi

printf "Ads-Wise MCP token: "
stty -echo
IFS= read -r token
stty echo
printf "\n"
[ -n "$token" ] || { echo "A token is required." >&2; exit 1; }

/usr/bin/security add-generic-password -U -a "${USER}" -s "$service" -w "$token" >/dev/null

codex mcp remove ads_wise >/dev/null 2>&1 || true
codex mcp add ads_wise --url "$endpoint" >/dev/null

python3 - "$config_file" "$script_dir/ads-wise-mcp-headers" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
helper = sys.argv[2]
text = path.read_text()
marker = "[mcp_servers.ads_wise]"
start = text.index(marker)
end = text.find("\n[", start + len(marker))
if end < 0:
    end = len(text)
block = text[start:end]
line = f'http_headers_helper = "{helper}"'
if "http_headers_helper =" in block:
    block = "\n".join(line if row.startswith("http_headers_helper =") else row for row in block.splitlines())
else:
    rows = block.splitlines()
    rows.insert(2, line)
    block = "\n".join(rows)
path.write_text(text[:start] + block + text[end:])
PY

if command -v claude >/dev/null 2>&1; then
  claude mcp remove ads_wise --scope user >/dev/null 2>&1 || true
  claude mcp add --scope user --transport http ads_wise "$endpoint" \
    --header "Authorization: Bearer $token" >/dev/null
fi

unset token
echo "Ads-Wise MCP connected to Codex and Claude. Restart each app once."
