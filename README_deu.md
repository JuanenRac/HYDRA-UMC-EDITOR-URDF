<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Desktop URDF creator and editor for the model catalogue of HYDRA-UMC-STUDIO
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>

# 🖌️ HYDRA-UMC-EDITOR-URDF

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🖌️ Grafischer URDF-Ersteller/-Editor für den Modellkatalog von HYDRA-UMC-STUDIO

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="Format">
  <img src="https://img.shields.io/badge/Tests-372%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

---

**Ehrlichkeitscheck - was heute wirklich läuft:** der Kern aus reiner Logik - URDF-Parsing/-Export (`urdf/parser.py`, `urdf/writer.py`), DOF-Machbarkeitsprüfung (`urdf/dof.py`), Vorwärtskinematik (`render/kinematics.py`), Trägheitsschätzung (`inertia_calc.py`), Mesh-Referenzauflösung und GitHub-Zipball-Download (`source/scan.py`, `source/github_fetcher.py`, `source/local_folder.py`), das In-Memory-Modell (`models.py`), die Galerie-Liste (`gallery.py`) und der i18n-Lader (`i18n.py`) - ist real und durch 372 bestandene Tests abgedeckt (`tests/`), von denen keiner PySide6/PyOpenGL importiert. `test_github_fetcher.py` simuliert jeden Netzwerkaufruf - ein echter GitHub-Zipball-Download wurde manuell ausgeführt, nie als Teil der automatisierten Suite. Die Qt/OpenGL-Schicht (`render/viewport.py` mit seinem `UrdfGLRenderer`, `render/mesh.py`, jedes `ui/*`-Panel und der `OffscreenUrdfRenderer` des `--qtquick`-Decks) ist echter, funktionierender Code, hat aber überhaupt keine automatisierte Testabdeckung - sie benötigt ein echtes Display/Qt-Plattform-Plugin, das die CI nicht hat, also wird sie von Hand geprüft, nicht durch eine Testsuite. `server/client.py`s `StudioClient` (Login/Push/Pull gegen das `server.ts` von HYDRA-UMC-SERVER) ist echter HTTP-Code, getestet gegen einen kleinen lokalen Server, der den Vertrag des `server.ts` einhält (das Token bei jedem Aufruf, eine Namenskollision, der Download eines Modells, eine feindliche Antwort). xacro-Expansion und das Laden von COLLADA-Meshes (`.dae`) sind explizite, benannte Nicht-Funktionen (ein klarer Fehler, kein stiller Fehlparse) - siehe den Ehrlichkeitshinweis im Überblick weiter unten und die Abschnitte URDF-Parsing/Mesh-Laden für das Warum. Siehe `CHANGELOG.md` für das, was bisher genau ausgeliefert wurde.

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem. Es gibt noch keinen Hardware-E-STOP-Pfad, keine von der Firmware durchgesetzten Grenzen oder Verriegelungen und keinen verifizierten Bewegungsbefehl; Firmware-Images werden mit CRC-32 und einer Ed25519-Signatur geprüft, und ein Release-Build verweigert die veröffentlichten Entwicklungsschlüssel (die Werkzeugköpfe und Erweiterungsplatinen hinter dem Relais laufen noch mit URTC-Bootloadern, die statt einer Signatur ein HMAC-SHA256 mit gemeinsamem Schlüssel verwenden); TLS und gegenseitiges TLS sind optional und standardmäßig aus; noch keine eigene Platine wurde bestückt oder getestet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.1.5` |
| Reifegrad | Etabliert |
| Tests | 372 (`python -m pytest tests -q`) |
| Technik | Python / PySide6 / Qt6 / OpenGL |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Nicht zutreffend: nichts hiervon läuft auf Hardware |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Funktionen](#-funktionen) · [Sicherheit und Schutz](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Konfiguration](#-konfiguration) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Fehlerbehebung](#-fehlerbehebung) · [Struktur des Repositorys](#-struktur-des-repositorys) · [Verwandte Projekte](#-verwandte-projekte)

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟢 | Für seinen Zweck vollständig und stabil; die Ehrlichkeitsprüfung oben nennt die bekannten Grenzen |
| Tests | 🟢 | 372 automatische Tests, bei jeder Änderung ausgeführt |
| Echte Hardware | 🟢 | Nicht zutreffend: nichts hiervon läuft auf Hardware |
| Dokumentation | 🟢 | README in acht Sprachen, bei jeder Änderung gegen das Manifest geprüft |

## 🎯 Überblick

**HYDRA-UMC EDITOR-URDF** ist das Desktop-Tool, das aus dem „Portieren eines neuen Roboters in den Modellkatalog von [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)" von einer manuellen, pro-Roboter durchgeführten Untersuchung einen wiederholbaren, grafischen Arbeitsablauf macht. Jedes reale Robotermodell im Katalog von STUDIO ist in der Vergangenheit auf demselben Weg dorthin gelangt: ein Beschreibungs-Repository auf GitHub finden, herausfinden, wie sich dessen Mesh-Referenzen auflösen, die Freiheitsgrade in seiner kinematischen Kette zählen, prüfen, ob STUDIO tatsächlich so viele ansteuern kann, und das Ergebnis von Hand nach `public/models/` legen. Diese App automatisiert genau diesen Durchlauf - sie zieht die Quelldateien von einer GitHub-URL oder aus einem bereits heruntergeladenen lokalen Ordner, löst jede `<mesh filename="...">`-Referenz auf (einschließlich `package://`-URIs) gegen die realen Dateien auf der Festplatte, validiert die Anzahl der Freiheitsgrade der Kette gegen das, was die Kinematik von STUDIO heute unterstützt, bearbeitet Farbe/Skalierung/Gelenkgrenzen/Gelenktyp mit einer Live-3D-Vorschau, und überträgt das fertige Ergebnis direkt an einen laufenden STUDIO-Server.

Erstellt mit **Python** und **PySide6/Qt6**, unter Verwendung derselben architektonischen Muster, die bereits im anderen Desktop-Tool dieses Ökosystems, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE), validiert wurden: ein andockbarer Arbeitsbereich im Stil von Photoshop/Fusion-360 (`QDockWidget`), ein handgeschriebenes OpenGL-3D-Viewport (`QOpenGLWidget` + GLSL-3.3-Core-Profile-Shader, kein `glBegin`/`glEnd`-Legacy-Pfad), sowie ein zentrales Controller-Objekt, das den Zustand besitzt und dem jedes UI-Panel über Qt-Signale zuhört. Dieses Muster hier wiederzuverwenden - anstatt einen neuen UI/Render-Stack für ein Schwester-Tool im selben Ökosystem zu erkunden - ist eine bewusste Entscheidung, kein Versehen.

