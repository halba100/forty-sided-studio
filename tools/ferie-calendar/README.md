# Calendario ferie A3

Genera ogni anno il **planner annuale delle ferie in A3 orizzontale**, pronto da
stampare e distribuire.

**Non serve installare niente**: né librerie, né browser. Basta Python 3.11 o
successivo, che è l'unico requisito.

---

## Indice

1. [Uso quotidiano](#1-uso-quotidiano)
2. [Il file dell'anno](#2-il-file-dellanno)
3. [Cambiare i colori](#3-cambiare-i-colori)
4. [Cambiare le dimensioni del testo](#4-cambiare-le-dimensioni-del-testo)
5. [Cambiare le proporzioni del foglio](#5-cambiare-le-proporzioni-del-foglio)
6. [Il logo](#6-il-logo)
7. [Stampare](#7-stampare)
8. [Quando qualcosa non va](#8-quando-qualcosa-non-va)
9. [Com'è fatto](#9-comè-fatto)

---

## 1. Uso quotidiano

```bash
python3 build.py 2028       # su Windows: py build.py 2028
```

Cosa succede la prima volta che chiedi un anno nuovo:

1. lo script scrive `data/2028.toml` con le sole festività che si ricavano dal
   calendario (Pasqua, le feste nazionali fisse);
2. stampa l'elenco di ciò che resta da decidere a mano;
3. genera comunque il PDF in `out/holiday-planner-2028.pdf`.

Poi apri `data/2028.toml`, aggiungi le giornate discrezionali (chiusure, Extra
Day, Director's Grant) e **rilanci lo stesso comando**. Il file dei dati non
viene mai sovrascritto: una volta creato è tuo.

L'elenco "still to decide" è un promemoria, non un errore. Il PDF esce comunque.

### Opzioni

| opzione | cosa fa |
|---|---|
| `--data CARTELLA` | dove cercare i file degli anni (default: `data/`) |
| `--out CARTELLA`  | dove scrivere il PDF (default: `out/`) |

---

## 2. Il file dell'anno

`data/<anno>.toml`. È un file di testo: si apre con qualunque editor.

```toml
year = 2028
footnotes = []

[header]
organization = "Science and Technology Organization"
centre = "Centre for Maritime Research and Experimentation"
url = "http://www.cmre.nato.int"
background = "#6c9adb"
year_colour = "#c00000"
logo = "assets/logo.png"

[[holidays]]
date = 2028-01-06
label = "Epiphany"
kind = "H"

[[holidays]]
date = 2028-04-14
label = "Good Friday"
qualifier = "(in lieu of 1 May)"
kind = "H"
```

### I campi di `[header]`

| campo | cosa controlla |
|---|---|
| `organization` | la prima riga del titolo, in alto al centro |
| `centre` | la seconda riga del titolo |
| `url` | il testo verticale bianco lungo il bordo sinistro |
| `background` | il colore del foglio (vedi [§3](#3-cambiare-i-colori)) |
| `year_colour` | il colore dell'anno in basso a sinistra |
| `logo` | il percorso di un PNG o JPEG (vedi [§6](#6-il-logo)) |

`background` e `year_colour` valgono **solo per quell'anno**: è il posto giusto
per cambiare colore a ogni edizione senza toccare il codice. Se scrivi un
colore in un formato che non esiste, te lo dice all'avvio invece di generare un
foglio sbagliato.

### I campi di ogni `[[holidays]]`

| campo | obbligatorio | cosa fa |
|---|---|---|
| `date` | sì | la data, scritta senza virgolette: `2028-01-06` |
| `label` | sì | l'etichetta nella casella, in corsivo |
| `kind` | no (default `"H"`) | vedi la tabella qui sotto |
| `qualifier` | no | la seconda riga piccola accanto all'etichetta |

### I valori di `kind`

| valore | significato | marcatore rosso |
|---|---|---|
| `"H"` | centro chiuso, festività | sì |
| `"HC"` | chiusura concordata (*holiday closure*) | sì |
| `"grant"` | giornata concessa (*extra day*, *grant*) | sì |
| `"note"` | giorno etichettato ma **lavorativo** | no |

I primi tre sono identici sul foglio: cambiano solo il significato, così sai
cosa stai contando quando rileggi il file l'anno dopo.

### Cosa calcola da solo e cosa no

Vengono calcolate: Capodanno, Epifania, Venerdì Santo e Lunedì dell'Angelo
(Pasqua con l'algoritmo gregoriano), 25 aprile, 1 maggio, 2 giugno, Ferragosto,
Ognissanti, Immacolata, Natale e Santo Stefano.

Una festività che cade di **sabato o domenica** resta come etichetta *senza* la
`H`, e viene segnalata fra le cose da decidere: il giorno sostitutivo lo sceglie
il centro, e lo script non se lo inventa.

Restano da inserire a mano, ogni anno: le chiusure `HC`, gli *Extra Day*, i
*Director's Grant*, il patrono, e il giorno preso in luogo di una festività
caduta nel weekend.

### Aggiungere una nota a piè di pagina

```toml
footnotes = ["H = centro chiuso", "HC = chiusura concordata"]
```

Compaiono in fondo al foglio, sotto la griglia.

---

## 3. Cambiare i colori

I colori stanno **tutti** in cima a `calferie/sheet.py`, nel blocco `# Ink`.
Si scrivono in esadecimale, `"#rrggbb"`, come nei programmi di grafica.

```python
# Ink -------------------------------------------------------------------
DEFAULT_PAPER = "#6c9adb"       # "#ffffff" to print on a white sheet
BAND = "#1f3f73"
BAND_INK = "#ffffff"
CELL = "#f4f5f3"
WEEKEND = "#99d6e4"
HOLIDAY = "#c00000"
DEFAULT_YEAR_INK = "#c00000"    # the year in the corner, set per year
RULE = "#7f97b8"
INK = "#1b2a4a"
```

| costante | che cosa colora |
|---|---|
| `DEFAULT_PAPER` | lo sfondo del foglio, quando l'anno non ne indica uno suo |
| `BAND` | le fasce blu scure: giorni della settimana, nomi dei mesi, cornice |
| `BAND_INK` | il testo *dentro* quelle fasce |
| `CELL` | il fondo delle caselle dei giorni feriali |
| `WEEKEND` | il fondo delle caselle di sabato e domenica |
| `HOLIDAY` | la `H` dei giorni chiusi |
| `DEFAULT_YEAR_INK` | l'anno in basso a sinistra, quando l'anno non ne indica uno suo |
| `RULE` | le righe sottili fra una casella e l'altra |
| `INK` | i numeri dei giorni e le etichette |

### Due colori si cambiano da un anno all'altro

Lo sfondo del foglio e il colore dell'anno hanno ciascuno **due posti** dove
si impostano:

| voglio… | dove |
|---|---|
| cambiare colore a questa edizione soltanto | `background` / `year_colour` nel file dell'anno |
| cambiare il colore di partenza di tutti gli anni futuri | `DEFAULT_PAPER` / `DEFAULT_YEAR_INK` in `sheet.py` |

Il file dell'anno vince sempre sul valore di partenza. È il modo consigliato:
non tocchi il codice, e rileggendo il file dell'anno scorso vedi che colore
avevi usato.

Il titolo e l'URL si adattano da soli: su sfondo scuro restano bianchi con
un'ombra, su sfondo chiaro diventano blu scuro. Non devi fare niente.

> **Per la stampante da ufficio**, metti `background = "#ffffff"`: un A3 pieno di
> fondo colorato consuma molto toner e la maggior parte delle stampanti lascia
> comunque un margine bianco tutto intorno.

### Esempio: una versione più sobria

```python
DEFAULT_PAPER = "#ffffff"
BAND = "#333333"
WEEKEND = "#eeeeee"
HOLIDAY = "#b00000"
RULE = "#bbbbbb"
INK = "#000000"
```

---

## 4. Cambiare le dimensioni del testo

Stesso file, blocco `# Type`. Sono **punti tipografici**, come in Word.

```python
DAY_SIZE = 9.5
LABEL_SIZE = 5
LABEL_MIN_SIZE = 3.2
LABEL_LEAD = 2.3
WEEKDAY_SIZE = 6.5
MONTH_SIZE = 7
ORG_SIZE = 20
CENTRE_SIZE = 18
URL_SIZE = 15
YEAR_SIZE = 28
```

| costante | che testo |
|---|---|
| `DAY_SIZE` | i numeri dei giorni e la `H` accanto |
| `LABEL_SIZE` | le etichette nelle caselle, quando ci stanno |
| `LABEL_MIN_SIZE` | quanto può rimpicciolire un'etichetta lunga (in mm sarebbe illeggibile sotto ~3) |
| `LABEL_LEAD` | la distanza, attraverso la casella, fra l'etichetta e il suo `qualifier` |
| `WEEKDAY_SIZE` | Mon Tue Wed… nelle fasce sopra e sotto |
| `MONTH_SIZE` | i nomi dei mesi ai due lati |
| `ORG_SIZE` / `CENTRE_SIZE` | le due righe del titolo |
| `URL_SIZE` | l'URL verticale a sinistra |
| `YEAR_SIZE` | l'anno in basso a sinistra |

### Come vengono gestite le etichette lunghe

Non c'è niente da regolare a mano: se un'etichetta non entra nell'altezza della
casella, lo script prima prova a **spezzarla in due righe** al punto migliore
(così `Immaculate Conception` diventa `Immaculate` / `Conception`), e solo se
neanche questo basta la **rimpicciolisce**, mai sotto `LABEL_MIN_SIZE`. Se
invece sborda di pochissimo, la rimpicciolisce e basta, perché non si nota.

Se alzi `LABEL_SIZE` di molto vedrai più etichette spezzate: è il
comportamento voluto.

### I caratteri

Sono i font che ogni lettore PDF ha già dentro, quindi non c'è nessun file da
installare. Disponibili: `Helvetica`, `Helvetica-Bold`, `Helvetica-Oblique`,
`Times-Italic`. Si cambiano con le costanti `PLAIN`, `BOLD`, `ITALIC`, `TITLE`
subito sotto le dimensioni.

### Il carattere stretto

```python
CONDENSE = 82
```

Helvetica ha le stesse metriche di Arial, e stringerla all'82% della sua
larghezza dà un testo molto vicino ad **Arial Narrow**, che non è fra i
quattordici font incorporati nei lettori PDF. È lo stesso meccanismo che usa
PDF internamente, quindi non serve nessun file di font.

`CONDENSE = 100` lascia il carattere alla sua larghezza normale; valori più
bassi lo stringono. Il titolo in alto, che è un serif corsivo, non viene
stretto.

Stringere il testo fa anche **entrare più etichette** a corpo pieno, perché ne
riduce la lunghezza.

> Non è *esattamente* Arial Narrow: quello è un carattere disegnato a parte, non
> una compressione meccanica dell'Arial. Alle dimensioni di questo foglio la
> differenza non si distingue. Per l'Arial Narrow vero servirebbe incorporare il
> file del font nel PDF.

---

## 5. Cambiare le proporzioni del foglio

Blocco `# Sheet`, tutto in **millimetri**.

```python
PAGE_W, PAGE_H = 420, 297       # A3 orizzontale
MARGIN = 6
HEADER_H = 28
SIDE_W = 26
GAP = 2
MONTH_W = 8
WEEKDAY_H = 5.5
```

| costante | che cosa misura |
|---|---|
| `PAGE_W`, `PAGE_H` | il foglio. `297, 420` per l'A3 verticale, `297, 210` per un A4 orizzontale |
| `MARGIN` | il bordo bianco tutto intorno |
| `HEADER_H` | l'altezza della fascia con logo e titolo |
| `SIDE_W` | la striscia a sinistra che contiene l'URL e l'anno |
| `GAP` | lo spazio fra quella striscia e la griglia |
| `MONTH_W` | la larghezza delle fasce con i nomi dei mesi |
| `WEEKDAY_H` | l'altezza delle fasce con i giorni della settimana |

Le caselle si ridimensionano da sole: la griglia occupa **tutto** lo spazio che
resta. Se allarghi `SIDE_W`, le caselle si stringono; se abbassi `HEADER_H`, si
alzano. Non c'è nessun numero da ricalcolare a mano.

> Se stringi troppo, i numeri dei giorni possono toccarsi: abbassa allora
> `DAY_SIZE`. Con le misure attuali una casella è 9,8 × 20,5 mm e il numero più
> largo con la `H` occupa 7,4 mm.

---

## 6. Il logo

Si punta `header.logo` a un file **PNG o JPEG** e finisce in alto a sinistra,
nello spazio di 34 × 24 mm, ridimensionato mantenendo le proporzioni.

Viene disegnato **nudo**: nessuna cornice, nessuno sfondo e nessun margine
aggiunti, perché il logo porta già i suoi. Se le proporzioni non sono
esattamente 34:24, ai due lati si vede lo sfondo del foglio: per riempire
esattamente, esporta in proporzione **17:12** (per esempio 680 × 480 pixel).

La trasparenza viene rispettata.

Gli **SVG non si possono usare**: non essendoci un browser, il PDF vuole
un'immagine a pixel. Esporta il logo in PNG.

Finché `logo` è vuoto, al suo posto compare un riquadro con la scritta `LOGO`,
che sparisce appena ne indichi uno.

Lo spazio riservato si cambia con `LOGO_W` e `LOGO_H` in `sheet.py`.

---

## 7. Stampare

Il file è un PDF **vettoriale** di una pagina, 420 × 297 mm esatti: si ingrandisce
quanto vuoi senza sgranare, e si può portare in tipografia così com'è.

Nella finestra di stampa scegli **A3**, **orizzontale**, e **dimensione reale**
(non "adatta alla pagina", che rimpicciolirebbe tutto).

---

## 8. Quando qualcosa non va

| messaggio | cosa significa |
|---|---|
| `this needs Python 3.11 or newer` | la tua versione di Python è troppo vecchia per leggere il TOML |
| `two entries on 2027-12-25` | hai due `[[holidays]]` con la stessa data: uniscile in una sola |
| `unknown kind 'ferie'` | `kind` accetta solo `"H"`, `"HC"`, `"grant"`, `"note"` |
| `2028-01-01 does not belong to 2027` | una data appartiene a un altro anno rispetto a `year` |
| `... is neither a PNG nor a JPEG` | il logo è in un formato che non si può incorporare (tipicamente un SVG) |
| `... is 16 bits per channel` / `is interlaced` | riapri il logo in un editor e risalvalo come PNG normale |
| `... is missing, the logo box stays empty` | il percorso in `header.logo` non esiste; il foglio esce comunque |

---

## 9. Com'è fatto

Python scrive il PDF direttamente, con la sola libreria standard. Il testo usa i
quattordici font che ogni lettore PDF ha già dentro, quindi non c'è nessun file
di font da trovare o incorporare.

```
build.py                riga di comando
calferie/holidays.py    Pasqua e festività italiane
calferie/model.py       lettura e scrittura del file dell'anno (TOML)
calferie/grid.py        geometria della griglia
calferie/sheet.py       il disegno del foglio: misure, colori, corpi  <- si ritocca qui
calferie/pdf.py         il PDF: rettangoli, linee, testo, immagini
calferie/images.py      lettura di un PNG o JPEG per incorporarlo
data/<anno>.toml        le festività di quell'anno                    <- si compila qui
out/                    i PDF generati
```

### La griglia

A3 orizzontale, 420 × 297 mm. I mesi sono dodici righe, gennaio in alto; i
giorni corrono da sinistra a destra su 37 colonne, sfalsate in modo che ogni
colonna contenga sempre lo stesso giorno della settimana — così una settimana si
legge come una fetta verticale del foglio. Sabato e domenica sono in verde.

Trentasette colonne perché il caso peggiore è un mese di 31 giorni che comincia
di domenica: 6 colonne di scarto più 31 giorni.

### Test

```bash
python3 -m unittest discover -s tests
```

Il poster 2027 del CMRE è la referenza: i test verificano che le giornate chiuse
generate coincidano con quelle stampate su quel foglio. Altri controllano che
nel codice non entrino dipendenze esterne né costrutti che su Windows si
rompono.

**Conviene lanciarli dopo ogni modifica ai colori o alle misure**: se hai
scritto un colore in un formato che non esiste, o rotto qualcosa, te lo dicono
subito invece di lasciartelo scoprire dal PDF.

### Automazione

`.github/workflows/build.yml` esegue i test e allega il PDF a ogni push.
`.github/workflows/new-year.yml` il 1° novembre apre una pull request con la
bozza dell'anno successivo, da completare con le giornate discrezionali.

---

## Nota sulla collocazione

Questa cartella è autonoma e nasce per stare in una repository propria. Per
spostarla basta creare la repo vuota e copiarci dentro il contenuto della
cartella: i due workflow, che in questa posizione GitHub ignora, si attivano da
soli una volta che `.github/workflows` si trova nella radice della repository.
