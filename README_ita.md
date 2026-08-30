<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>
# 🦾 HYDRA-UMC EDITOR-URDF

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  🇮🇹 <b>Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/Licenza-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Linguaggio-Python%203.11-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Formato-URDF-red.svg" alt="URDF">
</p>


### 🖌️ Creatore/Editor grafico di URDF per il Catalogo Modelli di HYDRA-UMC-STUDIO

**Versione attuale:** 0.0.0 (`MAJOR.MINOR.PATCH` - vedi la sezione **Build di Produzione** più sotto per come si muove questo numero)

---

## 🎯 Panoramica

**HYDRA-UMC EDITOR-URDF** è lo strumento desktop che trasforma il "portare un nuovo robot nel catalogo modelli di [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)" da un'indagine manuale, robot per robot, in un flusso di lavoro grafico e ripetibile. In passato, ogni modello di robot reale nel catalogo di STUDIO ci è arrivato allo stesso modo: trovare un repository di descrizione su GitHub, capire come si risolvono i suoi riferimenti alle mesh, contare i gradi di libertà nella sua catena cinematica, verificare se STUDIO è effettivamente in grado di pilotarne così tanti, e posizionare a mano il risultato in `public/models/`. Questa app automatizza l'intero processo - preleva i file sorgente da un URL GitHub o da una cartella locale già scaricata, risolve ogni riferimento `<mesh filename="...">` (URI `package://` incluse) contro i file reali su disco, valida il conteggio dei DOF della catena rispetto a ciò che la cinematica di STUDIO supporta oggi, modifica colore/scala/limiti di giunto/tipo di giunto con un'anteprima 3D in tempo reale, e invia il risultato finito direttamente a un server STUDIO in esecuzione.

Costruito con **Python** e **PySide6/Qt6**, usando gli stessi pattern architetturali già validati nell'altro strumento desktop di questo ecosistema, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE): uno spazio di lavoro agganciabile in stile Photoshop/Fusion-360 (`QDockWidget`), un viewport 3D OpenGL scritto a mano (`QOpenGLWidget` + shader GLSL 3.3 core-profile, nessun percorso legacy `glBegin`/`glEnd`), e un unico oggetto controllore centrale che possiede lo stato e a cui ogni pannello dell'interfaccia è in ascolto tramite segnali Qt. Riutilizzare qui questo pattern - invece di esplorare un nuovo stack UI/rendering per uno strumento gemello nello stesso ecosistema - è una scelta deliberata, non una svista.

