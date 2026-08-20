# 🦾 HYDRA-UMC EDITOR-URDF

### 🖌️ Grafischer URDF-Ersteller/-Editor für den Modellkatalog von HYDRA-UMC-STUDIO

---

## 🎯 Überblick

**HYDRA-UMC EDITOR-URDF** ist das Desktop-Tool, das aus dem „Portieren eines neuen Roboters in den Modellkatalog von [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)" von einer manuellen, pro-Roboter durchgeführten Untersuchung einen wiederholbaren, grafischen Arbeitsablauf macht. Jedes reale Robotermodell im Katalog von STUDIO ist in der Vergangenheit auf demselben Weg dorthin gelangt: ein Beschreibungs-Repository auf GitHub finden, herausfinden, wie sich dessen Mesh-Referenzen auflösen, die Freiheitsgrade in seiner kinematischen Kette zählen, prüfen, ob STUDIO tatsächlich so viele ansteuern kann, und das Ergebnis von Hand nach `public/models/` legen. Diese App automatisiert genau diesen Durchlauf - sie zieht die Quelldateien von einer GitHub-URL oder aus einem bereits heruntergeladenen lokalen Ordner, löst jede `<mesh filename="...">`-Referenz auf (einschließlich `package://`-URIs) gegen die realen Dateien auf der Festplatte, validiert die Anzahl der Freiheitsgrade der Kette gegen das, was die Kinematik von STUDIO heute unterstützt, bearbeitet Farbe/Skalierung/Gelenkgrenzen/Gelenktyp mit einer Live-3D-Vorschau, und überträgt das fertige Ergebnis direkt an einen laufenden STUDIO-Server.

Erstellt mit **Python** und **PySide6/Qt6**, unter Verwendung derselben architektonischen Muster, die bereits im anderen Desktop-Tool dieses Ökosystems, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE), validiert wurden: ein andockbarer Arbeitsbereich im Stil von Photoshop/Fusion-360 (`QDockWidget`), ein handgeschriebenes OpenGL-3D-Viewport (`QOpenGLWidget` + GLSL-3.3-Core-Profile-Shader, kein `glBegin`/`glEnd`-Legacy-Pfad), sowie ein zentrales Controller-Objekt, das den Zustand besitzt und dem jedes UI-Panel über Qt-Signale zuhört. Dieses Muster hier wiederzuverwenden - anstatt einen neuen UI/Render-Stack für ein Schwester-Tool im selben Ökosystem zu erkunden - ist eine bewusste Entscheidung, kein Versehen.

