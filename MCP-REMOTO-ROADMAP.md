# SwerpiCommerce MCP Remoto — Roadmap

> Documento di progetto per il team piattaforma. Obiettivo: portare SwerpiCommerce
> da "piattaforma con API" a "piattaforma agent-native" esponendo un server MCP
> remoto multi-tenant, con tool curati per mestiere.
>
> Stato: **proposta** · Ultimo aggiornamento: 07/07/2026 · Autori: Vincenzo Vigorito + Claude (Anja)

---

## 0. La scala che stiamo salendo

| Gradino | Cosa | Stato |
|---|---|---|
| 1 | **API v2** (77 path / 135 operazioni, OpenAPI live su `/openapi.json`) | ✅ in produzione |
| 2 | **CLI generato** (Printing Press, per umani in terminale e agenti con shell) | ✅ in produzione |
| 3 | **MCP locale** (bundle `.mcpb`, stesso binario in modalità stdio — Claude Desktop) | ✅ esiste |
| 4 | **MCP remoto v1** — endpoint HTTP sul server, tool generati 1:1 | 🎯 questa roadmap |
| 5 | **MCP remoto v2** — tool curati per mestiere | 🎯 questa roadmap |
| 6 | **Confezioni** — connector claude.ai, plugin Claude Code, GPT actions | 🎯 questa roadmap |

Il principio guida, in una frase: **le API espongono la piattaforma, l'MCP remoto
espone i mestieri.**

---

## 1. Perché remoto (e perché adesso)

- **Il locale non scala sui clienti finali**: nessun titolare di negozio installerà
  un binario. Il remoto è un URL + login OAuth: onboarding in un minuto, da
  claude.ai web/mobile, Claude Desktop e qualunque host che supporti i connector.
- **Aggiornamenti centralizzati**: si deploya il server, tutti i client hanno la
  versione nuova. Col locale ogni fix è una distribuzione.
- **Credenziali che non lasciano la piattaforma**: OAuth con i permessi del
  pannello, revoca centrale, audit completo.
- **Feature vendibile**: "collega il tuo negozio alla tua AI" è un argomento
  commerciale della piattaforma (e del posizionamento Swebby: l'agenzia con
  l'agente AI in organico vende il CMS che parla con gli agenti).

---

## 2. Architettura target

```
Client MCP (claude.ai, Desktop, Code, altri host)
        │  Streamable HTTP + OAuth 2.1
        ▼
https://<tenant>.swebbysites.com/mcp        ← per-tenant, come le API
        │
        ├── Layer AUTH: OAuth 2.1 (authorization code + PKCE), token legati
        │   a utente pannello o chiave API; scope = gruppi di tool
        ├── Layer TOOL: orchestrazione per-mestiere → chiama i SERVIZI INTERNI
        │   (stesso codice delle view API — NON self-call HTTP)
        ├── Layer POLICY: rate limit per token, idempotenza, conferme scritture
        └── Layer AUDIT: ogni chiamata loggata per tenant (visibile nel pannello)
```

Scelte vincolanti:

1. **Trasporto**: Streamable HTTP (lo standard MCP corrente per i remote server).
2. **Multi-tenancy**: l'endpoint vive sul dominio del tenant (o `mcp.` dedicato con
   tenant risolto dal token) — stessa filosofia delle API.
3. **Niente self-call HTTP**: i tool orchestrano i servizi interni direttamente.
   Un tool = una transazione applicativa, non una sequenza di richieste a sé stessi.
4. **Scope OAuth leggibili**: la schermata di consenso deve dire cose che un
   titolare capisce ("pubblicare contenuti", "leggere ordini"), mappate sui
   permessi chiave già esistenti nel pannello.

---

## 3. Fase v1 — Infrastruttura (tool generati 1:1)

**Obiettivo**: validare trasporto, OAuth, tenancy, audit — NON l'esperienza d'uso.

- [ ] Endpoint `/mcp` con handshake MCP + Streamable HTTP
- [ ] OAuth 2.1 completo (registrazione client, authorization code + PKCE, refresh,
      revoca dal pannello)
- [ ] Generazione tool 1:1 dallo schema OpenAPI (la mappatura esiste già nel
      generatore Printing Press — riuso, non riscrittura)
- [ ] Filtro tool per scope della chiave (una chiave read-only espone solo letture)
- [ ] Rate limiting per token + logging strutturato per tenant
- [ ] Collaudo end-to-end da claude.ai e Claude Desktop su tenant di test

**Criterio di uscita**: un agente esterno autentica via OAuth e completa letture e
scritture semplici su un tenant di prova. La v1 può restare dietro feature-flag:
è un'impalcatura, non il prodotto.

**Anti-goal dichiarato**: NON pubblicizzare la v1 ai clienti. 135 tool in contesto
degradano la scelta del modello e bruciano 20-40k token a conversazione.

---

## 4. Fase v2 — I mestieri (il prodotto)

### 4.1 Catalogo tool — v2.0 «Contenuti & Ordini»

