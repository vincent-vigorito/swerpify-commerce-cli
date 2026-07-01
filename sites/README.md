# sites/ — gestione multi-sito SwerpiCommerce

Ogni sito è una **sottocartella** con dentro un file `credentials.env`. Il wrapper
[`swc`](./swc) rileva il sito, rigenera/riusa il token Bearer e invoca il CLI generato
(`../generated/swerpicommerce-cli/swerpicommerce-pp-cli`) — senza toccare il binario Go
(che a ogni rigenerazione verrebbe sovrascritto).

```
sites/
├── swc                       # wrapper (versionato)
├── _template/credentials.env.example # modello da copiare (versionato)
├── site1/
│   ├── credentials.env       # api_id + api_secret + base_url   ← lo crei tu, MAI committato
│   └── .token.json           # cache token, auto-generata + auto-refresh
└── site2/ …
```

## Aggiungere un sito
```bash
cd sites
mkdir site1
cp _template/credentials.env.example site1/credentials.env
$EDITOR site1/credentials.env        # incolla api_id, api_secret, base_url
```

## Operare su un sito
```bash
cd sites/site1
../swc products list                # sito = cartella corrente
../swc pages content page-get 258
```
oppure da qualunque punto:
```bash
sites/swc --site site1 products list
```

Comodo: metti `sites/` nel PATH (o crea un alias `swc`) e potrai fare `cd site1 && swc …`.

## Token
`swc` chiama `POST <base_url>/auth/token` con `api_id`/`api_secret`, salva il token in
`.token.json` e lo riusa per 20 min (`SWC_TOKEN_TTL`). Se scade prima, fa **auto-refresh
su 401** e riprova una volta. Forzare: `swc --refresh …`.

## Sicurezza
Il [`.gitignore`](./.gitignore) è a **whitelist**: ignora tutto tranne `swc`, `README.md`
e `_template/`. Le cartelle-sito con `credentials.env`/`.token.json` non entrano **mai**
nel repo. Le credenziali restano solo in locale.

## Comandi utili del wrapper
| Comando | Cosa fa |
|---|---|
| `swc --which` | stampa sito attivo + base_url + api_id mascherato |
| `swc --site <n> …` | forza il sito `<n>` |
| `swc --refresh …` | rigenera il token prima di eseguire |