**Nota di onestà, in linea con la convenzione documentale già seguita nel resto di questo ecosistema:** questa app non espande le macro [xacro](http://wiki.ros.org/xacro) e non carica mesh COLLADA (`.dae`). Entrambe sono limitazioni nominate ed esplicite (un messaggio di errore chiaro, non un'analisi silenziosamente errata o un link mancante nel viewport) piuttosto che un tentativo implementato a metà - vedi le sezioni **URDF Parsing** e **Mesh Loading** più sotto per il motivo, e per cosa servirebbe un lavoro aggiuntivo consistente per un supporto reale di entrambe.

---

## 📥 Caricamento delle Sorgenti - GitHub o Cartella Locale

Due modi per indirizzare l'app verso i file sorgente di un robot, entrambi confluiscono nello stesso percorso di importazione:

- **Da un URL GitHub** - accetta un URL completo `https://github.com/owner/repo` (con o senza `/tree/<branch>`), uno stile SSH `git@github.com:owner/repo.git`, o la forma breve nuda `owner/repo`. Deliberatamente **non** invoca `git clone` come sottoprocesso, il che renderebbe un'installazione di `git` una dipendenza runtime obbligatoria sia su Windows che su Linux per qualcosa che un semplice download HTTPS già fa: GitHub serve uno zipball di qualsiasi branch/tag/commit da `codeload.github.com` senza bisogno di autenticazione per un repository pubblico, quindi questo usa esclusivamente `urllib.request` + `zipfile` della libreria standard, nient'altro. Sono supportati solo i repository pubblici - non c'è gestione di token/credenziali, e lo zipball di un repository privato restituisce 404 come uno inesistente.
- **Da una cartella locale** - per un repository già scaricato a mano, o una copia di lavoro che l'operatore sta modificando attivamente al di fuori di questa app.

In entrambi i casi, l'app trova poi ricorsivamente ogni file `*.urdf`/`*.xacro` sotto la cartella scelta, li elenca tutti (un vero repository di descrizione robot spesso ne distribuisce più di uno - un braccio nudo più una variante "con pinza" è un abbinamento comune), e seleziona automaticamente il più grande per dimensione del file come default ragionevole per "quello principale" - passare a un candidato diverso in seguito è un doppio clic nel pannello Source, non un nuovo recupero.

La **risoluzione dei riferimenti alle mesh** è il vero lavoro poco brillante che ogni sessione manuale passata di porting di un robot in questo ecosistema ha fatto a mano: un `<mesh filename="package://some_pkg/meshes/link1.stl"/>` di un URDF non è praticamente mai un percorso apribile direttamente una volta che il file si trova in una semplice cartella scaricata invece che in un workspace ROS attivo, dove `package://` si risolve tramite l'indice dei pacchetti ROS. Il resolver prova, in ordine: (1) il riferimento come percorso relativo alla cartella dello stesso URDF, (2) lo stesso riferimento con un segmento iniziale in stile `package://` col nome del pacchetto rimosso, (3) come percorso assoluto se già lo è, e (4) per solo basename ovunque sotto la cartella sorgente - che è ciò che effettivamente gestisce una vera URI `package://`, dato che lo schema e il nome del pacchetto sono privi di significato fuori da un workspace ROS attivo, ma il nome del file della mesh resta comunque individuabile.

---

## ✅ Validazione di Fattibilità DOF

La versione automatizzata dello stesso giudizio che le sessioni passate proprie di questo ecosistema facevano a mano per ogni robot aggiunto al catalogo di STUDIO: **la cinematica propria di STUDIO supporta oggi catene seriali a 3, 4, 5 e 6 DOF** (il suo `RobotState.joints` è una mappa fissa `j1..j6`) - una manciata di bracci candidati reali, con licenza chiara, ricercati in passato si sono rivelati a 7, 8 o 9 DOF e sono stati scartati esattamente per questo motivo, non ipoteticamente. A ogni importazione (e dopo ogni modifica dal vivo che potrebbe cambiare il conteggio - ridefinire il tipo di un giunto, per esempio), l'app percorre il grafo reale dei giunti genitore/figlio e riporta:

- **Conteggio DOF** - solo i giunti `revolute`/`continuous`/`prismatic` contano come un vero grado di libertà controllabile; `fixed` non ne contribuisce nessuno.
- **Tipi di giunto non supportati** - un singolo giunto `floating` o `planar` in qualsiasi punto della catena rende l'intero robot non fattibile indipendentemente dal conteggio DOF, poiché il modello di giunto di STUDIO non ha una rappresentazione per nessuno dei due.
- **Integrità dell'albero** - è richiesto esattamente un link radice (un vero albero, non una foresta o un ciclo); qualsiasi link non raggiungibile da quella radice tramite una catena di giunti viene segnalato come disconnesso, e qualsiasi link non referenziato da alcun giunto come orfano.
- **`<limit>` mancante** - richiesto dalla specifica URDF per qualsiasi giunto che non sia `continuous`; segnalato per ogni singolo giunto se assente.

Il verdetto e ogni motivazione dietro di esso vengono renderizzati dal vivo nel pannello DOF, e il pannello Upload rifiuta di inviare a un server un robot non fattibile.

---

## 🎨 Modifica dal Vivo con una vera Anteprima 3D

Il pannello Properties modifica qualsiasi link sia selezionato nell'albero dei link del pannello Viewport, e ogni modifica altera il modello caricato sul posto e ri-valida/ri-renderizza tramite un unico segnale (`EditorController.notify_tree_changed`) - nessun pannello deve sapere come il viewport o il report DOF reagiscono alla propria modifica:

- **Ricolorazione** - il materiale visivo di un link, scelto tramite una finestra di dialogo colore standard. Un materiale condiviso per nome tra più link (una dichiarazione `<material name="...">` di primo livello di un vero URDF, referenziata da più di un `<visual>`) ricolora insieme tutti i link che lo condividono, coerentemente con ciò che quella sintassi di materiale condiviso significa realmente nella specifica.
- **Riscalatura** - un fattore di scala per asse (X/Y/Z) sulla trasformazione `<mesh scale="...">` propria della geometria mesh, non una riscrittura distruttiva dei dati dei triangoli della mesh stessa - la stessa modifica riapplicata in seguito riparte sempre dalla mesh originale, non modificata.
- **Ricambio tipo e nuovi limiti di un giunto** - cambia il tipo di un giunto (uno qualsiasi dei 6 definiti dalla specifica URDF) e il suo limite inferiore/superiore, con il verdetto del pannello DOF che si aggiorna immediatamente, poiché un cambio di tipo può modificare il conteggio DOF o introdurre un tipo non supportato.

Il pannello **Viewport** ospita la vera vista 3D OpenGL più uno slider di jog per ogni giunto mobile, così l'operatore può visualizzare in anteprima l'URDF che si muove nel suo vero range prima ancora di toccare STUDIO. La cinematica diretta (`render/kinematics.py`) è generica rispetto a qualsiasi albero appena importato - a differenza del modulo di cinematica proprio di HYDRA-UMC SUITE, che pilota un registro fisso di poche decine di modelli di robot noti e verificati a mano, questa app deve posare un URDF arbitrario, mai visto prima, quindi compone il vero `<origin>`/`<axis>` di ogni giunto (formula di rotazione di Rodrigues per un asse revolute arbitrario, non solo la scorciatoia delle direzioni cardinali su cui un registro fisso potrebbe basarsi) percorrendo il vero grafo genitore/figlio.

**Z-up, non Y-up** - l'unica divergenza deliberata dalla convenzione di viewport propria di HYDRA-UMC SUITE: URDF è di per sé un formato Z-up (la gravità è `-Z`, ogni `<origin>`/`<axis>` in un file sorgente è scritto assumendolo), e il compito di questa app è mostrare e modificare fedelmente un URDF nella sua stessa convenzione, non riorientarlo in qualunque cosa un visualizzatore a valle (la scena Three.js di STUDIO, la scena OpenGL propria di SUITE) preferisca.

---

## 🗂️ Caricamento delle Mesh

Sia `.stl` (tramite `numpy-stl`) che `.obj` (un piccolo loader Wavefront scritto a mano - solo `v`/`vn`/`f`, facce n-gon triangolate a ventaglio) sono di prima classe. **COLLADA (`.dae`) non è supportato** - è un formato di scene-graph XML molto più grande (animazione scheletrica, sistemi di coordinate multipli, materiali/texture incorporati) che richiederebbe un vero parser per essere gestito onestamente invece che un tentativo di indovinare quali tag usi un `.dae` "semplice"; un link che ne referenzia uno riceve un errore chiaro e nominato invece di scomparire silenziosamente dal viewport o far crashare l'intera importazione. Ogni mesh caricata riceve anche la stessa protezione difensiva millimetri-contro-metri applicata dal proprio `useRealScaleSTL()` di HYDRA-UMC STUDIO e dal proprio loader di mesh di HYDRA-UMC SUITE: un link più grande di 5 metri reali su qualsiasi asse è molto più probabilmente un'esportazione in scala millimetrica priva di metadati sull'unità di misura che una vera parte gigante di robot, e viene riscalato automaticamente per 0.001.

---

## 📜 Parsing ed Esportazione URDF

XML semplice tramite `xml.etree.ElementTree` della libreria standard - nessuna dipendenza da `lxml` necessaria per un formato così semplice. Il modello in memoria (`hydra_editor_urdf/models.py`) è deliberatamente un albero di dataclass semplice, mutabile e sviluppato in casa, piuttosto che un wrapper attorno a una libreria Python URDF già esistente come `urdfpy` o `yourdfpy`: questa app ha bisogno di *modificare* l'albero interattivamente e ri-renderizzare ogni modifica dal vivo, cosa per cui una libreria di parsing pensata prevalentemente per la sola lettura non è adatta, e possedere il modello per intero lo mantiene piccolo, ispezionabile e libero dal ritmo di rilascio di una dipendenza di terze parti. Nomi dei campi e default seguono da vicino il vero [schema XML di URDF](http://wiki.ros.org/urdf/XML), così la coppia parser/writer resta una mappatura XML↔oggetto sottile e ovvia.

**xacro non viene espanso.** [xacro](http://wiki.ros.org/xacro) è un preprocessore di macro Python/XML con un proprio pacchetto ROS e una propria catena di dipendenze, e un vero file xacro è risolvibile in modo affidabile solo dentro lo stesso ambiente di pacchetto ROS contro cui è stato scritto (argomenti di macro, include in stile `$(find pkg)`, ecc.) - qualcosa che questa app non ha modo di riprodurre onestamente. Un file che usa tag `<xacro:...>` o dichiara il namespace xacro riceve un errore chiaro che spiega la limitazione e indirizza allo strumento a riga di comando `xacro` di ROS per preprocessarlo prima, invece di un'analisi silenziosamente errata.

L'esportazione (`urdf/writer.py`) riserializza da zero l'albero corrente in memoria invece di applicare patch al testo XML sorgente originale, così ogni modifica dal vivo - indipendentemente da quale pannello l'abbia fatta - si riflette esattamente una volta, attraverso un unico percorso di codice, sia nell'azione di menu "Export URDF" sia nel payload inviato a un server STUDIO.

---

## 🖥️ Spazio di Lavoro Agganciabile

Veri pannelli `QDockWidget` - trascina per rendere flottante, trascina indietro per agganciare, unisci in schede, dividi lo spazio di lavoro - lo stesso meccanismo e la stessa logica già applicati dalla finestra principale propria di HYDRA-UMC SUITE: il sistema di docking proprio di Qt fa già esattamente ciò di cui ha bisogno uno spazio di lavoro in stile Photoshop/Fusion-360, e uno scritto a mano lo reinventerebbe soltanto con più bug. Cinque pannelli, disposti con un layout predefinito sensato completamente riorganizzabile in seguito:

- **Source** - inserimento URL GitHub / cartella locale, elenco dei file `.urdf` trovati.
- **DOF** - il verdetto di fattibilità e ogni motivazione dietro di esso.
- **Viewport** - la vista 3D dal vivo, l'albero dei link e gli slider di jog.
- **Properties** - ricolorazione / riscalatura / ricambio-tipo-e-nuovi-limiti per il link selezionato.
- **Upload** - connessione a un server STUDIO, push o pull.

---

## ☁️ Andata e Ritorno con il Server

Comunica con il contratto di invio modelli proprio di HYDRA-UMC-SERVER (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` nel `server.ts` proprio di quel progetto, protetto dietro il proprio interruttore **Config > Models > "Accept model submissions"**) usando `urllib.request` della libreria standard - un'altra chiamata HTTP in più non giustificava l'aggiunta di `httpx`/`requests` per un progetto che ha bisogno solo di 4 endpoint, non di una connessione persistente. Ogni chiamata viene eseguita su un `QThread` in background, così un server lento o irraggiungibile non blocca mai l'interfaccia. Questo contratto viveva un tempo all'interno del processo stesso di HYDRA-UMC-STUDIO, prima che quel progetto si dividesse in un frontend puro (STUDIO) più un backend headless separato (HYDRA-UMC-SERVER, vedi **Progetti Correlati** più sotto) - questa app non fissa nessuno dei due nomi nel codice, l'operatore imposta semplicemente i campi host/porta del pannello **Upload** su dove sta girando davvero il backend.

- **Login** - `POST /api/login`; solo un token con ruolo `admin` può effettivamente raggiungere `POST /api/models/submit` lato server, quindi questa app è realmente utilizzabile solo con un account admin, come ogni altra funzionalità di STUDIO riservata agli admin.
- **Push** - riserializza il robot corrente in XML URDF ed encoda in base64 ogni file mesh referenziato dai suoi visual (risolto tramite lo stesso resolver di mesh costruito al momento dell'importazione) in linea nel corpo della richiesta, etichettato con la categoria scelta dall'operatore (rispecchiando le categorie proprie di Config > UI > Module Visibility di STUDIO: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - un URDF non ha un proprio campo che dica a quale di queste appartenga). Una collisione di nome torna indietro come la risposta 409 propria del server; l'operatore decide se reinviare con **Overwrite** spuntato o rinominare, questa app non indovina mai.
- **Pull** - scarica l'URDF + le mesh di un modello già inviato di nuovo in una cartella di lavoro locale e le carica direttamente nell'editor - la metà del ciclo "estrai, modifica, reinvia" proprio dello scopo di questa app, che permette di ritoccare una voce del catalogo esistente senza ripartire dal suo repository sorgente originale.

---

## 🌐 Interfaccia Multilingua

Traduzione completa dell'interfaccia in **inglese, spagnolo, italiano, francese e tedesco** (`language/*.lng`), usando esattamente lo stesso meccanismo a file semplice `CHIAVE=Valore` di ogni altro strumento Python di questo ecosistema (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - non reinventato qui, poiché il meccanismo stesso non porta alcuna logica specifica del progetto. Un cambio di lingua ha effetto dopo un riavvio dell'app invece di ritradurre dal vivo ogni widget già costruito, in linea con la stessa convenzione. `language/` si trova **accanto** all'eseguibile invece di essere incorporata al suo interno tramite `--add-data` di PyInstaller, così un traduttore può modificare o aggiungere un file `.lng` senza una ricompilazione.

---

## 🎛️ Tema

Riutilizza alla lettera il file `assets/qss/industrial_dark.qss` proprio di HYDRA-UMC SUITE (stesso percorso relativo, stesso file) invece di progettare un nuovo tema visivo per uno strumento desktop gemello nello stesso ecosistema.

---

## 📂 Repository Structure

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # Punto di ingresso - QApplication, tema, avvio massimizzato, toggle fullscreen F11
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (con versioni fissate)
├── build_exe.bat / build_exe.sh    # Script di build per eseguibile standalone Windows/Linux (PyInstaller) - esegue prima il bump della versione
├── bump_version.py                 # Bump della versione in stile contachilometri, invocato da build_exe.bat/.sh prima di ogni build reale
├── CHANGELOG.md                    # Cronologia delle versioni
├── README.md                       # Questo file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  # <- traduzioni
├── LICENSE                         # GPL-3.0
├── assets/
│   └── qss/industrial_dark.qss     # Riutilizzato alla lettera da HYDRA-UMC-SUITE
├── language/                       # english/spanish/italian/french/german.lng - si trova accanto all'exe, non incorporato
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ - unica fonte di verità, letta dalla finestra Informazioni e riscritta da bump_version.py
│   ├── app.py                      # EditorController - unico proprietario di "cosa è caricato", segnali Qt ascoltati da ogni pannello
│   ├── models.py                   # Albero oggetti URDF sviluppato in casa (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── i18n.py                     # Loader di language/*.lng, persistenza configurazione - portato dal proprio i18n.py di HYDRA-UMC-SUITE
│   ├── urdf/
│   │   ├── parser.py               # XML URDF -> albero di models.py (ElementTree, xacro rilevato e rifiutato con un errore chiaro)
│   │   ├── writer.py                # Albero di models.py -> stringa XML URDF (esportazione + payload di upload al server)
│   │   └── dof.py                  # Conteggio DOF, validazione di fattibilità contro il tetto di 3-6 DOF di STUDIO
│   ├── render/
│   │   ├── mesh.py                 # Caricamento STL/OBJ, generazione primitive box/cylinder/sphere, protezione mm-contro-m
│   │   ├── kinematics.py           # Cinematica diretta generica su un albero importato arbitrario (Z-up, convenzione propria di URDF)
│   │   └── viewport.py             # QOpenGLWidget - shader core GLSL 3.3, camera orbitale, buffer GPU per link
│   ├── source/
│   │   ├── scan.py                 # Trova i file .urdf/.xacro, costruisce il resolver di nomi file mesh consapevole di package://
│   │   ├── github_fetcher.py       # Download + estrazione zipball GitHub (urllib + zipfile, nessuna dipendenza da git)
│   │   └── local_folder.py         # Validazione cartella locale - la controparte snella di github_fetcher.py
│   ├── server/
│   │   └── client.py               # StudioClient - login/list_models/push_model/pull_model contro il server.ts di HYDRA-UMC-SERVER (il backend di STUDIO prima che i due repository si separassero)
│   └── ui/
│       ├── main_window.py          # QMainWindow - spazio di lavoro agganciabile, barra dei menu, cambio lingua, barra di stato
│       ├── theme.py                 # Applica assets/qss/industrial_dark.qss
│       └── panels/
│           ├── source_panel.py     # Inserimento URL GitHub / cartella locale, elenco URDF trovati
│           ├── dof_panel.py        # Visualizzazione del verdetto di fattibilità
│           ├── viewport_panel.py   # Host del viewport 3D, albero dei link, slider di jog
│           ├── properties_panel.py # Editor di ricolorazione / riscalatura / ricambio-tipo-e-nuovi-limiti
│           └── upload_panel.py     # Connessione/push/pull al server
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   └── INTEGRATION_CONTRACT.md
└── work/                            # Spazio di lavoro temporaneo runtime per repository GitHub scaricati e modelli server prelevati (in gitignore)
```

---

## 🛠️ Ambiente di Sviluppo

### Requisiti
- [Python](https://www.python.org/) 3.11 o superiore
- pip

### Installazione

```bash
pip install -r requirements.txt
```

Questo installa l'insieme di dipendenze con versioni fissate: **PySide6** (interfaccia Qt6), **PyOpenGL** (rendering del viewport 3D), **numpy** / **numpy-stl** (matematica delle mesh e caricamento STL). Non è richiesta alcuna installazione di `git` - il percorso di caricamento sorgenti da GitHub scarica un semplice zipball via HTTPS.

### Modalità di Sviluppo

```bash
python main.py
```

Si avvia massimizzata (non un vero fullscreen a livello di sistema operativo, quindi la barra del titolo e i controlli nativi della finestra restano visibili) - premi **F11** per attivare/disattivare il vero fullscreen senza bordi.

### Build di Produzione

Compila un eseguibile standalone (non serve alcuna installazione di Python per eseguirlo) tramite PyInstaller:

- **Windows:** esegui `build_exe.bat` → produce `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux:** esegui `./build_exe.sh` (`chmod +x build_exe.sh` una volta, prima) → produce `dist/HYDRA-UMC_EDITOR-URDF`

Entrambi gli script creano/attivano il proprio `.venv`, installano `requirements.txt` più `pyinstaller`, ripuliscono ogni precedente `build`/`dist`, **eseguono il bump del numero di versione**, compilano e infine copiano `README.md`, `LICENSE`, e l'intera cartella `language/` accanto al binario risultante (`language/` deliberatamente **non** viene incorporata dentro l'eseguibile tramite `--add-data`, così un file `.lng` può essere modificato o aggiunto in seguito senza ricompilazione).

**Versionamento:** la versione dell'app (`hydra_editor_urdf/__version__`, mostrata nella finestra di dialogo Guida → Informazioni) segue `MAJOR.MINOR.PATCH`. Ogni esecuzione reale di `build_exe.bat`/`build_exe.sh` invoca prima `bump_version.py`, che applica un bump in stile contachilometri: `PATCH` sale di 1; quando `PATCH` supererebbe 9 torna a 0 e sale `MINOR` invece (es. `0.0.9` → `0.1.0`). `MAJOR` non viene mai toccato automaticamente - resta una decisione deliberata e manuale. Vedi `CHANGELOG.md` per la cronologia delle versioni.

Se preferisci eseguire i passi equivalenti a mano invece che tramite lo script - utile per adattare la build a una piattaforma non coperta dagli script, o per fare debug di un flag di PyInstaller - il processo manuale è:

```bash
# 1. Crea e attiva un ambiente virtuale
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. Installa le dipendenze + PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# 3. Individua la cartella di installazione propria di PySide6 (i suoi plugin Qt vivono sotto di essa)
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> $PYSIDE_DIR qui sotto

# 4. Compila - solo 4 sottocartelle di plugin Qt vengono incluse esplicitamente (platforms/
#    styles/imageformats/iconengines), NON --collect-all PySide6, che altrimenti
#    trascinerebbe dentro Qt6WebEngineCore.dll e altri pezzi da centinaia di MB
#    che questa app non usa mai. L'analizzatore di dipendenze proprio di PyInstaller trova
#    le vere DLL Qt6Core/Gui/Widgets/OpenGL seguendo il vero grafo di import di main.py -
#    solo le cartelle dei plugin devono essere aggiunte a mano.
#
#    Windows (i plugin vivono direttamente sotto PySide6/plugins/):
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux (i plugin vivono invece sotto PySide6/Qt/plugins/ - un layout
#    diverso rispetto a Windows, confermato leggendo l'hook runtime proprio di PyInstaller
#    pyi_rth_pyside6.py):
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. Copia i file che devono stare ACCANTO al binario, non al suo interno
cp README.md LICENSE dist/
cp -r language dist/language
```

Su Linux, eseguire il binario compilato richiede la presenza del runtime OpenGL proprio del sistema (`libGL.so.1` - es. `libgl1` su Debian/Ubuntu, `mesa-libGL` su Fedora, `libglvnd` su Arch) più `libxkbcommon-x11-0`/`xcb-util-cursor` per il plugin di piattaforma XCB proprio di Qt; `build_exe.sh` controlla la presenza di `libGL.so.1` in anticipo e stampa il comando di installazione corretto per ogni distro se manca, invece di fallire nel profondo di un'esecuzione di PyInstaller.

---

## 🔗 Progetti Correlati

Questo progetto fa parte di un ecosistema robotico più ampio dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerlo, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository:

**Piattaforma HYDRA-UMC** — la cella micro-fabbrica multi-robot
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre stessa: host Raspberry Pi CM5 + co-processore real-time dual-core STM32H745, che orchestra fino a 8 bracci robotici distribuiti via CAN-OTA/SPI-OTA. Hardware + firmware propri, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo basata sul web per HYDRA-UMC: visualizzazione 3D multi-robot, registrazione cinematica/traiettorie, flashing e test CAN-OTA per l'intera piattaforma. React + Vite + Three.js.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il backend headless (Node/Express/WebSocket) che in precedenza era incluso nel processo stesso di HYDRA-UMC-STUDIO. Possiede l'API REST/WS di controllo robot (incluso `POST /api/models/submit`, l'endpoint a cui questo editor invia i modelli finiti), la persistenza di settings.json, l'autenticazione JWT e il discovery mDNS. HYDRA-UMC-STUDIO è ora un client frontend statico puro che comunica con esso in rete.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo Android per HYDRA-UMC via Wi-Fi/Bluetooth. App reale e funzionante - set completo di funzionalità di controllo remoto, autenticazione JWT, archiviazione cifrata delle credenziali.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo iOS/iPadOS per HYDRA-UMC via Wi-Fi, sviluppata in Flutter (cross-platform, verificabile su Windows senza un Mac; il packaging finale `.ipa` richiede comunque Xcode). App reale e funzionante - stesso set di funzionalità dell'app Android.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando desktop (Python/PySide6) per sciami di robot: discovery di rete multi-controller, sincronizzazione bidirezionale dal vivo, vero viewport 3D del robot, spazio di lavoro agganciabile in stile Photoshop. Reale e funzionante, non un segnaposto.
- **HYDRA-UMC-EDITOR-URDF** *(questo repository)* — creatore/editor grafico desktop (Python/PySide6) di URDF per il catalogo modelli proprio di HYDRA-UMC-STUDIO: preleva file sorgente da GitHub o da una cartella locale, valida la fattibilità DOF, modifica colore/scala/cinematica con un'anteprima 3D dal vivo, e invia il risultato finito a un server STUDIO in esecuzione. Reale e funzionante, non un segnaposto.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — UI touch nativa in Flutter per il touchscreen DSI da 5"/7" proprio di HYDRA-UMC (1280×720, stessa risoluzione in entrambe le dimensioni) sul Compute Module 5, che controlla questo stesso server direttamente dalla scheda. Scaffold reale e funzionante con tutte le 6 schermate del catalogo (dashboard, controllo manuale, camera, vista 3D semplificata, metriche di sistema, login) collegate al server live; la build reale del target Linux non è ancora stata eseguita su hardware reale (ambiente di lavoro finora solo Windows - vedere il README di quel progetto).

**Piattaforma URTC** — il controller della testa utensile che ogni braccio robotico HYDRA-UMC porta con sé
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: controller della testa utensile su bus CAN basato su STM32F303, 25 profili utensile completamente implementati, aggiornamento firmware CAN-OTA.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop di flashing CAN-OTA + SWD/JTAG a chip completo per le schede URTC (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica bus CAN dal vivo per le schede URTC, un pannello per ogni profilo utensile (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basata su browser ai 2 strumenti desktop sopra (Web Serial API + SLCAN), non richiede installazione locale.

**Direttamente correlati a questo repository**
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — utilizza i modelli URDF creati qui per alimentare la propria simulazione fisica.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — utilizza i modelli URDF creati qui per alimentare la propria simulazione fisica.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — genera dati di addestramento a partire dai modelli creati qui.

**Resto dell'ecosistema** — questo progetto si colloca all'interno di un insieme più ampio di molti progetti, raggruppati per area:
- 👁️ **Vision AI Node (Hailo-8):** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE), [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER), [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF), [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES), [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Cognitive AI Node (Hailo-10):** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE), [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE), [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI), [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER), [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestration & Swarm:** [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR), [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC), [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D), [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER), [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Digital Twin & Simulation:** [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- 📊 **Data & Analytics:** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE), [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR), [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR), [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Industrial Gateway:** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL), [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER), [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER), [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Complementary Tools:** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH), [HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI), [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 Author

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 Note su Licenza e Copyright

HYDRA-UMC EDITOR-URDF è (c) 2026 JuanenRac (Electro Hobby 3D). Questo avviso deve essere incluso in qualsiasi distribuzione di questo progetto o lavoro derivato.

Questo progetto consiste di codice sorgente e propria documentazione, resi disponibili sotto licenze diverse - ciascuna adatta a ciò che effettivamente copre:

1. Il codice sorgente (`hydra_editor_urdf/`, `main.py`, e qualsiasi binario compilato a partire da esso tramite `build_exe.bat`/`build_exe.sh`) è disponibile sotto la **GNU General Public License v3.0 (GPL-3.0)**. Testo completo su https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentazione (questo README e le proprie traduzioni - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) è disponibile sotto **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Testo completo su https://creativecommons.org/licenses/by-sa/4.0/.

Questa app non distribuisce alcun asset mesh di robot di terze parti proprio - a differenza di `public/models/` di HYDRA-UMC STUDIO, ogni mesh che questo editor carica proviene da qualunque repository sorgente o cartella locale verso cui l'operatore lo punta, sotto la licenza originale propria di quella sorgente. Rivedere e preservare quella licenza/attribuzione a monte prima di inviare un modello a un server STUDIO in esecuzione (nella cui convenzione propria `public/models/<slug>/ATTRIBUTION.txt` confluisce l'esportazione di questo editor) resta responsabilità propria dell'operatore - questa app non ha modo di rilevare o far rispettare automaticamente i termini di licenza di un repository sorgente.

Questo editor è lo strumento di creazione modelli per il catalogo di [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - consulta quel repository per la propria licenza lato server, a cui la licenza propria di questo repository non si estende, e viceversa.

Se costruisci su questo progetto, tieni presente la separazione delle licenze: le modifiche al codice qui dovrebbero rimanere GPL-3.0, i derivati della documentazione (questo README e le sue traduzioni) dovrebbero rimanere CC BY-SA 4.0, e qualsiasi asset mesh che passa attraverso questo editor (importato, modificato o esportato) dovrebbe rimanere sotto qualunque licenza porti il suo repository sorgente originale, con attribuzione a quella sorgente.

## 🛠️ BUILD & RUN

Usa il controllo di compilazione senza versionamento prima di una compilazione di rilascio:

| Azione | Windows | Linux / macOS |
|---|---|---|
| Controllo di compilazione (senza modificare versione o CHANGELOG) | `build-test.bat` | `./build-test.sh` |
| Esecuzione / sviluppo (se disponibile) | `run*.bat` o `dev*.bat` | `./run*.sh` o `./dev*.sh` |

`build-test.bat` e `build-test.sh` compilano o convalidano lo stack del progetto senza incrementare `hydra-umc.project.json` né modificare `CHANGELOG.md`. Possono creare solo i normali output del compilatore. Gli script esistenti `build*.bat`, `build*.sh`, `run*` e `dev*` mantengono il comportamento specifico di versione o esecuzione; usali quando tale comportamento è necessario.