| Tool | Firma (essenziale) | Assorbe (API + quirk) | Scope |
|---|---|---|---|
| `pubblica_articolo` | titolo, contenuto, categoria, immagine_url?, autore?, data?, seo? | POST /media (campo nudo) + risoluzione categoria per NOME + POST /articles (B45: principale solo in FK; url_diretto; slug) + compile + flush → **ritorna URL pubblico** | content:write |
| `aggiorna_articolo` | slug, campi | PUT /articles + compile/flush | content:write |
| `crea_pagina` | titolo, contenuto, padre?, seo? | POST /pages (pagina_padre_id, MAI slug con "/" — B31) + content + compile → nasce **noindex** | content:write |
| `pubblica_pagina` | slug | flip index/sitemap/llms + flush | content:write |
| `traduci_e_collega` | slug, lingua, contenuto, seo? | POST pagina lang + PUT alternates (mesh) + compile → hreflang automatici | content:write |
| `cerca_contenuti` | query, tipo? | GET articles/pages con filtri | content:read |
| `stato_ordini` | periodo, stato? | GET /orders + aggregazione (conteggi, totale) | orders:read |
| `dettaglio_ordine` | numero | GET /orders/{id} (+ cliente dal dettaglio) | orders:read |
| `aggiorna_stato_ordine` | numero, stato, nota? | PUT /orders (stato = stringa libera: valida contro gli stati del tenant) | orders:write |

### 4.2 Catalogo tool — v2.1 «Marketing»

| Tool | Firma | Assorbe | Scope |
|---|---|---|---|
| `crea_codice_sconto` | tipo, valore, scadenza?, limiti? | POST /discount-codes (booleani **0/1**, date **YYYY-MM-DD**) | marketing:write |
| `recupera_carrelli_abbandonati` | finestra_ore, sconto? | l'intero workflow della skill: carts?abbandonato → codice monouso per cliente → email transazionale. Un tool = una pagina di documentazione in meno | marketing:write |
| `invia_campagna` | lista, oggetto, contenuto_html | template → lista → campagna → send (il template viene COPIATO: modifica sulla campagna) | marketing:write |
| `iscrivi_contatto` | email, lista, consensi | subscribers add (idempotente) | marketing:write |
| `statistiche_campagna` | campagna | stats (inviate/errori/coda — niente aperture: dirlo nella description) | marketing:read |

### 4.3 Catalogo tool — v2.2 «Catalogo + coda lunga»

