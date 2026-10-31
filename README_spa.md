<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Desktop URDF creator and editor for the model catalogue of HYDRA-UMC-STUDIO
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>

# 🖌️ HYDRA-UMC-EDITOR-URDF

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🖌️ Creador/Editor Gráfico de URDF para el Catálogo de Modelos de HYDRA-UMC-STUDIO

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="Format">
  <img src="https://img.shields.io/badge/Tests-538%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

---

**Comprobación de honestidad - qué funciona realmente hoy:** el núcleo de lógica pura - parseo/exportación URDF (`urdf/parser.py`, `urdf/writer.py`), validación de factibilidad DOF (`urdf/dof.py`), cinemática directa (`render/kinematics.py`), estimación de inercia (`inertia_calc.py`), resolución de referencias de malla y descarga de zipball de GitHub (`source/scan.py`, `source/github_fetcher.py`, `source/local_folder.py`), el modelo en memoria (`models.py`), la lista de la galería (`gallery.py`) y el cargador i18n (`i18n.py`) - es real y está cubierto por 538 tests pasando (`tests/`), ninguno de los cuales importa PySide6/PyOpenGL. `test_github_fetcher.py` simula (mock) toda llamada de red - una descarga real de un zipball de GitHub se ha ejecutado manualmente, nunca como parte de la suite automatizada. La capa Qt/OpenGL (`render/viewport.py`'s `UrdfGLRenderer`, `render/mesh.py`, cada panel de `ui/*`, y el `OffscreenUrdfRenderer` del deck `--qtquick`) es código real y funcional pero no tiene ninguna cobertura de tests automatizada - necesita una pantalla/plugin de plataforma Qt real, que CI no tiene, así que se verifica a mano, no con una suite de tests. `server/client.py`'s `StudioClient` (login/push/pull contra el `server.ts` de HYDRA-UMC-SERVER) es código HTTP real, probado contra un pequeño servidor local que cumple el contrato de `server.ts` (el token en cada llamada, una colisión de nombre, la descarga de un modelo, una respuesta hostil). La expansión de xacro y la carga de mallas COLLADA (`.dae`) son no-funcionalidades explícitas y nombradas (un error claro, no un mal-parseo silencioso) - ver la Nota de Honestidad en la Visión General más abajo y las secciones de Parseo URDF/Carga de Mallas para el porqué. Ver `CHANGELOG.md` para lo que se ha entregado exactamente hasta ahora. La única excepción es opcional: con `xacro_expand` en true en `hydra_editor_urdf_config.json` y la herramienta `xacro` instalada en el equipo, un fichero xacro lo expande esa herramienta (no se incluye nada).

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado. Todavía no existe una ruta de E-STOP por hardware, ni límites ni enclavamientos aplicados por el firmware, ni un comando de movimiento verificado; las imágenes de firmware se comprueban con CRC-32 y una firma Ed25519, y una compilación de versión rechaza las claves de desarrollo publicadas (los cabezales de herramienta y las placas de expansión detrás del relé siguen con cargadores de URTC, que usan un HMAC-SHA256 de clave compartida en lugar de una firma); TLS y TLS mutuo son opcionales y están desactivados por defecto; aún no se ha poblado ni probado ninguna placa propia. Lee la [línea base de seguridad](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.1.7` |
| Madurez | Establecido |
| Tests | 538 (`python -m pytest tests -q`) |
| Tecnología | Python / PySide6 / Qt6 / OpenGL |
| Destino | El PC de quien lo usa |
| En hardware real | No aplica: nada de esto se ejecuta en hardware |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Funciones](#-funciones) · [Seguridad y protección](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Configuración](#-configuración) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Resolución de problemas](#-resolución-de-problemas) · [Estructura del repositorio](#-estructura-del-repositorio) · [Proyectos relacionados](#-proyectos-relacionados)

## 🚦 Estado del proyecto

Cada línea es una parte de este repositorio y la luz dice hasta dónde llega hoy. Se escribe con lo que el repositorio puede demostrar (pruebas, compilaciones, ejecuciones), no con lo previsto.

🟢 Hecho y verificado · 🟡 Funciona, con límites conocidos · 🟠 Hecho a medias o sin verificar · 🔴 Sin hacer o sin funcionar

| Área | Estado | Qué significa aquí |
|---|---|---|
| Software | 🟢 | Completo para su propósito y estable; la comprobación de honestidad de arriba lista los límites conocidos |
| Pruebas | 🟢 | 538 pruebas automáticas, ejecutadas en cada cambio |
| Hardware real | 🟢 | No aplica: nada de esto se ejecuta en hardware |
| Documentación | 🟢 | README en ocho idiomas, comprobado contra el manifiesto en cada cambio |

## 🎯 Resumen

**HYDRA-UMC EDITOR-URDF** es la herramienta de escritorio que convierte "portar un robot nuevo al catálogo de modelos de [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)" de una investigación manual, robot a robot, en un flujo de trabajo gráfico y repetible. Cada modelo de robot real en el catálogo de STUDIO llegó ahí de la misma forma en el pasado: encontrar un repositorio de descripción en GitHub, averiguar cómo se resuelven sus referencias a mallas, contar los grados de libertad de su cadena cinemática, comprobar si STUDIO realmente puede mover tantos, y colocar el resultado a mano en `public/models/`. Esta aplicación automatiza todo ese proceso: extrae los archivos fuente desde una URL de GitHub o desde una carpeta local ya descargada, resuelve cada referencia `<mesh filename="...">` (URIs `package://` incluidas) contra los archivos reales en disco, valida el número de grados de libertad de la cadena contra lo que la cinemática de STUDIO soporta hoy, edita color/escala/límites de junta/tipo de junta con una vista previa 3D en vivo, y sube el resultado terminado directamente a un servidor STUDIO en ejecución.

Construida con **Python** y **PySide6/Qt6**, usando los mismos patrones arquitectónicos ya validados en la otra herramienta de escritorio de este ecosistema, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE): un espacio de trabajo acoplable al estilo Photoshop/Fusion-360 (`QDockWidget`), una vista 3D OpenGL escrita a mano (`QOpenGLWidget` + shaders GLSL 3.3 core-profile, sin la ruta heredada `glBegin`/`glEnd`), y un único objeto controlador central que posee el estado y al que cada panel de la interfaz escucha mediante señales de Qt. Reutilizar ese patrón aquí -en vez de explorar una pila de UI/renderizado nueva para una herramienta hermana en el mismo ecosistema- es una decisión deliberada, no un descuido.

**Nota de honestidad, siguiendo la misma convención de documentación que el resto de este ecosistema:** esta aplicación no expande macros [xacro](http://wiki.ros.org/xacro), ni carga mallas COLLADA (`.dae`). Ambas son limitaciones nombradas y explícitas (un mensaje de error claro, no un mal-parseo silencioso o un enlace faltante en la vista) en vez de un intento a medio implementar - ver las secciones **Parseo de URDF** y **Carga de Mallas** más abajo para el porqué, y lo que costaría dar soporte real a cualquiera de las dos. La única excepción es opcional: con `xacro_expand` en true en `hydra_editor_urdf_config.json` y la herramienta `xacro` instalada en el equipo, un fichero xacro lo expande esa herramienta (no se incluye nada).

## 🧩 Papel en HYDRA-UMC

**HYDRA-UMC-EDITOR-URDF** es la herramienta de escritorio que convierte el portado de un robot nuevo al catálogo de modelos de HYDRA-UMC-STUDIO de una investigación manual en un flujo repetible. Carga un URDF de un repositorio de GitHub o de una carpeta local, dice si el robot cabe en los 3 a 6 grados de libertad que admite STUDIO, lo muestra en una vista 3D en vivo donde se pueden recolorear eslabones, cambiar su escala y darles nuevos límites de articulación, y exporta el URDF o lo envía a un HYDRA-UMC-SERVER.

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-EDITOR-URDF architecture" width="100%">
</p>

## ✨ Funciones

### Carga de Fuentes - GitHub o Carpeta Local

Dos formas de apuntar la aplicación a los archivos fuente de un robot, ambas terminando en la misma ruta de importación:

- **Desde una URL de GitHub** - acepta una URL completa `https://github.com/owner/repo` (con o sin `/tree/<branch>`), un formato estilo SSH `git@github.com:owner/repo.git`, o el atajo simple `owner/repo`. Deliberadamente **no** invoca `git clone`, lo cual convertiría una instalación de `git` en una dependencia dura en tiempo de ejecución tanto en Windows como en Linux para algo que una simple descarga HTTPS ya resuelve: GitHub sirve un zipball de cualquier rama/tag/commit desde `codeload.github.com` sin necesidad de autenticación para un repositorio público, así que esto usa el propio `urllib.request` + `zipfile` de la biblioteca estándar y nada más. Solo se soportan repositorios públicos - no hay manejo de tokens/credenciales, y el zipball de un repositorio privado da un 404 igual que uno inexistente.
- **Desde una carpeta local** - para un repositorio ya descargado a mano, o una copia de trabajo que el operador está editando activamente fuera de esta aplicación.
- **Desde la Galería** - un desplegable "Gallery" encima del campo de URL de GitHub (`hydra_editor_urdf/gallery.py`) lista un pequeño conjunto inicial de repositorios de descripción de robots reales y verificados a mano (`universal_robot` de ROS-Industrial, `open_manipulator` de ROBOTIS). Elegir una entrada solo rellena la URL y muestra su descripción - nunca descarga por sí sola, el operador sigue pulsando Fetch, igual que si escribiera la URL a mano.

De cualquier forma, la aplicación después busca recursivamente cada archivo `*.urdf`/`*.xacro` bajo la carpeta elegida, los lista todos (un repositorio real de descripción de robot a menudo trae más de uno - un brazo desnudo más una variante "con pinza" es un emparejamiento habitual), y elige automáticamente el de mayor tamaño de archivo como valor por defecto razonable para "el principal" - cambiar a otro candidato después es un doble clic en el panel Source, no una nueva descarga.

**La resolución de referencias a mallas** es el trabajo poco glamuroso que toda sesión pasada de portado manual de robots en este ecosistema hizo a mano: un `<mesh filename="package://some_pkg/meshes/link1.stl"/>` de un URDF prácticamente nunca es una ruta abrible directamente una vez que el archivo está sentado en una simple carpeta descargada en vez de un espacio de trabajo ROS en vivo, donde `package://` se resuelve a través del índice de paquetes de ROS. El resolvedor prueba, en orden: (1) la referencia como una ruta relativa a la propia carpeta del URDF, (2) la misma referencia quitando el segmento inicial de nombre de paquete al estilo `package://`, (3) como ruta absoluta si resulta que ya lo es, y (4) por nombre base a secas en cualquier lugar bajo la carpeta fuente - que es lo que realmente maneja una URI `package://` real, ya que el esquema y el nombre del paquete no significan nada fuera de un espacio de trabajo ROS en vivo, pero el propio nombre de archivo de la malla sigue siendo localizable.

### Validación de Viabilidad de DOF

La versión automatizada del mismo juicio que las propias sesiones pasadas de este ecosistema hicieron a mano para cada robot añadido al catálogo de STUDIO: **la propia cinemática de STUDIO soporta hoy cadenas seriales de 3, 4, 5 y 6 DOF** (su `RobotState.joints` es un mapa fijo `j1..j6`) - un puñado de brazos candidatos reales, con licencia clara, investigados en el pasado resultaron ser de 7, 8 o 9 DOF y fueron descartados exactamente por esta razón, no hipotéticamente. En cada importación (y después de cada edición en vivo que pueda cambiar el recuento - retipar una junta, por ejemplo), la aplicación recorre el grafo real de juntas padre/hijo e informa:

- **Recuento de DOF** - solo las juntas `revolute`/`continuous`/`prismatic` cuentan como un grado de libertad real y controlable; `fixed` no aporta ninguno.
- **Tipos de junta no soportados** - una sola junta `floating` o `planar` en cualquier lugar de la cadena hace que todo el robot sea inviable sin importar el recuento de DOF, ya que el modelo de juntas de STUDIO no tiene representación para ninguna de las dos.
- **Integridad del árbol** - se requiere exactamente un enlace raíz (un árbol propio, no un bosque ni un ciclo); cualquier enlace no alcanzable desde esa raíz por una cadena de juntas se marca como desconectado, y cualquier enlace al que ninguna junta hace referencia en absoluto se marca como huérfano.
- **`<limit>` faltante** - requerido por la especificación URDF para cualquier junta que no sea `continuous`; se marca por junta si está ausente.

El veredicto y cada razón detrás de él se renderizan en vivo en el panel DOF, y el panel Upload rechaza subir un robot inviable a un servidor.

### Edición en Vivo con una Vista Previa 3D Real

El panel Properties edita el enlace que esté seleccionado en el árbol de enlaces del panel Viewport, y cada edición muta el modelo cargado in situ y revalida/vuelve a renderizar a través de una sola señal (`EditorController.notify_tree_changed`) - ningún panel necesita saber cómo reacciona el viewport o el informe de DOF a su propia edición:

- **Recolorear** - el material visual de un enlace, elegido mediante un diálogo de color estándar. Un material compartido por nombre entre varios enlaces (una declaración `<material name="...">` de nivel superior de un URDF real, referenciada por más de un `<visual>`) recolorea juntos a todos los enlaces que lo comparten, respetando lo que esa sintaxis de material compartido realmente significa en la especificación.
- **Reescalar** - factor de escala por eje (X/Y/Z) sobre la propia transformación `<mesh scale="...">` de una geometría de malla, no una reescritura destructiva de los propios datos de triángulos de la malla - la misma edición vuelta a aplicar más tarde parte siempre de la malla original, sin modificar.
- **Retipar y re-limitar una junta** - cambiar el tipo de una junta (cualquiera de los 6 que define la especificación URDF) y su límite inferior/superior, con el veredicto del panel DOF actualizándose de inmediato ya que un retipado puede cambiar el recuento de DOF o introducir un tipo no soportado.
- **Masa e inercia** - "Auto-calculate" rellena masa/Ixx/Iyy/Izz a partir de la geometría del enlace seleccionado usando las fórmulas de forma cerrada de densidad uniforme de `inertia_calc.py` (exactas para Caja/Cilindro/Esfera, una aproximación por caja envolvente para Malla); una masa introducida a mano siempre gana sobre la estimación por densidad, y si aún no hay masa introducida asume una densidad genérica de aluminio (2700 kg/m³) y lo indica en una nota. "Apply" confirma los campos en `Link.inertial` - el mismo patrón de dos pasos calcular-y-aplicar que Scale/Joint arriba.

El **panel Viewport** aloja la propia vista 3D OpenGL más un control deslizante de jog por cada junta móvil, para que el operador pueda previsualizar el URDF moviéndose por su propio rango real antes de tocar STUDIO. La cinemática directa (`render/kinematics.py`) es genérica sobre cualquier árbol que se acabe de importar - a diferencia del propio módulo de cinemática de HYDRA-UMC SUITE, que maneja un registro fijo de unas pocas docenas de modelos de robot conocidos y verificados a mano, esta aplicación tiene que posar un URDF arbitrario, nunca antes visto, así que compone el propio `<origin>`/`<axis>` real de cada junta (fórmula de rotación de Rodrigues para un eje revolute arbitrario, no solo el atajo de dirección cardinal en el que podría apoyarse un registro fijo) recorriendo el propio grafo padre/hijo.

**Z-arriba, no Y-arriba** - la única divergencia deliberada respecto a la propia convención de viewport de HYDRA-UMC SUITE: URDF en sí mismo es un formato Z-arriba (la gravedad es `-Z`, cada `<origin>`/`<axis>` en un archivo fuente está redactado asumiendo eso), y el trabajo de esta aplicación es mostrar y editar un URDF fielmente en su propia convención, no reorientarlo hacia lo que un visor posterior (la escena Three.js de STUDIO, la propia escena OpenGL de SUITE) prefiera tener.

### Carga de Mallas

`.stl` (vía `numpy-stl`) y `.obj` (un pequeño cargador Wavefront escrito a mano - solo `v`/`vn`/`f`, caras n-gon trianguladas en abanico) son ambos de primera clase. **COLLADA (`.dae`) no está soportado** - es un formato de grafo de escena XML mucho más grande (animación esquelética, múltiples sistemas de coordenadas, materiales/texturas embebidos) que necesitaría un parser real para manejarse con honestidad en vez de una conjetura de mejor esfuerzo sobre cualesquiera etiquetas que use un `.dae` "simple"; un enlace que referencia uno recibe un error claro y nombrado en vez de desaparecer silenciosamente del viewport o hacer fallar toda la importación. Cada malla cargada también recibe la misma protección defensiva milímetros-contra-metros que aplican el propio `useRealScaleSTL()` de HYDRA-UMC STUDIO y el propio cargador de mallas de HYDRA-UMC SUITE: un enlace más grande que 5 metros reales en cualquier eje es mucho más probable que sea una exportación a escala de milímetros sin metadatos de unidad que una pieza de robot realmente gigante, y se reescala automáticamente por 0.001.

---

Las rutas de malla están confinadas: un `<mesh filename>` solo se resuelve a un archivo `.stl`, `.obj` o `.dae` dentro de la carpeta abierta, la carpeta del URDF o una carpeta añadida con «Locate Missing Meshes»; los segmentos `..`, las rutas absolutas y los URI `file://` que lleven a otro sitio se ignoran, y solo esos archivos se suben. Las mallas vacías, truncadas o mal formadas se notifican como no cargadas en lugar de detener el visor. La guarda de milímetros a metros reescala cualquier malla mayor de 5 unidades antes de aplicar la `scale` del URDF, de modo que una malla ya escalada por el URDF puede reducirse dos veces. Las etiquetas que el editor no modela (`<dynamics>`, `<safety_controller>`, `<mimic>`, `<transmission>`, `<gazebo>`, texturas de material) no se conservan al reexportar un URDF.

### Parseo y Exportación de URDF

XML plano vía el propio `xml.etree.ElementTree` de la biblioteca estándar - no se necesita una dependencia de `lxml` para un formato tan simple. El modelo en memoria (`hydra_editor_urdf/models.py`) es deliberadamente un árbol de dataclasses propio, plano y mutable, en vez de un envoltorio sobre una biblioteca Python de URDF ya existente como `urdfpy` o `yourdfpy`: esta aplicación necesita *editar* el árbol de forma interactiva y volver a renderizar cada cambio en vivo, algo para lo que una biblioteca de parseo pensada mayormente para lectura no está diseñada, y ser dueño del modelo por completo lo mantiene pequeño, inspeccionable y libre del propio ritmo de publicación de una dependencia de terceros. Los nombres de campo y los valores por defecto siguen de cerca el [esquema XML real de URDF](http://wiki.ros.org/urdf/XML), así que el par parser/writer se mantiene como un mapeo XML↔objeto delgado y evidente.

**xacro no se expande.** [xacro](http://wiki.ros.org/xacro) es un preprocesador de macros Python/XML con su propio paquete ROS y cadena de dependencias, y un archivo xacro real solo se puede resolver de forma fiable dentro del mismo entorno de paquete ROS contra el que fue redactado (argumentos de macro, includes al estilo `$(find pkg)`, etc.) - algo que esta aplicación no tiene forma de reproducir con honestidad. Un archivo que use etiquetas `<xacro:...>` o declare el namespace de xacro recibe un error claro que explica la limitación y señala hacia la herramienta de línea de comandos `xacro` de ROS para preprocesarlo primero, en vez de un mal-parseo silencioso. La única excepción es opcional: con `xacro_expand` en true en `hydra_editor_urdf_config.json` y la herramienta `xacro` instalada en el equipo, un fichero xacro lo expande esa herramienta (no se incluye nada).

**Comprobaciones y exportaciones opcionales, todas desactivadas por defecto** (interruptores en `hydra_editor_urdf_config.json`): `self_collision_check` lista, como avisos, los pares de eslabones cuyas cajas se solapan en la pose inicial o al mover una articulación cada vez (`self_collision_steps`, `self_collision_tolerance_m`; las cajas contienen las formas reales, así que puede avisar de un roce cercano pero no se le escapa un solape); `license_check` avisa de mallas sin fichero LICENSE, COPYING, NOTICE o ATTRIBUTION en sus carpetas y de licencias con condiciones, y con lo encontrado se puede generar un texto ATTRIBUTION; la ventana Exportar tiene una casilla Y arriba que escribe el modelo para una escena Three.js (un eslabón raíz gira el mundo un cuarto de vuelta, `y_up_scale` escala las longitudes). Ninguna cambia la viabilidad ni lo que se escribe mientras no se active.

**Comprobación física del modelo, desactivada por defecto** (`physical_check` en `hydra_editor_urdf_config.json`; detalles en `docs/PHYSICAL_CHECK.md`): la pantalla de GDL lista, como avisos, lo que un cuerpo real no podría ser - más de una raíz, un ciclo, un eslabón sin uso o inalcanzable, una masa que no es mayor que 0, un tensor de inercia que no es definido positivo o cuyos momentos principales incumplen la desigualdad triangular (Ixx + Iyy >= Izz y las permutaciones), lower por encima de upper, effort o velocity que no son mayores que 0, un eje nulo o no unitario, una articulación continua con límites, una malla ausente o mal escalada, y longitudes, ángulos o masas que parecen milímetros, grados o gramos. Cada aviso da la regla, el elemento, el valor, el límite y una corrección sugerida que nunca se aplica. La misma comprobación se ejecuta sin ventana con `python main.py --cli physical-check ARCHIVO.urdf [--json]` (salida 0 limpio, 1 avisos, 2 error). Probada con modelos generados y casos simulados, no con un catálogo de robots reales.

La exportación (`urdf/writer.py`) reserializa el árbol actual en memoria desde cero en vez de parchear el texto XML fuente original, así que cada edición en vivo -sin importar qué panel la hizo- se refleja exactamente una vez, a través de una sola ruta de código, tanto en la acción de menú "Export URDF" como en el payload enviado a un servidor STUDIO.

Los elementos para los que el modelo no tiene campo (`<transmission>`, `<gazebo>`, el `<dynamics>`, `<safety_controller>` y `<calibration>` de una articulación, y el multiplicador y el desplazamiento de un `<mimic>`) se conservan como texto al leer un fichero. El botón **Exportar** abre una ventana que dice cuántos elementos así tiene el fichero y tiene un interruptor, desactivado por defecto y desactivado de nuevo con cada robot que se carga, para escribirlos de nuevo como los tenía el fichero de origen; los que nombran una articulación o un enlace que se borró no se escriben nunca.

### Espacio de Trabajo Acoplable

Paneles `QDockWidget` reales - arrastrar para flotar, arrastrar de vuelta para acoplar, fusionar en pestañas, dividir el espacio de trabajo - el mismo mecanismo y razonamiento que la propia ventana principal de HYDRA-UMC SUITE ya aplica: el propio sistema de acoplamiento de Qt ya hace exactamente lo que un espacio de trabajo al estilo Photoshop/Fusion-360 necesita, y uno hecho a mano solo lo reinventaría con más errores. Cinco paneles, dispuestos con una disposición por defecto sensata que es completamente reorganizable después:

- **Source** - entrada de URL de GitHub / carpeta local, lista de `.urdf` encontrados.
- **DOF** - el veredicto de viabilidad y cada razón detrás de él.
- **Viewport** - la vista 3D en vivo, el árbol de enlaces, y los controles deslizantes de jog.
- **Properties** - recolorear / reescalar / retipar-y-re-limitar para el enlace seleccionado.
- **Upload** - conectar a un servidor STUDIO, subir, o descargar.

### Ida y Vuelta con el Servidor

Habla con el propio contrato de envío de modelos de HYDRA-UMC-SERVER (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` en el propio `server.ts` de ese proyecto, protegido tras su propio interruptor **Config > Models > "Accept model submissions"**) usando el propio `urllib.request` de la biblioteca estándar - una llamada HTTP más no justificaba traer `httpx`/`requests` para un proyecto que solo necesita 4 endpoints, no una conexión en vivo persistente. Cada llamada corre en un `QThread` en segundo plano para que un servidor lento o inalcanzable nunca congele la interfaz. Este contrato solía vivir dentro del propio proceso de HYDRA-UMC-STUDIO antes de que ese proyecto se dividiera en un frontend puro (STUDIO) más un backend headless separado (HYDRA-UMC-SERVER, ver **Proyectos Relacionados** más abajo) - esta app no fija ningún nombre por código, el operador simplemente apunta los campos host/puerto del panel **Upload** a donde esté corriendo el backend real.

- **Login** - `POST /api/login`; solo un token con rol `admin` puede realmente alcanzar `POST /api/models/submit` en el lado del servidor, así que esta aplicación solo es realmente usable contra una cuenta admin, igual que cualquier otra función de STUDIO exclusiva para administradores.
- **Push** - serializa el robot actual de vuelta a XML URDF y codifica en base64 cada archivo de malla que sus visuales referencian (resuelto a través del mismo resolvedor de mallas construido en el momento de importar) inline en el cuerpo de la petición, etiquetado con la categoría elegida por el operador (reflejando las propias categorías de Config > UI > Module Visibility de STUDIO: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - un URDF no tiene un campo propio que diga cuál de estas es). Una colisión de nombre vuelve como la propia respuesta 409 del servidor; el operador decide si reenviar con **Overwrite** marcado o renombrar, esta aplicación nunca adivina.
- **Pull** - descarga el URDF + mallas de un modelo ya enviado de vuelta a una carpeta de trabajo local y lo carga directamente en el editor - la mitad "extraer, editar, reenviar" del propio propósito de esta aplicación, permitiendo retocar una entrada de catálogo existente sin volver a empezar desde su repositorio fuente original.

### Interfaz Multi-Idioma

Traducción completa de la interfaz a través de **inglés, español, italiano, francés, alemán, chino simplificado, japonés y portugués** (`language/*.lng`), usando exactamente el mismo mecanismo de archivo plano `CLAVE=Valor` que cualquier otra herramienta Python de este ecosistema (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - no reinventado aquí, ya que el propio mecanismo no lleva ninguna lógica específica del proyecto. Un cambio de idioma surte efecto después de reiniciar la aplicación en vez de retraducir en vivo cada widget ya construido, siguiendo esa misma convención. `language/` está **junto a** el ejecutable en vez de empaquetado dentro de él vía el `--add-data` de PyInstaller, así que un traductor puede editar o añadir un archivo `.lng` sin necesidad de recompilar.

### Tema

La barra superior del espacio de trabajo acoplable es un panel de comandos
real con `QToolBar`/`QLabel`/`QToolButton`, no una UI Qt Quick/QML aparte -
una versión anterior integrada mediante QQuickWidget (mismo motor visual que
HYDRA-UMC-UPDATER y HYDRA-UMC-SUITE) se renderizaba como una barra negra
sólida sin ningún error en consola una vez colocada dentro del
`QDockWidget` real de este `QMainWindow`, así que se revirtió a widgets
planos; ver `CHANGELOG.md` para la historia completa. Sus botones Source,
DOF, Viewport, Properties y Upload sólo enfocan los docks existentes; Export
y About reusan las acciones existentes, y Export permanece deshabilitado
hasta que hay un modelo realmente cargado. Tras cargar un URDF (y tras cada
edición de propiedad en vivo), su chip de estado muestra el nombre del
modelo cargado, el conteo de DOF y el veredicto de viabilidad actual. No
sustituye el visor OpenGL, editor, parser ni la implementación de subida al
servidor.

Reutiliza el propio `assets/qss/industrial_dark.qss` de HYDRA-UMC SUITE tal cual (misma ruta relativa, mismo archivo) en vez de diseñar un tema visual nuevo para una herramienta de escritorio hermana en el mismo ecosistema.

### Panel de comandos visual (`--qtquick`)

Ese intento de integración es algo distinto y separado del panel de comandos Qt Quick real que esta app tiene ahora:

~~~
python main.py --qtquick
~~~

Una `ApplicationWindow` QML totalmente independiente (`qt_editor_urdf.py` + `assets/qml/EditorDeck.qml`), nunca embebida dentro del `QMainWindow` clásico - el mismo patrón ya probado que usan HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER y HYDRA-UMC-SUITE, lanzada junto al punto de entrada clásico sin reemplazarlo. Reproduce fielmente la disposición real del espacio de trabajo acoplable clásico (Source y DOF en pestañas a la izquierda, Viewport y Properties lado a lado, Upload abajo del todo) y las 5 funciones reales de cada panel - carga desde GitHub/galería/carpeta local, validación DOF en vivo, un preview 3D con orbit/pan/zoom con árbol de enlaces clicable y controles deslizantes de jog por articulación, edición de color/escala/límites de joint/masa e inercia, y el ciclo real de conectar/subir/descargar con el servidor STUDIO - a través del mismo `EditorController`, sin una segunda implementación de nada de esto. El preview 3D reutiliza el propio renderizado real del viewport clásico (`UrdfGLRenderer` de `render/viewport.py`) mediante un `OffscreenUrdfRenderer` dedicado, el mismo enfoque real de `QOpenGLContext`/`QOffscreenSurface`/framebuffer que ya usa el propio panel Viewport de Qt Quick de HYDRA-UMC-SUITE, alimentado a QML mediante un `QQuickImageProvider`.

## 🔒 Seguridad y protección

| Amenaza | Defensa | Dónde |
|---|---|---|
| Una ruta de malla que sale de la carpeta | Un `<mesh filename>` solo se resuelve a un fichero `.stl`, `.obj` o `.dae` dentro de la carpeta abierta, la del URDF o una que hayas añadido con «Localizar mallas que faltan»; se ignoran `..`, las rutas absolutas y los URI `file://` que lleven a otro sitio, y solo esos ficheros se suben | `source/scan.py`, `render/mesh.py` |
| Una malla o un fichero URDF roto, vacío u hostil | Las mallas vacías, truncadas o mal formadas se comunican como no cargadas en lugar de detener el visor; los ficheros que no son UTF-8 o son binarios, el texto mal formado y un ciclo en el árbol de eslabones se rechazan con un mensaje; una malla de más de 5 unidades se reescala una vez como milímetros | `render/mesh.py`, `urdf/parser.py`, `tests/test_edge_cases.py` |
| Una descarga de GitHub que se cuelga o que no es de GitHub | Solo se descargan direcciones que reconoce el patrón de URL de GitHub, como zipball con un límite de 20 s por petición y sin llamar a `git`; se aplica el propio límite de GitHub de 60 peticiones por hora y dirección | `source/github_fetcher.py` |
| Un robot que STUDIO no puede ejecutar, o un modelo guardado con valores imposibles | La comprobación de viabilidad acepta de 3 a 6 grados de libertad y rechaza articulaciones flotantes y planas, huérfanos y árboles desconectados o con varios padres; se hace una comprobación antes de guardar (límites de articulación, masas) y la exportación conserva una copia de seguridad | `urdf/dof.py`, `urdf/save_check.py` |
| Enviar un modelo a un servidor que no lo pidió | Decide el servidor: debe tener «Aceptar envíos de modelos» activado (Config > Modelos) y la cuenta debe ser administradora; cada llamada tiene un límite de 15 s y corre en un hilo de segundo plano; un nombre que ya existe se rechaza hasta marcar Sobrescribir | `server/client.py` |

**Lo que nunca hace:** conectarse a un robot, moverlo, ni dar a quien consuma un URDF exportado ninguna garantía sobre él. Quien use el fichero debe comprobarlo por su cuenta.

## 🔌 Interfaces

| Topic o ruta | Qué lleva |
|---|---|
| URDF file or folder / GitHub address | lo que se abre: una carpeta en disco, o un repositorio público de GitHub descargado como zip; los ficheros `.xacro` se rechazan con una explicación y las mallas `.dae` se nombran como no soportadas |
| URDF export | el árbol completo se vuelve a escribir desde el modelo con `urdf/writer.py`, así que cada edición está en el fichero exactamente una vez; el fichero que se sobrescribe se respalda antes |
| `POST /api/login` | inicia sesión; solo un token `admin` llega a la ruta de envío, y el cliente se adapta a un servidor que pide inicio de sesión incluso para listar modelos |
| `POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` | envía el URDF con sus mallas incluidas, lista el catálogo y trae de vuelta un modelo enviado a una carpeta de trabajo local |

## ⚙️ Configuración

Hay un pequeño fichero de configuración y las dependencias fijadas; no se lee nada más del entorno.

| Variable | Por defecto | Qué fija |
|---|---|---|
| `hydra_editor_urdf_config.json` | `{"language": ...}` | el idioma de la ventana, uno de los ocho ficheros `.lng` de `language/`; el fichero está junto al programa |
| `requirements.txt` | fijado | numpy 2.5.2, numpy-stl 4.0.0, PyOpenGL 3.1.10 y PySide6 6.11.1 |
| `MIN_SUPPORTED_DOF`, `MAX_SUPPORTED_DOF` | 3, 6 | los grados de libertad que STUDIO puede ejecutar, en `urdf/dof.py`; cámbialos allí si STUDIO cambia |

## 🚀 Inicio rápido

Requiere Python 3.11 o superior y un controlador gráfico con OpenGL 3.3. Los paquetes están fijados en `requirements.txt` y no hace falta instalar `git`: las fuentes de GitHub se descargan como zip.

```bash
pip install -r requirements.txt  # installs PySide6, PyOpenGL, numpy and numpy-stl at the pinned versions
python main.py                   # starts the editor (run.bat or run.sh do the same inside a .venv when there is one)
python main.py --qtquick         # the separate Qt Quick command deck
python -m pytest tests -q        # runs the tests (pip install -r requirements-dev.txt first)
```

### Requisitos
- [Python](https://www.python.org/) 3.11 o superior
- pip

### Instalación

```bash
pip install -r requirements.txt
```

Esto trae el conjunto de dependencias con versiones fijadas: **PySide6** (interfaz Qt6), **PyOpenGL** (renderizado del viewport 3D), **numpy** / **numpy-stl** (matemática de mallas y carga de STL). No se requiere una instalación de `git` - la ruta de carga de fuentes de GitHub descarga un simple zipball por HTTPS.

### Modo de Desarrollo

```bash
python main.py
```

O usa el script de conveniencia - `run.bat` (Windows) / `run.sh` (Linux/Mac), que activa `.venv` si existe junto a él y reenvía los argumentos a `main.py`; ninguno de los dos cierra su ventana de terminal por sí solo al hacer doble clic.

Arranca maximizado (no pantalla completa real a nivel de sistema operativo, así que la barra de título y los controles nativos de la ventana siguen visibles) - pulsa **F11** para alternar la pantalla completa real sin bordes y volver.

## 🧪 Pruebas

538 pruebas automáticas se ejecutan con `python -m pytest tests -q`. No necesitan hardware ni nada fuera de esta máquina.

El CI ejecuta `HYDRA_UMC_CI=1 python tools/ci_validate.py`, que comprueba el manifiesto, los documentos, los ocho README y las imágenes.

### Pruebas Automatizadas

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Nota: la lógica pura de esta app (parseo/exportación de URDF, validación de viabilidad DOF, cinemática directa, estimación de inercia, resolución de referencias de malla, obtención desde GitHub, i18n) tenía cero cobertura de pruebas automatizadas. Arreglado: 538 pruebas reales repartidas en 15 módulos de test, ninguno de los cuales importa PySide6/PyOpenGL - `requirements-dev.txt` solo instala lo que `tests/` necesita de verdad (`numpy` + `pytest`), así que la suite corre sin pantalla ni plugin de Qt. Varias pruebas son regresiones explícitas de errores ya encontrados y arreglados anteriormente y documentados directamente en el propio código fuente (la protección contra bucle infinito en un ciclo real de `render/kinematics.py`, la condición `had_scheme` de `source/scan.py`, la comprobación de masa negativa de `urdf/dof.py`) - una edición futura no puede reintroducir silenciosamente ninguno de ellos sin que falle una prueba. La CI (`.github/workflows/ci.yml`) ejecuta el mismo comando en cada push.

## 🏗️ Compilación y publicación

### Compilación de Producción

Compila un ejecutable independiente (no necesita una instalación de Python para ejecutarse) vía PyInstaller:

- **Windows:** ejecuta `build_exe.bat` → produce `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux:** ejecuta `./build_exe.sh` (`chmod +x build_exe.sh` una vez primero) → produce `dist/HYDRA-UMC_EDITOR-URDF`

Ambos scripts crean su propio `.venv`, instalan `requirements.txt` más `pyinstaller`, limpian cualquier `build`/`dist` previo, compilan, y finalmente copian `README.md`, `LICENSE`, y toda la carpeta `language/` junto al binario resultante (`language/` deliberadamente **no** se empaqueta dentro del ejecutable vía `--add-data`, así que un archivo `.lng` se puede editar o añadir después sin necesidad de recompilar).

**Versionado:** la versión de la aplicación (`hydra_editor_urdf/__version__`, mostrada en el diálogo Ayuda → Acerca de) sigue el esquema `MAJOR.MINOR.PATCH`. Compilar con `build_exe.bat`/`build_exe.sh` nunca la cambia; `python tools/hydra_project_tool.py bump` ejecuta `bump_version.py`, que aplica una subida al estilo cuentakilómetros: `PATCH` sube en 1; en cuanto `PATCH` superaría 9 vuelve a 0 y en su lugar `MINOR` sube en 1 (p.ej. `0.0.9` → `0.1.0`). `MAJOR` nunca se toca automáticamente - eso sigue siendo una decisión manual y deliberada. Ver `CHANGELOG.md` para el historial de versiones.

Si prefieres ejecutar los pasos equivalentes a mano en vez del script -útil para adaptar la compilación a una plataforma que los scripts no cubren, o para depurar un flag de PyInstaller- el proceso manual es:

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. Instalar dependencias + PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# 3. Localizar la propia carpeta de instalación de PySide6 (sus plugins Qt viven bajo ella)
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> $PYSIDE_DIR abajo

# 4. Compilar - solo se preparan explícitamente 4 subcarpetas de plugins Qt (platforms/
#    styles/imageformats/iconengines), NO --collect-all PySide6, que de otro modo
#    traería Qt6WebEngineCore.dll y otras piezas de varios cientos de MB que
#    esta aplicación nunca usa. El propio analizador de dependencias de PyInstaller
#    encuentra las verdaderas DLL de Qt6Core/Gui/Widgets/OpenGL siguiendo el grafo
#    de importación real de main.py - solo las carpetas de plugins hay que añadirlas a mano.
#
#    Windows (los plugins viven directamente bajo PySide6/plugins/):
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux (los plugins viven bajo PySide6/Qt/plugins/ en su lugar - una disposición
#    distinta a la de Windows, confirmada leyendo el propio runtime hook de PyInstaller
#    pyi_rth_pyside6.py):
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. Copiar los archivos que deben estar JUNTO AL binario, no dentro de él
cp README.md LICENSE dist/
cp -r language dist/language
```

En Linux, ejecutar el binario compilado necesita que el propio runtime de OpenGL del sistema esté presente (`libGL.so.1` - por ejemplo `libgl1` en Debian/Ubuntu, `mesa-libGL` en Fedora, `libglvnd` en Arch) más `libxkbcommon-x11-0`/`xcb-util-cursor` para el propio plugin de plataforma XCB de Qt; `build_exe.sh` comprueba `libGL.so.1` de antemano e imprime el comando de instalación correcto según la distribución si falta, en vez de fallar en lo profundo de una ejecución de PyInstaller.

## 🩺 Resolución de problemas

| Ves | Porque | Haz |
|---|---|---|
| Un error que nombra xacro, o un eslabón que falta en el visor | El fichero usa macros `<xacro:...>`, que no se expanden, o el eslabón apunta a una malla `.dae`, que no se carga | Expande antes el xacro con la herramienta `xacro` de ROS y exporta las mallas como `.stl` o `.obj` |
| Eslabones sin malla tras abrir un repositorio | Las rutas de las mallas no se resuelven dentro de la carpeta abierta, o las mallas están vacías o mal formadas | Usa «Localizar mallas que faltan» para añadir la carpeta que las contiene |
| El panel de GDL dice que el robot no es viable | El robot tiene menos de 3 o más de 6 grados de libertad, una articulación flotante o plana, un eslabón huérfano, o un árbol desconectado o con varios padres | Lee los motivos que aparecen bajo el veredicto y edita los tipos y límites de articulación en el panel de Propiedades |
| El envío se rechaza: un 409, un 401 o «no se aceptan envíos» | El nombre ya existe (409), la cuenta no es administradora o la sesión ya no existe (401), o el servidor tiene desactivado Aceptar envíos de modelos | Marca Sobrescribir para reemplazar, inicia sesión como administrador o activa los envíos en Config > Modelos del servidor |

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-EDITOR-URDF" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
HYDRA-UMC-EDITOR-URDF/
├── hydra_editor_urdf/
│   ├── __init__.py                  __version__ - única fuente de verdad, leída por el diálogo Acerca de y reescrita por bump_version.py
│   ├── app.py                       EditorController - único dueño de "qué está cargado", señales Qt que escucha cada panel
│   ├── models.py                    Árbol de objetos URDF propio (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                   Lista inicial de repositorios públicos reales y verificados de descripciones de robots
│   ├── inertia_calc.py              Fórmulas cerradas de momento de inercia para las geometrías primitivas
│   ├── i18n.py                      Cargador de language/*.lng, persistencia de configuración - portado desde el propio i18n.py de HYDRA-UMC-SUITE
│   ├── urdf/                        analizador, escritor, GDL y comprobación al guardar
│   ├── render/                      mallas, cinemática directa, vista OpenGL
│   ├── source/                      descarga de GitHub y carpetas locales
│   ├── server/                      el cliente de HYDRA-UMC-SERVER
│   └── ui/                          ventana, paneles, diálogos y tema
├── assets/                          icono, tema oscuro y la cubierta Qt Quick
├── images/                          banner e imágenes del README
├── language/                        english/spanish/italian/french/german/japanese/chinese/portuguese.lng - junto al exe, no empaquetado dentro
├── docs/                            documentos del proyecto
├── tests/                           Suite real de pytest (355 pruebas) - solo logica pura, sin ningun import de PySide6 aqui
├── tools/                           herramientas del proyecto y comprobaciones del CI
├── .github/                         flujo de CI y plantillas de incidencias
├── main.py                          Punto de entrada - QApplication, tema, arranque maximizado, alternancia F11 de pantalla completa; --qtquick cambia al panel de abajo
├── qt_editor_urdf.py                Interfaz Qt Quick - panel de comandos `--qtquick` independiente, conecta el EditorController sin tocar con QML
├── run.bat / run.sh                 Script de conveniencia - activa .venv si existe, ejecuta main.py, no se autocierra
├── requirements.txt                 PySide6, PyOpenGL, numpy-stl, numpy (con versiones fijadas)
├── requirements-dev.txt             Solo numpy + pytest - lo que tests/ necesita de verdad, sin PySide6
├── build_exe.bat / build_exe.sh     Scripts de compilación de ejecutable independiente para Windows/Linux (PyInstaller) - primero sube la versión
├── build-test.bat / build-test.sh   Comprobación de build/compilación sin subir versión
├── HYDRA-UMC_EDITOR-URDF.spec       Spec de PyInstaller usado por build_exe.bat/.sh
├── bump_version.py                  Incremento de versión tipo cuentakilómetros (solo lo ejecuta el comando `bump` explícito)
├── bump_manifest_version.py         Sincroniza la versión de hydra-umc.project.json con la nativa (--sync)
├── CHANGELOG.md                     Historial de versiones
├── LICENSE                          GPL-3.0-or-later
├── hydra-umc.project.json           manifiesto: versión, madurez, familia
└── test.sh                          comprobación de compilación sin cambios
```

</details>

## 🗺️ Hoja de ruta y límites conocidos

Las macros xacro no se expanden y las mallas COLLADA (`.dae`) no se cargan; ambas dan un error claro. Un robot debe caber en 3 a 6 grados de libertad para que STUDIO lo acepte. El viaje de ida y vuelta con el servidor se probó solo con un servidor de pruebas local, no con un HYDRA-UMC-SERVER real. La cubierta de mando Qt Quick es una ventana `--qtquick` aparte y no forma parte del espacio de trabajo acoplable.

## 🌍 Idiomas

Este README y los documentos del repositorio existen en ocho idiomas: inglés, español, alemán, francés, italiano, japonés, chino y portugués (Portugal). Se escriben a la vez y el CI comprueba que los ocho ficheros tengan las mismas secciones y los mismos enlaces.

## 🔗 Proyectos relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlo, ya que una petición podría en realidad ser sobre alguno de estos en vez de sobre este repositorio.

**Proyecto Padre**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — el catálogo de modelos que este editor existe para poblar; el resultado terminado se envía directamente a un servidor STUDIO en marcha vía `POST /api/models/submit`.

**Directamente Relacionados**
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de escritorio hermano para la geometría STL cruda del mismo catálogo de modelos, en vez del lado URDF/cinemática que edita esta herramienta.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — posee el endpoint real `POST /api/models/submit` al que este editor envía los modelos terminados.
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — consume los modelos URDF creados aquí para impulsar su simulación física.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — consume los modelos URDF creados aquí para impulsar su simulación física.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — genera datos de entrenamiento a partir de los modelos creados aquí.

**También Parte del Ecosistema**

*Núcleo de Hardware y Plataforma*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — capa de producto reproducible sobre Raspberry Pi OS para el CM5: agente de solo lectura, config/perfiles validados, aprovisionamiento WiFi de primer contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato JSON-Schema compartido y la barrera de software de puerta de trabajos contra la que cada bridge valida sus comandos (no es una función de seguridad certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro declarativo y validador de manifiestos de adaptador para conectores de máquinas externas; extiende la propia idea de contrato del SDK a máquinas externas sin sustituir a los proyectos de pasarela industrial.

*Backend y Clientes Principales*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — el diseño de la placa madre del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, pensado para coordinar hasta 8 brazos herramienta por CAN-OTA/SPI-OTA (firmware en fase temprana; todavía no hay ninguna placa poblada).
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de mando de enjambre de escritorio (PySide6) para varios servidores a la vez.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app de control Android nativa con login biométrico y una compañera Wear OS emparejada.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control iOS/iPadOS (Flutter) con sincronización WebSocket en tiempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla DSI de 7" integrada en la propia CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barrera de coordinación para flotas AGV/AMR mediante un publicador MQTT VDA 5050 (probado solo contra una flota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de alto nivel para celdas CNC con acceso a estado/bytes de control GRBL (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barrera de coordinación para droides con patas/humanoides, con un emisor de comandos para Boston Dynamics Spot (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de celdas láser que lee 3 señales GPIO de llave/carcasa/enclavamiento (probado solo contra un chip simulado; no puede armar ni disparar un láser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador seguro de alto nivel del flujo de placas para pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — límite de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo realmente controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador con un transporte ROS 2 rclpy importado de forma perezosa (todavía no ejecutado contra una instalación de ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barrera de coordinación para UAV equipados con cámara, con un emisor de comandos MAVLink (probado solo contra un emulador).

*Plataforma de Herramientas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física Universal Robot Tool Controller, 25+ perfiles de herramienta sobre bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — herramienta de escritorio con GUI para grabar placas URTC, CAN-OTA además de SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de escritorio de diagnóstico en vivo del bus CAN para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa en navegador a URTC-TESTER vía la Web Serial API, sin instalación local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — pasarela delante del bus CAN de URTC: lista de identificadores permitidos, límite de tasa y clave de sesión; software probado en ordenador, aún no en un bus real.

*Nodo de Visión IA (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integración del pipeline de visión Hailo-8, con una comprobación real de preparación de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación segura de arquitectura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + configuración MediaMTX con un límite real de integración HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección Position-Based Visual Servoing con autorización condicionada al estado de zona; todavía sin estimación de pose por cámara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — comprobación real de invasión de zona y solicitud de parada de emergencia, con exigencia de calibración vigente.

*Nodo Cognitivo IA (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integración del pipeline cognitivo Hailo-10 (orquestación LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectorias para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé al Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición de tareas real basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos con TF-IDF solo con la stdlib sobre la documentación Markdown propia de este ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de mantenimiento con IA local y con puertas de política para el propio ecosistema - observa, diagnostica y propone arreglos; los dos niveles de riesgo más altos están deliberadamente sin implementar todavía.

*Orquestación y Enjambre*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integración con un contrato real de informe de salud gRPC/Protobuf y máquina de estados de misión.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de salud de flota basado en gRPC con reintentos/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de rutas 3D real basado en RRT con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización real de estado CRDT LWW-Element-Map, probada con tests de propiedades para convergencia multi-celda.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enrutador hardware-in-the-loop con un enclavamiento de software por colisión entre simulación y hardware real (probado sin hardware real).

*Datos y Analítica*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — almacén real de series temporales sobre sqlite3 con una API HTTP real de ingesta/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detector real de anomalías por FFT + línea base estadística con monitorización de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidad sobre el histórico de DATALAKE, con exportación CSV reproducible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingesta CAN/WebSocket hacia DATALAKE, con deduplicación por secuencia.

*Pasarela Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integración que retransmite a protocolos industriales, con una capa real de lista blanca de comandos/contrapresión.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espacio de direcciones OPC-UA real, verificado con una sesión de cliente real de protocolo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real con autenticación opcional por cliente y ACLs de topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reales `/probe` y `/current` de MTConnect con salida en modo degradado.

*Herramientas Complementarias y Operaciones del Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — paneles de Resúmenes Inteligentes y Resaltado de Anomalías sobre DATALAKE/ANOMALY-DETECTOR, con un respaldo estadístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, un cliente genuino y en vivo de la API propia de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera de WearOS con patrones de alerta háptica y un relé de voz al teléfono emparejado (todavía no ejecutada en un reloj físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión real en Python para un cabezal de inspección térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — herramienta administrativa de escritorio que descubre, clona y actualiza cada repositorio de este ecosistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — herramienta de escritorio Windows/Linux que construye una imagen de la CM5 lista para grabar, precargada con las versiones más actuales del ecosistema, con configuración de primer arranque de Wi-Fi/usuario/SSH al estilo de Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinador de incidencias de mantenimiento: un rol edge de bajo privilegio recopila un snapshot de inventario/salud saneado, un rol control-plane lo renderiza de solo lectura y pide a un proveedor de IA que sugiera un diagnóstico - nunca aplica un parche ni despliega nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host de desarrollo reproducible (Raspberry Pi 5 / CM5) que almacena el código del ecosistema y ejecuta tareas acotadas de compilación/pruebas bajo una cola duradera; un rol de desarrollo dedicado, explícitamente distinto de un CM5 operativo.

## 📚 Documentación

Dónde leer más:

* [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md) - cada fichero fuente del editor con una línea sobre lo que hace
* [docs/LICENSING.md](docs/LICENSING.md) - cómo se licencian el código, los documentos y las mallas
* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — la forma interna propia del editor: por qué el parseo, la validación de viabilidad, la resolución de mallas y la previsualización 3D son carriles separados, y lo que esta app deliberadamente **no** hace (conectarse a un robot, subir un URDF o mandar movimiento por su cuenta).
* **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** — la ruta de validación no destructiva `build-test.bat`/`.sh` frente a un paquete real `build_exe.bat`/`.sh`, y qué es realmente hoy el panel de comandos (`QToolBar`, no Qt Quick/QML - ver la sección **Tema** arriba).
* **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** — lo que un consumidor final de un archivo URDF exportado debe validar por su cuenta; este proyecto no ofrece ningún endpoint de red ni autoridad de control de hardware propia.
* [Base de seguridad del ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modelo de amenazas del ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Historial de cambios de este repositorio](CHANGELOG.md)
* [Licencia de este repositorio](LICENSE.md)

## 🤝 Contribuir y comunidad

* Antes de un pull request ejecuta `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (o `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): debe imprimir `CI_VALIDATION=PASS`. No ejecutes `build.sh` ni `build.bat` para esta comprobación; compilar no es comprobar.
* Los ocho README se escriben desde una sola fuente en HYDRA-UMC-DOCS; no los edites a mano. Cambia la fuente y vuelve a escribirlos con `tools/make_readmes.py`.
* No afirmes en un README lo que no se ha ejecutado: di «simulado» o «sin probar en hardware» cuando esa sea la verdad.
* Mira [CONTRIBUTING.md](CONTRIBUTING.md), el [código de conducta](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) y [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - [LICENSE](LICENSE).
