# Calendario ferie A3

Genera ogni anno il **planner annuale delle ferie in A3 orizzontale**, pronto da
stampare e distribuire. Un file per anno descrive le festività; lo script
produce il PDF.

**Non serve installare niente**: né librerie, né browser. Basta Python 3.11 o
successivo, che è l'unico requisito.

## Come si usa

```bash
python3 build.py 2028       # su Windows: py build.py 2028
```

Al primo lancio di un anno nuovo lo script scrive `data/<anno>.toml` con le sole
festività ricavabili dal calendario, e stampa l'elenco di ciò che resta da
decidere a mano. Il file **non viene mai sovrascritto**: si apre, si completa e
si rilancia il comando.

Il risultato finisce in `out/holiday-planner-<anno>.pdf`: una pagina, A3
orizzontale, vettoriale.

L'elenco di "still to decide" è un promemoria, non un errore: il PDF viene
generato comunque.

## Il file dei dati

```toml
year = 2028
footnotes = []

[header]
organization = "Science and Technology Organization"
centre = "Centre for Maritime Research and Experimentation"
url = "http://www.cmre.nato.int"
background = "#8e9aab"     # "#ffffff" per stampare su fondo bianco
logo = "assets/logo.png"

[[holidays]]
date = 2028-01-06
label = "Epiphany"
kind = "H"

[[holidays]]
date = 2028-03-26
label = "Good Friday"
qualifier = "(in lieu of 1 May)"
kind = "H"
```

`kind` vale:

| valore   | significato                                 | marcatore |
|----------|---------------------------------------------|-----------|
| `"H"`    | centro chiuso, festività                    | `H` rosso |
| `"HC"`   | chiusura concordata (*holiday closure*)     | `H` rosso |
| `"grant"`| giornata concessa (*extra day*, *grant*)    | `H` rosso |
| `"note"` | giorno etichettato ma lavorativo            | nessuno   |

`qualifier` è la riga piccola accanto all'etichetta, tipo `(in lieu of 1 May)`.

## Cosa calcola da solo e cosa no

Vengono calcolate: Capodanno, Epifania, Venerdì Santo e Lunedì dell'Angelo
(Pasqua con l'algoritmo gregoriano), 25 aprile, 1 maggio, 2 giugno, Ferragosto,
Ognissanti, Immacolata, Natale e Santo Stefano. Una festività che cade di sabato
o domenica resta come etichetta **senza** la `H`, perché il giorno sostitutivo lo
sceglie il centro.

Restano da inserire a mano, ogni anno: le chiusure `HC`, gli *Extra Day*, i
*Director's Grant* e il giorno preso in luogo di una festività caduta nel
weekend. Lo script li elenca a ogni lancio finché non ci sono.

## Il logo

Si punta `header.logo` a un file **PNG o JPEG** e finisce nel riquadro in alto a
sinistra, ridimensionato mantenendo le proporzioni. Il riquadro è 34 × 24 mm, e
un'immagine con trasparenza viene rispettata.

Gli SVG non si possono usare: non essendoci un browser, il PDF vuole
un'immagine a pixel. Un PNG a 16 bit, interlacciato, o con un colore
trasparente nella tavolozza viene rifiutato con un messaggio che dice come
riesportarlo.

Finché `logo` è vuoto, al suo posto compare un riquadro con la scritta `LOGO`.

## Il foglio

A3 orizzontale, 420 × 297 mm. I mesi sono dodici righe, gennaio in alto; i
giorni corrono da sinistra a destra su 37 colonne, sfalsate in modo che ogni
colonna contenga sempre lo stesso giorno della settimana — così una settimana si
legge come una fetta verticale del foglio. Sabato e domenica sono in verde.

Misure, colori e corpi del testo sono le costanti in cima a `calferie/sheet.py`,
tutte in millimetri: si cambiano lì, senza toccare il disegno sotto.

Il fondo grigio-azzurro (`background`) è quello del poster stampato in
tipografia. Per una stampante da ufficio conviene metterlo a `"#ffffff"`: il
titolo e l'URL passano automaticamente al blu scuro.

## Come è fatto

Python scrive il PDF direttamente, con la sola libreria standard. Il testo usa i
quattordici font che ogni lettore PDF ha già dentro, quindi non c'è nessun file
di font da trovare o incorporare.

```
build.py                riga di comando
calferie/holidays.py    Pasqua e festività italiane
calferie/model.py       lettura e scrittura del file dell'anno (TOML)
calferie/grid.py        geometria della griglia
calferie/sheet.py       il disegno del foglio: misure, colori, corpi
calferie/pdf.py         il PDF: rettangoli, linee, testo, immagini
calferie/images.py      lettura di un PNG o JPEG per incorporarlo
data/<anno>.toml        le festività di quell'anno
```

## Test

```bash
python3 -m unittest discover -s tests
```

Il poster 2027 del CMRE è la referenza: i test verificano che le giornate chiuse
generate coincidano con quelle stampate su quel foglio. Altri controllano che
nel codice non entrino dipendenze esterne né costrutti che su Windows si
rompono.

## Automazione

`.github/workflows/build.yml` esegue i test e allega il PDF a ogni push.
`.github/workflows/new-year.yml` il 1° novembre apre una pull request con la
bozza dell'anno successivo, da completare con le giornate discrezionali.

## Nota sulla collocazione

Questa cartella è autonoma e nasce per stare in una repository propria. Per
spostarla basta creare la repo vuota e copiarci dentro il contenuto della
cartella: i due workflow, che in questa posizione GitHub ignora, si attivano da
soli una volta che `.github/workflows` si trova nella radice della repository.