| Tool | Firma | Assorbe | Scope |
|---|---|---|---|
| `cerca_prodotti` | query, filtri? | GET /products (varianti: include e filtra client-side il padre) | catalog:read |
| `scheda_prodotto` | sku \| nome | dettaglio + varianti + immagini | catalog:read |
| `crea_prodotto` | dati | POST /products → nasce in **bozza** | catalog:write |
| `aggiorna_prodotto` | sku, campi | PUT con **validazione campi** (l'API ignora i campi sconosciuti in silenzio: il tool valida prima) | catalog:write |
| `gestisci_stock` | sku, quantità \| delta | PUT mirato | catalog:write |
| `carica_media` | url \| base64, alt | POST /media (10MB, formati; **niente SVG**) | content:write |
| `cerca_operazioni` | domanda in linguaggio naturale | indice semantico delle 135 operazioni → torna le pertinenti CON schema | * :read |
| `esegui_operazione` | nome, parametri, conferma? | proxy 1:1; **le scritture richiedono `conferma: true`** | * per scope |

### 4.4 Regole di design (vincolanti per ogni tool)

1. **Input nella lingua del dominio**: nomi, non id. La risoluzione nome→id è
   compito del server. Ogni id richiesto all'agente = un lookup in più + un errore
   possibile.
2. **Default sicuri**: le creazioni nascono in bozza/noindex; pubblicare è un verbo
   esplicito. **Niente delete** in v2 (pannello o coda lunga con conferma).
3. **Errori = indicazioni stradali**: ogni errore suggerisce la mossa successiva
   ("slug già esistente in it → usa aggiorna_articolo"). Mai un codice nudo.
4. **Idempotenza**: chiave di idempotenza o semantica get-or-create su ogni
   scrittura (lezione B32: retry su 500 non deve creare doppioni).
5. **Description = micro-skill**: le regole d'uso vivono NEI tool ("HTML semantico
   puro, il tema fornisce gli stili; niente class/style inline"). La skill
   `swerpicommerce-ops` si scioglie progressivamente dentro le description.
6. **Output progettati per il modello**: brevi, con URL finale e stato; warning
   strutturati; niente dump di envelope.
7. **Nomi in italiano**: il dominio API è italiano, i clienti sono PMI italiane.
8. **Test di accettazione universale**: *un agente SENZA la skill completa il
   mestiere al primo colpo?* Se deve sapere di compile/envelope/B45, il tool non
   è finito.

### 4.5 Chicche di prodotto

- **Audit "azioni dell'AI" nel pannello**: timeline per tenant di ogni chiamata
  MCP (chi, cosa, quando, esito). Fiducia vendibile + debugging + marketing.
- **MCP Resources**: esporre come risorse read-only la guida SWCSS, l'elenco
  categorie/lingue del tenant, la palette — contesto senza consumare tool call.
- **MCP Prompts**: prompt preconfezionati per-tenant ("scrivi un articolo nello
  stile del blog di questo sito e pubblicalo in bozza").

---

## 5. Fase v3 — Coltivazione (data-driven)

- **La telemetria della coda lunga è il backlog**: ogni pattern ricorrente su
  `esegui_operazione` è un candidato tool curato. Rivedere mensilmente.
- KPI da tracciare per tool: tasso di successo al primo colpo, retry, errori per
  tipo, token medi per completamento mestiere, tempo end-to-end.
- Espansioni candidate (in ordine di domanda attesa): resi/rimborsi, gestione
  recensioni, insight vendite aggregati, operazioni design (applica_css +
  compile per le agenzie), gestione form/submission.
- **Versioning**: i tool sono un contratto. Cambi additivi liberi; breaking
  changes = tool nuovo con nome nuovo + deprecazione annunciata di quello vecchio.

---

## 6. Confezioni (dopo v2.0)

| Canale | Cosa | Effort |
|---|---|---|
| **Connector claude.ai** | l'URL MCP + OAuth: documentazione e listing | basso |
| **Plugin Claude Code** | skill swerpicommerce-ops + config MCP + comandi in un pacchetto | basso |
| **GPT actions** | generate dallo schema OpenAPI già pubblico | basso |
| **Docs "AI" sul sito** | pagina per sviluppatori e clienti: come collegare il proprio agente | medio |

---

## 7. Sicurezza — requisiti non negoziabili

- OAuth 2.1 con PKCE; token brevi + refresh; revoca immediata dal pannello.
- Scope granulari (`content:read/write`, `orders:read/write`, `marketing:*`,
  `catalog:*`) mappati sui permessi chiave esistenti.
- Rate limit per token e per tenant; circuit breaker sulle scritture massive.
- Audit log immutabile per tenant (base della timeline nel pannello).
- Idempotency key obbligatoria sulle scritture "costose" (ordini, campagne).
- Nessun tool di cancellazione dura in v2; `esegui_operazione` in scrittura solo
  con `conferma: true` e scope elevato.
- Prompt-injection awareness: i contenuti restituiti dai tool (es. descrizioni
  prodotto, messaggi cliente) sono DATI: mai interpolarli nelle description dei
  tool o in messaggi di sistema.

---

## 8. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Esplosione del numero di tool nel tempo | budget fisso (~25 in contesto); la coda lunga assorbe il resto |
| Scritture accidentali da parte degli agenti | default bozza/noindex + conferme + audit + niente delete |
| Drift tra tool curati e API sottostanti | i tool chiamano i servizi interni (stesso codice delle view); test di contratto in CI |
| Costo di manutenzione doppio binario (locale+remoto) | il locale resta generato 1:1 (zero manutenzione manuale); solo il remoto è curato |
| Host MCP con capacità diverse | testare su claude.ai, Desktop, Code come matrice minima di compatibilità |

---

## 9. Sequenza consigliata (effort t-shirt, senza date)

1. **v1 infra** — M (trasporto+OAuth+generazione: il grosso è riuso del generatore)
2. **v2.0 Contenuti+Ordini** — M (9 tool, quelli con i workflow già documentati nella skill)
3. **Audit nel pannello** — S (ma da progettare insieme alla v1: i log nascono giusti)
4. **v2.1 Marketing** — S/M
5. **Confezioni** (connector + plugin) — S
6. **v2.2 Catalogo + coda lunga** — M (l'indice semantico delle operazioni è il pezzo nuovo)
7. **v3 coltivazione** — continuo

**Primo collaudo pubblico suggerito**: far ripubblicare a un agente "vergine"
(senza skill) un articolo del blog swebby.it via MCP remoto. Se ottiene l'URL
pubblico al primo colpo, la v2.0 è pronta. Il tester si offre volontario. 🤖

---

## Appendice A — Il sapere da assorbire nei tool (cicatrici sul campo)

Quirk documentati in `SWERPICOMMERCE-ISSUES.md` e nella skill che i tool curati
devono rendere invisibili:

- `design compile` obbligatorio dopo ogni modifica design/contenuti (regola d'oro)
- Envelope: letture `{results:{data}}` vs scritture `{data:{data}}` — API raw `{data:[...]}`
- Categorie articolo: la principale va SOLO in `categoria_id`, mai anche nell'M2M (B45)
- `immagine_evidenza` vuole `valore_campo` NUDO (il template antepone /uploads/)
- Slug con `/` → 500 frontend: gerarchie SOLO via `pagina_padre_id` (B31)
- POST /pages può 500-are avendo creato (B32) → idempotenza obbligatoria
- Booleani discount-codes = interi 0/1; date solo YYYY-MM-DD
- PUT prodotti/pagine ignora campi sconosciuti in silenzio → validare prima
- `<select>` dei form inviano il TESTO dell'opzione, non il value
- Media: max 10MB, jpg/png/webp/gif/avif, NIENTE SVG (B36)
- Multilingua: record per-lingua + `alternates` (mesh bidirezionale) — hreflang default vuoto (B44, in fix)
