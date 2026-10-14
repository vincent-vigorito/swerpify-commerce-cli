# SwerpiCommerce v2 — Issue di piattaforma (registro aperto)

> Registro **ripartito pulito il 27/08/2026**: qui stanno solo le issue ancora aperte. La storia
> completa (B1–B77, sezioni A/C/D, report cronologici giugno–agosto, retest di massa del 20/08) è
> nel git del repo: `git show 1a43cdc:SWERPICOMMERCE-ISSUES.md`. La numerazione **continua**:
> prossimo id **B94**.
>
> Convenzioni: una riga per issue — titolo in grassetto, poi sintomo, evidenza (tenant, data,
> misure), impatto e richiesta; stato = 🔴 aperta · 🟡 aperta minore/residuo · ⚪ decisione da
> prendere. A ogni rilascio si ritestano le aperte: chi chiude sposta la riga nell'archivio in fondo
> (id → titolo → data), non la cancella. Entità di test `ZZTEST` con cleanup.

## Aperte (piattaforma)

| # | Problema | Stato |
|---|---|---|
| B80 | **Restyle dell'area account (2.70.2, commit `798b1e88`) fatto nel solo layer `default/mio-account/`: i tenant già provisionati restano alla versione vecchia** — i preset per-istanza `mio_account/{variabili,componenti,tabs}.css` di Così Com'è (122-h000743, 2.70.2) sono **byte-identici al default PRE-restyle** (md5 uguali a `798b1e88~1`) e diversi dal nuovo default; il bundle live `account.css` serve ancora `--sw-stato-completato: #059669` invece di `var(--sw-success)`. Nessun `update_hooks/` accompagna il commit (a differenza di `2.61.18__css_form_base_campi_in_place.py` per B63). Impatto: il restyle esiste solo per i tenant creati da oggi; quelli vecchi non lo vedranno mai, e chi legge il default nel repo crede sia live. **Richiesta**: hook di aggiornamento che riscriva in place i preset `mio_account/*` non modificati dal tenant (stessa idempotenza del 2.61.18: no-op se il file è stato riscritto a mano), oppure documentare che i layer `pagine-sistema/` non seguono il default dopo il provisioning. **Workaround applicato su Così Com'è il 29/08**: i 5 file ricopiati dal default HEAD via `PUT /design/css/mio_account/<file>` + compile (backup dei precedenti conservato); `account.css` live ora con `--sw-stato-*` sui token della palette. Resta da fare sugli altri tenant esistenti finché non c'è l'hook. ⬆️ Retest 05/10 (2.93.2): **ancora aperta** — nessun hook `mio-account` dopo il 2.61.19 in `update_hooks/`; i 5 preset `mio_account/*` per-istanza di spnew e detergenzaprofessionale restano alla versione pre-restyle (es. `variabili.css` 536 byte contro 669 del default, bundle live `account.css` di spnew con `--sw-stato-completato:#059669`); fresenium (provisionato dopo) è allineato al default. ⬆️ Retest 14/10 (2.94.94): **ancora aperta** — gli 8 preset `mio_account/*` di spnew restano alla versione vecchia (`variabili.css` 536 byte contro 669). Novità utile: `GET /design/css` espone ora `allineato_al_default` per ogni preset (richiesta (3) di B92), quindi i file rimasti indietro si vedono da API: spnew 46 preset su 66 non allineati (molti però modificati a mano), DP 26, cosicome 28, fresenium 12. Manca ancora l'hook che riallinei i preset non toccati dal tenant. | 🔴 aperta (workaround su 122-h000743) |
| B58 | **Consenso iubenda (Consent Database): la registrazione server-side non avviene MAI, e fallisce in silenzio** — con la catena completa attiva, alla submission il consenso **non compare nella Consent Database** di iubenda. Setup verificato su String Project (122-h000672, dominio `stringproject.com`): (a) **config globale completa** nel pannello Impostazioni→Integrazioni→iubenda — master switch attivo + **Private API Key** della Consent Database presente (confermato dal titolare; Consent Database attiva anche lato iubenda); (b) **form con `iubenda_attivo: true`** e `iubenda_mapping` valido — form 1 "Contatti IT": `subject: {email:"email", first_name:"nome"}`, `preferences: [{key:"consenso_privacy", campo:"privacy"}]`; la checkbox nel markup è `name="privacy"` con `sw-required` (consenso quindi sempre accettato all'invio); (c) submission **riuscite**. **Repro (2 submission reali dal form live `/contatti/`, browser vero, reCAPTCHA attivo e superato)**: submission **id 22** (30/07 10:33:59) e **id 23** (30/07 10:41:27), entrambe a buon fine — email recapitata, record persistito in `GET /forms/1/submissions` — ma **zero consensi nella Consent Database** (verificato dal titolare sul dashboard iubenda; subject attesi `zztest-iubenda@example.com` e `zztest-iubenda-repro2@example.com`). **Il fallimento è completamente silenzioso**: nessun errore lato client, la submission riesce comunque (comportamento corretto), ma nemmeno lato API c'è traccia dell'esito — `GET /forms/{id}/submissions` non espone alcun campo sull'esito iubenda. **Richieste**: (1) controllare i log del backend per l'esito della `POST consent.iubenda.com` in corrispondenza delle 2 submission sopra (eccezione swallowed? chiave non letta? payload rifiutato?); (2) **loggare ed esporre l'esito** della registrazione (es. campo `iubenda_status`/`iubenda_consent_id` sulla submission) così un fallimento non resta invisibile — per un adempimento GDPR il "sembra attivo ma non registra" è il caso peggiore; (3) verificare formato payload e header (`ApiKey` della **Consent Database**, non il site key della cookie solution) contro l'API Consent v1 di iubenda. ⬆️ **Aggiornamento 11/08**: la richiesta (2) risulta implementata — `GET /forms/{id}/submissions` ora espone **`esito`/`errore`** per submission (visto su 122-h000744: `esito:"error"`, `errore:"Email di notifica NON inviata: … SMTP di sistema non configurato"`). Resta da riverificare la registrazione iubenda vera su 122-h000672 con la catena completa. ⬆️ Retest 05/10 (spnew 2.93.2, solo API): le submission del form 1 espongono ora `iubenda_esito`/`iubenda_errore` e **tutte le 11 submission reali dal 04/09 al 04/10 hanno `iubenda_esito: success`** (le 18 precedenti, fino al 21/08, hanno il campo vuoto). Lato piattaforma la registrazione risulta riuscita; **non ritestabile via API** la presenza effettiva dei consensi nella Consent Database: va confermata dal titolare sul dashboard iubenda (è il modo in cui era stato rilevato il guasto). | 🟡 probabile risolta, da confermare sul dashboard (05/10) |
| B34 | **A11y dei template tema (header/nav)** — axe 4.12 (WCAG 2.1 AA + best-practice) su una pagina CMS pulita segnala 4 violazioni tutte del tema, nessuna del contenuto: `landmark-no-duplicate-banner` (`#header_basic`), `landmark-unique` (nav principale duplicata), `list` (il selettore lingua `.sw-mobile-nav-list` ha figli non-`li` dentro `<ul>`), `region` (skip-link fuori dai landmark). Inoltre il tema referenzia `/static/img/uploads/favicon.ico` che è 404 su tenant nuovo (errore console su ogni pagina). ⬆️ Retest 05/10 (axe 4.10.2 a 1440 e 390 px su fresenium `/privacy-policy/` 2.93.2, cosicome `/contatti/` 2.93.2, swerpifywebsite `/contatti/` 2.90.1): **0 violazioni** su `landmark-no-duplicate-banner`, `landmark-unique`, `list`, `region` e sulle altre regole di header/nav. Favicon 200 su fresenium e cosicome; **non ritestato** il 404 del favicon su un tenant appena creato (bzchem, l'unico vuoto, risponde 502). | 🟡 resta solo il favicon su tenant nuovo (05/10) |

## Decisioni in sospeso (non bug)

| # | Questione | Stato |
|---|---|---|
| B2 | I token di `POST /auth/token` **non scadono più** (`expires_at: null`): confermare che sia voluto. L'issue originale (scadenza 1h senza refresh) è superata; resta il tema della revoca come unico modo di invalidarli (`swerpicommerce-auth token-revoke`). | ⚪ da confermare |
| B6 | `GET /openapi.json` è **pubblico senza autenticazione**: comodo per rigenerare il CLI dallo schema live, ma espone l'intera superficie API a chiunque. Decidere se è voluto. | ⚪ decisione |

## Lato nostro (toolchain, non piattaforma)

- **D1 — Printing Press 4.6.1 nasconde i comandi risorsa principali**: `products`, `orders`, `customers`, `pages` (e altri) sono generati con `Hidden: true` → non compaiono in `--help` ma funzionano; l'elenco completo è `swerpicommerce-pp-cli api`. Da segnalare upstream, non patchabile localmente (file generati, sovrascritti a ogni regen). ✅ Superata al 14/10: col CLI generato da Printing Press 4.32.3 (regen del 13/10) `products`, `orders`, `customers` e `pages` compaiono in `--help` (84 comandi); anche `pages list --all` ora pagina (197 righe su spnew).
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
- B19 — Motore mailing senza tracking aperture/click e senza webhook `cart.abandoned` — ✅ 05/10 (2.93.2): `campaigns stats` espone `aperte`/`aperture_totali`/`cliccate`/`click_totali`/`open_rate`/`click_rate` (verificato in lettura sulla campagna 5 di spnew, valori 0 perché inviata nel 2025, prima del tracking) e `WebhookEvent` comprende `cart.abandoned`; il funzionamento del tracking su un invio reale non è stato verificato (nessuna campagna nuova inviata)
- B20 — Doc spec errata: placeholder documentati come `{{chiave}}` ma il motore usa `{chiave}` — ✅ 20/08
- B21 — Variazioni: modello non documentato (enum tipo_prodotto, forma valori_attributi); manca filtro `prod_principale_id` e… — ✅ 20/08
- B22 — Template tag custom (`{% get_recensioni %}`) → 500 su pagine create via API — ✅ 05/10 (spnew 2.93.2): pagina ZZTEST creata via API con `{% load recensioni_custom_tags %}{% get_recensioni 'armour-soft' as recensioni %}` → 200 e 4 recensioni rese, senza compile; pagina eliminata (API e URL pubblico 404, nessun file residuo nel fork)
- B23 — Routing pagine legato a `sitemap`: con `sitemap:false` la pagina creata via API non è raggiungibile (404). Impossibile… — ✅ 11/08
- B24 — Propagazione lenta dopo create/compile (prodotto nuovo in 404 anche dopo il flush) — ✅ 05/10 (fresenium 2.93.2): prodotto ZZTEST pubblicato in categoria → scheda 200 e prodotto presente nella pagina categoria già a t+0 e fino a t+80 s, **senza** `cache flush`; dopo il delete scheda 404 e categoria pulita subito. Ritestato su fresenium perché detergenza è un negozio live e bzchem risponde 502
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
- B74 — Canonical delle schede prodotto self-referential su qualsiasi segmento categoria — ✅ 05/10 (detergenzaprofessionale 2.93.2): categoria inesistente → 404; alias di categoria secondaria e path a 4 livelli → 200 con canonical fisso sul path della categoria principale (`/negozio/industria/<slug>/`). Dettaglio trascurabile: la pagina 404 porta un canonical che ripete l'URL richiesto
- B75 — `list-style-type: disc` dichiarato sui `<li>` → `list-style:none` sul contenitore inefficace — ✅ 05/10 (2.90.1 e 2.93.2): nel bundle `cms.css` la regola è ora `:where(#main_content ul:not([class])) li` (e `ol:not([class])` per decimal), quindi le liste con classe non ricevono più il marker; verificato su swerpifywebsite, spnew e detergenzaprofessionale
- B76 — Il tree-shake scartava le regole a selettore singolo su classi runtime dichiarate in commento — ✅ 05/10 (swebify-new 2.90.1): con `<!-- runtime: sw-zzt76--pin -->` nel contenuto, `.sw-zzt76--pin{height:640vh;padding:0}` resta nel bundle insieme alla regola discendente, mentre una classe di controllo non dichiarata viene scartata; la guida SWCSS ora documenta la sintassi `<!-- runtime: … -->`. Pagina e CSS ZZTEST eliminati e ricompilato (0 residui nel bundle e nel fork)
- B77 — Il tooltip dei punti fedeltà (preset `prodotto/componenti.css`) sporge oltre il viewport su mobile e fa scorrere… — ✅ 26/08
- B78 — `POST /media` 500 sopra ~1,85 MB decodificati (default Django `DATA_UPLOAD_MAX_MEMORY_SIZE`), limite documentato di 10 MB irraggiungibile — ✅ 27/08 (2.66.11): 9,5 MB → 201; 12 MB → 400 `IMAGE_TOO_LARGE` «File oltre i 10 MB»; 26 MB → 413 `PAYLOAD_TOO_LARGE` «body max 16 MiB». Resta il nome del codice (`IMAGE_TOO_LARGE` anche per i PDF), minore. 01/09 (2.71.0): limite applicativo rimosso del tutto (`nessun limite di dimensione applicativo` nello schema; PDF da 24,7 MB → 201 su fresenium)
- B79 — Template `custombox-v2.html`: stringhe `{% blocktrans %}` mancanti nei cataloghi en/es/fr, custom box mista IT/EN — ✅ 14/10 (spnew 2.94.94): sulla box da 9 in EN/ES/FR tradotti anche gli ultimi residui — pulsante esaurito «Not available»/«No disponible»/«Non disponible», «Only N available»/«Solo N disponibles»/«Seulement N disponibles», minicart «Expected restock»/«Previsión de reposición»/«Réassort prévu»
- B81 — I partial upstream `*_base*` non sono esposti dall'API, contro quanto promette la guida — ✅ 03/09 (2.79): area `examples` in sola lettura con i riferimenti canonici di header/sticky/footer/home (ecommerce e vetrina); retest 04/09 su cosicome 2.79.3
- B82 — `cms/layout.css` ridefiniva `.sw-container` con `padding-inline: 0` da `--xl` — ✅ 05/10: il `cms/layout.css` per-istanza di spnew (2.93.2) e swerpifywebsite (2.90.1) non contiene più il blocco `.sw-container` (691 byte, solo utility); a 1300 px su swerpifywebsite `.sw-container` ha `padding-left` 24 px (era 0)
- B83 — `GET /reviews` 500 `INTERNAL_ERROR` su tutti i tenant 2.79.3 (leggeva il campo `attiva` rimosso dal modello) — ✅ 04/09 (2.79.5, `fb9e5a8e`): retest 200 su detergenza e cosicome; bzchem 500 finché resta a 2.79.3
- B84 — `GET /forms` 500 `ProgrammingError` sul solo tenant spnew — ✅ 05/10 (2.93.2): `forms list` risponde 200 con 19 form
- B85 — Segnaposto dei form invisibili: `cms.css` (2.79.8) ha `.sw-contact-field::placeholder{color:var(--sw-testo-chiaro);opacity:0.6}` e `--sw-testo-chiaro` è #e8e8e8 (grigio da fondo scuro) → su input bianchi il placeholder non si vede. Visto su swerpifywebsite /contatti/ e /prova-gratuita/ il 10/09; pezza tenant in `cms/contatti.css` e `cms/prova-gratuita.css` (`--sw-testo-semi-chiaro`, opacity 1). Aperta: il default del tema andrebbe corretto a monte.
- B86 — **La pagina di sistema del blog non si crea via API**: `POST /pages` rifiuta `pagina_sistema` (400 additional property), `PUT /pages/{id}` lo accetta e il record mostra `pagina_sistema: "blog"` + `template_name`, ma il router risponde 404 su `/blog/` e `PUT /page-templates/blog-*` dice «Pagina di sistema 'blog' non trovata»: la risoluzione usa un'entità che solo il pannello crea. Su swerpifywebsite (10/09, pagina 330) articoli e categorie (`/blog/<slug>/`, `/blog/guide/`) rispondono 200 con i template di serie, i fork `blog-home-swerpify.html`/`blog-articolo-swerpify.html` restano non assegnabili finché la pagina di sistema non viene creata dal pannello. **Risolta al retest del 14/09/2026 (piattaforma 2.82.0)**: `/blog/` risponde 200 sulla pagina 330, `PUT /page-templates/blog|blog-articolo|blog-categoria|blog-search|blog-tag` accetta i fork e le quattro viste rendono `blog-home-swerpify.html`/`blog-articolo-swerpify.html`. Chiusa.
- B87 — A11y dei componenti upstream di negozio, blog, card prodotto e carrello — ✅ 14/10 (2.94.94): chiuso anche il punto (5), `carrello.html` ha ora `<h1>` «Riepilogo carrello» → `<h2>` «Prodotti» → `<h3>` della riga → `<h2>` coupon (verificato sul sorgente upstream, non con axe: servirebbe un carrello pieno sul negozio live); i punti (1)-(4) erano già corretti al retest del 05/10
- B88 — Scheda prodotto mobile: gli accordion non si aprivano al primo tocco se un'altra sezione era aperta — ✅ 14/10 (2.94.94): `toggleSection()` decide ora lo stato dal `display` calcolato (`getComputedStyle(content).display !== 'none'`, la seconda soluzione proposta); a 390 px il primo tocco apre la sezione e chiude l'altra su fresenium (senza pezze) e su spnew. La pezza `prodotto/zz-sp-accordion.css` di spnew non serve più
- B89 — Sicurezza: la `api_key` di Tree-Nation era nell'HTML pubblico di scheda prodotto e custom box — ✅ 14/10 (2.94.94): `treenation_data` espone solo `{"attivo": true, "alberi_default": 1}` (context processor `app/context_processors.py`, test `frontend/test_treenation_api_key.py`); 0 occorrenze di `api_key` sulla scheda Magic e sulle custom box IT/EN/ES/FR di spnew. **Resta lato cliente**: rigenerare la chiave sul pannello Tree-Nation, quella vecchia è stata pubblica
- B90 — Menu mobile aperto dallo sticky: il pannello finiva sotto lo sticky — ✅ 14/10 (2.94.94): nel `cms.css` di default `#header_basic .sw-mobile-panel` passa a z-index 40, sopra `#menu_sticky` (39); su detergenzaprofessionale (default, senza pezze) a 390 px `elementFromPoint` sulla X è il pannello. Le pezze tenant (fresenium a 60, vigesrl, swerpifywebsite) sono ora ridondanti
- B91 — Header sticky: `header-footer/vetrina.css` spostava a sinistra il menu di tutti gli sticky — ✅ 14/10 (2.94.94): la regola è ora `body:has(#header_basic.header-vetrina) #menu_sticky .sw-header-nav-col` nel `cms.css` compilato di fresenium, DP e cosicome; a 1440 px centro del menu header/sticky 690/690 su fresenium, 895/895 su cosicome, 720/720 su spnew (DP ha una regola propria `flex-end`, non è B91)
- B92 — Tooltip dei punti fedeltà: sui tenant provisionati prima della correzione allargava la scheda da 640 a ~1400 px — ✅ 14/10 (2.94.94): in coda al `prodotto.css` di spnew e DP le tre regole richieste (`.sw-tooltip.sw-tooltip{display:none}`, `.group:hover .sw-tooltip.sw-tooltip{display:block}`, `.sw-prod-points-wrap .sw-tooltip.sw-tooltip{left:auto;right:0;transform:none}`); `scrollWidth` = viewport da 390 a 1440 px su spnew e fresenium, e su DP salvo 1024 px (1041) per la colonna carrello dell'header del sito, non per il tooltip; in hover a 768 px il tooltip resta dentro il viewport. Anche la richiesta (3) è arrivata: `allineato_al_default` in `GET /design/css`
- B93 — Recupero password rotto su tutti i tenant dal 28/09: «Invia codice» rispondeva sempre «Richiesta non valida, ricarica la pagina e riprova» — il commit `ab008f5a` del 28/09 («email o body mancanti nel reset password non generano più un 500») ha aggiunto in `reset_password_send` il rifiuto di `cookie` vuoto, mentre `mio_account.js` generava il codice casuale in una variabile locale e mandava `self.cookie`, sempre `""`. Trovata su spnew il 13/10 (2.93.42, richiesta con indirizzo `@example.com`, stesso esito anche col token reCAPTCHA) — ✅ 14/10 (2.94.94): il JS assegna `cookie` prima della chiamata (256 caratteri nel body) e il server risponde «Email non registrata» all'indirizzo finto; su fresenium `sw_page_account.min.js` è identico byte per byte (md5 `6ab52daa…`), ma `/mio-account/` è dietro la verifica di Cloudflare e non si è potuto provare dal browser automatico

</details>
