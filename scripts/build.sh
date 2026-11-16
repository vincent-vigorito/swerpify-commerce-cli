#!/usr/bin/env bash
# Compila CLI e server MCP in generated/swerpicommerce-cli/bin con la versione della
# prima voce del CHANGELOG. Il generatore lascia "1.0.0": nel CLI e' una variabile
# (si passa con -ldflags -X), nel server MCP e' un letterale dentro server.NewMCPServer,
# sostituito in una copia passata a go build con -overlay (il sorgente generato non cambia).
set -euo pipefail

radice="$(cd "$(dirname "$0")/.." && pwd)"
cli="$radice/generated/swerpicommerce-cli"
versione="$(sed -n 's/^## \[\([0-9][0-9.]*\)\].*/\1/p' "$radice/CHANGELOG.md" | head -1)"
[ -n "$versione" ] || { echo "build: nessuna voce di versione in CHANGELOG.md" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
main_mcp="$cli/cmd/swerpicommerce-pp-mcp/main.go"
sed "/server\.NewMCPServer(/,/)/ s/\"[0-9][0-9.]*\"/\"$versione\"/" "$main_mcp" > "$tmp/main.go"
grep -q "\"$versione\"" "$tmp/main.go" || {
  echo "build: versione MCP non trovata in server.NewMCPServer di $main_mcp (generatore cambiato?)" >&2
  exit 1
}
printf '{"Replace":{"%s":"%s"}}\n' "$main_mcp" "$tmp/main.go" > "$tmp/overlay.json"

cd "$cli"
go build -trimpath -ldflags "-X swerpicommerce-pp-cli/internal/cli.version=$versione" \
  -o bin/swerpicommerce-pp-cli ./cmd/swerpicommerce-pp-cli
go build -trimpath -overlay "$tmp/overlay.json" \
  -o bin/swerpicommerce-pp-mcp ./cmd/swerpicommerce-pp-mcp
chmod +x bin/swerpicommerce-pp-cli bin/swerpicommerce-pp-mcp

# Controllo: entrambi i binari devono riportare la versione del CHANGELOG.
v_cli="$(bin/swerpicommerce-pp-cli version | awk '{print $2}')"
v_mcp="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"build","version":"0"}}}' \
  | timeout 10 bin/swerpicommerce-pp-mcp --transport stdio 2>/dev/null \
  | sed -n 's/.*"serverInfo":{[^}]*"version":"\([^"]*\)".*/\1/p' | head -1)"
echo "CHANGELOG $versione | swerpicommerce-pp-cli $v_cli | swerpicommerce-pp-mcp ${v_mcp:-?}"
[ "$v_cli" = "$versione" ] && [ "$v_mcp" = "$versione" ] || { echo "build: versione dei binari diversa dal CHANGELOG" >&2; exit 1; }