**Ehrlichkeitshinweis, im Einklang mit der Dokumentationskonvention des übrigen Ökosystems:** Diese App expandiert keine [xacro](http://wiki.ros.org/xacro)-Makros und lädt keine COLLADA-Meshes (`.dae`). Beides sind benannte, explizite Einschränkungen (eine klare Fehlermeldung, kein stillschweigendes Fehlparsen und keine fehlende Verbindung im Viewport) statt eines halbfertigen Versuchs - siehe die Abschnitte **URDF-Parsing** und **Mesh-Laden** weiter unten dafür, warum echte Unterstützung für eines von beidem erheblichen zusätzlichen Aufwand erfordern würde.

## 🧩 Rolle in HYDRA-UMC

**HYDRA-UMC-EDITOR-URDF** ist das Desktop-Werkzeug, das die Übernahme eines neuen Roboters in den Modellkatalog von HYDRA-UMC-STUDIO von einer manuellen Recherche in einen wiederholbaren Ablauf verwandelt. Es lädt ein URDF aus einem GitHub-Repository oder einem lokalen Ordner, sagt, ob der Roboter in die 3 bis 6 Freiheitsgrade passt, die STUDIO unterstützt, zeigt ihn in einer 3D-Live-Ansicht, in der Glieder umgefärbt, skaliert und mit neuen Gelenkgrenzen versehen werden können, und exportiert das URDF oder sendet es an einen HYDRA-UMC-SERVER.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-EDITOR-URDF architecture" width="100%">
</p>

## ✨ Funktionen

### Quellen laden - GitHub oder lokaler Ordner

Zwei Wege, um die App auf die Quelldateien eines Roboters zeigen zu lassen, die beide im selben Importpfad enden:

- **Von einer GitHub-URL** - akzeptiert eine vollständige `https://github.com/owner/repo`-URL (mit oder ohne `/tree/<branch>`), eine SSH-artige `git@github.com:owner/repo.git`, oder die bloße `owner/repo`-Kurzform. Führt bewusst **keinen** `git clone` über die Shell aus, was auf Windows und Linux gleichermaßen eine `git`-Installation zu einer harten Laufzeitabhängigkeit für etwas machen würde, das ein einfacher HTTPS-Download bereits leistet: GitHub liefert eine Zip-Datei jedes Branches/Tags/Commits von `codeload.github.com` aus, ohne dass für ein öffentliches Repository eine Authentifizierung nötig wäre - daher wird ausschließlich `urllib.request` + `zipfile` aus der Standardbibliothek verwendet, sonst nichts. Nur öffentliche Repositories werden unterstützt - es gibt keine Token-/Anmeldedaten-Behandlung, und die Zip-Datei eines privaten Repositorys liefert einen 404, genau wie bei einem nicht existierenden.
- **Von einem lokalen Ordner** - für ein Repository, das bereits von Hand heruntergeladen wurde, oder eine Arbeitskopie, die der Bediener gerade außerhalb dieser App aktiv bearbeitet.
- **Aus der Gallery** - ein "Gallery"-Dropdown oberhalb des GitHub-URL-Felds (`hydra_editor_urdf/gallery.py`) listet eine kleine, von Hand geprüfte Startauswahl echter Roboterbeschreibungs-Repositories (`universal_robot` von ROS-Industrial, `open_manipulator` von ROBOTIS). Eine Auswahl füllt nur die URL und zeigt deren Beschreibung - sie löst nie von sich aus einen Download aus, der Bediener muss weiterhin Fetch drücken, genau wie bei einer von Hand eingegebenen URL.

In beiden Fällen durchsucht die App anschließend rekursiv jede `*.urdf`/`*.xacro`-Datei unter dem gewählten Ordner, listet sie alle auf (ein reales Roboter-Beschreibungs-Repository liefert oft mehr als eine - ein nackter Arm plus eine „mit Greifer"-Variante ist eine gängige Paarung) und wählt automatisch die größte nach Dateigröße als vernünftigen Standardwert für „die Hauptdatei" aus - danach zu einem anderen Kandidaten zu wechseln ist ein Doppelklick im Source-Panel, kein erneutes Abrufen.

**Die Auflösung von Mesh-Referenzen** ist die eigentliche unglamouröse Arbeit, die jede vergangene manuelle Roboter-Portierungssitzung in diesem Ökosystem von Hand erledigt hat: Der `<mesh filename="package://some_pkg/meshes/link1.stl"/>` einer URDF ist so gut wie nie ein direkt öffenbarer Pfad, sobald die Datei in einem einfachen heruntergeladenen Ordner liegt statt in einem laufenden ROS-Workspace, in dem `package://` über den ROS-Paketindex aufgelöst wird. Der Resolver versucht, in dieser Reihenfolge: (1) die Referenz als Pfad relativ zum eigenen Ordner der URDF, (2) dieselbe Referenz mit einem entfernten führenden `package://`-artigen Paketnamen-Segment, (3) als absoluten Pfad, falls sie zufällig bereits einer ist, und (4) über den bloßen Basisnamen irgendwo unter dem Quellordner - was tatsächlich die reale `package://`-URI behandelt, da das Schema und der Paketname außerhalb eines laufenden ROS-Workspace bedeutungslos sind, der eigentliche Dateiname des Meshes aber weiterhin auffindbar ist.

### Validierung der DOF-Machbarkeit

Die automatisierte Version derselben Ermessensentscheidung, die die vergangenen Sitzungen dieses Ökosystems selbst von Hand für jeden zum Katalog von STUDIO hinzugefügten Roboter getroffen haben: **die eigene Kinematik von STUDIO unterstützt heute serielle Ketten mit 3, 4, 5 und 6 Freiheitsgraden** (deren `RobotState.joints` ist eine feste `j1..j6`-Map) - eine Handvoll echter, lizenzrechtlich unbedenklicher Kandidatenarme, die in der Vergangenheit recherchiert wurden, stellten sich als 7-, 8- oder 9-DOF heraus und wurden genau aus diesem Grund verworfen, nicht hypothetisch. Bei jedem Import (und nach jeder Live-Bearbeitung, die die Anzahl ändern könnte - etwa das Umtypisieren eines Gelenks) durchläuft die App den tatsächlichen Eltern-/Kind-Gelenkgraphen und meldet:

- **DOF-Anzahl** - nur Gelenke vom Typ `revolute`/`continuous`/`prismatic` zählen als echter, ansteuerbarer Freiheitsgrad; `fixed` trägt keinen bei.
- **Nicht unterstützte Gelenktypen** - ein einzelnes `floating`- oder `planar`-Gelenk irgendwo in der Kette macht den gesamten Roboter unabhängig von der DOF-Anzahl nicht machbar, da das Gelenkmodell von STUDIO für keines von beiden eine Repräsentation hat.
- **Baumintegrität** - genau ein Wurzel-Link ist erforderlich (ein echter Baum, kein Wald und kein Zyklus); jeder Link, der von dieser Wurzel aus über eine Gelenkkette nicht erreichbar ist, wird als getrennt markiert, und jeder Link, auf den überhaupt kein Gelenk verweist, als Waise.
- **Fehlendes `<limit>`** - laut URDF-Spezifikation für alles außer einem `continuous`-Gelenk erforderlich; wird pro Gelenk markiert, falls nicht vorhanden.

Das Urteil und jeder dahinterliegende Grund werden live im DOF-Panel dargestellt, und das Upload-Panel verweigert es, einen nicht machbaren Roboter an einen Server zu übertragen.

### Live-Bearbeitung mit echter 3D-Vorschau

Das Properties-Panel bearbeitet jeweils den im Link-Baum des Viewport-Panels ausgewählten Link, und jede Bearbeitung verändert das geladene Modell direkt und validiert/rendert es über ein einziges Signal (`EditorController.notify_tree_changed`) neu - kein Panel muss wissen, wie das Viewport oder der DOF-Bericht auf seine eigene Bearbeitung reagiert:

- **Umfärben** - das visuelle Material eines Links, ausgewählt über einen Standard-Farbdialog. Ein Material, das über den Namen von mehreren Links gemeinsam genutzt wird (eine übergeordnete `<material name="...">`-Deklaration in einer echten URDF, auf die mehr als ein `<visual>` verweist), färbt jeden Link, der es teilt, gemeinsam um - passend zu dem, was diese gemeinsame Material-Syntax laut Spezifikation tatsächlich bedeutet.
- **Neu skalieren** - Skalierungsfaktor pro Achse (X/Y/Z) auf der eigenen `<mesh scale="...">`-Transformation der Mesh-Geometrie, keine destruktive Neuschreibung der Dreiecksdaten des Meshes selbst - dieselbe Bearbeitung, später erneut angewendet, startet jedes Mal wieder vom ursprünglichen, unveränderten Mesh.
- **Gelenktyp und Grenzen neu setzen** - den Typ eines Gelenks ändern (jeden der 6, die die URDF-Spezifikation definiert) sowie dessen untere/obere Grenze, wobei sich das Urteil im DOF-Panel sofort aktualisiert, da ein Typwechsel die DOF-Anzahl ändern oder einen nicht unterstützten Typ einführen kann.
- **Masse und Trägheit** - "Auto-calculate" füllt Masse/Ixx/Iyy/Izz aus der Geometrie des ausgewählten Links mit den geschlossenen Formeln gleichmäßiger Dichte aus `inertia_calc.py` (exakt für Box/Zylinder/Kugel, eine Bounding-Box-Näherung für Mesh); eine von Hand eingegebene Masse hat immer Vorrang vor der dichtebasierten Schätzung, und ohne eingegebene Masse nimmt die App eine generische Aluminiumdichte an (2700 kg/m³) und weist in einer Notiz darauf hin. "Apply" überträgt die Felder nach `Link.inertial` - dasselbe zweistufige Berechnen-dann-Anwenden-Muster wie bei Scale/Joint oben.

Das **Viewport-Panel** beherbergt die eigentliche OpenGL-3D-Ansicht sowie einen Jog-Schieberegler pro beweglichem Gelenk, sodass der Bediener eine Vorschau darauf bekommt, wie sich die URDF durch ihren eigenen realen Bewegungsbereich bewegt, noch bevor STUDIO überhaupt berührt wird. Die Vorwärtskinematik (`render/kinematics.py`) ist generisch gegenüber jedem gerade importierten Baum - anders als das eigene Kinematikmodul von HYDRA-UMC SUITE, das eine feste Registry von einigen Dutzend bekannter, von Hand verifizierter Robotermodelle ansteuert, muss diese App ein beliebiges, zuvor unbekanntes URDF posieren, weshalb sie den echten `<origin>`/`<axis>`-Wert jedes Gelenks zusammensetzt (Rodrigues-Rotationsformel für eine beliebige Rotationsachse, nicht nur die Abkürzung über Kardinalrichtungen, auf die sich eine feste Registry verlassen könnte), indem sie den tatsächlichen Eltern-/Kind-Graphen durchläuft.

**Z-nach-oben, nicht Y-nach-oben** - die eine bewusste Abweichung von der eigenen Viewport-Konvention von HYDRA-UMC SUITE: URDF selbst ist ein Z-nach-oben-Format (die Schwerkraft ist `-Z`, jedes `<origin>`/`<axis>` in einer Quelldatei wird unter dieser Annahme verfasst), und die Aufgabe dieser App ist es, eine URDF originalgetreu in ihrer eigenen Konvention anzuzeigen und zu bearbeiten, nicht sie in das umzuorientieren, was ein nachgelagerter Betrachter (die Three.js-Szene von STUDIO, die eigene OpenGL-Szene von SUITE) zufällig bevorzugt.

### Mesh-Laden

`.stl` (über `numpy-stl`) und `.obj` (ein kleiner, handgeschriebener Wavefront-Loader - nur `v`/`vn`/`f`, n-Eck-Flächen werden fächerförmig trianguliert) sind beide erstklassig unterstützt. **COLLADA (`.dae`) wird nicht unterstützt** - es handelt sich um ein deutlich größeres XML-Szenegraph-Format (Skelettanimation, mehrere Koordinatensysteme, eingebettete Materialien/Texturen), das einen echten Parser bräuchte, um es ehrlich zu handhaben, statt eines Best-Effort-Ratens, welche Tags ein „einfaches" `.dae` gerade zufällig verwendet; ein Link, der auf eines verweist, erhält eine klare, benannte Fehlermeldung, statt stillschweigend im Viewport zu fehlen oder den gesamten Import zum Absturz zu bringen. Jedes geladene Mesh erhält außerdem denselben defensiven Millimeter-vs-Meter-Schutz, den `useRealScaleSTL()` von HYDRA-UMC STUDIO und der eigene Mesh-Loader von HYDRA-UMC SUITE anwenden: Ein Link, der in irgendeiner Achse größer als 5 reale Meter ist, ist weit wahrscheinlicher ein Export im Millimeter-Maßstab ohne Einheiten-Metadaten als ein tatsächlich riesiges Roboterteil, und wird automatisch um den Faktor 0,001 neu skaliert.

---

Mesh-Pfade sind eingegrenzt: Ein `<mesh filename>` wird nur zu einer `.stl`-, `.obj`- oder `.dae`-Datei im geöffneten Ordner, im URDF-Ordner oder in einem über „Locate Missing Meshes“ hinzugefügten Ordner aufgelöst; `..`-Segmente, absolute Pfade und `file://`-URIs, die woanders hinführen, werden ignoriert, und nur diese Dateien werden hochgeladen. Leere, abgeschnittene oder fehlerhafte Meshes werden als nicht geladen gemeldet, statt den Viewer zu stoppen. Die Millimeter-zu-Meter-Absicherung skaliert jedes Mesh über 5 Einheiten, bevor die `scale` des URDF angewendet wird; ein vom URDF bereits skaliertes Mesh kann also doppelt verkleinert werden. Vom Editor nicht modellierte Tags (`<dynamics>`, `<safety_controller>`, `<mimic>`, `<transmission>`, `<gazebo>`, Material-Texturen) bleiben beim erneuten Export eines URDF nicht erhalten.

### URDF-Parsing und -Export

Einfaches XML über das eigene `xml.etree.ElementTree` der Standardbibliothek - keine `lxml`-Abhängigkeit für ein derart einfaches Format nötig. Das In-Memory-Modell (`hydra_editor_urdf/models.py`) ist ein bewusst schlichter, veränderbarer, hausgemachter Dataclass-Baum statt eines Wrappers um eine bestehende Python-URDF-Bibliothek wie `urdfpy` oder `yourdfpy`: Diese App muss den Baum interaktiv *bearbeiten* und jede Änderung live neu rendern, wofür eine überwiegend lesende Parsing-Bibliothek nicht ausgelegt ist, und das Modell selbst zu besitzen, hält es klein, inspizierbar und frei vom eigenen Release-Rhythmus einer Drittanbieter-Abhängigkeit. Feldnamen und Standardwerte folgen eng dem echten [URDF-XML-Schema](http://wiki.ros.org/urdf/XML), sodass Parser und Writer ein dünnes, offensichtliches XML↔Objekt-Mapping bleiben.

**xacro wird nicht expandiert.** [xacro](http://wiki.ros.org/xacro) ist ein Python/XML-Makro-Präprozessor mit einem eigenen ROS-Paket und einer eigenen Abhängigkeitskette, und eine echte xacro-Datei ist nur zuverlässig innerhalb derselben ROS-Paketumgebung auflösbar, gegen die sie verfasst wurde (Makro-Argumente, Includes im Stil von `$(find pkg)` usw.) - etwas, das diese App auf keine ehrliche Weise reproduzieren kann. Eine Datei, die `<xacro:...>`-Tags verwendet oder den xacro-Namensraum deklariert, erhält eine klare Fehlermeldung, die die Einschränkung erklärt und auf das ROS-Kommandozeilentool `xacro` verweist, um sie zuerst zu präprozessieren, statt sie stillschweigend falsch zu parsen.

Der Export (`urdf/writer.py`) serialisiert den aktuellen In-Memory-Baum von Grund auf neu, statt den ursprünglichen Quell-XML-Text zu patchen, sodass jede Live-Bearbeitung - unabhängig davon, welches Panel sie vorgenommen hat - genau einmal, über einen einzigen Codepfad, sowohl in der Menüaktion „Export URDF" als auch in der an einen STUDIO-Server gesendeten Payload widergespiegelt wird.

Die Elemente, für die das Modell kein Feld hat (`<transmission>`, `<gazebo>`, `<dynamics>`, `<safety_controller>` und `<calibration>` eines Gelenks sowie Multiplikator und Versatz eines `<mimic>`), werden beim Lesen einer Datei als Text behalten. Die Schaltfläche **Exportieren** öffnet ein Fenster, das sagt, wie viele solche Elemente die Datei hat, und einen Schalter hat, standardmäßig aus und bei jedem geladenen Roboter wieder aus, um sie so zurückzuschreiben, wie die Quelldatei sie hatte; Elemente, die ein gelöschtes Gelenk oder Glied nennen, werden nie zurückgeschrieben.

### Andockbarer Arbeitsbereich

Echte `QDockWidget`-Panels - zum Loslösen ziehen, zum Andocken zurückziehen, zu Tabs zusammenführen, den Arbeitsbereich aufteilen - derselbe Mechanismus und dieselbe Begründung, die das eigene Hauptfenster von HYDRA-UMC SUITE bereits anwendet: Das eigene Andocksystem von Qt leistet bereits genau das, was ein Arbeitsbereich im Stil von Photoshop/Fusion-360 braucht, und ein handgestricktes würde es nur mit mehr Fehlern neu erfinden. Fünf Panels, angeordnet in einem sinnvollen Standardlayout, das danach vollständig neu anordenbar ist:

- **Source** - Eingabe von GitHub-URL / lokalem Ordner, Liste gefundener `.urdf`-Dateien.
- **DOF** - das Machbarkeitsurteil und jeder dahinterliegende Grund.
- **Viewport** - die Live-3D-Ansicht, der Link-Baum, und die Jog-Schieberegler.
- **Properties** - Umfärben / Neu-Skalieren / Gelenktyp-und-Grenzen-Neusetzen für den ausgewählten Link.
- **Upload** - Verbindung zu einem STUDIO-Server, Push, oder Pull.

### Server-Roundtrip

Spricht mit dem eigenen Modell-Übermittlungsvertrag von HYDRA-UMC-SERVER (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` in der eigenen `server.ts` dieses Projekts, abgesichert hinter dem eigenen Umschalter **Config > Models > „Accept model submissions"**) unter Verwendung des eigenen `urllib.request` der Standardbibliothek - ein weiterer HTTP-Aufruf rechtfertigte nicht das Einbinden von `httpx`/`requests` für ein Projekt, das nur jemals 4 Endpunkte braucht, keine dauerhafte Live-Verbindung. Jeder Aufruf läuft in einem Hintergrund-`QThread`, damit ein langsamer oder nicht erreichbarer Server die Oberfläche niemals einfriert. Dieser Vertrag lebte früher innerhalb des eigenen Prozesses von HYDRA-UMC-STUDIO, bevor sich dieses Projekt in ein reines Frontend (STUDIO) plus ein separates headless Backend (HYDRA-UMC-SERVER, siehe **Verwandte Projekte** weiter unten) aufteilte - diese App legt keinen der beiden Namen fest im Code fest, der Bediener trägt einfach in die Host-/Port-Felder des **Upload**-Panels ein, wo das eigentliche Backend gerade läuft.

- **Login** - `POST /api/login`; nur ein Token mit `admin`-Rolle kann serverseitig überhaupt `POST /api/models/submit` erreichen, daher ist diese App tatsächlich nur mit einem Admin-Konto nutzbar, genau wie jede andere reine Admin-Funktion von STUDIO.
- **Push** - serialisiert den aktuellen Roboter zurück in URDF-XML und base64-kodiert jede Mesh-Datei, auf die dessen Visuals verweisen (aufgelöst über denselben Mesh-Resolver, der beim Import erstellt wurde), inline im Request-Body, versehen mit der vom Bediener gewählten Kategorie (spiegelt die eigenen Config > UI > Module-Visibility-Kategorien von STUDIO wider: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - eine URDF hat kein eigenes Feld, das aussagt, welche davon zutrifft). Ein Namenskonflikt kommt als eigene 409-Antwort des Servers zurück; der Bediener entscheidet, ob mit aktiviertem **Overwrite** erneut übermittelt oder umbenannt wird, diese App rät niemals selbst.
- **Pull** - lädt die URDF + Meshes eines bereits übermittelten Modells zurück in einen lokalen Arbeitsordner herunter und lädt es direkt in den Editor - die „extrahieren, bearbeiten, erneut senden"-Hälfte des Roundtrips, die den eigentlichen Zweck dieser App ausmacht, indem sie erlaubt, einen bestehenden Katalogeintrag nachzubessern, ohne wieder bei dessen ursprünglichem Quell-Repository anzufangen.

### Mehrsprachige Oberfläche

Vollständige Übersetzung der Oberfläche in **Englisch, Spanisch, Italienisch, Französisch, Deutsch, vereinfachtem Chinesisch, Japanisch und Portugiesisch** (`language/*.lng`), unter Verwendung genau desselben einfachen `SCHLÜSSEL=Wert`-Dateimechanismus wie jedes andere Python-Tool in diesem Ökosystem (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - hier nicht neu erfunden, da der Mechanismus selbst keine projektspezifische Logik trägt. Ein Sprachwechsel wird erst nach einem Neustart der App wirksam, statt jedes bereits erstellte Widget live neu zu übersetzen, entsprechend derselben Konvention. `language/` liegt **neben** der ausführbaren Datei, statt über `--add-data` von PyInstaller darin gebündelt zu sein, sodass ein Übersetzer eine `.lng`-Datei bearbeiten oder hinzufügen kann, ohne einen Neubau durchzuführen.

### Theme

Die obere Symbolleiste des andockbaren Arbeitsbereichs ist ein echtes
`QToolBar`/`QLabel`/`QToolButton`-Kommandopult, keine separate Qt-Quick/QML-UI
- eine frühere, über QQuickWidget eingebettete Version (gleiche visuelle
Engine wie HYDRA-UMC-UPDATER und HYDRA-UMC-SUITE) wurde innerhalb des echten
`QDockWidget`-Layouts dieses `QMainWindow` als durchgehend schwarzer Balken
ohne Konsolenfehler dargestellt und wurde deshalb auf einfache Widgets
zurückgesetzt; die vollständige Geschichte steht in `CHANGELOG.md`. Die
Schaltflächen Source, DOF, Viewport, Properties und Upload heben nur die
vorhandenen Docks hervor; Export und About verwenden vorhandene Aktionen
wieder, und Export bleibt deaktiviert, bis ein Modell geladen ist. Nach dem
Laden eines URDF (und nach jeder Live-Eigenschaftsänderung) zeigt sein
Status-Chip den Namen des geladenen Modells, die DOF-Anzahl und das aktuelle
Machbarkeits-Urteil. OpenGL-Viewport, Editor, Parser und Server-Upload werden
nicht ersetzt.

Verwendet die eigene `assets/qss/industrial_dark.qss` von HYDRA-UMC SUITE wörtlich wieder (gleicher relativer Pfad, gleiche Datei), statt für ein Schwester-Desktop-Tool im selben Ökosystem ein neues visuelles Theme zu entwerfen.

### Visuelles Kommandopult (`--qtquick`)

Dieser Einbettungsversuch ist etwas anderes und Separates vom echten Qt-Quick-Kommandopult, das diese App jetzt hat:

~~~
python main.py --qtquick
~~~

Ein völlig eigenständiges QML-`ApplicationWindow` (`qt_editor_urdf.py` + `assets/qml/EditorDeck.qml`), niemals in das klassische `QMainWindow` eingebettet - dasselbe bereits bewährte Muster, das HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER und HYDRA-UMC-SUITE bereits verwenden, gestartet neben dem unveränderten klassischen Einstiegspunkt, ohne ihn zu ersetzen. Es bildet das reale räumliche Layout des klassischen andockbaren Arbeitsbereichs originalgetreu nach (Source und DOF links als Tabs, Viewport und Properties nebeneinander, Upload über die volle Breite unten) sowie alle realen Funktionen seiner 5 Panels - Laden von GitHub/Galerie/lokalem Ordner, Live-DOF-Validierung, eine Orbit/Pan/Zoom-3D-Vorschau mit klickbarem Link-Baum und Jog-Schiebereglern pro Gelenk, Bearbeitung von Farbe/Skalierung/Gelenkgrenzen/Masse und Trägheit sowie den echten Verbinden/Senden/Abrufen-Kreislauf mit dem STUDIO-Server - über denselben `EditorController`, ohne eine zweite Implementierung von alldem. Die 3D-Vorschau verwendet den echten Rendering-Code des klassischen Viewports (`UrdfGLRenderer` aus `render/viewport.py`) über einen eigenen `OffscreenUrdfRenderer` wieder, denselben echten `QOpenGLContext`/`QOffscreenSurface`/Framebuffer-Ansatz, den auch das Qt-Quick-Viewport-Panel von HYDRA-UMC-SUITE bereits verwendet, über einen `QQuickImageProvider` an QML weitergereicht.

## 🔒 Sicherheit und Schutz

| Bedrohung | Abwehr | Wo |
|---|---|---|
| Ein Mesh-Pfad, der aus dem Ordner herausführt | Ein `<mesh filename>` wird nur zu einer `.stl`-, `.obj`- oder `.dae`-Datei im geöffneten Ordner, im URDF-Ordner oder in einem mit „Fehlende Meshes suchen“ hinzugefügten Ordner aufgelöst; `..`, absolute Pfade und `file://`-URIs, die woandershin führen, werden ignoriert, und nur diese Dateien werden je hochgeladen | `source/scan.py`, `render/mesh.py` |
| Eine kaputte, leere oder feindliche Mesh- oder URDF-Datei | Leere, abgeschnittene oder fehlerhafte Meshes werden als nicht geladen gemeldet, statt den Betrachter anzuhalten; Dateien, die nicht UTF-8 oder binär sind, fehlerhafter Text und ein Zyklus im Gliederbaum werden mit einer Meldung abgelehnt; ein Mesh über 5 Einheiten wird einmal als Millimeter umskaliert | `render/mesh.py`, `urdf/parser.py`, `tests/test_edge_cases.py` |
| Ein GitHub-Download, der hängt oder gar nicht von GitHub ist | Es werden nur Adressen geholt, die das GitHub-URL-Muster erkennt, als Zipball mit 20 s Zeitlimit je Anfrage und ohne `git`-Aufruf; GitHubs eigenes Limit von 60 Anfragen pro Stunde und Adresse gilt | `source/github_fetcher.py` |
| Ein Roboter, den STUDIO nicht ausführen kann, oder ein mit unmöglichen Werten gespeichertes Modell | Die Machbarkeitsprüfung akzeptiert 3 bis 6 Freiheitsgrade und lehnt schwebende und ebene Gelenke, Waisen sowie getrennte oder mehrfach verelterte Bäume ab; vor dem Speichern läuft eine Prüfung (Gelenkgrenzen, Massen) und der Export behält eine Sicherung | `urdf/dof.py`, `urdf/save_check.py` |
| Ein Modell an einen Server senden, der es nicht wollte | Der Server entscheidet: „Modelleinreichungen akzeptieren“ muss aktiv sein (Config > Modelle) und das Konto muss ein Administrator sein; jeder Aufruf hat ein Zeitlimit von 15 s und läuft in einem Hintergrund-Thread; ein bereits vorhandener Name wird abgelehnt, bis Überschreiben angehakt ist | `server/client.py` |

**Was es nie tut:** sich mit einem Roboter verbinden, einen bewegen oder einem Abnehmer eines exportierten URDF irgendeine Garantie geben. Wer die Datei verwendet, muss sie selbst prüfen.

## 🔌 Schnittstellen

| Topic oder Route | Was es trägt |
|---|---|
| URDF file or folder / GitHub address | was geöffnet wird: ein Ordner auf der Platte oder ein öffentliches GitHub-Repository als Zip; `.xacro`-Dateien werden mit einer Erklärung abgelehnt und `.dae`-Meshes als nicht unterstützt benannt |
| URDF export | der gesamte Baum wird von `urdf/writer.py` aus dem Modell neu geschrieben, sodass jede Änderung genau einmal in der Datei steht; die überschriebene Datei wird vorher gesichert |
| `POST /api/login` | meldet an; nur ein `admin`-Token erreicht die Einreichungsroute, und der Client kommt mit einem Server zurecht, der schon zum Auflisten der Modelle eine Anmeldung verlangt |
| `POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` | sendet das URDF mit eingebetteten Meshes, listet den Katalog und holt ein eingereichtes Modell in einen lokalen Arbeitsordner zurück |

## ⚙️ Konfiguration

Es gibt eine kleine Konfigurationsdatei und die festgelegten Abhängigkeiten; aus der Umgebung wird sonst nichts gelesen.

| Variable | Standard | Was sie festlegt |
|---|---|---|
| `hydra_editor_urdf_config.json` | `{"language": ...}` | die Sprache des Fensters, eine der acht `.lng`-Dateien in `language/`; die Datei liegt neben dem Programm |
| `requirements.txt` | festgelegt | numpy 2.5.2, numpy-stl 4.0.0, PyOpenGL 3.1.10 und PySide6 6.11.1 |
| `MIN_SUPPORTED_DOF`, `MAX_SUPPORTED_DOF` | 3, 6 | die Freiheitsgrade, die STUDIO ausführen kann, in `urdf/dof.py`; dort ändern, wenn sich STUDIO ändert |

## 🚀 Schnellstart

Benötigt Python 3.11 oder neuer und einen Grafiktreiber mit OpenGL 3.3. Die Pakete sind in `requirements.txt` festgelegt und es ist kein `git` nötig: Die GitHub-Quellen werden als Zip geladen.

```bash
pip install -r requirements.txt  # installs PySide6, PyOpenGL, numpy and numpy-stl at the pinned versions
python main.py                   # starts the editor (run.bat or run.sh do the same inside a .venv when there is one)
python main.py --qtquick         # the separate Qt Quick command deck
python -m pytest tests -q        # runs the tests (pip install -r requirements-dev.txt first)
```

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

Oder das Komfort-Skript nutzen - `run.bat` (Windows) / `run.sh` (Linux/Mac), das `.venv` aktiviert, falls es daneben liegt, und Argumente an `main.py` weiterreicht; keines der beiden schließt sein Terminalfenster von selbst bei Doppelklick.

Startet maximiert (kein echtes Vollbild auf Betriebssystemebene, sodass die native Fenstertitelleiste und ihre Steuerelemente sichtbar bleiben) - drücken Sie **F11**, um zwischen echtem randlosem Vollbild und diesem Zustand umzuschalten.

## 🧪 Tests

372 automatische Tests laufen mit `python -m pytest tests -q`. Sie brauchen weder Hardware noch etwas außerhalb dieses Rechners.

Die CI führt `HYDRA_UMC_CI=1 python tools/ci_validate.py` aus; das prüft das Manifest, die Dokumente, die acht READMEs und die Bilder.

### Automatisierte Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Hinweis: die eigene reine Logik dieser App (URDF-Parsing/-Export, DOF-Machbarkeitsprüfung, Vorwärtskinematik, Trägheitsschätzung, Mesh-Referenzauflösung, GitHub-Abruf, i18n) hatte null automatisierte Testabdeckung. Behoben: 372 echte Tests über 15 Testmodule, von denen keines PySide6/PyOpenGL importiert - `requirements-dev.txt` installiert nur das, was `tests/` tatsächlich braucht (`numpy` + `pytest`), sodass die Suite ohne Display oder Qt-Plattform-Plugin läuft. Mehrere Tests sind explizite Regressionstests für Bugs, die bereits zuvor gefunden und behoben wurden und direkt im Quellcode dokumentiert sind (die Schutzmaßnahme gegen die Endlosschleife bei einem echten Zyklus in `render/kinematics.py`, die `had_scheme`-Bedingung in `source/scan.py`, die Prüfung auf negative Masse in `urdf/dof.py`) - eine zukünftige Änderung kann keinen davon mehr stillschweigend wieder einführen, ohne dass ein Test fehlschlägt. Die CI (`.github/workflows/ci.yml`) führt bei jedem Push denselben Befehl aus.

## 🏗️ Build und Veröffentlichung

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

## 🩺 Fehlerbehebung

| Du siehst | Weil | Tu |
|---|---|---|
| Ein Fehler, der xacro nennt, oder ein Glied, das im Betrachter fehlt | Die Datei verwendet `<xacro:...>`-Makros, die nicht expandiert werden, oder das Glied zeigt auf ein `.dae`-Mesh, das nicht geladen wird | Expandiere das xacro zuerst mit dem ROS-Werkzeug `xacro` und exportiere die Meshes als `.stl` oder `.obj` |
| Glieder ohne Mesh nach dem Öffnen eines Repositorys | Die Mesh-Pfade lassen sich im geöffneten Ordner nicht auflösen, oder die Meshes sind leer oder fehlerhaft | Nutze „Fehlende Meshes suchen“, um den Ordner mit ihnen hinzuzufügen |
| Das DOF-Panel meldet, der Roboter sei nicht machbar | Der Roboter hat weniger als 3 oder mehr als 6 Freiheitsgrade, ein schwebendes oder ebenes Gelenk, ein verwaistes Glied oder einen getrennten oder mehrfach verelterten Baum | Lies die unter dem Urteil aufgeführten Gründe und bearbeite Gelenktypen und -grenzen im Eigenschaften-Panel |
| Das Senden wird abgelehnt: ein 409, ein 401 oder „Einreichungen werden nicht akzeptiert“ | Der Name existiert schon (409), das Konto ist kein Administrator oder die Sitzung ist weg (401), oder beim Server ist „Modelleinreichungen akzeptieren“ aus | Hake Überschreiben an, melde dich als Administrator an oder schalte die Einreichungen in Config > Modelle des Servers ein |

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-EDITOR-URDF" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
HYDRA-UMC-EDITOR-URDF/
├── hydra_editor_urdf/
│   ├── __init__.py                  __version__ - einzige Quelle der Wahrheit, gelesen vom Über-Dialog und neu geschrieben von bump_version.py
│   ├── app.py                       EditorController - alleiniger Besitzer von „was geladen ist", Qt-Signale, denen jedes Panel zuhört
│   ├── models.py                    Hausgemachter URDF-Objektbaum (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                   Startliste echter, verifizierter öffentlicher Robotermodell-Repositories
│   ├── inertia_calc.py              Geschlossene Trägheitsmoment-Formeln für die primitiven Geometrien
│   ├── i18n.py                      Loader für language/*.lng, Persistenz der Konfiguration - portiert aus der eigenen i18n.py von HYDRA-UMC-SUITE
│   ├── urdf/                        Parser, Writer, DOF und Speicherprüfung
│   ├── render/                      Meshes, Vorwärtskinematik, OpenGL-Ansicht
│   ├── source/                      GitHub-Download und lokale Ordner
│   ├── server/                      der Client von HYDRA-UMC-SERVER
│   └── ui/                          Fenster, Docks, Dialoge und Thema
├── assets/                          Symbol, dunkles Thema und das Qt-Quick-Bedienfeld
├── images/                          Banner und Bilder der README
├── language/                        english/spanish/italian/french/german/japanese/chinese/portuguese.lng - liegt neben der exe, nicht gebündelt
├── docs/                            Dokumente des Projekts
├── tests/                           Echte pytest-Suite (355 Tests) - nur reine Logik, hier wird nirgends PySide6 importiert
├── tools/                           Projektwerkzeuge und CI-Prüfungen
├── .github/                         CI-Workflow und Issue-Vorlagen
├── main.py                          Einstiegspunkt - QApplication, Theme, maximierter Start, F11-Vollbild-Umschalter; --qtquick wechselt zum Panel unten
├── qt_editor_urdf.py                Qt-Quick-Frontend - eigenständiges `--qtquick`-Kommandopult, verbindet den unveränderten EditorController mit QML
├── run.bat / run.sh                 Komfort-Skript - aktiviert .venv falls vorhanden, startet main.py, schliesst sich nicht selbst
├── requirements.txt                 PySide6, PyOpenGL, numpy-stl, numpy (fest gepinnt)
├── requirements-dev.txt             Nur numpy + pytest - was tests/ tatsaechlich braucht, ohne PySide6
├── build_exe.bat / build_exe.sh     Build-Skripte für eigenständige Windows-/Linux-Executables (PyInstaller) - erhöht zuerst die Versionsnummer
├── build-test.bat / build-test.sh   Build-/Kompilierprüfung ohne Versionserhöhung
├── HYDRA-UMC_EDITOR-URDF.spec       PyInstaller-Build-Spec, verwendet von build_exe.bat/.sh
├── bump_version.py                  ausdrückliche Versionserhöhung
├── bump_manifest_version.py         Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
├── CHANGELOG.md                     Versionshistorie
├── LICENSE                          GPL-3.0-or-later
├── hydra-umc.project.json           Manifest: Version, Reifegrad, Familie
└── test.sh                          Build-Prüfung ohne Änderungen
```

</details>

## 🗺️ Roadmap und bekannte Grenzen

xacro-Makros werden nicht expandiert und COLLADA-Meshes (`.dae`) nicht geladen; beides ergibt eine klare Fehlermeldung. Ein Roboter muss in 3 bis 6 Freiheitsgrade passen, damit STUDIO ihn akzeptiert. Der Server-Hin-und-Rück-Weg wurde nur gegen einen lokalen Testserver erprobt, nicht gegen einen echten HYDRA-UMC-SERVER. Das Qt-Quick-Bedienfeld ist ein eigenes `--qtquick`-Fenster und nicht Teil des andockbaren Arbeitsbereichs.

## 🌍 Sprachen

Diese README und die Dokumente des Repositorys gibt es in acht Sprachen: Englisch, Spanisch, Deutsch, Französisch, Italienisch, Japanisch, Chinesisch und Portugiesisch (Portugal). Sie entstehen gemeinsam, und die CI prüft, dass die acht Dateien dieselben Abschnitte und dieselben Links haben.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage tatsächlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Übergeordnetes Projekt**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — der Modellkatalog, den dieser Editor befüllen soll; das fertige Ergebnis wird direkt über `POST /api/models/submit` an einen laufenden STUDIO-Server gesendet.

**Direkt Verwandt**
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — Schwester-Desktop-Editor für die rohe STL-Geometrie desselben Modellkatalogs, statt der URDF-/Kinematik-Seite, die dieses Werkzeug bearbeitet.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — besitzt den echten Endpunkt `POST /api/models/submit`, an den dieser Editor fertige Modelle sendet.
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — verwendet die hier erstellten URDF-Modelle, um seine Physiksimulation anzutreiben.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — verwendet die hier erstellten URDF-Modelle, um seine Physiksimulation anzutreiben.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — erzeugt Trainingsdaten aus den hier erstellten Modellen.

**Ebenfalls Teil des Ökosystems**

*Hardware- und Plattform-Kern*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Software-Auftragsschranke, gegen die jede Bridge ihre Befehle validiert (keine zertifizierte Sicherheitsfunktion).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — deklaratives Adapter-Manifest-Register und Validator für Konnektoren externer Maschinen; erweitert die eigene Vertragsidee des SDK auf externe Maschinen, ohne die Industrie-Gateway-Projekte zu ersetzen.

*Kern-Backend und Clients*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — der Entwurf des Motherboards des Roboterarms: CM5-Host + Dual-Core-STM32H745, gedacht zur Koordination von bis zu 8 Werkzeugarmen über CAN-OTA/SPI-OTA (Firmware in einer frühen Phase; noch keine bestückte Platine).
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarm-Kommandozentrale (PySide6) für mehrere Server gleichzeitig.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und gekoppeltem Wear-OS-Begleiter.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisation.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-Oberfläche für den eingebauten 7"-DSI-Touchscreen direkt auf der CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen VDA-5050-MQTT-Publisher (nur gegen eine emulierte Flotte getestet).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit GRBL-Status-/Steuerbyte-Zugriff (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem Boston-Dynamics-Spot-Befehlssender (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Koordinator für Laserzellen, liest 3 Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Signale (nur gegen einen simulierten Chip getestet; kann keinen Laser scharfschalten oder auslösen).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer hochrangiger Board-Flow-Koordinator für OpenPnP-Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsgrenze für Moonraker-/Klipper-3D-Drucker, mit real gesperrten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Koordinator mit einem träge importierten rclpy-ROS-2-Transport (noch nicht gegen eine ROS-2-Installation ausgeführt).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem MAVLink-Befehlssender (nur gegen einen Emulator getestet).

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Boards, CAN-OTA plus vollständiges SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnose-Tool für URTC-Boards, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, keine lokale Installation nötig.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — Gateway vor dem CAN-Bus von URTC: Liste erlaubter Kennungen, Ratenbegrenzung und Sitzungsschlüssel; Software auf dem Computer getestet, noch nicht an einem echten Bus.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrations-Hub für die Hailo-8-Vision-Pipeline, mit einer echten Hardware-Bereitschaftsprüfung pro Stufe.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echtes Registry für kompilierte Modelle mit sicherer Hailo-Architektur-/Checksummenprüfung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit echter HailoRT-Integrationsgrenze.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based-Visual-Servoing-Korrekturgesetz mit Freigabe abhängig vom Zonenstatus; noch keine Posenschätzung per Kamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und Notaus-Anforderung, mit Durchsetzung der Kalibrierungsaktualität.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrations-Hub für die kognitive Hailo-10-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Codierung/-Decodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungspflichtigen Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur-stdlib-basierte TF-IDF-Dokumentensuche über die eigene Markdown-Dokumentation dieses Ökosystems.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — lokaler, richtlinien-gesteuerter KI-Wartungstechniker für das Ökosystem selbst - beobachtet, diagnostiziert und schlägt Korrekturen vor; die zwei höchsten Risikostufen sind absichtlich noch nicht implementiert.

*Orchestrierung und Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrations-Hub mit einem echten gRPC-/Protobuf-Health-Report-Vertrag und Missions-Zustandsautomat.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Gesundheits-Watchdog mit Retry/Backoff und Identitätsabweichungserkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet für Multi-Zellen-Konvergenz.

*Digitaler Zwilling und Simulation*
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — Hardware-in-the-Loop-Router mit einer Software-Kollisionsverriegelung zwischen Simulation und echter Hardware (ohne echte Hardware getestet).

*Daten und Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Query-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Baseline-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über die DATALAKE-Historie, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN-/WebSocket-Ingestion-Pipeline nach DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrations-Hub, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Client-Sitzung im Binärprotokoll.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-XML-Endpunkte `/probe` und `/current` mit Ausgabe im Degraded-Modus.

*Ergänzende Tools und Ökosystem-Operationen*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit haptischen Alarmmustern und einem Sprach-Relay zum gekoppelten Telefon (noch nicht auf einer physischen Uhr ausgeführt).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Board-Montage-Rack mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen thermischen/RGB-Inspektionswerkzeugkopf.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux-Desktop-Tool, das ein flashbereites CM5-Image baut, vorgeladen mit den aktuellsten Versionen des Ökosystems, mit Ersteinrichtungs-Konfiguration für WLAN/Benutzer/SSH im Stil von Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — Wartungsvorfall-Koordinator: eine Edge-Rolle mit niedrigem Privileg sammelt einen bereinigten Inventar-/Gesundheits-Snapshot, eine Control-Plane-Rolle rendert ihn schreibgeschützt und bittet einen KI-Anbieter um einen Diagnosevorschlag - wendet nie einen Patch an und stellt nie etwas bereit.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproduzierbarer Entwicklungshost (Raspberry Pi 5 / CM5), der den Quellcode des Ökosystems vorhält und begrenzte Build-/Test-Aufgaben über eine dauerhafte Warteschlange ausführt; eine dedizierte Entwicklerrolle, ausdrücklich kein operativer CM5.

## 📚 Dokumentation

Hier steht mehr:

* [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md) - jede Quelldatei des Editors mit einer Zeile dazu, was sie tut
* [docs/LICENSING.md](docs/LICENSING.md) - wie Code, Dokumente und Meshes lizenziert sind
* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — der eigene interne Aufbau des Editors: warum Parsing, Machbarkeitsprüfung, Mesh-Auflösung und 3D-Vorschau getrennte Bahnen sind, und was diese App bewusst **nicht** tut (sich mit einem Roboter verbinden, ein URDF hochladen oder eigenständig eine Bewegung befehligen).
* **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** — der nicht-verändernde Validierungspfad `build-test.bat`/`.sh` im Vergleich zu einem echten Paket via `build_exe.bat`/`.sh`, und was das Kommandopult heute tatsächlich ist (`QToolBar`, kein Qt Quick/QML - siehe Abschnitt **Theme** oben).
* **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** — was ein nachgelagerter Konsument einer exportierten URDF-Datei selbst prüfen muss; dieses Projekt stellt selbst keinen Netzwerk-Endpunkt und keine Hardware-Steuerungsautorität bereit.
* [Sicherheitsgrundlage des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Bedrohungsmodell des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Änderungsprotokoll dieses Repositorys](CHANGELOG.md)
* [Lizenz dieses Repositorys](LICENSE.md)

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (oder `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`) aus: Es muss `CI_VALIDATION=PASS` ausgeben. Führe dafür nicht `build.sh` oder `build.bat` aus; Bauen ist keine Prüfung.
* Die acht READMEs entstehen aus einer einzigen Quelle in HYDRA-UMC-DOCS; bearbeite sie nicht von Hand. Ändere die Quelle und schreibe sie mit `tools/make_readmes.py` neu.
* Behaupte in einer README nichts, was nicht gelaufen ist: Schreibe „simuliert“ oder „nicht auf Hardware erprobt“, wo das stimmt.
* Siehe [CONTRIBUTING.md](CONTRIBUTING.md), den [Verhaltenskodex](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) und [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - [LICENSE](LICENSE).
