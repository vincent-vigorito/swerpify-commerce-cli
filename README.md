# swerpify-commerce-cli

CLI, server MCP e skill per agenti che lavorano su **SwerpiCommerce**, la piattaforma
e-commerce di Swerpify (API v2). Generato da uno schema OpenAPI neutro con
[CLI Printing Press](https://github.com/mvanhorn/cli-printing-press) → binario CLI Go +
bundle MCP + skill operativa.

> Repo gemello: il CLI **Swerpify ERP** (gestionale) è in
> [vincent-vigorito/swerpify-cli](https://github.com/vincent-vigorito/swerpify-cli).

## Cosa contiene

| Cartella / file | Cosa è |
|---|---|
| [`generated/swerpicommerce-cli/`](generated/swerpicommerce-cli/) | CLI Go generato (127 operazioni) + server MCP + `SKILL.md`/`AGENTS.md` (riferimento comandi) + `Makefile` |
| [`sites/`](sites/) | Gestione **multi-sito**: wrapper `swc` + una sottocartella per sito con `credentials.env` (vedi sotto) |
| [`skills/swerpicommerce-ops/`](skills/swerpicommerce-ops/) | Skill operativa per agenti (workflow, quirk dell'API, design system SWCSS) |
| `swerpicommerce-v2-openapi-neutral.json` | Schema OpenAPI v2 neutralizzato (server = placeholder `YOUR-TENANT`) |

Cronologia versioni in [`CHANGELOG.md`](CHANGELOG.md).

---

## Installazione (da GitHub)

### Prerequisiti
- **Go ≥ 1.26** per compilare la CLI (il toolchain esatto si scarica da solo grazie al
  pin `toolchain` nel `go.mod`).
- **Accesso al repo** (è privato): chiave SSH abilitata sul repo, oppure *Download ZIP*
  dalla pagina GitHub.
- *(opzionale, solo per il bundle MCP o per rigenerare)* la
  [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press) in `~/go/bin`.
- *(opzionale, per la skill)* [Claude Code](https://claude.com/claude-code).

### 1. Clona il repo
```bash
git clone git@github.com:vincent-vigorito/swerpify-commerce-cli.git
cd swerpify-commerce-cli
```
> Repo privato → serve accesso SSH. In alternativa: pagina GitHub → **Code → Download ZIP**.

### 2. Compila e installa la CLI
```bash
cd generated/swerpicommerce-cli

make install          # compila e installa `swerpicommerce-pp-cli` in $(go env GOPATH)/bin
#   — in alternativa, solo build locale:
make build            # produce ./bin/swerpicommerce-pp-cli
```
Assicurati che `$(go env GOPATH)/bin` sia nel `PATH` (dopo `make install`). Se la build
locale non risulta eseguibile: `chmod +x bin/swerpicommerce-pp-cli`.

### 3. Configura e autenticati
```bash
export SWERPICOMMERCE_BASE_URL="https://<il-tuo-tenant>/api/v2"

swerpicommerce-pp-cli swerpicommerce-auth token --api-id <ID> --api-secret <SECRET> --agent
swerpicommerce-pp-cli auth set-token <TOKEN>
swerpicommerce-pp-cli doctor          # verde = pronto
```
Base URL del tenant via env `SWERPICOMMERCE_BASE_URL`, `base_url` nel `config.toml`,
oppure `--config <file>`. Con l'auth "manuale" il token NON si rinnova da solo alla
scadenza → per gestire più siti con refresh automatico usa il wrapper `swc` (sotto).

### 3b. Gestione multi-sito con `swc` (consigliato per più tenant)
Invece di file sparsi in `~/.config`, ogni sito è una sottocartella di [`sites/`](sites/)
con un solo `credentials.env`. Il wrapper [`sites/swc`](sites/swc) rileva il sito, rigenera
e cachea da solo il token Bearer (auto-refresh su scadenza) e invoca il CLI — senza toccare
il binario generato.
```bash
cd sites
mkdir gevi
cp _template/credentials.env.example gevi/credentials.env   # incolla api_id, api_secret, base_url
cd gevi
../swc pages list --agent            # opera su gevi; il sito è la cartella corrente
../swc --which                       # sito/base_url attivi
```
Le cartelle-sito con le credenziali sono escluse dal versionamento da un `.gitignore` a
whitelist. Dettagli in [`sites/README.md`](sites/README.md).

### 4. Server MCP (Claude Desktop) — opzionale
```bash
make build-mcp                        # binario server MCP in ./bin/
printing-press bundle .               # crea il bundle .mcpb (richiede ~/go/bin/printing-press)
```
Apri il file `.mcpb` con Claude Desktop: all'installazione chiede **base URL** del tenant
e **Bearer token**. *(Quando pubblicati, il `.mcpb` sarà scaricabile dalle
[Releases](../../releases) senza clonare nulla.)*

### 5. Skill per agenti (Claude Code) — opzionale
```bash
cp -r skills/swerpicommerce-ops ~/.claude/skills/
```
Guida operativa completa (workflow pagine/CSS/JS, regola d'oro `design compile`, quirk
dell'API, design system SWCSS). Il riferimento comandi è in
`generated/swerpicommerce-cli/SKILL.md`.

---

## Aggiornare / rigenerare (quando l'API evolve)
```bash
# 1. scarica lo schema live e neutralizzalo (server URL → placeholder YOUR-TENANT)
# 2. rigenera:
~/go/bin/printing-press generate --spec <schema-neutro> \
  --output generated/swerpicommerce-cli --force --validate=false
# 3. due passi manuali dopo OGNI regen:
#    a. ri-pin del toolchain nel go.mod  (go 1.26.x → + "toolchain go1.26.4")
#    b. ri-patch di manifest.json: aggiungere swerpicommerce_base_url al user_config,
#       mappata su env SWERPICOMMERCE_BASE_URL (il generatore non la emette)
# 4. make build (+ chmod +x se serve) · 5. printing-press bundle .
```

## Note operative
- Le route a **2 path-param** (es. `/design/css/{sezione}/{file}`) hanno un URL errato nel
  CLI generato (bug noto della Printing Press) → workaround con `curl` + Bearer token.
- Alcuni comandi-risorsa risultano `Hidden: true` (invisibili in `--help` ma funzionanti).

## Licenza
Apache-2.0 (vedi `generated/swerpicommerce-cli/LICENSE`).
