# Calendario ferie A3

Genera ogni anno il **planner annuale delle ferie in A3 orizzontale**, pronto da
stampare e distribuire. Un file YAML per anno descrive le festività; lo script
produce l'HTML, il PDF in formato A3 e, se serve, un'anteprima PNG.

## Come si usa

```bash
pip install -r requirements.txt

python3 build.py 2028          # crea la bozza dei dati e stampa il PDF
python3 build.py 2028 --png    # aggiunge l'anteprima PNG
python3 build.py 2028 --html   # si ferma all'HTML, per ritoccare il CSS
```

Al primo lancio di un anno nuovo lo script scrive `data/<anno>.yaml` con le sole
festività ricavabili dal calendario, e stampa l'elenco di ciò che resta da
decidere a mano. Il file **non viene mai sovrascritto**: si apre, si completa e
si rilancia il comando.

Il risultato finisce in `out/holiday-planner-<anno>.pdf`.

### Su Windows

Il comando è `py` invece di `python3`:

```
py -m pip install --user -r requirements.txt
py build.py 2028
```

Lo script usa il browser che trova già installato — Chrome, Chromium o **Edge**,
che su Windows c'è sempre. Non c'è niente da scaricare. Se sta in una posizione
insolita, glielo si dice così:

```
set CHROMIUM=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
py build.py 2028
```

## Il file dei dati

```yaml
year: 2028

header:
  organization: "Science and Technology Organization"
  centre: "Centre for Maritime Research and Experimentation"
  url: "http://www.cmre.nato.int"
  background: "#8e9aab"                     # "#ffffff" per stampare su fondo bianco
  logo_left: "assets/logo-placeholder.svg"
  logo_right: ""

holidays:
  - date: 2028-01-06
    label: "Epiphany"
    kind: H
  - date: 2028-03-26
    label: "Good Friday"
    qualifier: "(in lieu of 1 May)"
    kind: H

footnotes: []
```

`kind` vale:

| valore  | significato                                    | marcatore |
|---------|------------------------------------------------|-----------|
| `H`     | centro chiuso, festività                       | `H` rosso |
| `HC`    | chiusura concordata (*holiday closure*)        | `H` rosso |
| `grant` | giornata concessa (*extra day*, *grant*)       | `H` rosso |
| `note`  | giorno etichettato ma lavorativo               | nessuno   |

`qualifier` è la riga piccola sotto l'etichetta, tipo `(in lieu of 1 May)`.

## Cosa calcola da solo e cosa no

Vengono calcolate: Capodanno, Epifania, Venerdì Santo e Lunedì dell'Angelo
(Pasqua con l'algoritmo gregoriano), 25 aprile, 1 maggio, 2 giugno, Ferragosto,
Ognissanti, Immacolata, Natale e Santo Stefano. Una festività che cade di sabato
o domenica resta come etichetta **senza** la `H`, perché il giorno sostitutivo lo
sceglie il centro.

Restano da inserire a mano, ogni anno: le chiusure `HC`, gli *Extra Day*, i
*Director's Grant* e il giorno preso in luogo di una festività caduta nel
weekend. Lo script li elenca a ogni lancio finché non ci sono.

## Loghi

`assets/logo-placeholder.svg` è un segnaposto: va sostituito con il logo vero
mantenendo più o meno le stesse proporzioni (circa 340 × 240). Con
`logo_right` si aggiunge un secondo logo a fianco.

## Il foglio

A3 orizzontale, 420 × 297 mm. I mesi sono dodici righe, gennaio in alto; i
giorni corrono da sinistra a destra su 37 colonne, sfalsate in modo che ogni
colonna contenga sempre lo stesso giorno della settimana — così una settimana si
legge come una fetta verticale del foglio. Sabato e domenica sono in verde.

Tutte le misure, i colori e i corpi del testo sono variabili CSS in cima a
`templates/planner.html.j2`: si cambiano lì, senza toccare il codice.

Il fondo grigio-azzurro (`background`) è quello del poster stampato in
tipografia. Per una stampante da ufficio conviene metterlo a `"#ffffff"`: il
titolo e l'URL passano automaticamente al blu scuro.

## Come è fatto

Python genera l'HTML con Jinja2 e un browser in modalità headless lo stampa in
PDF vettoriale. Va bene qualsiasi browser basato su Chromium — Chromium, Chrome
o Edge — e viene cercato prima in `$CHROMIUM`, poi nel PATH, poi nelle posizioni
consuete di Windows, macOS e Linux. Normalmente ne hai già uno e non c'è nulla
da installare.

```
build.py                    riga di comando
calferie/holidays.py        Pasqua e festività italiane
calferie/model.py           lettura e scrittura del file dell'anno
calferie/grid.py            geometria della griglia
calferie/render.py          HTML, PDF, anteprima
templates/planner.html.j2   il foglio
data/<anno>.yaml            le festività di quell'anno
```

## Test

```bash
python3 -m unittest discover -s tests
```

Il poster 2027 del CMRE è la referenza: i test verificano che le giornate chiuse
generate coincidano con quelle stampate su quel foglio.

## Automazione

`.github/workflows/build.yml` esegue i test e allega il PDF a ogni push.
`.github/workflows/new-year.yml` il 1° novembre apre una pull request con la
bozza dell'anno successivo, da completare con le giornate discrezionali.

## Nota sulla collocazione

Questa cartella è autonoma e nasce per stare in una repository propria. È
arrivata qui perché l'integrazione GitHub di questa sessione non ha il permesso
di creare repository nuove. Per spostarla basta creare la repo vuota e copiarci
dentro il contenuto della cartella: i due workflow, che in questa posizione
GitHub ignora, si attivano da soli una volta che `.github/workflows` si trova
nella radice della repository.
