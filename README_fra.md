<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>
# 🦾 HYDRA-UMC EDITOR-URDF

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Langage-Python%203.11-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="URDF">
</p>

### 🖌️ Créateur/Éditeur graphique de URDF pour le catalogue de modèles de HYDRA-UMC-STUDIO

**Version actuelle :** 0.0.0 (`MAJOR.MINOR.PATCH` - voir la section **Build de production** ci-dessous pour comprendre comment ce numéro évolue)

---

## 🎯 Aperçu

**HYDRA-UMC EDITOR-URDF** est l'outil de bureau qui transforme le fait de « porter un nouveau robot dans le catalogue de modèles de [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) » - jusqu'ici une investigation manuelle, propre à chaque robot - en un flux de travail graphique et reproductible. Chaque modèle de robot réel du catalogue de STUDIO y est arrivé de la même façon par le passé : trouver un dépôt de description sur GitHub, comprendre comment ses références de maillage se résolvent, compter les degrés de liberté de sa chaîne cinématique, vérifier si STUDIO peut réellement en piloter autant, et placer le résultat à la main dans `public/models/`. Cette application automatise l'ensemble de ce processus - récupérer les fichiers source depuis une URL GitHub ou un dossier local déjà téléchargé, résoudre chaque référence `<mesh filename="...">` (URIs `package://` incluses) contre les fichiers réels présents sur le disque, valider le nombre de DDL de la chaîne par rapport à ce que la cinématique de STUDIO prend en charge aujourd'hui, éditer couleur/échelle/limites de joint/type de joint avec un aperçu 3D en direct, et pousser le résultat final directement vers un serveur STUDIO en cours d'exécution.

Construit avec **Python** et **PySide6/Qt6**, en utilisant les mêmes patrons architecturaux déjà validés dans l'autre outil de bureau de cet écosystème, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE) : un espace de travail ancrable (`QDockWidget`) de style Photoshop/Fusion 360, une vue 3D OpenGL écrite à la main (`QOpenGLWidget` + shaders GLSL 3.3 en profil core, aucun chemin hérité `glBegin`/`glEnd`), et un objet contrôleur central unique qui possède l'état et que chaque panneau de l'interface écoute via des signaux Qt. Réutiliser ce patron ici - plutôt que d'explorer une nouvelle pile UI/rendu pour un outil frère du même écosystème - est un choix délibéré, pas un oubli.

**Note d'honnêteté, conforme à la même convention de documentation que le reste de cet écosystème :** cette application n'expanse pas les macros [xacro](http://wiki.ros.org/xacro), et ne charge pas les maillages COLLADA (`.dae`). Ce sont là deux limitations explicites et nommées (un message d'erreur clair, pas une analyse silencieusement erronée ou un lien manquant dans la vue 3D) plutôt qu'une tentative à moitié implémentée - voir les sections **Analyse de URDF** et **Chargement des maillages** ci-dessous pour comprendre pourquoi une véritable prise en charge de l'un ou l'autre exigerait un travail supplémentaire conséquent.

---

## 📥 Chargement de la source - GitHub ou dossier local

Deux façons de pointer l'application vers les fichiers source d'un robot, toutes deux aboutissant au même chemin d'import :

- **Depuis une URL GitHub** - accepte une URL complète `https://github.com/owner/repo` (avec ou sans `/tree/<branch>`), une URL de style SSH `git@github.com:owner/repo.git`, ou le raccourci brut `owner/repo`. Ne lance délibérément **pas** de sous-processus `git clone`, ce qui rendrait une installation `git` une dépendance d'exécution obligatoire sous Windows comme sous Linux pour quelque chose qu'un simple téléchargement HTTPS accomplit déjà : GitHub sert une archive zip de n'importe quelle branche/tag/commit depuis `codeload.github.com` sans authentification nécessaire pour un dépôt public, donc ceci utilise uniquement les modules `urllib.request` + `zipfile` de la bibliothèque standard et rien d'autre. Seuls les dépôts publics sont pris en charge - il n'y a aucune gestion de token/identifiants, et l'archive zip d'un dépôt privé renvoie un 404 comme celle d'un dépôt inexistant.
- **Depuis un dossier local** - pour un dépôt déjà téléchargé à la main, ou une copie de travail que l'opérateur est en train de modifier en dehors de cette application.

Dans les deux cas, l'application trouve ensuite récursivement chaque fichier `*.urdf`/`*.xacro` sous le dossier choisi, les liste tous (un dépôt de description de robot réel en fournit souvent plus d'un - un bras nu plus une variante « avec pince » est un appariement courant), et sélectionne automatiquement le plus volumineux par taille de fichier comme choix par défaut raisonnable pour « le principal » - passer à un autre candidat ensuite se fait en un double-clic dans le panneau Source, sans nouveau téléchargement.

