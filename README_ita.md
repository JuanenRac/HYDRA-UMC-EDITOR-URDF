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

**Versione attuale:** 0.0.2 (`MAJOR.MINOR.PATCH` - vedi la sezione **Build di Produzione** più sotto per come si muove questo numero)

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
- **Dalla Gallery** - un menu a tendina "Gallery" sopra il campo URL GitHub (`hydra_editor_urdf/gallery.py`) elenca un piccolo set iniziale di repository di descrizione robot reali, verificati a mano (`universal_robot` di ROS-Industrial, `open_manipulator` di ROBOTIS). Scegliere una voce compila solo l'URL e mostra la sua descrizione - non avvia mai da sola un download, l'operatore deve comunque premere Fetch, come se avesse digitato l'URL a mano.

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
- **Massa e inerzia** - "Auto-calculate" compila massa/Ixx/Iyy/Izz dalla geometria del link selezionato usando le formule chiuse a densità uniforme di `inertia_calc.py` (esatte per Box/Cilindro/Sfera, un'approssimazione a bounding-box per Mesh); una massa inserita a mano prevale sempre sulla stima basata sulla densità, e senza una massa inserita l'app assume una densità generica dell'alluminio (2700 kg/m³) e lo segnala in una nota. "Apply" applica i campi a `Link.inertial` - lo stesso schema in due passi calcola-poi-applica di Scale/Joint sopra.

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

Traduzione completa dell'interfaccia in **inglese, spagnolo, italiano, francese, tedesco, cinese semplificato e giapponese** (`language/*.lng`), usando esattamente lo stesso meccanismo a file semplice `CHIAVE=Valore` di ogni altro strumento Python di questo ecosistema (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - non reinventato qui, poiché il meccanismo stesso non porta alcuna logica specifica del progetto. Un cambio di lingua ha effetto dopo un riavvio dell'app invece di ritradurre dal vivo ogni widget già costruito, in linea con la stessa convenzione. `language/` si trova **accanto** all'eseguibile invece di essere incorporata al suo interno tramite `--add-data` di PyInstaller, così un traduttore può modificare o aggiungere un file `.lng` senza una ricompilazione.

---

## 🎛️ Tema

La barra degli strumenti superiore dello spazio di lavoro agganciabile è un
vero pannello comandi `QToolBar`/`QLabel`/`QToolButton`, non una UI Qt
Quick/QML separata - una versione precedente incorporata tramite
QQuickWidget (stesso motore visivo di HYDRA-UMC-UPDATER e HYDRA-UMC-SUITE)
veniva renderizzata come una barra nera piena senza alcun errore in console
una volta collocata dentro il vero `QDockWidget` di questo `QMainWindow`,
quindi è stata ripristinata a widget semplici; vedi `CHANGELOG.md` per la
storia completa. I pulsanti Source, DOF, Viewport, Properties e Upload
portano soltanto ai dock esistenti; Export e About riutilizzano le azioni
esistenti, ed Export resta disabilitato finché non è stato caricato un
modello. Dopo il caricamento di un URDF (e dopo ogni modifica di proprietà
dal vivo), il suo chip di stato mostra il nome del modello caricato, il
conteggio dei DOF e il verdetto di fattibilità attuale. Non sostituisce
viewport OpenGL, editor, parser o implementazione di caricamento sul server.

Riutilizza alla lettera il file `assets/qss/industrial_dark.qss` proprio di HYDRA-UMC SUITE (stesso percorso relativo, stesso file) invece di progettare un nuovo tema visivo per uno strumento desktop gemello nello stesso ecosistema.

---

## 📂 Repository Structure

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # Punto di ingresso - QApplication, tema, avvio massimizzato, toggle fullscreen F11
├── run.bat / run.sh                # Script di comodo - attiva .venv se presente, esegue main.py, non si chiude da solo
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (con versioni fissate)
├── build_exe.bat / build_exe.sh    # Script di build per eseguibile standalone Windows/Linux (PyInstaller) - esegue prima il bump della versione
├── build-test.bat / build-test.sh  # Controllo build/compilazione senza incremento di versione
├── HYDRA-UMC_EDITOR-URDF.spec      # Spec PyInstaller usata da build_exe.bat/.sh
├── bump_version.py                 # Bump della versione in stile contachilometri, invocato da build_exe.bat/.sh prima di ogni build reale
├── bump_manifest_version.py        # Sincronizza la versione di hydra-umc.project.json con quella nativa (--sync)
├── CHANGELOG.md                    # Cronologia delle versioni
├── README.md                       # Questo file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  # <- traduzioni
├── LICENSE                         # GPL-3.0
├── assets/
│   ├── HYDRA_UMC_ICON.svg          # Marchio HYDRA-UMC animato del pannello della barra strumenti
│   └── qss/industrial_dark.qss     # Riutilizzato alla lettera da HYDRA-UMC-SUITE
├── images/
│   └── HYDRA_UMC_BANNER.svg        # Media e diagrammi
├── language/                       # english/spanish/italian/french/german/japanese/chinese.lng - si trova accanto all'exe, non incorporato
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ - unica fonte di verità, letta dalla finestra Informazioni e riscritta da bump_version.py
│   ├── app.py                      # EditorController - unico proprietario di "cosa è caricato", segnali Qt ascoltati da ogni pannello
│   ├── models.py                   # Albero oggetti URDF sviluppato in casa (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                  # Elenco iniziale di repository pubblici reali e verificati di descrizioni robot
│   ├── inertia_calc.py             # Formule chiuse del momento d'inerzia per le geometrie primitive
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
│       ├── about_dialog.py         # Finestra Informazioni reale, come About.tsx di STUDIO e about_dialog.py di SUITE
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
├── tools/
│   ├── build_test.py               # Controllo build/compilazione senza incremento di versione
│   └── ci_validate.py              # Validazione manifest/CHANGELOG/docs usata dalla CI
├── build/                           # Directory intermedia propria di PyInstaller (in gitignore)
├── dist/                            # Eseguibile standalone compilato (output di build_exe.bat/.sh, in gitignore)
└── work/                            # Spazio di lavoro temporaneo runtime per repository GitHub scaricati e modelli server prelevati (in gitignore)
```

Nota: il pannello dei comandi Qt Quick (`assets/qml/CommandDeck.qml`,
`ui/qtquick_deck.py`) è stato revertito - un `QQuickWidget` incorporato nel
vero layout `QDockWidget` di questo `QMainWindow` non veniva mai
composto correttamente (nero pieno, nessun errore in console). Il
pannello della barra strumenti oggi è composto da semplici widget
`QToolBar`/`QLabel`/`QToolButton`; vedi `CHANGELOG.md` per la storia
completa.

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

Oppure usa lo script di comodo - `run.bat` (Windows) / `run.sh` (Linux/Mac), che attiva `.venv` se presente accanto e inoltra gli argomenti a `main.py`; nessuno dei due chiude la finestra del terminale da solo con un doppio clic.

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

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Utile da conoscere, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Progetto Padre**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — il catalogo di modelli che questo editor esiste per popolare; il risultato finito viene inviato direttamente a un server STUDIO in esecuzione tramite `POST /api/models/submit`.

**Direttamente Correlati**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — possiede il vero endpoint `POST /api/models/submit` a cui questo editor invia i modelli finiti.
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — consuma i modelli URDF creati qui per guidare la propria simulazione fisica.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — consuma i modelli URDF creati qui per guidare la propria simulazione fisica.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — genera dati di addestramento a partire dai modelli creati qui.

**Anche Parte dell'Ecosistema**

*Nucleo Hardware e Piattaforma*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto condiviso JSON-Schema e il limite del gate di sicurezza contro cui ogni bridge valida i propri comandi.

*Backend e Client Principali*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre fisica del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, che coordina fino a 8 bracci-utensile via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando sciame desktop (PySide6) per più server contemporaneamente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo Android nativa con login biometrico e compagno Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" integrato sulla stessa CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — confine di coordinamento per flotte AGV/AMR tramite un vero publisher MQTT VDA 5050.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore di cella CNC di alto livello con vero accesso a stato/byte di controllo GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — confine di coordinamento per droidi con zampe/umanoidi, con un vero invio di comandi Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore di sicurezza per cella laser che legge 3 vere protezioni GPIO chiave/recinzione/interlock.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore sicuro di alto livello del flusso schede per il pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — confine di coordinamento sicuro per stampanti 3D Moonraker/Klipper, con comandi di lavoro realmente controllati.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore di sicurezza con un vero trasporto rclpy ROS 2, importato in modo lazy.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — confine di coordinamento per UAV dotati di telecamera, con un vero invio di comandi MAVLink.

*Piattaforma Strumenti URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware per la scheda fisica Universal Robot Tool Controller, 25+ profili utensile su bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop con GUI per flashare schede URTC, CAN-OTA più SWD/JTAG a chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica bus CAN in tempo reale per schede URTC, un pannello per profilo utensile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa via browser a URTC-TESTER tramite la Web Serial API, senza installazione locale.

*Nodo Vision AI (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per stadio.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica sicura di architettura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + configurazione MediaMTX con un vero confine di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vera legge di correzione Position-Based Visual Servoing, con gate di sicurezza basato sullo stato di zona a monte.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vero controllo di violazione zona e richiesta di arresto di emergenza, con obbligo di calibrazione aggiornata.

*Nodo Cognitivo AI (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay al Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione di task basata su regole e recupero semantico degli errori sui codici di errore dell'MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF solo stdlib sulla documentazione Markdown propria di questo ecosistema.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e macchina a stati di missione.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute flotta basato su gRPC con retry/backoff e rilevamento di identità non corrispondente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorso 3D basato su RRT con validazione reale di collisione ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, testata a proprietà per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vero interlock di sicurezza hardware-in-the-loop, che instrada i comandi tra simulazione e hardware reale.

*Dati e Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vero archivio di serie temporali su sqlite3 con una vera API HTTP di ingest/query.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vero rilevatore di anomalie con FFT + baseline statistica con monitoraggio della deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vero calcolo OEE/disponibilità sullo storico DATALAKE, con esportazione CSV riproducibile.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vera pipeline di ingest CAN/WebSocket verso DATALAKE, con deduplicazione per sequenza.

*Gateway Industriale*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub di integrazione che inoltra verso protocolli industriali, con un vero livello di allowlist comandi/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vero address space OPC-UA, verificato con una vera sessione client di protocollo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vero broker MQTT con autenticazione opzionale per client e ACL sui topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — veri endpoint XML `/probe` e `/current` MTConnect con output in modalità degradata.

*Strumenti Complementari e Operazioni dell'Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — pannelli Smart Summaries e Anomaly Highlighting su DATALAKE/ANOMALY-DETECTOR, con un fallback statistico onesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI di flotta con un vero contratto di exit-code stabile, un genuino client live della propria API di HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compagna WearOS con vere notifiche aptiche e un relay vocale al telefono abbinato.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware per un rack di montaggio schede con vera decodifica ID utensile e logica di pre-riscaldamento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware più un vero compagno di visione Python per una testa di ispezione termica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — strumento amministrativo desktop che scopre, clona e aggiorna ogni repository di questo ecosistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — strumento desktop Windows/Linux che costruisce un'immagine della CM5 pronta da scrivere, precaricata con le versioni più aggiornate dell'ecosistema, con configurazione di primo avvio Wi-Fi/utente/SSH in stile Raspberry Pi Imager.

---

## 📚 Documentazione e Comunità

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — la forma interna dell'editor: perché parsing, validazione di fattibilità, risoluzione delle mesh e anteprima 3D sono percorsi separati, e cosa questa app deliberatamente **non** fa (connettersi a un robot, caricare un URDF o comandare un movimento di propria iniziativa).
- **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** — il percorso di validazione non distruttivo `build-test.bat`/`.sh` rispetto a un vero pacchetto `build_exe.bat`/`.sh`, e cosa è realmente oggi il pannello comandi (`QToolBar`, non Qt Quick/QML - vedi la sezione **Tema** sopra).
- **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** — ciò che un consumatore a valle di un file URDF esportato deve validare da solo; questo progetto non fornisce alcun endpoint di rete o autorità di controllo hardware propria.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnologico e linee guida di codifica per una pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — gli standard di comportamento attesi in questa comunità.
- **[SECURITY.md](SECURITY.md)** — come segnalare una vulnerabilità, e le reali aree di attenzione sulla sicurezza di questo progetto.
- **[SUPPORT.md](SUPPORT.md)** — dove porre domande e segnalare bug.
- **[LICENSE.md](LICENSE.md)** — la licenza propria di questo progetto.

## 👤 AUTORE
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENZA

HYDRA-UMC EDITOR-URDF è (c) 2026 JuanenRac (Electro Hobby 3D). Questo avviso deve essere incluso in qualsiasi distribuzione di questo progetto o lavoro derivato.

Questo progetto consiste di codice sorgente e propria documentazione, resi disponibili sotto licenze diverse - ciascuna adatta a ciò che effettivamente copre:

1. Il codice sorgente (`hydra_editor_urdf/`, `main.py`, e qualsiasi binario compilato a partire da esso tramite `build_exe.bat`/`build_exe.sh`) è disponibile sotto la **GNU General Public License v3.0 (GPL-3.0)**. Testo completo su https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentazione (questo README e le proprie traduzioni - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) è disponibile sotto **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Testo completo su https://creativecommons.org/licenses/by-sa/4.0/.

Questa app non distribuisce alcun asset mesh di robot di terze parti proprio - a differenza di `public/models/` di HYDRA-UMC STUDIO, ogni mesh che questo editor carica proviene da qualunque repository sorgente o cartella locale verso cui l'operatore lo punta, sotto la licenza originale propria di quella sorgente. Rivedere e preservare quella licenza/attribuzione a monte prima di inviare un modello a un server STUDIO in esecuzione (nella cui convenzione propria `public/models/<slug>/ATTRIBUTION.txt` confluisce l'esportazione di questo editor) resta responsabilità propria dell'operatore - questa app non ha modo di rilevare o far rispettare automaticamente i termini di licenza di un repository sorgente.

Questo editor è lo strumento di creazione modelli per il catalogo di [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - consulta quel repository per la propria licenza lato server, a cui la licenza propria di questo repository non si estende, e viceversa.

Se costruisci su questo progetto, tieni presente la separazione delle licenze: le modifiche al codice qui dovrebbero rimanere GPL-3.0, i derivati della documentazione (questo README e le sue traduzioni) dovrebbero rimanere CC BY-SA 4.0, e qualsiasi asset mesh che passa attraverso questo editor (importato, modificato o esportato) dovrebbe rimanere sotto qualunque licenza porti il suo repository sorgente originale, con attribuzione a quella sorgente.