**Ehrlichkeitshinweis, im Einklang mit der Dokumentationskonvention des übrigen Ökosystems:** Diese App expandiert keine [xacro](http://wiki.ros.org/xacro)-Makros und lädt keine COLLADA-Meshes (`.dae`). Beides sind benannte, explizite Einschränkungen (eine klare Fehlermeldung, kein stillschweigendes Fehlparsen und keine fehlende Verbindung im Viewport) statt eines halbfertigen Versuchs - siehe die Abschnitte **URDF-Parsing** und **Mesh-Laden** weiter unten für die Gründe, sowie `SONNET/HYDRA-UMC-EDITOR-URDF/mejoras_futuras.txt` in der privaten Nachverfolgung dieses Ökosystems dafür, was echte Unterstützung für eines von beidem erfordern würde.

---

## 📥 Quellen laden - GitHub oder lokaler Ordner

Zwei Wege, um die App auf die Quelldateien eines Roboters zeigen zu lassen, die beide im selben Importpfad enden:

- **Von einer GitHub-URL** - akzeptiert eine vollständige `https://github.com/owner/repo`-URL (mit oder ohne `/tree/<branch>`), eine SSH-artige `git@github.com:owner/repo.git`, oder die bloße `owner/repo`-Kurzform. Führt bewusst **keinen** `git clone` über die Shell aus, was auf Windows und Linux gleichermaßen eine `git`-Installation zu einer harten Laufzeitabhängigkeit für etwas machen würde, das ein einfacher HTTPS-Download bereits leistet: GitHub liefert eine Zip-Datei jedes Branches/Tags/Commits von `codeload.github.com` aus, ohne dass für ein öffentliches Repository eine Authentifizierung nötig wäre - daher wird ausschließlich `urllib.request` + `zipfile` aus der Standardbibliothek verwendet, sonst nichts. Nur öffentliche Repositories werden unterstützt - es gibt keine Token-/Anmeldedaten-Behandlung, und die Zip-Datei eines privaten Repositorys liefert einen 404, genau wie bei einem nicht existierenden.
- **Von einem lokalen Ordner** - für ein Repository, das bereits von Hand heruntergeladen wurde, oder eine Arbeitskopie, die der Bediener gerade außerhalb dieser App aktiv bearbeitet.

In beiden Fällen durchsucht die App anschließend rekursiv jede `*.urdf`/`*.xacro`-Datei unter dem gewählten Ordner, listet sie alle auf (ein reales Roboter-Beschreibungs-Repository liefert oft mehr als eine - ein nackter Arm plus eine „mit Greifer"-Variante ist eine gängige Paarung) und wählt automatisch die größte nach Dateigröße als vernünftigen Standardwert für „die Hauptdatei" aus - danach zu einem anderen Kandidaten zu wechseln ist ein Doppelklick im Source-Panel, kein erneutes Abrufen.

**Die Auflösung von Mesh-Referenzen** ist die eigentliche unglamouröse Arbeit, die jede vergangene manuelle Roboter-Portierungssitzung in diesem Ökosystem von Hand erledigt hat: Der `<mesh filename="package://some_pkg/meshes/link1.stl"/>` einer URDF ist so gut wie nie ein direkt öffenbarer Pfad, sobald die Datei in einem einfachen heruntergeladenen Ordner liegt statt in einem laufenden ROS-Workspace, in dem `package://` über den ROS-Paketindex aufgelöst wird. Der Resolver versucht, in dieser Reihenfolge: (1) die Referenz als Pfad relativ zum eigenen Ordner der URDF, (2) dieselbe Referenz mit einem entfernten führenden `package://`-artigen Paketnamen-Segment, (3) als absoluten Pfad, falls sie zufällig bereits einer ist, und (4) über den bloßen Basisnamen irgendwo unter dem Quellordner - was tatsächlich die reale `package://`-URI behandelt, da das Schema und der Paketname außerhalb eines laufenden ROS-Workspace bedeutungslos sind, der eigentliche Dateiname des Meshes aber weiterhin auffindbar ist.

---

## ✅ Validierung der DOF-Machbarkeit

Die automatisierte Version derselben Ermessensentscheidung, die die vergangenen Sitzungen dieses Ökosystems selbst von Hand für jeden zum Katalog von STUDIO hinzugefügten Roboter getroffen haben: **die eigene Kinematik von STUDIO unterstützt heute serielle Ketten mit 3, 4, 5 und 6 Freiheitsgraden** (deren `RobotState.joints` ist eine feste `j1..j6`-Map) - eine Handvoll echter, lizenzrechtlich unbedenklicher Kandidatenarme, die in der Vergangenheit recherchiert wurden, stellten sich als 7-, 8- oder 9-DOF heraus und wurden genau aus diesem Grund verworfen, nicht hypothetisch. Bei jedem Import (und nach jeder Live-Bearbeitung, die die Anzahl ändern könnte - etwa das Umtypisieren eines Gelenks) durchläuft die App den tatsächlichen Eltern-/Kind-Gelenkgraphen und meldet:

- **DOF-Anzahl** - nur Gelenke vom Typ `revolute`/`continuous`/`prismatic` zählen als echter, ansteuerbarer Freiheitsgrad; `fixed` trägt keinen bei.
- **Nicht unterstützte Gelenktypen** - ein einzelnes `floating`- oder `planar`-Gelenk irgendwo in der Kette macht den gesamten Roboter unabhängig von der DOF-Anzahl nicht machbar, da das Gelenkmodell von STUDIO für keines von beiden eine Repräsentation hat.
- **Baumintegrität** - genau ein Wurzel-Link ist erforderlich (ein echter Baum, kein Wald und kein Zyklus); jeder Link, der von dieser Wurzel aus über eine Gelenkkette nicht erreichbar ist, wird als getrennt markiert, und jeder Link, auf den überhaupt kein Gelenk verweist, als Waise.
- **Fehlendes `<limit>`** - laut URDF-Spezifikation für alles außer einem `continuous`-Gelenk erforderlich; wird pro Gelenk markiert, falls nicht vorhanden.

Das Urteil und jeder dahinterliegende Grund werden live im DOF-Panel dargestellt, und das Upload-Panel verweigert es, einen nicht machbaren Roboter an einen Server zu übertragen.

---

## 🎨 Live-Bearbeitung mit echter 3D-Vorschau

Das Properties-Panel bearbeitet jeweils den im Link-Baum des Viewport-Panels ausgewählten Link, und jede Bearbeitung verändert das geladene Modell direkt und validiert/rendert es über ein einziges Signal (`EditorController.notify_tree_changed`) neu - kein Panel muss wissen, wie das Viewport oder der DOF-Bericht auf seine eigene Bearbeitung reagiert:

- **Umfärben** - das visuelle Material eines Links, ausgewählt über einen Standard-Farbdialog. Ein Material, das über den Namen von mehreren Links gemeinsam genutzt wird (eine übergeordnete `<material name="...">`-Deklaration in einer echten URDF, auf die mehr als ein `<visual>` verweist), färbt jeden Link, der es teilt, gemeinsam um - passend zu dem, was diese gemeinsame Material-Syntax laut Spezifikation tatsächlich bedeutet.
- **Neu skalieren** - Skalierungsfaktor pro Achse (X/Y/Z) auf der eigenen `<mesh scale="...">`-Transformation der Mesh-Geometrie, keine destruktive Neuschreibung der Dreiecksdaten des Meshes selbst - dieselbe Bearbeitung, später erneut angewendet, startet jedes Mal wieder vom ursprünglichen, unveränderten Mesh.
- **Gelenktyp und Grenzen neu setzen** - den Typ eines Gelenks ändern (jeden der 6, die die URDF-Spezifikation definiert) sowie dessen untere/obere Grenze, wobei sich das Urteil im DOF-Panel sofort aktualisiert, da ein Typwechsel die DOF-Anzahl ändern oder einen nicht unterstützten Typ einführen kann.

Das **Viewport-Panel** beherbergt die eigentliche OpenGL-3D-Ansicht sowie einen Jog-Schieberegler pro beweglichem Gelenk, sodass der Bediener eine Vorschau darauf bekommt, wie sich die URDF durch ihren eigenen realen Bewegungsbereich bewegt, noch bevor STUDIO überhaupt berührt wird. Die Vorwärtskinematik (`render/kinematics.py`) ist generisch gegenüber jedem gerade importierten Baum - anders als das eigene Kinematikmodul von HYDRA-UMC SUITE, das eine feste Registry von einigen Dutzend bekannter, von Hand verifizierter Robotermodelle ansteuert, muss diese App ein beliebiges, zuvor unbekanntes URDF posieren, weshalb sie den echten `<origin>`/`<axis>`-Wert jedes Gelenks zusammensetzt (Rodrigues-Rotationsformel für eine beliebige Rotationsachse, nicht nur die Abkürzung über Kardinalrichtungen, auf die sich eine feste Registry verlassen könnte), indem sie den tatsächlichen Eltern-/Kind-Graphen durchläuft.

**Z-nach-oben, nicht Y-nach-oben** - die eine bewusste Abweichung von der eigenen Viewport-Konvention von HYDRA-UMC SUITE: URDF selbst ist ein Z-nach-oben-Format (die Schwerkraft ist `-Z`, jedes `<origin>`/`<axis>` in einer Quelldatei wird unter dieser Annahme verfasst), und die Aufgabe dieser App ist es, eine URDF originalgetreu in ihrer eigenen Konvention anzuzeigen und zu bearbeiten, nicht sie in das umzuorientieren, was ein nachgelagerter Betrachter (die Three.js-Szene von STUDIO, die eigene OpenGL-Szene von SUITE) zufällig bevorzugt.

---

## 🗂️ Mesh-Laden

`.stl` (über `numpy-stl`) und `.obj` (ein kleiner, handgeschriebener Wavefront-Loader - nur `v`/`vn`/`f`, n-Eck-Flächen werden fächerförmig trianguliert) sind beide erstklassig unterstützt. **COLLADA (`.dae`) wird nicht unterstützt** - es handelt sich um ein deutlich größeres XML-Szenegraph-Format (Skelettanimation, mehrere Koordinatensysteme, eingebettete Materialien/Texturen), das einen echten Parser bräuchte, um es ehrlich zu handhaben, statt eines Best-Effort-Ratens, welche Tags ein „einfaches" `.dae` gerade zufällig verwendet; ein Link, der auf eines verweist, erhält eine klare, benannte Fehlermeldung, statt stillschweigend im Viewport zu fehlen oder den gesamten Import zum Absturz zu bringen. Jedes geladene Mesh erhält außerdem denselben defensiven Millimeter-vs-Meter-Schutz, den `useRealScaleSTL()` von HYDRA-UMC STUDIO und der eigene Mesh-Loader von HYDRA-UMC SUITE anwenden: Ein Link, der in irgendeiner Achse größer als 5 reale Meter ist, ist weit wahrscheinlicher ein Export im Millimeter-Maßstab ohne Einheiten-Metadaten als ein tatsächlich riesiges Roboterteil, und wird automatisch um den Faktor 0,001 neu skaliert.

---

## 📜 URDF-Parsing und -Export

Einfaches XML über das eigene `xml.etree.ElementTree` der Standardbibliothek - keine `lxml`-Abhängigkeit für ein derart einfaches Format nötig. Das In-Memory-Modell (`hydra_editor_urdf/models.py`) ist ein bewusst schlichter, veränderbarer, hausgemachter Dataclass-Baum statt eines Wrappers um eine bestehende Python-URDF-Bibliothek wie `urdfpy` oder `yourdfpy`: Diese App muss den Baum interaktiv *bearbeiten* und jede Änderung live neu rendern, wofür eine überwiegend lesende Parsing-Bibliothek nicht ausgelegt ist, und das Modell selbst zu besitzen, hält es klein, inspizierbar und frei vom eigenen Release-Rhythmus einer Drittanbieter-Abhängigkeit. Feldnamen und Standardwerte folgen eng dem echten [URDF-XML-Schema](http://wiki.ros.org/urdf/XML), sodass Parser und Writer ein dünnes, offensichtliches XML↔Objekt-Mapping bleiben.

**xacro wird nicht expandiert.** [xacro](http://wiki.ros.org/xacro) ist ein Python/XML-Makro-Präprozessor mit einem eigenen ROS-Paket und einer eigenen Abhängigkeitskette, und eine echte xacro-Datei ist nur zuverlässig innerhalb derselben ROS-Paketumgebung auflösbar, gegen die sie verfasst wurde (Makro-Argumente, Includes im Stil von `$(find pkg)` usw.) - etwas, das diese App auf keine ehrliche Weise reproduzieren kann. Eine Datei, die `<xacro:...>`-Tags verwendet oder den xacro-Namensraum deklariert, erhält eine klare Fehlermeldung, die die Einschränkung erklärt und auf das ROS-Kommandozeilentool `xacro` verweist, um sie zuerst zu präprozessieren, statt sie stillschweigend falsch zu parsen.

Der Export (`urdf/writer.py`) serialisiert den aktuellen In-Memory-Baum von Grund auf neu, statt den ursprünglichen Quell-XML-Text zu patchen, sodass jede Live-Bearbeitung - unabhängig davon, welches Panel sie vorgenommen hat - genau einmal, über einen einzigen Codepfad, sowohl in der Menüaktion „Export URDF" als auch in der an einen STUDIO-Server gesendeten Payload widergespiegelt wird.

---

## 🖥️ Andockbarer Arbeitsbereich

Echte `QDockWidget`-Panels - zum Loslösen ziehen, zum Andocken zurückziehen, zu Tabs zusammenführen, den Arbeitsbereich aufteilen - derselbe Mechanismus und dieselbe Begründung, die das eigene Hauptfenster von HYDRA-UMC SUITE bereits anwendet: Das eigene Andocksystem von Qt leistet bereits genau das, was ein Arbeitsbereich im Stil von Photoshop/Fusion-360 braucht, und ein handgestricktes würde es nur mit mehr Fehlern neu erfinden. Fünf Panels, angeordnet in einem sinnvollen Standardlayout, das danach vollständig neu anordenbar ist:

- **Source** - Eingabe von GitHub-URL / lokalem Ordner, Liste gefundener `.urdf`-Dateien.
- **DOF** - das Machbarkeitsurteil und jeder dahinterliegende Grund.
- **Viewport** - die Live-3D-Ansicht, der Link-Baum, und die Jog-Schieberegler.
- **Properties** - Umfärben / Neu-Skalieren / Gelenktyp-und-Grenzen-Neusetzen für den ausgewählten Link.
- **Upload** - Verbindung zu einem STUDIO-Server, Push, oder Pull.

---

## ☁️ Server-Roundtrip

Spricht mit dem eigenen Modell-Übermittlungsvertrag von HYDRA-UMC-STUDIO (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` in der eigenen `server.ts` dieses Projekts, abgesichert hinter dem eigenen Umschalter **Config > Models > „Accept model submissions"**) unter Verwendung des eigenen `urllib.request` der Standardbibliothek - ein weiterer HTTP-Aufruf rechtfertigte nicht das Einbinden von `httpx`/`requests` für ein Projekt, das nur jemals 4 Endpunkte braucht, keine dauerhafte Live-Verbindung. Jeder Aufruf läuft in einem Hintergrund-`QThread`, damit ein langsamer oder nicht erreichbarer Server die Oberfläche niemals einfriert.

- **Login** - `POST /api/login`; nur ein Token mit `admin`-Rolle kann serverseitig überhaupt `POST /api/models/submit` erreichen, daher ist diese App tatsächlich nur mit einem Admin-Konto nutzbar, genau wie jede andere reine Admin-Funktion von STUDIO.
- **Push** - serialisiert den aktuellen Roboter zurück in URDF-XML und base64-kodiert jede Mesh-Datei, auf die dessen Visuals verweisen (aufgelöst über denselben Mesh-Resolver, der beim Import erstellt wurde), inline im Request-Body, versehen mit der vom Bediener gewählten Kategorie (spiegelt die eigenen Config > UI > Module-Visibility-Kategorien von STUDIO wider: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - eine URDF hat kein eigenes Feld, das aussagt, welche davon zutrifft). Ein Namenskonflikt kommt als eigene 409-Antwort des Servers zurück; der Bediener entscheidet, ob mit aktiviertem **Overwrite** erneut übermittelt oder umbenannt wird, diese App rät niemals selbst.
- **Pull** - lädt die URDF + Meshes eines bereits übermittelten Modells zurück in einen lokalen Arbeitsordner herunter und lädt es direkt in den Editor - die „extrahieren, bearbeiten, erneut senden"-Hälfte des Roundtrips, die den eigentlichen Zweck dieser App ausmacht, indem sie erlaubt, einen bestehenden Katalogeintrag nachzubessern, ohne wieder bei dessen ursprünglichem Quell-Repository anzufangen.

---

## 🌐 Mehrsprachige Oberfläche

Vollständige Übersetzung der Oberfläche in **Englisch, Spanisch, Italienisch, Französisch und Deutsch** (`language/*.lng`), unter Verwendung genau desselben einfachen `SCHLÜSSEL=Wert`-Dateimechanismus wie jedes andere Python-Tool in diesem Ökosystem (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - hier nicht neu erfunden, da der Mechanismus selbst keine projektspezifische Logik trägt. Ein Sprachwechsel wird erst nach einem Neustart der App wirksam, statt jedes bereits erstellte Widget live neu zu übersetzen, entsprechend derselben Konvention. `language/` liegt **neben** der ausführbaren Datei, statt über `--add-data` von PyInstaller darin gebündelt zu sein, sodass ein Übersetzer eine `.lng`-Datei bearbeiten oder hinzufügen kann, ohne einen Neubau durchzuführen.

---

## 🎛️ Theme

Verwendet die eigene `assets/qss/industrial_dark.qss` von HYDRA-UMC SUITE wörtlich wieder (gleicher relativer Pfad, gleiche Datei), statt für ein Schwester-Desktop-Tool im selben Ökosystem ein neues visuelles Theme zu entwerfen.

---

## 📂 Repository Structure

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # Einstiegspunkt - QApplication, Theme, maximierter Start, F11-Vollbild-Umschalter
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (fest gepinnt)
├── build_exe.bat / build_exe.sh    # Build-Skripte für eigenständige Windows-/Linux-Executables (PyInstaller)
├── README.md                       # Diese Datei
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md  # <- Übersetzungen
├── LICENSE                         # GPL-3.0
├── assets/
│   └── qss/industrial_dark.qss     # Wörtlich von HYDRA-UMC-SUITE wiederverwendet
├── language/                       # english/spanish/italian/french/german.lng - liegt neben der exe, nicht gebündelt
├── hydra_editor_urdf/
│   ├── app.py                      # EditorController - alleiniger Besitzer von „was geladen ist", Qt-Signale, denen jedes Panel zuhört
│   ├── models.py                   # Hausgemachter URDF-Objektbaum (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── i18n.py                     # Loader für language/*.lng, Persistenz der Konfiguration - portiert aus der eigenen i18n.py von HYDRA-UMC-SUITE
│   ├── urdf/
│   │   ├── parser.py               # URDF-XML -> models.py-Baum (ElementTree, xacro wird erkannt und mit klarer Fehlermeldung abgelehnt)
│   │   ├── writer.py                # models.py-Baum -> URDF-XML-String (Export + Server-Upload-Payload)
│   │   └── dof.py                  # DOF-Zählung, Machbarkeitsvalidierung gegen die 3-6-DOF-Obergrenze von STUDIO
│   ├── render/
│   │   ├── mesh.py                 # STL/OBJ-Laden, Generierung von Box/Zylinder/Kugel-Primitiven, mm-vs-m-Schutz
│   │   ├── kinematics.py           # Generische Vorwärtskinematik über einen beliebigen importierten Baum (Z-nach-oben, die eigene Konvention von URDF)
│   │   └── viewport.py             # QOpenGLWidget - GLSL-3.3-Core-Shader, Orbit-Kamera, GPU-Puffer pro Link
│   ├── source/
│   │   ├── scan.py                 # Findet .urdf/.xacro-Dateien, baut den package://-fähigen Mesh-Dateinamen-Resolver auf
│   │   ├── github_fetcher.py       # Download + Extraktion der GitHub-Zip-Datei (urllib + zipfile, keine git-Abhängigkeit)
│   │   └── local_folder.py         # Validierung des lokalen Ordners - das dünne Gegenstück zu github_fetcher.py
│   ├── server/
│   │   └── client.py               # StudioClient - login/list_models/push_model/pull_model gegen die server.ts von HYDRA-UMC-STUDIO
│   └── ui/
│       ├── main_window.py          # QMainWindow - andockbarer Arbeitsbereich, Menüleiste, Sprachumschalter, Statusleiste
│       ├── theme.py                 # Wendet assets/qss/industrial_dark.qss an
│       └── panels/
│           ├── source_panel.py     # Eingabe von GitHub-URL / lokalem Ordner, Liste gefundener URDFs
│           ├── dof_panel.py        # Anzeige des Machbarkeitsurteils
│           ├── viewport_panel.py   # 3D-Viewport-Host, Link-Baum, Jog-Schieberegler
│           ├── properties_panel.py # Editoren für Umfärben / Neu-Skalieren / Gelenktyp-und-Grenzen-Neusetzen
│           └── upload_panel.py     # Server-Verbindung/Push/Pull
└── work/                            # Laufzeit-Arbeitsbereich für abgerufene GitHub-Repositories und heruntergeladene Server-Modelle (per gitignore ausgeschlossen)
```

---

## 🛠️ Entwicklungsumgebung

### Voraussetzungen
- [Python](https://www.python.org/) 3.11 oder höher
- pip

### Installation

```bash
pip install -r requirements.txt
```

Dies zieht den festgelegten Abhängigkeitssatz nach: **PySide6** (Qt6-UI), **PyOpenGL** (3D-Viewport-Rendering), **numpy** / **numpy-stl** (Mesh-Mathematik und STL-Laden). Keine `git`-Installation ist erforderlich - der GitHub-Quellladepfad lädt eine einfache Zip-Datei über HTTPS herunter.

### Entwicklungsmodus

```bash
python main.py
```

Startet maximiert (kein echtes Vollbild auf Betriebssystemebene, sodass die native Fenstertitelleiste und ihre Steuerelemente sichtbar bleiben) - drücken Sie **F11**, um zwischen echtem randlosem Vollbild und diesem Zustand umzuschalten.

### Produktions-Build

Kompiliert eine eigenständige ausführbare Datei (keine Python-Installation zum Ausführen nötig) über PyInstaller:

- **Windows:** `build_exe.bat` ausführen → erzeugt `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux:** `./build_exe.sh` ausführen (zuvor einmalig `chmod +x build_exe.sh`) → erzeugt `dist/HYDRA-UMC_EDITOR-URDF`

Beide Skripte erstellen/aktivieren ihre eigene `.venv`, installieren `requirements.txt` plus `pyinstaller`, bereinigen ein etwaiges vorheriges `build`/`dist`, kompilieren und kopieren schließlich `README.md`, `LICENSE` sowie den gesamten Ordner `language/` neben die entstandene Binärdatei (`language/` wird absichtlich **nicht** über `--add-data` in die ausführbare Datei gebündelt, sodass eine `.lng`-Datei danach ohne Neubau bearbeitet oder hinzugefügt werden kann).

Wenn Sie die entsprechenden Schritte lieber von Hand ausführen möchten, statt das Skript zu verwenden - nützlich, um den Build an eine Plattform anzupassen, die die Skripte nicht abdecken, oder um ein PyInstaller-Flag zu debuggen -, sieht der manuelle Ablauf so aus:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. Install dependencies + PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# 3. Locate PySide6's own install directory (its Qt plugins live under it)
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> $PYSIDE_DIR below

# 4. Compile - only 4 Qt plugin subfolders are staged explicitly (platforms/
#    styles/imageformats/iconengines), NOT --collect-all PySide6, which would
#    otherwise pull in Qt6WebEngineCore.dll and other multi-hundred-MB pieces
#    this app never uses. PyInstaller's own dependency analyzer finds the
#    actual Qt6Core/Gui/Widgets/OpenGL DLLs by following main.py's real import
#    graph - only the plugin folders need to be added by hand.
#
#    Windows (plugins live directly under PySide6/plugins/):
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux (plugins live under PySide6/Qt/plugins/ instead - a different
#    layout than Windows, confirmed by reading PyInstaller's own runtime hook
#    pyi_rth_pyside6.py):
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. Copy files that must sit NEXT TO the binary, not inside it
cp README.md LICENSE dist/
cp -r language dist/language
```

Unter Linux benötigt das Ausführen der kompilierten Binärdatei die eigene OpenGL-Laufzeitumgebung des Systems (`libGL.so.1` - z. B. `libgl1` auf Debian/Ubuntu, `mesa-libGL` auf Fedora, `libglvnd` auf Arch) sowie `libxkbcommon-x11-0`/`xcb-util-cursor` für das eigene XCB-Plattform-Plugin von Qt; `build_exe.sh` prüft `libGL.so.1` bereits im Vorfeld und gibt den passenden Installationsbefehl für die jeweilige Distribution aus, falls es fehlt, statt tief in einem PyInstaller-Lauf zu scheitern.

---

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil eines größeren Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage tatsächlich eher eines dieser Projekte betreffen könnte als dieses Repository:

**HYDRA-UMC-Plattform** — die Multi-Roboter-Mikrofabrikzelle
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — die Hauptplatine selbst: Raspberry-Pi-CM5-Host + Dual-Core-STM32H745-Echtzeit-Co-Prozessor, der bis zu 8 verteilte Roboterarme über CAN-OTA/SPI-OTA orchestriert. Eigene Hardware + Firmware, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — webbasiertes Steuerungsdashboard für HYDRA-UMC: Multi-Roboter-3D-Visualisierung, Kinematik-/Trajektorienaufzeichnung, CAN-OTA-Flashen und -Testen für die gesamte Plattform. React + Vite + Three.js.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android-Steuerungs-App für HYDRA-UMC über WLAN/Bluetooth. Echte, funktionierende App - vollständiger Funktionsumfang zur Fernsteuerung, JWT-Authentifizierung, verschlüsselte Speicherung der Zugangsdaten.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App für HYDRA-UMC über WLAN, erstellt mit Flutter (plattformübergreifend, unter Windows ohne Mac überprüfbar; die endgültige `.ipa`-Paketierung benötigt weiterhin Xcode). Echte, funktionierende App - derselbe Funktionsumfang wie die Android-App.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Kommandozentrale (Python/PySide6) für den Roboterschwarm: Netzwerkerkennung mehrerer Controller, bidirektionale Live-Synchronisation, echtes 3D-Roboter-Viewport, andockbarer Arbeitsbereich im Photoshop-Stil. Real und funktionsfähig, kein Platzhalter.
- **HYDRA-UMC-EDITOR-URDF** *(dieses Repository)* — grafischer URDF-Ersteller/-Editor (Python/PySide6) für den eigenen Modellkatalog von HYDRA-UMC-STUDIO: zieht Quelldateien von GitHub oder aus einem lokalen Ordner, validiert die DOF-Machbarkeit, bearbeitet Farbe/Skalierung/Kinematik mit Live-3D-Vorschau, und überträgt das fertige Ergebnis an einen laufenden STUDIO-Server. Real und funktionsfähig, kein Platzhalter.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — geplant: eine native Touch-UI für den eigenen 7"-DSI-Touchscreen (1280×800) von HYDRA-UMC auf dem Compute Module 5, die denselben Server direkt vom Board aus steuert. Noch nicht begonnen.

**URTC-Plattform** — der Werkzeugkopf-Controller, den jeder HYDRA-UMC-Roboterarm trägt
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: CAN-Bus-Werkzeugkopf-Controller auf STM32F303-Basis, 25 vollständig implementierte Werkzeugprofile, CAN-OTA-Firmware-Update.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-Tool zum CAN-OTA- sowie vollständigen Chip-SWD/JTAG-Flashen von URTC-Platinen (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Tool zur Live-CAN-Bus-Diagnose von URTC-Platinen, ein Panel pro Werkzeugprofil (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu den 2 obigen Desktop-Tools (Web Serial API + SLCAN), keine lokale Installation nötig.

---

## 👤 Autor

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 Lizenz- und Urheberrechtshinweise

HYDRA-UMC EDITOR-URDF ist (c) 2026 JuanenRac (Electro Hobby 3D). Dieser Hinweis muss in jeder Verbreitung dieses Projekts oder abgeleiteten Werken enthalten sein.

Dieses Projekt besteht aus Quellcode und eigener Dokumentation, die unter unterschiedlichen Lizenzen bereitgestellt werden - jeweils passend zu dem, was sie tatsächlich abdecken:

1. Der Quellcode (`hydra_editor_urdf/`, `main.py`, sowie jede daraus über `build_exe.bat`/`build_exe.sh` erstellte Binärdatei) ist unter der **GNU General Public License v3.0 (GPL-3.0)** verfügbar. Vollständiger Text unter https://www.gnu.org/licenses/gpl-3.0.html.

2. Die Dokumentation (dieses README und dessen eigene Übersetzungen - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`) ist unter der **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** verfügbar. Vollständiger Text unter https://creativecommons.org/licenses/by-sa/4.0/.

Diese App liefert keine eigenen Drittanbieter-Robotermesh-Assets aus - anders als die `public/models/` von HYDRA-UMC STUDIO stammt jedes von diesem Editor jemals geladene Mesh aus dem jeweiligen Quell-Repository oder lokalen Ordner, auf das der Bediener es verweist, unter der ursprünglichen Lizenz dieser Quelle. Die Überprüfung und Wahrung dieser vorgelagerten Lizenz-/Attributionsangaben vor der Übermittlung eines Modells an einen laufenden STUDIO-Server (dessen eigene `public/models/<slug>/ATTRIBUTION.txt`-Konvention der Export dieses Editors speist) bleibt die eigene Verantwortung des Bedieners - diese App hat keine Möglichkeit, die Lizenzbedingungen eines Quell-Repositorys automatisch zu erkennen oder durchzusetzen.

Dieser Editor ist das Werkzeug zur Modellerstellung für den Katalog von [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - siehe dieses Repository für dessen eigene serverseitige Lizenzierung, auf die sich die eigene Lizenz dieses Repositorys nicht erstreckt, und umgekehrt.

Wenn Sie auf diesem Projekt aufbauen, behalten Sie die Lizenzaufteilung im Hinterkopf: Code-Änderungen hier sollten unter GPL-3.0 bleiben, abgeleitete Dokumentation (dieses README und dessen Übersetzungen) sollte unter CC BY-SA 4.0 bleiben, und jedes Mesh-Asset, das diesen Editor durchläuft (importiert, bearbeitet oder exportiert), sollte unter der jeweiligen ursprünglichen Lizenz seines eigenen Quell-Repositorys bleiben, mit Attribution zurück zu dieser Quelle.