**La résolution des références de maillage** est le véritable travail peu glamour que chaque session passée de portage manuel de robot dans cet écosystème a fait à la main : un `<mesh filename="package://some_pkg/meshes/link1.stl"/>` d'un URDF n'est essentiellement jamais un chemin directement ouvrable une fois que le fichier se trouve dans un simple dossier téléchargé plutôt que dans un espace de travail ROS actif, où `package://` se résout via l'index de paquets ROS. Le résolveur essaie, dans l'ordre : (1) la référence comme chemin relatif au propre dossier du URDF, (2) la même référence avec un segment de nom de paquet de style `package://` initial retiré, (3) comme chemin absolu si elle en est déjà un, et (4) par simple nom de fichier de base n'importe où sous le dossier source - ce qui est ce qui prend en charge en réalité une véritable URI `package://`, puisque le schéma et le nom du paquet n'ont aucun sens en dehors d'un espace de travail ROS actif, mais le nom du fichier de maillage lui-même reste trouvable.

---

## ✅ Validation de faisabilité en DDL

La version automatisée du même jugement que les sessions passées propres de cet écosystème ont porté à la main pour chaque robot ajouté au catalogue de STUDIO : **la propre cinématique de STUDIO prend en charge aujourd'hui les chaînes sérielles à 3, 4, 5 et 6 DDL** (son `RobotState.joints` est une correspondance fixe `j1..j6`) - une poignée de bras candidats réels, avec licence claire, recherchés par le passé, se sont révélés avoir 7, 8 ou 9 DDL et ont été écartés exactement pour cette raison, pas hypothétiquement. À chaque import (et après chaque édition en direct susceptible de changer ce nombre - retyper un joint, par exemple), l'application parcourt le véritable graphe de joints parent/enfant et rapporte :

- **Nombre de DDL** - seuls les joints `revolute`/`continuous`/`prismatic` comptent comme un véritable degré de liberté contrôlable ; `fixed` n'en apporte aucun.
- **Types de joint non pris en charge** - un seul joint `floating` ou `planar` n'importe où dans la chaîne rend l'ensemble du robot infaisable, quel que soit le nombre de DDL, puisque le modèle de joint de STUDIO n'a de représentation pour aucun des deux.
- **Intégrité de l'arborescence** - exactement un lien racine est requis (une véritable arborescence, pas une forêt ni un cycle) ; tout lien non atteignable depuis cette racine par une chaîne de joints est signalé comme déconnecté, et tout lien référencé par aucun joint du tout comme orphelin.
- **`<limit>` manquant** - requis par la spécification URDF pour tout ce qui n'est pas un joint `continuous` ; signalé par joint si absent.

Le verdict et chaque raison qui le sous-tend s'affichent en direct dans le panneau DOF, et le panneau Upload refuse de pousser un robot infaisable vers un serveur.

---

## 🎨 Édition en direct avec un véritable aperçu 3D

Le panneau Properties modifie le lien actuellement sélectionné dans l'arbre de liens du panneau Viewport, et chaque édition modifie le modèle chargé sur place et le revalide/re-rend via un unique signal (`EditorController.notify_tree_changed`) - aucun panneau n'a besoin de savoir comment la vue 3D ou le rapport DOF réagit à sa propre édition :

