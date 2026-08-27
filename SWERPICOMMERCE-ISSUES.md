# SwerpiCommerce v2 — Issue di piattaforma (registro aperto)

> Registro **ripartito pulito il 27/08/2026**: qui stanno solo le issue ancora aperte. La storia
> completa (B1–B77, sezioni A/C/D, report cronologici giugno–agosto, retest di massa del 20/08) è
> nel git del repo: `git show 1a43cdc:SWERPICOMMERCE-ISSUES.md`. La numerazione **continua**:
> prossimo id **B79**.
>
> Convenzioni: una riga per issue — titolo in grassetto, poi sintomo, evidenza (tenant, data,
> misure), impatto e richiesta; stato = 🔴 aperta · 🟡 aperta minore/residuo · ⚪ decisione da
> prendere. A ogni rilascio si ritestano le aperte: chi chiude sposta la riga nell'archivio in fondo
> (id → titolo → data), non la cancella. Entità di test `ZZTEST` con cleanup.

## Aperte (piattaforma)

| # | Problema | Stato |
|---|---|---|
| B76 | **Il tree-shake scarta le regole il cui INTERO selettore è una classe applicata solo da JS a runtime (dichiarata in commento HTML), mentre le regole discendenti con la stessa classe sopravvivono** — su swebify-new (135-h000776, 25/08, pagina `stack-lab`): classe `sw-stk--pin` aggiunta da JS e dichiarata nel commento del template (il meccanismo documentato per le classi runtime). Nel bundle compilato le regole **discendenti** `.sw-stk--pin .sw-stk__pin { … }`, `.sw-stk--pin .sw-stk__tower { … }` ecc. **ci sono tutte**, ma la regola **standalone** `.sw-stk--pin { height: 640vh; padding: 0 }` viene **scartata** — verificata assente dal bundle in due compile consecutivi (prima con `height: calc(100vh + 6 * 90vh)`, poi con `640vh` secco: stessa sorte, quindi non è il `calc`). Sintomo: la sezione pinnata non ha l'altezza di scroll e lo scrollytelling non parte, senza alcun errore. Il filtro sembra quindi valutare il selettore nel suo insieme (coerente con le osservazioni di B66): la dichiarazione in commento basta a salvare la classe come *token* nelle regole composte, non una regola il cui unico soggetto è la classe runtime. **Workaround:** selettore doppio con una classe presente nel markup statico — `.sw-stk.sw-stk--pin { … }` → regola presente nel bundle al primo compile. **Richiesta:** trattare le classi dichiarate nei commenti come usate anche per le regole a selettore singolo, o documentare il workaround del selettore doppio nella guida SWCSS. | 🔴 aperta |
| B75 | **Il design system dichiara `list-style-type: disc` sui `<li>` invece che su `<ul>/<ol>` → `list-style: none` sul contenitore è inefficace e ogni lista custom nasce col pallino doppio** — nel bundle `cms.css` c'è `:where(#main_content) li { list-style-type: disc }`: essendo dichiarato sull'elemento, vince sull'eredità da `ul { list-style: none }`, che è il modo canonico (e quello che ogni autore scrive per primo) di azzerare i marker. Risultato: le liste con icona custom in `::before` (check, step, chip) mostrano **pallino + icona**. Su swerpifywebsite (135-h000777, 23/08) il difetto era in **35 file CSS su 62** della sezione `cms` — non un errore isolato ma una trappola sistematica del design system, riemersa più volte nel tempo ("sempre lo stesso problema"). Workaround applicato per-pagina: `.sw-x-list > li { list-style: none; }`. **Richiesta:** spostare la regola sul contenitore (`:where(#main_content) ul, :where(#main_content) ol { list-style-type: disc }` / `decimal`) o limitarla alle liste senza classe (`:where(#main_content) ul:not([class]) > li`), così il pattern standard torna a funzionare. | 🔴 aperta |
| B74 | **Il canonical delle schede prodotto è self-referential su QUALSIASI segmento categoria: la stessa scheda risponde 200 su infiniti URL, ognuno dichiarato canonico** — su detergenzaprofessionale (122-h000744, 23/08) la route prodotto `/negozio/<categoria>/<slug>/` non valida il segmento categoria: la scheda risponde 200 sotto ogni categoria di appartenenza, sotto path a 4 livelli con la sottocategoria (`/negozio/sgrassatori/sgrassatori-base-solvente/<slug>/`) e **perfino sotto una categoria inesistente** (`/negozio/zzcategoria-fasulla/<slug>/` → 200). Il problema SEO è che il `<link rel="canonical">` **riecheggia l'URL richiesto** invece di puntare al path della categoria principale: ogni alias si autodichiara canonico, quindi per Google sono N pagine distinte con contenuto identico (duplicate content) e i segnali si spalmano invece di consolidarsi. Il caso d'uso che lo rende visibile è la migrazione da WordPress: i vecchi URL Woo con categoria diversa da quella principale del tenant "funzionano" (200) ma competono con l'URL in sitemap invece di passargli l'equity. **Richiesta:** (a) canonical fisso al path della categoria principale (`/negozio/<cat_main>/<slug>/`) qualunque sia l'URL richiesto — risolverebbe anche gli alias legittimi senza bisogno di redirect; in subordine (b) 301 automatico verso il path canonico quando il segmento non corrisponde alla categoria principale, e comunque (c) 404 sul segmento categoria inesistente. | 🔴 aperta |
| B58 | **Consenso iubenda (Consent Database): la registrazione server-side non avviene MAI, e fallisce in silenzio** — con la catena completa attiva, alla submission il consenso **non compare nella Consent Database** di iubenda. Setup verificato su String Project (122-h000672, dominio `stringproject.com`): (a) **config globale completa** nel pannello Impostazioni→Integrazioni→iubenda — master switch attivo + **Private API Key** della Consent Database presente (confermato dal titolare; Consent Database attiva anche lato iubenda); (b) **form con `iubenda_attivo: true`** e `iubenda_mapping` valido — form 1 "Contatti IT": `subject: {email:"email", first_name:"nome"}`, `preferences: [{key:"consenso_privacy", campo:"privacy"}]`; la checkbox nel markup è `name="privacy"` con `sw-required` (consenso quindi sempre accettato all'invio); (c) submission **riuscite**. **Repro (2 submission reali dal form live `/contatti/`, browser vero, reCAPTCHA attivo e superato)**: submission **id 22** (30/07 10:33:59) e **id 23** (30/07 10:41:27), entrambe a buon fine — email recapitata, record persistito in `GET /forms/1/submissions` — ma **zero consensi nella Consent Database** (verificato dal titolare sul dashboard iubenda; subject attesi `zztest-iubenda@example.com` e `zztest-iubenda-repro2@example.com`). **Il fallimento è completamente silenzioso**: nessun errore lato client, la submission riesce comunque (comportamento corretto), ma nemmeno lato API c'è traccia dell'esito — `GET /forms/{id}/submissions` non espone alcun campo sull'esito iubenda. **Richieste**: (1) controllare i log del backend per l'esito della `POST consent.iubenda.com` in corrispondenza delle 2 submission sopra (eccezione swallowed? chiave non letta? payload rifiutato?); (2) **loggare ed esporre l'esito** della registrazione (es. campo `iubenda_status`/`iubenda_consent_id` sulla submission) così un fallimento non resta invisibile — per un adempimento GDPR il "sembra attivo ma non registra" è il caso peggiore; (3) verificare formato payload e header (`ApiKey` della **Consent Database**, non il site key della cookie solution) contro l'API Consent v1 di iubenda. ⬆️ **Aggiornamento 11/08**: la richiesta (2) risulta implementata — `GET /forms/{id}/submissions` ora espone **`esito`/`errore`** per submission (visto su 122-h000744: `esito:"error"`, `errore:"Email di notifica NON inviata: … SMTP di sistema non configurato"`). Resta da riverificare la registrazione iubenda vera su 122-h000672 con la catena completa. | 🔴 aperto (30/07) |
| B34 | **A11y dei template tema (header/nav)** — axe 4.12 (WCAG 2.1 AA + best-practice) su una pagina CMS pulita segnala 4 violazioni tutte del tema, nessuna del contenuto: `landmark-no-duplicate-banner` (`#header_basic`), `landmark-unique` (nav principale duplicata), `list` (il selettore lingua `.sw-mobile-nav-list` ha figli non-`li` dentro `<ul>`), `region` (skip-link fuori dai landmark). Inoltre il tema referenzia `/static/img/uploads/favicon.ico` che è 404 su tenant nuovo (errore console su ogni pagina). | 🟡 aperto (03/07) |
| B24 | Propagazione lenta e incoerente dopo create/compile: per minuti lo stesso URL alterna 200/404/500 a seconda del worker che risponde (URLconf/template non ricaricati in modo atomico su tutti i worker). ⬆️ **Retest 11/08**: sulle pagine CMS la propagazione è ok, ma il sintomo persiste sul **routing dei prodotti nuovi**: la scheda di un prodotto appena creato via API risponde **404 finché non si esegue `cache flush`** (visto su 122-h000744). Manca ancora l'invalidazione automatica alla creazione. ⬆️ **Retest 20/08 (122-h000744): peggiorato o più lento** — prodotto nuovo completo (stato 1, prezzo su listino 1, categoria 9) → scheda **404 anche DOPO `POST /cache/flush`**, ritentato fino a +80s; il prodotto non compare nemmeno nella pagina categoria. Il workaround del flush non è più sufficiente nei tempi osservati. — _di chi: Swerpify (infra)_ | 🟡 ANCORA APERTO (retest 20/08) |
| B22 | Template tag custom (`{% get_recensioni %}`) → 500 su pagine create via API anche dopo `PUT pages/{id}` con `contexts` identici alla pagina originale + re-PUT del content + compile. Funziona solo rimuovendo il tag dal content. Da chiarire col team come attivare i contexts sulle pagine nuove. — _di chi: Swerpify (backend)_ | 🟡 ANCORA APERTO (retest 20/08, spnew): pagina ZZTEST con `{% get_recensioni %}` → 500 riprodotto; pagina rimossa e compile rieseguito |
| B19 | **Motore mailing: restano senza API il tracking aperture/click delle campagne e il trigger/webhook `cart.abandoned`** — il resto (template, transazionale, campagne, stats, revoca token) è coperto dal 12/06; le statistiche campagna espongono totale/inviate/errori/in coda ma non aperture né click, e il recupero carrelli abbandonati resta a polling (`GET /carts?abbandonato=true`) senza evento outbound. _di chi: Swerpify (API)_ | 🟡 aperta (residuo) |

## Decisioni in sospeso (non bug)

| # | Questione | Stato |
|---|---|---|
| B2 | I token di `POST /auth/token` **non scadono più** (`expires_at: null`): confermare che sia voluto. L'issue originale (scadenza 1h senza refresh) è superata; resta il tema della revoca come unico modo di invalidarli (`swerpicommerce-auth token-revoke`). | ⚪ da confermare |
| B6 | `GET /openapi.json` è **pubblico senza autenticazione**: comodo per rigenerare il CLI dallo schema live, ma espone l'intera superficie API a chiunque. Decidere se è voluto. | ⚪ decisione |

## Lato nostro (toolchain, non piattaforma)

- **D1 — Printing Press 4.6.1 nasconde i comandi risorsa principali**: `products`, `orders`, `customers`, `pages` (e altri) sono generati con `Hidden: true` → non compaiono in `--help` ma funzionano; l'elenco completo è `swerpicommerce-pp-cli api`. Da segnalare upstream, non patchabile localmente (file generati, sovrascritti a ogni regen).
- **D2 — Go di sistema 1.26.3 con 2 CVE stdlib** (GO-2026-5039 net/textproto, GO-2026-5037 crypto/x509): pin `toolchain go1.26.4` nel `go.mod` del CLI, da rimettere a ogni `generate --force` (è la patch manuale (a) della pipeline di rigenerazione).

<details>
<summary>Archivio — issue risolte o ritirate (id → titolo → chiusura). Testo integrale nel git, vedi sopra.</summary>

- B1 — Server URL relativo nello schema — ✅
- B3 — CRUD clienti incompleto (no get/update/delete) — ✅
- B4 — 404 API in HTML — ✅
- B5 — Envelope risposte incoerente — ✅
- B7 — Manca endpoint whoami/verify — ✅
- B8 — Prodotti senza campi meta/SEO (pagine e categorie ok) — ✅
- B9 — PUT ignora silenziosamente i campi sconosciuti — ✅ 11/08
- B10 — Articoli blog non esposti dall'API (meta non gestibili) — ✅
- B12 — Niente codici sconto/coupon (solo sconto ad-hoc per ordine) — ✅
- B13 — Punti fedeltà in sola lettura via API — ✅ 12/06
- B14 — Pagine CMS: no create/delete, HTML non gestibile (template-driven) — ✅
- B15 — Upload media assente (immagini solo da pannello) — ✅
- B16 — PUT/DELETE immagine dichiarati nello spec ma 405 (route solo GET); errore in HTML non JSON — ✅
- B17 — Mailing/newsletter non esposti (liste email, iscritti, campagne) — ✅ 12/06
- B18 — Carrelli (e carrelli abbandonati) non esposti — ✅ 12/06
- B20 — Doc spec errata: placeholder documentati come `{{chiave}}` ma il motore usa `{chiave}` — ✅ 20/08
- B21 — Variazioni: modello non documentato (enum tipo_prodotto, forma valori_attributi); manca filtro `prod_principale_id` e… — ✅ 20/08
- B23 — Routing pagine legato a `sitemap`: con `sitemap:false` la pagina creata via API non è raggiungibile (404). Impossibile… — ✅ 11/08
- B25 — Con `no_cache:false` la pagina è cachata lato app con `max-age=84600` (~23,5h) e `POST /design/compile` NON invalida… — ✅ 11/08
- B26 — Il tree-shaking del bundle `prodotto` non scansiona il campo `descrizione` dei prodotti (il `cms` invece scansiona il… — ✅ 24/06
- B27 — Documentazione `lang` / `?lang` — ✅ 30/06
- B28 — Collegamento traduzioni — PAGINE CMS — campo `alternates` (`[{alternate_lang, alternate_page_id}]`), impostabile solo… — ✅ 30/06
- B29 — Collegamento traduzioni — PRODOTTI, ARTICOLI, CATEGORIE — `alternates` ora esposto su tutte le risorse:… — ✅ 30/06
- B30 — Codici lingua — i campi `lang` restano senza `enum` e non c'è un endpoint dedicato per elencare le lingue configurate… — ✅ 20/08
- B31 — Slug con `/` accettati dall'API ma rotti sul frontend — ✅ 20/08
- B32 — `POST /pages` può rispondere 500 avendo però creato la pagina — ✅ 20/08
- B33 — Gerarchie pagine: funzionano via `pagina_padre_id`, ma l'URL piatto resta attivo senza canonical — ✅ 11/08
- B35 — Impostazioni grafiche (colori del tema) non esposte via API — ✅ 03/07
- B36 — Logo non gestibile via API — ✅
- B37 — `PUT /fonts/assignments` non valida le chiavi — ✅ 20/08
- B38 — `font-display` ignorato nell'upload font — ✅ 04/07
- B39 — Lingue del sito non creabili/attivabili via API — ✅ 20/08
- B40 — Blog: autore = tendina nel pannello ma stringa libera via API; byline assente nella pagina articolo — ✅ 20/08
- B41 — Nessun motore di redirect (301) gestibile — ✅ 16/07
- B42 — Template articolo blog: forkabile ma NON attivabile — ✅ 11/08
- B43 — `<link rel="canonical">` e Open Graph assenti su tutto il frontend — ✅ 20/07
- B44 — hreflang vuoto per la lingua predefinita — ✅ 11/08
- B45 — `num_articoli` delle categorie blog conta doppio la categoria principale — ✅ 20/08
- B46 — Pagine categoria blog: meta description del record non emessa — ✅ 06/07
- B47 — Dati azienda del tenant non esposti via API — ✅ 08/07
- B48 — Slot loghi del tema non impostabili via API — ✅ 15/07
- B49 — Doc custom-apps contraddittoria sul CSS admin → app con look diverso dal pannello nativo — ✅ 11/08
- B50 — Tipografia di default: `<a>` ha un font-size ASSOLUTO invece di ereditare → i link escono più grandi del testo che li… — ✅ 17/07
- B51 — `/redirects`: le regole si salvano ma nginx non le applica MAI → il motore di B41 non funziona end-to-end — ✅ 17/07
- B52 — Redirect: la destinazione esce in `http://` → hop extra in chiaro — ✅ 17/07
- B53 — Header di default: `id="cart_el"` duplicato tra header e sticky-header → ID duplicato nel DOM — ✅ 11/08
- B54 — `llms.txt` non generato/servito nonostante i campi `llms_*` valorizzati — ✅ 20/08
- B55 — `<html lang>` usa il «Codice (slug)» invece del tag locale BCP-47 già presente nella config — ✅ 20/07
- B56 — La cache-pagina non si invalida all'update → le modifiche SEO/contenuto NON arrivano al sito live senza un `cache… — ⚪ ritirata 20/07
- B57 — Recidiva B51 su PIÙ istanze (122-h000662 VigeSrl, 122-h000737 Leica Campania): `/redirects` salva le regole ma nginx… — ✅ 20/08
- B59 — Export OpenAPI dal pannello: una virgola in una description non quotata spezza il campo in una chiave JSON spuria — ✅ 21/08
- B60 — Variazioni prodotto: l'API non può crearle in forma funzionante → scheda del padre variabile in 500 nudo — ✅ 11/08
- B61 — Preset `storefront-home`: `.sw-cta--solid:hover` non ridichiara `color` → testo blu su fondo scuro nei tenant… — ✅ 20/08
- B62 — Scheda prodotto: selezionando una variazione la galleria si impila in colonna — ✅ 20/08
- B63 — Preset cms/form.css: line-height 1.2, input[type=date] disallineato e sw-form-select senza base — ✅ retest 26/08 (2.66.x): base condivisa, `line-height: 1.5`, `height` esplicita (hook 2.54.26 + 2.61.18)
- B64 — `GET /products?categoria_id=<id>` restituisce sempre 0 risultati — ✅ 20/08
- B65 — Filtri del negozio senza scrittura via API (attiva_filtri / separa_prodotti) — ✅ 20/08: CRUD attributi con i due flag
- B66 — Il tree-shake di `design compile` scarta 4 regole del preset `categoria_prodotto` che sono definite E usate → pagina… — ✅ 20/08
- B67 — Gli schemi `*UpdateInput` dichiarano `default` su campi di stato → ogni update parziale via CLI li reinvia e… — ✅ 20/08
- B68 — `ProductInput.tipologia`: default `"prodotto"` che nessun catalogo usa, nessun enum, nessuna validazione → i prodotti… — ✅ 20/08
- B69 — L'esempio di markup in `GET /forms-guide` non è accessibile né conforme al GDPR → ogni form costruito copiandolo nasce… — ✅ 20/08
- B70 — Il motore redirect accetta le regole via API ma non le applica: nessun 301, gli URL restano 404 — ✅ 20/08
- B71 — I bundle CSS compilati non hanno cache-busting per-compile → dopo un `design compile` i visitatori di ritorno vedono… — ✅ 20/08
- B72 — Tutte le richieste `DELETE` via API falliscono con Cloudflare 520 sul dominio custom — ✅ 20/08
- B73 — Nessuna validazione VIES né reverse charge B2B intra-UE: l'IVA è configurabile solo come mappa nazione→aliquota — ✅ 20/08
- B77 — Il tooltip dei punti fedeltà (preset `prodotto/componenti.css`) sporge oltre il viewport su mobile e fa scorrere… — ✅ 26/08
- B78 — `POST /media` 500 sopra ~1,85 MB decodificati (default Django `DATA_UPLOAD_MAX_MEMORY_SIZE`), limite documentato di 10 MB irraggiungibile — ✅ 27/08 (2.66.11): 9,5 MB → 201; 12 MB → 400 `IMAGE_TOO_LARGE` «File oltre i 10 MB»; 26 MB → 413 `PAYLOAD_TOO_LARGE` «body max 16 MiB». Resta il nome del codice (`IMAGE_TOO_LARGE` anche per i PDF), minore

</details>
