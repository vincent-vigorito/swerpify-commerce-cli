# swerpify-commerce-cli

CLI, server MCP e skill per agenti che lavorano su **SwerpiCommerce**, la piattaforma
e-commerce di Swerpify (API v2). Generato da uno schema OpenAPI neutro con
[CLI Printing Press](https://github.com/mvanhorn/cli-printing-press) → binario CLI Go +
bundle MCP + skill operativa.

> Repo gemello: il CLI **Swerpify ERP** (gestionale) è in
> [vincent-vigorito/swerpify-cli](https://github.com/vincent-vigorito/swerpify-cli).

## Struttura

| Cartella / file | Cosa è |
|---|---|
| [`generated/swerpicommerce-cli/`](generated/swerpicommerce-cli/) | CLI Go generato (99 operazioni) + `SKILL.md` (riferimento comandi) + sorgenti bundle MCP |
| [`skills/swerpicommerce-ops/`](skills/swerpicommerce-ops/) | Skill operativa per agenti (workflow, quirk dell'API, design system SWCSS) |
| `swerpicommerce-v2-openapi-neutral.json` | Schema OpenAPI v2 neutralizzato (server = placeholder `YOUR-TENANT`) |

## Quick start

```bash
cd generated/swerpicommerce-cli
make install                       # richiede Go (il toolchain giusto si scarica da solo)

export SWERPICOMMERCE_BASE_URL="https://<il-tuo-tenant>/api/v2"
swerpicommerce-pp-cli swerpicommerce-auth token --api-id <ID> --api-secret <SECRET> --agent
swerpicommerce-pp-cli auth set-token <TOKEN>
swerpicommerce-pp-cli doctor       # verde = pronto
```

Base URL del tenant via env `SWERPICOMMERCE_BASE_URL`, `base_url` nel `config.toml`
oppure `--config <file>` (multi-tenant).

## Server MCP e skill

- **Server MCP** (Claude Desktop): bundle `.mcpb` generato da `printing-press bundle`;
  all'installazione chiede base URL del tenant e Bearer token.
- **Skill per agenti** (Claude Code):
  `cp -r skills/swerpicommerce-ops ~/.claude/skills/` — guida operativa completa
  (workflow pagine/CSS/JS, regola d'oro `design compile`, quirk dell'API). Il riferimento
  comandi è in `generated/swerpicommerce-cli/SKILL.md`.

## Note operative

- Le route a 2 path-param (es. `/design/css/{sezione}/{file}`) hanno un URL errato nel CLI
  generato (bug noto della Printing Press) → workaround con `curl` + Bearer token.
- Dopo ogni `--force` di rigenerazione vanno rifatti i 2 passi manuali: pin `toolchain` nel
  `go.mod` e patch di `manifest.json` (base URL nel `user_config`).

## Licenza

Apache-2.0 (vedi `generated/swerpicommerce-cli/LICENSE`).