- **Recoloration** - le matériau visuel d'un lien, choisi via une boîte de dialogue de couleur standard. Un matériau partagé par nom entre plusieurs liens (une déclaration `<material name="...">` de premier niveau d'un véritable URDF, référencée par plus d'un `<visual>`) recolore ensemble tous les liens qui le partagent, conformément à ce que cette syntaxe de matériau partagé signifie réellement dans la spécification.
- **Redimensionnement** - un facteur d'échelle par axe (X/Y/Z) sur la propre transformation `<mesh scale="...">` de la géométrie d'un maillage, pas une réécriture destructrice des données de triangles du maillage lui-même - la même édition réappliquée plus tard repart à chaque fois du maillage original, non modifié.
- **Retyper et re-limiter un joint** - changer le type d'un joint (l'un quelconque des 6 que définit la spécification URDF) et sa limite inférieure/supérieure, avec le verdict du panneau DOF se mettant à jour immédiatement, puisqu'un retypage peut changer le nombre de DDL ou introduire un type non pris en charge.

Le **panneau Viewport** héberge la vraie vue 3D OpenGL ainsi qu'un curseur de mouvement (« jog ») par joint mobile, de sorte que l'opérateur puisse prévisualiser le URDF se déplaçant à travers sa propre plage réelle avant même de toucher à STUDIO. La cinématique directe (`render/kinematics.py`) est générique quel que soit l'arbre qui vient d'être importé - contrairement au propre module de cinématique de HYDRA-UMC SUITE, qui pilote un registre fixe de quelques dizaines de modèles de robots connus, vérifiés à la main, cette application doit poser un URDF arbitraire, jamais vu auparavant, elle compose donc le véritable `<origin>`/`<axis>` de chaque joint (formule de rotation de Rodrigues pour un axe revolute arbitraire, pas seulement le raccourci de direction cardinale sur lequel un registre fixe pourrait s'appuyer) en parcourant le véritable graphe parent/enfant.

**Z vers le haut, pas Y vers le haut** - la seule divergence délibérée par rapport à la propre convention de vue 3D de HYDRA-UMC SUITE : URDF est lui-même un format Z-up (la gravité est `-Z`, chaque `<origin>`/`<axis>` d'un fichier source est rédigé en partant de cette hypothèse), et le rôle de cette application est de montrer et d'éditer un URDF fidèlement dans sa propre convention, pas de le réorienter selon ce qu'une visionneuse en aval (la scène Three.js de STUDIO, la propre scène OpenGL de SUITE) préfère par ailleurs.

---

## 🗂️ Chargement des maillages

`.stl` (via `numpy-stl`) et `.obj` (un petit chargeur Wavefront écrit à la main - uniquement `v`/`vn`/`f`, les faces n-gones triangulées en éventail) sont tous deux de première classe. **COLLADA (`.dae`) n'est pas pris en charge** - c'est un format de scène-graphe XML bien plus vaste (animation squelettique, systèmes de coordonnées multiples, matériaux/textures intégrés) qui nécessiterait un véritable analyseur pour être géré honnêtement, plutôt qu'une estimation au mieux des balises qu'un `.dae` « simple » utilise par hasard ; un lien qui en référence un obtient une erreur claire et nommée plutôt que de manquer silencieusement dans la vue 3D ou de faire planter tout l'import. Chaque maillage chargé reçoit aussi la même garde défensive millimètre-contre-mètre que le propre `useRealScaleSTL()` de HYDRA-UMC STUDIO et le propre chargeur de maillage de HYDRA-UMC SUITE appliquent : un lien de plus de 5 mètres réels sur n'importe quel axe est bien plus probablement un export à l'échelle millimétrique sans métadonnées d'unité qu'une véritable pièce géante de robot, et est redimensionné automatiquement par 0,001.

---

## 📜 Analyse et export de URDF

XML pur via le propre `xml.etree.ElementTree` de la bibliothèque standard - aucune dépendance `lxml` n'est nécessaire pour un format aussi simple. Le modèle en mémoire (`hydra_editor_urdf/models.py`) est un arbre de dataclasses interne, délibérément simple et mutable, plutôt qu'une enveloppe autour d'une bibliothèque Python URDF existante telle que `urdfpy` ou `yourdfpy` : cette application a besoin d'*éditer* l'arbre de façon interactive et de re-rendre chaque changement en direct, ce pour quoi une bibliothèque d'analyse plutôt orientée lecture n'est pas conçue, et posséder le modèle en propre le garde petit, inspectable, et libre du cycle de publication propre d'une dépendance tierce. Les noms de champs et les valeurs par défaut suivent de près le véritable [schéma XML de URDF](http://wiki.ros.org/urdf/XML), de sorte que la paire analyseur/écrivain reste une correspondance XML↔objet fine et évidente.

**xacro n'est pas expansé.** [xacro](http://wiki.ros.org/xacro) est un préprocesseur de macros Python/XML doté de son propre paquet ROS et de sa propre chaîne de dépendances, et un véritable fichier xacro n'est fiablement résolvable qu'à l'intérieur du même environnement de paquet ROS contre lequel il a été rédigé (arguments de macro, inclusions de style `$(find pkg)`, etc.) - quelque chose que cette application n'a aucun moyen de reproduire honnêtement. Un fichier qui utilise des balises `<xacro:...>` ou déclare l'espace de noms xacro obtient une erreur claire expliquant la limitation et pointant vers l'outil en ligne de commande ROS `xacro` pour le prétraiter d'abord, plutôt qu'une analyse silencieusement erronée.

L'export (`urdf/writer.py`) re-sérialise l'arbre en mémoire actuel entièrement depuis zéro plutôt que de rapiécer le texte XML source original, de sorte que chaque édition en direct - quel que soit le panneau qui l'a effectuée - se reflète exactement une fois, via un seul chemin de code, à la fois dans l'action de menu « Export URDF » et dans le payload envoyé à un serveur STUDIO.

---

## 🖥️ Espace de travail ancrable

De véritables panneaux `QDockWidget` - faites-les glisser pour les détacher, faites-les glisser en retour pour les ré-ancrer, fusionnez-les en onglets, divisez l'espace de travail - le même mécanisme et le même raisonnement que la propre fenêtre principale de HYDRA-UMC SUITE applique déjà : le propre système d'ancrage de Qt fait déjà exactement ce qu'un espace de travail de style Photoshop/Fusion 360 exige, et un système écrit à la main ne ferait que le réinventer avec plus de bugs. Cinq panneaux, disposés selon une mise en page par défaut sensée, entièrement réarrangeable ensuite :

- **Source** - saisie d'URL GitHub / de dossier local, liste des `.urdf` trouvés.
- **DOF** - le verdict de faisabilité et chaque raison qui le sous-tend.
- **Viewport** - la vue 3D en direct, l'arbre de liens, et les curseurs de mouvement (« jog »).
- **Properties** - recoloration / redimensionnement / retypage-et-relimitation pour le lien sélectionné.
- **Upload** - connexion à un serveur STUDIO, envoi (push), ou récupération (pull).

---

## ☁️ Aller-retour avec le serveur

Communique avec le propre contrat de soumission de modèles de HYDRA-UMC-SERVER (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` dans le propre `server.ts` de ce projet, protégé derrière son propre commutateur **Config > Models > « Accept model submissions »**) en utilisant le propre `urllib.request` de la bibliothèque standard - un appel HTTP de plus ne justifiait pas d'intégrer `httpx`/`requests` pour un projet qui n'a besoin que de 4 points de terminaison, pas d'une connexion persistante en direct. Chaque appel s'exécute sur un `QThread` en arrière-plan, de sorte qu'un serveur lent ou inaccessible ne fige jamais l'interface. Ce contrat vivait autrefois à l'intérieur du propre processus de HYDRA-UMC-STUDIO, avant que ce projet ne se scinde en un frontend pur (STUDIO) plus un backend headless séparé (HYDRA-UMC-SERVER, voir **Projets liés** ci-dessous) - cette application ne fige aucun des deux noms dans le code, l'opérateur se contente de pointer les champs hôte/port du panneau **Upload** vers l'endroit où tourne réellement le backend.

- **Login** - `POST /api/login` ; seul un jeton de rôle `admin` peut réellement atteindre `POST /api/models/submit` côté serveur, donc cette application n'est réellement utilisable que contre un compte admin, comme toute autre fonctionnalité de STUDIO réservée aux admins.
- **Push** - sérialise le robot actuel en retour vers du XML URDF et encode en base64 chaque fichier de maillage que ses visuels référencent (résolu via le même résolveur de maillage construit au moment de l'import) directement dans le corps de la requête, étiqueté avec la catégorie choisie par l'opérateur (reflétant les propres catégories de Config > UI > Module Visibility de STUDIO : Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - un URDF n'a aucun champ propre indiquant laquelle de ces catégories il représente). Une collision de nom revient sous la forme de la propre réponse 409 du serveur ; l'opérateur décide de resoumettre avec **Overwrite** coché ou de renommer, cette application ne devine jamais.
- **Pull** - télécharge en retour le URDF + les maillages d'un modèle déjà soumis vers un dossier de travail local et le charge directement dans l'éditeur - la moitié « extraire, éditer, renvoyer » de l'aller-retour propre du but de cette application, permettant de retoucher une entrée de catalogue existante sans repartir de son dépôt source original.

---

## 🌐 Interface multilingue

Traduction complète de l'interface en **anglais, espagnol, italien, français et allemand** (`language/*.lng`), en utilisant exactement le même mécanisme de fichier `CLÉ=Valeur` simple que tout autre outil Python de cet écosystème (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - pas réinventé ici, puisque le mécanisme lui-même ne porte aucune logique propre au projet. Un changement de langue prend effet après un redémarrage de l'application plutôt que de retraduire chaque widget déjà construit en direct, conformément à cette même convention. `language/` se trouve **à côté** de l'exécutable plutôt que d'être intégré à l'intérieur via le `--add-data` de PyInstaller, de sorte qu'un traducteur puisse modifier ou ajouter un fichier `.lng` sans reconstruction.

---

## 🎛️ Thème

Réutilise verbatim le propre `assets/qss/industrial_dark.qss` de HYDRA-UMC SUITE (même chemin relatif, même fichier) plutôt que de concevoir un nouveau thème visuel pour un outil de bureau frère du même écosystème.

---

## 📂 Structure du dépôt

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # Point d'entree - QApplication, theme, demarrage maximise, bascule plein ecran F11
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (versions figees)
├── build_exe.bat / build_exe.sh    # Scripts de build d'executable autonome Windows/Linux (PyInstaller) - fait d'abord monter le numero de version
├── bump_version.py                 # Incrementation de version de type compteur kilometrique, appelee par build_exe.bat/.sh avant chaque build reel
├── CHANGELOG.md                    # Historique des versions
├── README.md                       # Ce fichier
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  # <- traductions
├── LICENSE                         # GPL-3.0
├── assets/
│   └── qss/industrial_dark.qss     # Reutilise verbatim depuis HYDRA-UMC-SUITE
├── language/                       # english/spanish/italian/french/german.lng - se trouve a cote de l'exe, pas integre
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ - source unique de verite, lue par la boite de dialogue A propos et reecrite par bump_version.py
│   ├── app.py                      # EditorController - proprietaire unique de "ce qui est charge", signaux Qt que chaque panneau ecoute
│   ├── models.py                   # Arbre d'objets URDF interne (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── i18n.py                     # Chargeur de language/*.lng, persistance de la configuration - porte depuis le propre i18n.py de HYDRA-UMC-SUITE
│   ├── urdf/
│   │   ├── parser.py               # URDF XML -> arbre models.py (ElementTree, xacro detecte et rejete avec une erreur claire)
│   │   ├── writer.py                # Arbre models.py -> chaine XML URDF (export + payload d'upload serveur)
│   │   └── dof.py                  # Comptage des DDL, validation de faisabilite par rapport au plafond de 3-6 DDL de STUDIO
│   ├── render/
│   │   ├── mesh.py                 # Chargement STL/OBJ, generation de primitives boite/cylindre/sphere, garde mm-contre-m
│   │   ├── kinematics.py           # Cinematique directe generique sur un arbre importe arbitraire (Z-up, propre convention de URDF)
│   │   └── viewport.py             # QOpenGLWidget - shader core GLSL 3.3, camera orbitale, buffers GPU par lien
│   ├── source/
│   │   ├── scan.py                 # Trouve les fichiers .urdf/.xacro, construit le resolveur de nom de fichier de maillage conscient de package://
│   │   ├── github_fetcher.py       # Telechargement + extraction d'archive zip GitHub (urllib + zipfile, sans dependance git)
│   │   └── local_folder.py         # Validation de dossier local - le pendant leger de github_fetcher.py
│   ├── server/
│   │   └── client.py               # StudioClient - login/list_models/push_model/pull_model contre le server.ts de HYDRA-UMC-SERVER (le backend de STUDIO avant la séparation des deux dépôts)
│   └── ui/
│       ├── main_window.py          # QMainWindow - espace de travail ancrable, barre de menu, selecteur de langue, barre d'etat
│       ├── theme.py                 # Applique assets/qss/industrial_dark.qss
│       └── panels/
│           ├── source_panel.py     # Saisie d'URL GitHub / de dossier local, liste des URDF trouves
│           ├── dof_panel.py        # Affichage du verdict de faisabilite
│           ├── viewport_panel.py   # Hote de la vue 3D, arbre de liens, curseurs de mouvement
│           ├── properties_panel.py # Editeurs de recoloration / redimensionnement / retypage-et-relimitation
│           └── upload_panel.py     # Connexion/envoi/recuperation serveur
└── work/                            # Espace de travail temporaire d'execution pour les depots GitHub recuperes et les modeles serveur telecharges (ignore par git)
```

---

## 🛠️ Environnement de développement

### Prérequis
- [Python](https://www.python.org/) 3.11 ou supérieur
- pip

### Installation

```bash
pip install -r requirements.txt
```

Ceci récupère le jeu de dépendances figé : **PySide6** (interface Qt6), **PyOpenGL** (rendu de la vue 3D), **numpy** / **numpy-stl** (calcul de maillage et chargement STL). Aucune installation de `git` n'est requise - le chemin de chargement de source GitHub télécharge une simple archive zip par HTTPS.

### Mode développement

```bash
python main.py
```

Démarre maximisé (pas un plein écran véritablement natif au niveau du système d'exploitation, de sorte que la barre de titre native et les contrôles de la fenêtre restent visibles) - appuyez sur **F11** pour basculer vers un véritable plein écran sans bordure et inversement.

### Build de production

Compile un exécutable autonome (aucune installation de Python n'est nécessaire pour l'exécuter) via PyInstaller :

- **Windows :** exécutez `build_exe.bat` → produit `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux :** exécutez `./build_exe.sh` (`chmod +x build_exe.sh` une fois au préalable) → produit `dist/HYDRA-UMC_EDITOR-URDF`

Les deux scripts créent/activent leur propre `.venv`, installent `requirements.txt` plus `pyinstaller`, nettoient tout `build`/`dist` précédent, **font monter le numéro de version**, compilent, et enfin copient `README.md`, `LICENSE`, et l'intégralité du dossier `language/` à côté du binaire résultant (`language/` n'est délibérément **pas** intégré à l'intérieur de l'exécutable via `--add-data`, de sorte qu'un fichier `.lng` puisse être modifié ou ajouté ensuite sans reconstruction).

**Numérotation de version :** la version de l'application (`hydra_editor_urdf/__version__`, affichée dans la boîte de dialogue Aide → À propos) suit le schéma `MAJOR.MINOR.PATCH`. Chaque exécution réelle de `build_exe.bat`/`build_exe.sh` appelle d'abord `bump_version.py`, qui applique une incrémentation de type compteur kilométrique : `PATCH` augmente de 1 ; une fois que `PATCH` dépasserait 9, il revient à 0 et c'est `MINOR` qui augmente de 1 à la place (p. ex. `0.0.9` → `0.1.0`). `MAJOR` n'est jamais touché automatiquement - cela reste une décision délibérée et manuelle. Voir `CHANGELOG.md` pour l'historique des versions.

Si vous préférez exécuter les étapes équivalentes à la main plutôt que via le script - utile pour adapter le build sur une plateforme que les scripts ne couvrent pas, ou pour déboguer un indicateur PyInstaller - le processus manuel est :

```bash
# 1. Creer et activer un environnement virtuel
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. Installer les dependances + PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# 3. Localiser le propre dossier d'installation de PySide6 (ses plugins Qt y vivent)
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> $PYSIDE_DIR ci-dessous

# 4. Compiler - seuls 4 sous-dossiers de plugins Qt sont explicitement etages
#    (platforms/styles/imageformats/iconengines), PAS --collect-all PySide6, ce qui
#    entrainerait sinon Qt6WebEngineCore.dll et d'autres composants de plusieurs
#    centaines de Mo que cette application n'utilise jamais. Le propre analyseur
#    de dependances de PyInstaller trouve les vraies DLL Qt6Core/Gui/Widgets/OpenGL
#    en suivant le veritable graphe d'import de main.py - seuls les dossiers de
#    plugins doivent etre ajoutes a la main.
#
#    Windows (les plugins vivent directement sous PySide6/plugins/):
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux (les plugins vivent sous PySide6/Qt/plugins/ a la place - une disposition
#    differente de Windows, confirmee en lisant le propre hook d'execution de
#    PyInstaller pyi_rth_pyside6.py):
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. Copier les fichiers qui doivent se trouver A COTE du binaire, pas a l'interieur
cp README.md LICENSE dist/
cp -r language dist/language
```

Sous Linux, l'exécution du binaire compilé nécessite la présence du propre runtime OpenGL du système (`libGL.so.1` - p. ex. `libgl1` sous Debian/Ubuntu, `mesa-libGL` sous Fedora, `libglvnd` sous Arch) plus `libxkbcommon-x11-0`/`xcb-util-cursor` pour le propre plugin de plateforme XCB de Qt ; `build_exe.sh` vérifie la présence de `libGL.so.1` en amont et affiche la bonne commande d'installation par distribution si elle manque, plutôt que d'échouer profondément à l'intérieur d'une exécution de PyInstaller.

---

## 🔗 Projets liés

Ce projet fait partie d'un écosystème de robotique plus vaste du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt :

**Plateforme HYDRA-UMC** — la cellule de micro-usine multi-robots
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère elle-même : hôte Raspberry Pi CM5 + coprocesseur temps réel double cœur STM32H745, orchestrant jusqu'à 8 bras robotiques distribués via CAN-OTA/SPI-OTA. Matériel + firmware propres, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web pour HYDRA-UMC : visualisation 3D multi-robots, enregistrement de cinématique/trajectoire, flashage et test CAN-OTA pour toute la plateforme. React + Vite + Three.js.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le backend headless (Node/Express/WebSocket) qui était auparavant intégré au propre processus de HYDRA-UMC-STUDIO. Possède l'API REST/WS de contrôle des robots (y compris `POST /api/models/submit`, le point de terminaison vers lequel cet éditeur pousse les modèles finis), la persistance settings.json, l'authentification JWT et la découverte mDNS. HYDRA-UMC-STUDIO est désormais un client frontend statique pur qui communique avec lui via le réseau.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android pour HYDRA-UMC via Wi-Fi/Bluetooth. Application réelle et fonctionnelle - ensemble complet de fonctionnalités de télécommande, authentification JWT, stockage chiffré des identifiants.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS pour HYDRA-UMC via Wi-Fi, construite en Flutter (multiplateforme, vérifiable sous Windows sans Mac ; l'empaquetage final `.ipa` nécessite encore Xcode). Application réelle et fonctionnelle - même ensemble de fonctionnalités que l'application Android.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande de bureau (Python/PySide6) pour essaim de robots : découverte réseau multi-contrôleurs, synchronisation bidirectionnelle en direct, véritable vue 3D de robot, espace de travail ancrable de style Photoshop. Réel et fonctionnel, pas un placeholder.
- **HYDRA-UMC-EDITOR-URDF** *(ce dépôt)* — créateur/éditeur graphique de URDF de bureau (Python/PySide6) pour le propre catalogue de modèles de HYDRA-UMC-STUDIO : récupère les fichiers source depuis GitHub ou un dossier local, valide la faisabilité en DDL, édite couleur/échelle/cinématique avec un aperçu 3D en direct, et pousse le résultat final vers un serveur STUDIO en cours d'exécution. Réel et fonctionnel, pas un placeholder.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native en Flutter pour l'écran tactile DSI 5"/7" propre à HYDRA-UMC (1280×720, même résolution dans les deux tailles) sur le Compute Module 5, contrôlant ce même serveur directement depuis la carte. Scaffold réel et fonctionnel avec les 6 écrans du catalogue (dashboard, contrôle manuel, caméra, vue 3D simplifiée, métriques système, connexion) connectés au serveur en direct ; la compilation réelle de la cible Linux n'a pas encore été exécutée sur du matériel réel (environnement de travail uniquement Windows jusqu'à présent - voir le README de ce projet).

**Plateforme URTC** — le contrôleur de tête d'outil que porte chaque bras robotique HYDRA-UMC
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller : contrôleur de tête d'outil à bus CAN basé sur STM32F303, 25 profils d'outils entièrement implémentés, mise à jour de firmware CAN-OTA.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau de flashage CAN-OTA + SWD/JTAG puce complète pour les cartes URTC (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic bus CAN en direct pour les cartes URTC, un panneau par profil d'outil (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur aux 2 outils de bureau ci-dessus (Web Serial API + SLCAN), aucune installation locale nécessaire.

**Directement liés à ce dépôt**
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — consomme les modèles URDF créés ici pour alimenter sa simulation physique.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — consomme les modèles URDF créés ici pour alimenter sa simulation physique.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — génère des données d'entraînement à partir des modèles créés ici.

**Le reste de l'écosystème** — ce projet s'inscrit dans un ensemble plus vaste de nombreux projets, regroupés par domaine :
- 👁️ **Vision AI Node (Hailo-8) :** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE), [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER), [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF), [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES), [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Cognitive AI Node (Hailo-10) :** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE), [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE), [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI), [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER), [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestration & Swarm :** [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR), [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC), [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D), [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER), [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Digital Twin & Simulation :** [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- 📊 **Data & Analytics :** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE), [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR), [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR), [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Industrial Gateway :** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL), [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER), [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER), [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Complementary Tools :** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH), [HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI), [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 Auteur

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 Licence et Avis de Copyright

HYDRA-UMC EDITOR-URDF est (c) 2026 JuanenRac (Electro Hobby 3D). Cet avis doit être inclus dans toute distribution de ce projet ou de ses travaux dérivés.

Ce projet consiste en du code source et sa propre documentation, mis à disposition sous des licences différentes - chacune adaptée à ce qu'elle couvre réellement :

1. Le code source (`hydra_editor_urdf/`, `main.py`, et tout binaire construit à partir de celui-ci via `build_exe.bat`/`build_exe.sh`) est disponible sous la **GNU General Public License v3.0 (GPL-3.0)**. Texte complet sur https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentation (ce README et ses propres traductions - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) est disponible sous **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Texte complet sur https://creativecommons.org/licenses/by-sa/4.0/.

Cette application ne fournit aucun asset de maillage de robot tiers propre - contrairement au `public/models/` de HYDRA-UMC STUDIO, chaque maillage que cet éditeur charge provient du dépôt source ou du dossier local vers lequel l'opérateur le pointe, sous la licence originale propre de cette source. Examiner et préserver cette licence/attribution en amont avant de soumettre un modèle à un serveur STUDIO en cours d'exécution (dont la propre convention `public/models/<slug>/ATTRIBUTION.txt` est alimentée par la fonction d'export de cet éditeur) demeure la propre responsabilité de l'opérateur - cette application n'a aucun moyen de détecter ou de faire respecter automatiquement les conditions de licence d'un dépôt source.

Cet éditeur est l'outil de création de modèles pour le catalogue [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - voir ce dépôt pour sa propre licence côté serveur, à laquelle la propre licence de ce dépôt-ci ne s'étend pas, et vice versa.

Si vous construisez sur ce projet, gardez la séparation des licences à l'esprit : les modifications de code ici devraient rester GPL-3.0, les dérivés de documentation (ce README et ses traductions) devraient rester CC BY-SA 4.0, et tout asset de maillage qui transite par cet éditeur (importé, édité ou exporté) devrait rester sous quelque licence que porte son propre dépôt source original, avec attribution à cette source.
</content>

## 🛠️ BUILD & RUN

Utilisez la vérification de compilation sans versionnement avant une compilation de publication :

| Action | Windows | Linux / macOS |
|---|---|---|
| Vérification de compilation (sans modifier la version ni le CHANGELOG) | `build-test.bat` | `./build-test.sh` |
| Exécution / développement (si disponible) | `run*.bat` ou `dev*.bat` | `./run*.sh` ou `./dev*.sh` |

`build-test.bat` et `build-test.sh` compilent ou valident la pile du projet sans incrémenter `hydra-umc.project.json` ni modifier `CHANGELOG.md`. Ils peuvent uniquement créer les sorties normales du compilateur. Les scripts existants `build*.bat`, `build*.sh`, `run*` et `dev*` conservent leur comportement spécifique de versionnement ou d'exécution ; utilisez-les lorsque ce comportement est requis.