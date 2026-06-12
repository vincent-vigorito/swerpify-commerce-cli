# CLI e API raw — primer d'uso per agenti

## Il CLI: flag globali che contano

| Flag | Uso |
|---|---|
| `--agent` | imposta tutti i default agent-friendly: JSON, compact, no-input, no-color, yes. **Mettilo sempre** |
| `--stdin` | body JSON da stdin per create/update (`echo '{...}' \| cli <risorsa> create --stdin --agent`) |
| `--no-cache` | bypassa la cache di risposta: usalo nelle **riletture di verifica** dopo una scrittura |
| `--dry-run` | mostra la richiesta senza inviarla: utile per verificare il body prima di una scrittura delicata |
| `--config <file>` | config alternativo = altro tenant |
| `--compact` | solo campi chiave (id, nome, stato, timestamp): risparmio token sulle liste lunghe |
| `--csv` | output CSV per tabelle e array |
| `--data-source` | `auto` (default, live con fallback locale) · `live` · `local` (solo dati sincronizzati) |
| `--idempotent` | un create su entità già esistente diventa no-op riuscito |
| `--ignore-missing` | un delete su entità mancante diventa no-op riuscito |

## Comandi di servizio utili

```bash
swerpicommerce-pp-cli api                  # elenco VERO delle risorse (l'--help ne nasconde molte)
swerpicommerce-pp-cli api <risorsa>        # metodi di una risorsa
swerpicommerce-pp-cli which "<capacità>"   # trova il comando che fa una cosa
swerpicommerce-pp-cli doctor               # auth, base URL, connettività
swerpicommerce-pp-cli agent-context        # descrizione JSON del CLI per agenti
swerpicommerce-pp-cli sync                 # idrata il DB SQLite locale
swerpicommerce-pp-cli search "<testo>"     # full-text sui dati sincronizzati
swerpicommerce-pp-cli export / import      # backup/migrazione in JSONL
```

`sync` + `search`/`--data-source local` = interrogazioni ripetute senza
martellare l'API (e funzionano offline).

## Pattern CLI ricorrenti

```bash
# creare con body JSON complesso (heredoc evita problemi di quoting)
cat > /tmp/body.json << 'EOF'
{"nome": "...", "prezzi": [{"listino_id": 1, "prezzo_listino": 19.90}]}
EOF
swerpicommerce-pp-cli products create --stdin --agent < /tmp/body.json | jq '(.data.data // .data)'

# file grandi (HTML/CSS/base64) dentro un body JSON: jq --rawfile
jq -n --rawfile content /tmp/pagina.html '{content: $content}' \
  | swerpicommerce-pp-cli pages content page-update <id> --stdin --agent

# rilettura di verifica dopo OGNI scrittura
swerpicommerce-pp-cli products get <id> --agent --no-cache | jq '(.results.data // .results)'
```

## API raw (curl) — quando e come

Quando: route con **due path-param** (bug del CLI: `/design/css/{section}/{filename}`,
`/media/{folder}/{filename}`), debugging, o integrazioni server-to-server.

```bash
TOKEN=$(curl -sk -X POST "$BASE/auth/token" -H "Content-Type: application/json" \
  -d '{"api_id":"<ID>","api_secret":"<SECRET>"}' | jq -r '.data.token')

curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/products?limit=50&offset=0"
# scrittura:
jq -n --rawfile css /tmp/file.css '{content: $css}' \
  | curl -sk -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d @- "$BASE/design/css/cms/<slug>.css"
```

## Forme di risposta dell'API (raw)

- Liste: `{"data": [...], "meta": {"total", "limit", "offset"}}` — paginazione
  con `?limit=&offset=`.
- Dettaglio/scritture: `{"data": {...}}`.
- Errori: `{"error": {"code", "message", "details": [...]}}` — i `details`
  indicano il campo esatto (es. validazione). Codici visti: `UNAUTHORIZED`,
  `VALIDATION_ERROR`, `INVALID_INPUT`, `NOT_FOUND`, `CODE_IN_USE`,
  `SYSTEM_PAGE`, `SEND_FAILED`, `CAMPAIGN_SENDING`, `IMAGE_NOT_FOUND`,
  `MEDIA_NOT_FOUND`.
- ⚠️ Il CLI INCAPSULA queste risposte nel proprio envelope: letture in
  `.results.*`, scritture in `.data.*` → da CLI i path jq diventano
  `.results.data` e `.data.data`.

## Filtri di lista documentati (da verificare sullo schema live del tenant)

- `products`: `sku`, `tipo_prodotto`, `stato`, `categoria_id`, `lang`,
  `include_variants`, `include_prices`
- `articles`: `lang`, `slug`, `stato`, `categoria_id`, `in_evidenza`
- `customers`: `email`
- `carts`: `abbandonato`, `recuperato`, `email`, `older_than`
- `media`: `folder` (`product_images`, `cat_images`, `blog`, `blog_cat_images`)
- `orders`: nessun filtro (solo paginazione)

## Evoluzione dell'API

Lo schema live (`GET <base>/openapi.json`, pubblico) è la fonte di verità.
Se compare una risorsa nuova: rigenerare il CLI con la CLI Printing Press
(`printing-press generate --spec <schema> --force`) — il regen preserva i
comandi scritti a mano e ricompila anche il bundle MCP.
