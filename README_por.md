<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>
# 🦾 HYDRA-UMC EDITOR-URDF

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  🇵🇹 <b>Português</b>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="URDF">
</p>


### 🖌️ Criador/editor gráfico de URDF para o catálogo de modelos do HYDRA-UMC-STUDIO

**Versão atual:** 0.1.5 (`MAJOR.MINOR.PATCH` - ver a secção **Compilação de produção** abaixo para saber como este número se move)

---

**Verificação de honestidade - o que realmente funciona hoje:** o núcleo de lógica pura - leitura/exportação de URDF (`urdf/parser.py`, `urdf/writer.py`), validação da viabilidade de GDL (`urdf/dof.py`), cinemática direta (`render/kinematics.py`), estimativa de inércia (`inertia_calc.py`), resolução de referências a malhas e descarga de zipballs do GitHub (`source/scan.py`, `source/github_fetcher.py`, `source/local_folder.py`), o modelo em memória (`models.py`), a lista da galeria (`gallery.py`) e o carregador de i18n (`i18n.py`) - é real e coberto por 355 testes a passar (`tests/`), nenhum dos quais importa PySide6/PyOpenGL. O `test_github_fetcher.py` simula todas as chamadas de rede - uma descarga real de zipball do GitHub foi executada manualmente, nunca como parte da suíte automática. A camada Qt/OpenGL (o `UrdfGLRenderer` do `render/viewport.py`, o `render/mesh.py`, cada painel de `ui/*` e o `OffscreenUrdfRenderer` do painel `--qtquick`) é código real e funcional, mas não tem qualquer cobertura de testes automáticos - precisa de um ecrã real/plugin de plataforma Qt, que o CI não tem, pelo que é verificada à mão, não por uma suíte de testes. O `StudioClient` do `server/client.py` (login/push/pull contra o `server.ts` do HYDRA-UMC-SERVER) é código HTTP real, testado contra um pequeno servidor local que respeita o contrato do `server.ts` (o token em cada chamada, uma colisão de nome, a transferência de um modelo, uma resposta hostil). A expansão de xacro e o carregamento de malhas COLLADA (`.dae`) são não-funcionalidades explícitas e nomeadas (um erro claro, não uma má interpretação silenciosa) - ver a nota de honestidade na Visão geral abaixo e as secções Leitura de URDF/Carregamento de malhas para saber porquê. Consulte o `CHANGELOG.md` para saber exatamente o que já foi entregue.

---


> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado. Ainda não existe um caminho de E-STOP por hardware, nem limites ou interlocks impostos pelo firmware, nem um comando de movimento verificado; as imagens de firmware são verificadas com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica; TLS e TLS mútuo são opcionais e estão desativados por defeito; nenhuma placa própria foi ainda montada ou testada. Leia a [base de segurança](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.1.5` |
| Maturidade | Estabelecido |
| Testes | 355 |
| Tecnologia | Python / PySide6 / Qt6 / OpenGL |
| Destino | O PC de quem o usa |
| Em hardware real | Não aplicável: nada aqui corre em hardware |

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟢 | Completo para o seu propósito e estável; a verificação de honestidade acima lista os limites conhecidos |
| Testes | 🟢 | 355 testes automáticos, executados a cada alteração |
| Hardware real | 🟢 | Não aplicável: nada aqui corre em hardware |
| Documentação | 🟢 | README em oito idiomas, verificado contra o manifesto a cada alteração |

## 🎯 Visão geral

O **HYDRA-UMC EDITOR-URDF** é a ferramenta de desktop que transforma «portar um robô novo para o catálogo de modelos do [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)» de uma investigação manual, robô a robô, num fluxo de trabalho gráfico e repetível. Cada modelo de robô real do catálogo do STUDIO chegou lá da mesma maneira no passado: encontrar um repositório de descrição no GitHub, perceber como se resolvem as suas referências a malhas, contar os graus de liberdade da sua cadeia cinemática, verificar se o STUDIO consegue realmente acionar tantos e colocar à mão o resultado em `public/models/`. Esta aplicação automatiza toda essa passagem - traz os ficheiros de origem a partir de um URL do GitHub ou de uma pasta local já descarregada, resolve cada referência `<mesh filename="...">` (incluindo URIs `package://`) contra os ficheiros reais em disco, valida o número de GDL da cadeia contra o que a cinemática do STUDIO suporta hoje, edita cor/escala/limites das juntas/tipo de junta com uma pré-visualização 3D em direto e envia o resultado final diretamente para um servidor STUDIO em execução.

Construída com **Python** e **PySide6/Qt6**, usa os mesmos padrões de arquitetura já validados na outra ferramenta de desktop deste ecossistema, o [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE): um espaço de trabalho acoplável ao estilo Photoshop/Fusion-360 (`QDockWidget`), uma vista 3D OpenGL escrita à mão (`QOpenGLWidget` + shaders GLSL 3.3 de perfil core, sem o caminho legado `glBegin`/`glEnd`) e um objeto controlador central que detém o estado e a que todos os painéis da interface escutam através de sinais Qt. Reutilizar esse padrão aqui - em vez de explorar uma nova pilha de interface/renderização para uma ferramenta irmã do mesmo ecossistema - é uma escolha deliberada, não um descuido.

**Nota de honestidade, em linha com a convenção de documentação do resto deste ecossistema:** esta aplicação não expande macros [xacro](http://wiki.ros.org/xacro) e não carrega malhas COLLADA (`.dae`). Ambas são limitações nomeadas e explícitas (uma mensagem de erro clara, não uma má interpretação silenciosa nem um link em falta na vista) em vez de uma tentativa a meio - ver as secções **Leitura de URDF** e **Carregamento de malhas** abaixo para saber porque é que um suporte real para qualquer uma delas exigiria um trabalho adicional significativo.

---

## 📥 Carregamento da origem - GitHub ou pasta local

Duas formas de apontar a aplicação aos ficheiros de origem de um robô, ambas a desaguar no mesmo caminho de importação:

- **A partir de um URL do GitHub** - aceita um URL completo `https://github.com/owner/repo` (com ou sem `/tree/<branch>`), um `git@github.com:owner/repo.git` ao estilo SSH ou a abreviatura simples `owner/repo`. Deliberadamente **não** invoca `git clone`, o que tornaria uma instalação do `git` uma dependência obrigatória de execução tanto no Windows como no Linux para algo que uma simples descarga HTTPS já faz: o GitHub serve um zipball de qualquer ramo/etiqueta/commit a partir de `codeload.github.com` sem autenticação para um repositório público, pelo que isto usa o `urllib.request` + `zipfile` da própria biblioteca padrão e nada mais. Só são suportados repositórios públicos - não há tratamento de tokens/credenciais, e o zipball de um repositório privado dá 404 tal como o de um inexistente.
- **A partir de uma pasta local** - para um repositório já descarregado à mão, ou uma cópia de trabalho que o operador está a editar ativamente fora desta aplicação.
- **A partir da Galeria** - um pequeno menu «Galeria» acima do campo de URL do GitHub (`hydra_editor_urdf/gallery.py`) lista um conjunto inicial curto e verificado à mão de repositórios reais e ativos de descrição de robôs (o `universal_robot` da ROS-Industrial, o `open_manipulator` da ROBOTIS). Escolher uma entrada apenas preenche o campo de URL e mostra a sua descrição - nunca descarrega por si só, o operador ainda carrega em Descarregar, tal como ao escrever um URL à mão. Uma lista deliberadamente curta e escolhida à mão, e não recolhida automaticamente: uma entrada da galeria a apontar para um repositório morto ou malicioso seria pior do que não ter galeria nenhuma.

Seja como for, a aplicação procura depois recursivamente todos os ficheiros `*.urdf`/`*.xacro` sob a pasta escolhida, lista-os todos (um repositório real de descrição de robô traz muitas vezes mais do que um - um braço simples mais uma variante «com pinça» é um par comum) e escolhe automaticamente o maior por tamanho de ficheiro como valor razoável para «o principal» - passar para outro candidato depois é um duplo clique no painel Origem, e não uma nova descarga.

A **resolução de referências a malhas** é o trabalho pouco glamoroso que cada sessão manual anterior de portagem de robôs neste ecossistema fazia à mão: um `<mesh filename="package://some_pkg/meshes/link1.stl"/>` de um URDF quase nunca é um caminho diretamente abrível quando o ficheiro está numa pasta descarregada simples em vez de num espaço de trabalho ROS em direto, onde o `package://` se resolve através do índice de pacotes do ROS. O resolvedor tenta, por ordem: (1) a referência como caminho relativo à pasta do próprio URDF, (2) a mesma referência sem o segmento inicial de nome de pacote ao estilo `package://`, (3) como caminho absoluto, se por acaso já o for, e (4) pelo nome base simples em qualquer ponto da pasta de origem - que é o que realmente trata um URI `package://` real, já que o esquema e o nome do pacote não têm significado fora de um espaço de trabalho ROS em direto, mas o nome do ficheiro da malha continua a ser encontrável.

---

## ✅ Validação da viabilidade de GDL

A versão automática do mesmo juízo que as sessões anteriores deste ecossistema faziam à mão para cada robô acrescentado ao catálogo do STUDIO: **a cinemática do STUDIO suporta hoje cadeias em série de 3, 4, 5 e 6 GDL** (o seu `RobotState.joints` é um mapa fixo `j1..j6`) - alguns braços candidatos reais e de licença clara investigados no passado revelaram-se de 7, 8 ou 9 GDL e foram descartados exatamente por este motivo, não hipoteticamente. A cada importação (e após cada edição em direto que possa mudar a contagem - voltar a tipar uma junta, por exemplo), a aplicação percorre o grafo real de juntas pai/filho e reporta:

- **Contagem de GDL** - só as juntas `revolute`/`continuous`/`prismatic` contam como um grau de liberdade real e controlável; as `fixed` não contribuem com nenhum.
- **Tipos de junta não suportados** - uma única junta `floating` ou `planar` em qualquer ponto da cadeia torna todo o robô inviável independentemente da contagem de GDL, já que o modelo de juntas do STUDIO não tem representação para nenhuma delas.
- **Integridade da árvore** - exige-se exatamente um link raiz (uma árvore propriamente dita, não uma floresta nem um ciclo); qualquer link não alcançável a partir dessa raiz por uma cadeia de juntas é assinalado como desligado, e qualquer link referenciado por nenhuma junta como órfão.
- **`<limit>` em falta** - exigido pela especificação URDF para tudo exceto uma junta `continuous`; assinalado por junta se estiver ausente.

O veredicto e cada razão por trás dele são apresentados em direto no painel GDL, e o painel Envio recusa-se a enviar um robô inviável para um servidor.

---

## 🎨 Edição em direto com uma pré-visualização 3D real

O painel Propriedades edita o link que estiver selecionado na árvore de links do painel Vista, e cada edição altera o modelo carregado no lugar e revalida/volta a renderizar através de um único sinal (`EditorController.notify_tree_changed`) - nenhum painel precisa de saber como a vista ou o relatório de GDL reagem à sua própria edição:

- **Recolorir** - o material visual de um link, escolhido através de uma caixa de diálogo de cor padrão. Um material partilhado por nome por vários links (uma declaração `<material name="...">` de nível superior de um URDF real, referenciada por mais de um `<visual>`) recoloriza em conjunto todos os links que o partilham, em linha com o que essa sintaxe de material partilhado realmente significa na especificação.
- **Reescalar** - fator de escala por eixo (X/Y/Z) na própria transformação `<mesh scale="...">` da geometria da malha, e não uma reescrita destrutiva dos próprios dados de triângulos da malha - a mesma edição reaplicada mais tarde parte sempre da malha original e inalterada.
- **Voltar a tipar e a limitar uma junta** - mudar o tipo de uma junta (qualquer um dos 6 que a especificação URDF define) e o seu limite inferior/superior, com o veredicto do painel GDL a atualizar-se de imediato, já que uma mudança de tipo pode alterar a contagem de GDL ou introduzir um tipo não suportado.
- **Massa e inércia** - «Calcular automaticamente» preenche massa/Ixx/Iyy/Izz a partir da geometria do próprio link selecionado usando as fórmulas de densidade uniforme de forma fechada do `inertia_calc.py` (Caixa/Cilindro/Esfera exatas, Malha uma aproximação por caixa delimitadora - dito explicitamente, já que aqui não há integrador de malha por triângulo); uma massa introduzida pelo operador ganha sempre à estimativa baseada na densidade, e sem massa introduzida assume uma densidade genérica de alumínio (2700 kg/m³) e indica que o fez. «Aplicar» grava os campos no `Link.inertial` - o mesmo padrão de duas etapas calcular-e-depois-aplicar da Escala/Junta acima, para que um valor calculado possa ser observado ou ajustado à mão antes de ser escrito no modelo.

O **painel Vista** aloja a vista 3D OpenGL propriamente dita mais um cursor de jog por junta móvel, para que o operador possa pré-visualizar o URDF a mover-se ao longo do seu próprio intervalo real antes de tocar no STUDIO. A cinemática direta (`render/kinematics.py`) é genérica para qualquer árvore que acabou de ser importada - ao contrário do módulo de cinemática do próprio HYDRA-UMC SUITE, que aciona um registo fixo de algumas dezenas de modelos de robô conhecidos e verificados à mão, esta aplicação tem de posicionar um URDF arbitrário e nunca visto, pelo que compõe o `<origin>`/`<axis>` real de cada junta (fórmula de rotação de Rodrigues para um eixo revolute arbitrário, e não apenas o atalho de direções cardinais em que um registo fixo se poderia apoiar) percorrendo o grafo real pai/filho.

**Z para cima, não Y para cima** - a única divergência deliberada da convenção de vista do próprio HYDRA-UMC SUITE: o próprio URDF é um formato Z para cima (a gravidade é `-Z`, cada `<origin>`/`<axis>` de um ficheiro de origem é escrito a assumi-lo), e a tarefa desta aplicação é mostrar e editar um URDF fielmente na sua própria convenção, não reorientá-lo para o que um visualizador a jusante (a cena Three.js do STUDIO, a cena OpenGL do SUITE) por acaso prefira.

---

## 🗂️ Carregamento de malhas

O `.stl` (via `numpy-stl`) e o `.obj` (um pequeno carregador Wavefront escrito à mão - só `v`/`vn`/`f`, faces n-gon trianguladas em leque) são ambos cidadãos de primeira classe. **O COLLADA (`.dae`) não é suportado** - é um formato de grafo de cena XML muito maior (animação esquelética, vários sistemas de coordenadas, materiais/texturas embebidos) que precisaria de um analisador a sério para ser tratado com honestidade, em vez de um palpite do melhor esforço sobre as etiquetas que um `.dae` «simples» por acaso use; um link que referencie um recebe um erro claro e nomeado em vez de ficar em silêncio ausente da vista ou de fazer falhar toda a importação. Cada malha carregada recebe também a mesma proteção defensiva milímetros-versus-metros que o `useRealScaleSTL()` do próprio HYDRA-UMC STUDIO e o carregador de malhas do próprio HYDRA-UMC SUITE aplicam: um link com mais de 5 metros reais em qualquer eixo é muito mais provavelmente uma exportação em escala de milímetros sem metadados de unidade do que uma peça de robô gigante a sério, e é automaticamente reescalado por 0,001.

---

Os caminhos de malha estão confinados: um `<mesh filename>` só é resolvido para um ficheiro `.stl`, `.obj` ou `.dae` dentro da pasta aberta, da pasta do URDF ou de uma pasta adicionada em «Locate Missing Meshes»; os segmentos `..`, os caminhos absolutos e os URI `file://` que levem a outro sítio são ignorados, e só esses ficheiros são enviados. As malhas vazias, truncadas ou mal formadas são indicadas como não carregadas em vez de parar o visualizador. A proteção milímetros-metros redimensiona qualquer malha com mais de 5 unidades antes de aplicar a `scale` do URDF, pelo que uma malha já escalada pelo URDF pode ser reduzida duas vezes. As etiquetas que o editor não modela (`<dynamics>`, `<safety_controller>`, `<mimic>`, `<transmission>`, `<gazebo>`, texturas de material) não são conservadas ao reexportar um URDF.

## 📜 Leitura e exportação de URDF

XML simples através do `xml.etree.ElementTree` da própria biblioteca padrão - não é preciso nenhuma dependência `lxml` para um formato tão simples. O modelo em memória (`hydra_editor_urdf/models.py`) é uma árvore de dataclasses própria, deliberadamente simples e mutável, e não um invólucro de uma biblioteca Python de URDF existente como a `urdfpy` ou a `yourdfpy`: esta aplicação precisa de *editar* a árvore de forma interativa e voltar a renderizar cada alteração em direto, para o que uma biblioteca de análise de leitura predominante não está desenhada, e ser dona do modelo mantém-no pequeno, inspecionável e livre do ritmo de lançamentos de uma dependência de terceiros. Os nomes dos campos e os valores por defeito seguem de perto o [esquema XML do URDF](http://wiki.ros.org/urdf/XML) real, para que o par leitor/escritor continue a ser um mapeamento XML↔objeto fino e óbvio.

**O xacro não é expandido.** O [xacro](http://wiki.ros.org/xacro) é um pré-processador de macros Python/XML com o seu próprio pacote ROS e cadeia de dependências, e um ficheiro xacro real só é resolúvel de forma fiável dentro do mesmo ambiente de pacotes ROS contra o qual foi escrito (argumentos de macros, inclusões ao estilo `$(find pkg)`, etc.) - algo que esta aplicação não tem forma de reproduzir com honestidade. Um ficheiro que use etiquetas `<xacro:...>` ou declare o espaço de nomes xacro recebe um erro claro que explica a limitação e aponta para a ferramenta de linha de comandos `xacro` do ROS para o pré-processar primeiro, em vez de uma má interpretação silenciosa.

A exportação (`urdf/writer.py`) volta a serializar a árvore atual em memória de raiz, em vez de remendar o texto XML de origem original, pelo que cada edição em direto - qualquer que seja o painel que a fez - se reflete exatamente uma vez, por um único caminho de código, tanto na ação de menu «Exportar URDF» como no payload enviado a um servidor STUDIO.

---

## 🖥️ Espaço de trabalho acoplável

Painéis `QDockWidget` reais - arraste para flutuar, arraste de volta para acoplar, junte em separadores, divida o espaço de trabalho - o mesmo mecanismo e raciocínio que a janela principal do próprio HYDRA-UMC SUITE já aplica: o sistema de acoplamento do próprio Qt já faz exatamente o que um espaço de trabalho ao estilo Photoshop/Fusion-360 precisa, e um feito à mão apenas o reinventaria com mais erros. Cinco painéis, dispostos com uma disposição por defeito sensata que depois é totalmente reorganizável:

- **Origem** - entrada de URL do GitHub / pasta local, lista de `.urdf` encontrados.
- **GDL** - o veredicto de viabilidade e cada razão por trás dele.
- **Vista** - a vista 3D em direto, a árvore de links e os cursores de jog.
- **Propriedades** - recolorir / reescalar / voltar a tipar e a limitar o link selecionado.
- **Envio** - ligar a um servidor STUDIO, enviar ou trazer.

---

## ☁️ Ida e volta com o servidor

Fala com o contrato de submissão de modelos do próprio HYDRA-UMC-SERVER (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` no próprio `server.ts` desse projeto, protegido pelo seu próprio interruptor **Config > Models > «Accept model submissions»**) usando o `urllib.request` da própria biblioteca padrão - mais uma chamada HTTP não justificou trazer o `httpx`/`requests` para um projeto que só precisa de 4 endpoints, não de uma ligação viva persistente. Cada chamada corre num `QThread` em segundo plano, para que um servidor lento ou inalcançável nunca congele a interface. Este contrato vivia dentro do processo do próprio HYDRA-UMC-STUDIO antes de esse projeto se dividir num frontend puro (STUDIO) mais um back-end headless separado (HYDRA-UMC-SERVER, ver **Projetos relacionados** abaixo) - esta aplicação não codifica nenhum dos dois nomes, o operador limita-se a apontar os campos de anfitrião/porta do painel **Envio** para onde quer que o back-end real esteja a correr.

- **Login** - `POST /api/login`; só um token com papel `admin` consegue de facto chegar a `POST /api/models/submit` no servidor, pelo que esta aplicação só é realmente utilizável contra uma conta de administrador, tal como qualquer outra funcionalidade do STUDIO reservada a administradores.
- **Enviar (push)** - serializa o robô atual de volta para XML URDF e codifica em base64 cada ficheiro de malha que os seus visuais referenciam (resolvido através do mesmo resolvedor de malhas construído na importação) dentro do corpo do pedido, etiquetado com a categoria escolhida pelo operador (espelhando as categorias de Config > UI > Module Visibility do próprio STUDIO: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - um URDF não tem campo próprio que diga qual destas é). Uma colisão de nome volta como a própria resposta 409 do servidor; o operador decide se volta a submeter com **Overwrite** marcado ou se muda o nome, esta aplicação nunca adivinha.
- **Trazer (pull)** - descarrega o URDF + malhas de um modelo já submetido para uma pasta de trabalho local e carrega-o diretamente no editor - a metade «extrair, editar, reenviar» da ida e volta que é o próprio propósito desta aplicação, permitindo retocar uma entrada existente do catálogo sem recomeçar a partir do seu repositório de origem.

---

## 🌐 Interface multilingue

Tradução completa da interface em **inglês, espanhol, italiano, francês, alemão, chinês (simplificado), japonês e português** (`language/*.lng`), usando exatamente o mesmo mecanismo simples de ficheiros `KEY=Value` que todas as outras ferramentas Python deste ecossistema (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - não reinventado aqui, já que o próprio mecanismo não leva nenhuma lógica específica do projeto. Uma mudança de idioma tem efeito depois de reiniciar a aplicação, em vez de voltar a traduzir em direto cada widget já construído, em linha com essa mesma convenção. A pasta `language/` fica **ao lado** do executável em vez de empacotada dentro dele via `--add-data` do PyInstaller, para que um tradutor possa editar ou acrescentar um ficheiro `.lng` sem recompilar.

---

## 🎛️ Tema

A barra de ferramentas superior do espaço de trabalho acoplável é um verdadeiro painel de comandos `QToolBar`/`QLabel`/`QToolButton`, e não uma interface Qt Quick/QML separada - uma versão anterior embebida através de QQuickWidget (o mesmo renderizador do HYDRA-UMC-UPDATER e do HYDRA-UMC-SUITE) renderizava uma barra preta sólida, sem erro na consola, depois de colocada dentro do verdadeiro layout `QDockWidget` desta `QMainWindow`, pelo que foi revertida para widgets simples; ver o `CHANGELOG.md` para a história completa. Os seus botões Origem, GDL, Vista, Propriedades e Envio apenas levantam os painéis existentes; Exportar e Acerca de encaminham para as ações existentes, e o Exportar fica desativado até um modelo estar realmente carregado. Depois de carregar um URDF (e depois de cada edição de propriedade em direto), o seu indicador de estado mostra o nome do modelo carregado, a contagem de GDL e o veredicto atual de viabilidade. Não substitui a vista OpenGL, o editor, o leitor nem a implementação de envio ao servidor.

Reutiliza tal como está o `assets/qss/industrial_dark.qss` do próprio HYDRA-UMC SUITE (o mesmo caminho relativo, o mesmo ficheiro) em vez de desenhar um novo tema visual para uma ferramenta de desktop irmã do mesmo ecossistema.

### Painel de comandos visual (`--qtquick`)

Essa tentativa de embebimento é uma coisa diferente e separada do verdadeiro painel de comandos Qt Quick que esta aplicação tem agora:

~~~
python main.py --qtquick
~~~

Uma `ApplicationWindow` QML genuinamente autónoma (`qt_editor_urdf.py` + `assets/qml/EditorDeck.qml`), nunca embebida dentro da `QMainWindow` clássica - o mesmo padrão comprovado que o HYDRA-UMC-OS-REBUILDER, o HYDRA-UMC-UPDATER, o URTC-TESTER, o URTC-FLASHER e o HYDRA-UMC-SUITE já usam, lançada ao lado do ponto de entrada clássico inalterado em vez de o substituir. Espelha a disposição real do espaço de trabalho acoplável clássico (Origem e GDL em separadores à esquerda, Vista e Propriedades lado a lado, Envio ao longo da parte inferior) e as funcionalidades reais de cada um dos seus 5 painéis - carregamento a partir do GitHub/galeria/pasta local, validação de GDL em direto, uma pré-visualização 3D com órbita/deslocação/zoom com árvore de links clicável e cursores de jog por junta, edição de cor/escala/limites das juntas/massa e inércia, e a ida e volta de ligar/enviar/trazer com o servidor STUDIO - através do mesmo `EditorController`, sem uma segunda implementação de nada disso. A pré-visualização 3D reutiliza o código real de renderização da vista clássica (o `UrdfGLRenderer` do `render/viewport.py`) através de um `OffscreenUrdfRenderer` dedicado, a mesma abordagem real de `QOpenGLContext`/`QOffscreenSurface`/framebuffer que o painel Viewport Qt Quick do próprio HYDRA-UMC-SUITE já usa, alimentada ao QML através de um `QQuickImageProvider`.

---

## 📂 Estrutura do repositório

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # Ponto de entrada - QApplication, tema, arranque maximizado, F11 alterna ecrã inteiro; --qtquick muda para o painel abaixo
├── qt_editor_urdf.py               # Front end Qt Quick - painel de comandos `--qtquick` autónomo, liga o EditorController inalterado ao QML
├── run.bat / run.sh                # Invólucro de conveniência - ativa o .venv se existir, executa o main.py, sem fecho automático
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (fixados)
├── requirements-dev.txt            # só numpy + pytest - o que os tests/ realmente precisam, sem PySide6
├── build_exe.bat / build_exe.sh    # Scripts de compilação de executável autónomo para Windows/Linux (PyInstaller) - sobem primeiro a versão
├── build-test.bat / build-test.sh  # Verificação de compilação sem alterar versões
├── HYDRA-UMC_EDITOR-URDF.spec      # Especificação de compilação do PyInstaller usada pelo build_exe.bat/.sh
├── bump_version.py                 # Subida de versão ao estilo conta-quilómetros (executada só pelo comando `bump` explícito)
├── bump_manifest_version.py        # Sincroniza a versão do hydra-umc.project.json com a nativa (--sync)
├── CHANGELOG.md                    # Histórico de versões
├── README.md                       # Este ficheiro
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  # <- traduções
├── LICENSE                         # GPL-3.0-or-later
├── assets/
│   ├── HYDRA_UMC_ICON.svg          # Marca animada do HYDRA-UMC usada pelo painel de comandos da barra de ferramentas
│   ├── qss/industrial_dark.qss     # Reutilizado tal como está do HYDRA-UMC-SUITE
│   └── qml/EditorDeck.qml          # Interface Qt Quick do painel de comandos `--qtquick`
├── images/
│   └── HYDRA_UMC_BANNER.svg        # Multimédia e diagramas
├── language/                       # english/spanish/italian/french/german/japanese/chinese/portuguese.lng - ficam ao lado do exe, não empacotados
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ - fonte única de verdade, lida pela caixa Acerca de e reescrita pelo bump_version.py
│   ├── app.py                      # EditorController - único dono de «o que está carregado», sinais Qt a que todos os painéis escutam
│   ├── models.py                   # Árvore própria de objetos URDF (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                  # Lista inicial de repositórios públicos reais e verificados de descrição de robôs
│   ├── inertia_calc.py             # Fórmulas de momento de inércia de forma fechada para as geometrias primitivas
│   ├── i18n.py                     # Carregador de language/*.lng, persistência da configuração - portado do i18n.py do próprio HYDRA-UMC-SUITE
│   ├── urdf/
│   │   ├── parser.py               # XML URDF -> árvore do models.py (ElementTree, xacro detetado e rejeitado com um erro claro)
│   │   ├── writer.py                # árvore do models.py -> cadeia XML URDF (exportação + payload de envio ao servidor)
│   │   └── dof.py                  # Contagem de GDL, validação de viabilidade contra o teto de 3-6 GDL do STUDIO
│   ├── render/
│   │   ├── mesh.py                 # Carregamento de STL/OBJ, geração de primitivas caixa/cilindro/esfera, proteção mm-versus-m
│   │   ├── kinematics.py           # Cinemática direta genérica sobre uma árvore importada arbitrária (Z para cima, a convenção do próprio URDF)
│   │   └── viewport.py             # UrdfGLRenderer (shader core GLSL 3.3, câmara orbital, buffers de GPU por link) + o invólucro clássico QOpenGLWidget + OffscreenUrdfRenderer para o painel `--qtquick`
│   ├── source/
│   │   ├── scan.py                 # Encontra ficheiros .urdf/.xacro, constrói o resolvedor de nomes de malhas consciente de package://
│   │   ├── github_fetcher.py       # Descarga e extração de zipball do GitHub (urllib + zipfile, sem dependência do git)
│   │   └── local_folder.py         # Validação de pasta local - a contraparte fina do github_fetcher.py
│   ├── server/
│   │   └── client.py               # StudioClient - login/list_models/push_model/pull_model contra o server.ts do HYDRA-UMC-SERVER (o back-end do próprio STUDIO antes de os dois repositórios se dividirem)
│   └── ui/
│       ├── main_window.py          # QMainWindow - espaço de trabalho acoplável, barra de menus, seletor de idioma, barra de estado
│       ├── about_dialog.py         # Caixa Acerca de real, em linha com o About.tsx do próprio STUDIO e o about_dialog.py do próprio SUITE
│       ├── theme.py                 # Aplica o assets/qss/industrial_dark.qss
│       └── panels/
│           ├── source_panel.py     # Entrada de URL do GitHub / pasta local, lista de URDF encontrados
│           ├── dof_panel.py        # Leitura do veredicto de viabilidade
│           ├── viewport_panel.py   # Anfitrião da vista 3D, árvore de links, cursores de jog
│           ├── properties_panel.py # Editores de recolorir / reescalar / voltar a tipar e a limitar
│           └── upload_panel.py     # Ligar/enviar/trazer com o servidor
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   └── INTEGRATION_CONTRACT.md
├── tests/                          # Suíte pytest real (355 testes) - só lógica pura, sem importar PySide6 em lado nenhum
│   ├── test_urdf_parser.py / test_urdf_writer.py  # XML URDF <-> models.py, incluindo idas e voltas leitura -> escrita -> leitura
│   ├── test_dof.py                 # Validação de viabilidade, limites de GDL, deteção de raiz/órfão/desligado/multi-pai
│   ├── test_kinematics.py          # Cinemática direta, incluindo a regressão corrigida do ciclo real que bloqueava para sempre
│   ├── test_inertia_calc.py        # Tensores de caixa/cilindro/esfera de forma fechada contra valores de manual calculados de forma independente
│   ├── test_models.py              # Robot.root_link_name()/joints_by_parent()/movable_joints()
│   ├── test_scan.py                # find_urdf_files()/build_mesh_resolver(), incluindo a regressão corrigida do had_scheme e a escolha determinista do ficheiro mais próximo
│   ├── test_local_folder.py / test_github_fetcher.py  # Validação da origem; chamadas de rede do GitHub simuladas, nunca reais
│   ├── test_i18n.py                # E/S de configuração/ficheiros de idioma contra ficheiros temporários reais, nunca a configuração real do operador
│   └── test_gallery.py             # Verificações estruturais da lista GALLERY escolhida à mão
├── tools/
│   ├── build_test.py               # Verificação de compilação sem subir versão
│   └── ci_validate.py              # Validação de manifesto/CHANGELOG/docs usada pelo CI
├── build/                           # Diretoria de trabalho intermédia do próprio PyInstaller (ignorada pelo git)
├── dist/                            # Executável autónomo compilado (saída do build_exe.bat/.sh, ignorado pelo git)
└── work/                            # Espaço de trabalho temporário de execução para repositórios do GitHub descarregados e modelos do servidor trazidos (ignorado pelo git)
```

Nota: uma tentativa anterior embebeu um painel de comandos Qt Quick/QML (`assets/qml/CommandDeck.qml`, `ui/qtquick_deck.py`) diretamente dentro do verdadeiro layout `QDockWidget` desta `QMainWindow` via `QQuickWidget` - nunca compôs corretamente (preto sólido, sem erro na consola) e foi revertida; o painel de comandos da barra de ferramentas acima são widgets simples `QToolBar`/`QLabel`/`QToolButton`. O verdadeiro painel de comandos Qt Quick que esta aplicação tem hoje (`qt_editor_urdf.py` / `assets/qml/EditorDeck.qml`, listado acima) é, em vez disso, uma janela `--qtquick` autónoma, diferente e posterior - ver **🎛️ Tema** acima e o `CHANGELOG.md` para a história completa.

---

## 🛠️ Ambiente de desenvolvimento

### Requisitos
- [Python](https://www.python.org/) 3.11 ou superior
- pip

### Instalação

```bash
pip install -r requirements.txt
```

Isto traz o conjunto fixado de dependências: **PySide6** (interface Qt6), **PyOpenGL** (renderização da vista 3D), **numpy** / **numpy-stl** (matemática de malhas e carregamento de STL). Não é preciso instalar o `git` - o caminho de carregamento da origem do GitHub descarrega um zipball simples por HTTPS.

### Modo de desenvolvimento

```bash
python main.py
```

Ou use o invólucro de conveniência - `run.bat` (Windows) / `run.sh` (Linux/Mac), que ativa o `.venv` se existir ao lado e reencaminha quaisquer argumentos para o `main.py`; nenhum dos scripts fecha por si só a janela do terminal quando se faz duplo clique.

Arranca maximizado (não em ecrã inteiro verdadeiro do sistema operativo, para que a barra de título e os controlos nativos da janela continuem visíveis) - carregue em **F11** para alternar o ecrã inteiro real sem bordas e voltar.

### Testes automáticos

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Nota: a lógica pura desta aplicação (leitura/exportação de URDF, viabilidade de GDL, cinemática direta, estimativa de inércia, resolução de referências a malhas, descarga do GitHub, i18n) tinha cobertura de testes automáticos zero. Corrigido: 355 testes reais em 15 módulos de teste, nenhum dos quais importa PySide6/PyOpenGL - o `requirements-dev.txt` instala apenas o que os `tests/` realmente precisam (`numpy` + `pytest`), pelo que a suíte corre sem ecrã nem plugin de plataforma Qt. Vários testes são regressões explícitas de erros já encontrados e corrigidos anteriormente e documentados em linha no próprio código-fonte (a proteção contra ciclo infinito num ciclo real do `render/kinematics.py`, a condição `had_scheme` do `source/scan.py`, a verificação de massa negativa do `urdf/dof.py`) - uma edição futura não pode reintroduzir nenhum deles em silêncio sem que um teste falhe. O CI (`.github/workflows/ci.yml`) executa o mesmo comando a cada push.

### Compilação de produção

Compila um executável autónomo (não é preciso instalação de Python para o executar) via PyInstaller:

- **Windows:** execute `build_exe.bat` → produz `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux:** execute `./build_exe.sh` (`chmod +x build_exe.sh` uma vez antes) → produz `dist/HYDRA-UMC_EDITOR-URDF`

Ambos os scripts criam o seu próprio `.venv`, instalam o `requirements.txt` mais o `pyinstaller`, limpam qualquer `build`/`dist` anterior, compilam e, por fim, copiam o `README.md`, o `LICENSE` e toda a pasta `language/` para junto do binário resultante (a `language/` deliberadamente **não** é empacotada dentro do executável via `--add-data`, para que um ficheiro `.lng` possa ser editado ou acrescentado depois sem recompilar).

**Versionamento:** a versão da aplicação (`hydra_editor_urdf/__version__`, mostrada na caixa Ajuda → Acerca de) segue `MAJOR.MINOR.PATCH`. Compilar com o `build_exe.bat`/`build_exe.sh` nunca a altera; `python tools/hydra_project_tool.py bump` executa o `bump_version.py`, que aplica uma subida estilo odómetro: o `PATCH` sobe 1; quando o `PATCH` ultrapassaria 9 volta a 0 e é o `MINOR` que sobe 1 (p. ex. `0.0.9` → `0.1.0`). O `MAJOR` nunca é tocado automaticamente - isso continua a ser uma decisão deliberada e manual. Consulte o `CHANGELOG.md` para o histórico de versões.

Se preferir executar à mão os passos equivalentes em vez do script - útil para adaptar a compilação a uma plataforma que os scripts não cobrem, ou para depurar uma flag do PyInstaller - o processo manual é:

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

No Linux, executar o binário compilado precisa de o runtime OpenGL do próprio sistema presente (`libGL.so.1` - p. ex. `libgl1` em Debian/Ubuntu, `mesa-libGL` em Fedora, `libglvnd` em Arch) mais `libxkbcommon-x11-0`/`xcb-util-cursor` para o plugin de plataforma XCB do próprio Qt; o `build_exe.sh` verifica logo de início a presença de `libGL.so.1` e imprime o comando de instalação certo por distribuição se faltar, em vez de falhar nas profundezas de uma execução do PyInstaller.

---

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Projeto-mãe**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — o catálogo de modelos que este editor existe para povoar; o resultado final é enviado diretamente para um servidor STUDIO em execução através de `POST /api/models/submit`.

**Diretamente relacionados**
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de desktop irmão para a geometria STL em bruto do mesmo catálogo de modelos, em vez do lado URDF/cinemática que esta ferramenta edita.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — é dono do endpoint real `POST /api/models/submit` para onde este editor envia os modelos concluídos.
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — consome os modelos URDF criados aqui para conduzir a sua simulação física.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — consome os modelos URDF criados aqui para conduzir a sua simulação física.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gera dados de treino a partir dos modelos criados aqui.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame para desktop (PySide6) para vários servidores ao mesmo tempo, empacotado como executável independente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway à frente do barramento CAN do URTC: lista de identificadores permitidos, limite de taxa e chave de sessão; software testado num computador, ainda não num barramento real.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Nó de IA cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integração do pipeline cognitivo do Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé para o relógio limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

*Orquestração e enxame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integração com um contrato real de relatório de saúde gRPC/Protobuf e uma máquina de estados de missões.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integração que retransmite para protocolos industriais, com uma camada real de lista de comandos permitidos e contrapressão.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão de cliente real do protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML MTConnect `/probe` e `/current` reais com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta administrativa de desktop que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop para Windows/Linux que constrói uma imagem do CM5 pronta a gravar com as versões mais recentes do ecossistema, com configuração de primeiro arranque de Wi-Fi/utilizador/SSH ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

---

## 📚 Documentação e comunidade

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — a forma interna do próprio editor: porque é que a leitura, a validação de viabilidade, a resolução de malhas e a pré-visualização 3D são vias separadas, e o que esta aplicação deliberadamente *não* faz (ligar-se a um robô, enviar um URDF ou comandar movimento por si própria).
- **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** — o caminho de validação sem alterações do `build-test.bat`/`.sh` face a um pacote real do `build_exe.bat`/`.sh`, mais o que o painel de comandos realmente é hoje (`QToolBar`, não Qt Quick/QML - ver a secção **Tema** acima).
- **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** — o que um consumidor a jusante de um ficheiro URDF exportado tem de validar por si; este projeto não oferece nenhum endpoint de rede nem autoridade própria de controlo de hardware.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pilha tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como comunicar uma vulnerabilidade e as áreas de segurança em que este projeto se concentra.
- **[SUPPORT.md](SUPPORT.md)** — onde fazer perguntas e comunicar erros.
- **[LICENSE.md](LICENSE.md)** — a licença deste projeto.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA

O HYDRA-UMC EDITOR-URDF é (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso tem de ser incluído em qualquer distribuição deste projeto ou de obras derivadas.

Este projeto é composto por código-fonte e pela sua própria documentação, disponibilizados sob licenças diferentes - cada uma adequada ao que realmente cobre:

1. O código-fonte (`hydra_editor_urdf/`, `main.py` e qualquer binário compilado a partir dele através do `build_exe.bat`/`build_exe.sh`) está disponível sob a **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Texto completo em https://www.gnu.org/licenses/gpl-3.0.html.

2. A documentação (este README e as suas próprias traduções - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`, `README_por.md`) está disponível sob a **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Texto completo em https://creativecommons.org/licenses/by-sa/4.0/.

Esta aplicação não distribui ativos de malha de robôs de terceiros - ao contrário do `public/models/` do HYDRA-UMC STUDIO, cada malha que este editor alguma vez carrega vem do repositório de origem ou da pasta local para onde o operador o apontar, sob a licença original própria dessa origem. Rever e preservar essa licença/atribuição de origem antes de submeter um modelo a um servidor STUDIO em execução (cuja convenção `public/models/<slug>/ATTRIBUTION.txt` é alimentada pela exportação deste editor) continua a ser responsabilidade do próprio operador - esta aplicação não tem forma de detetar nem de fazer cumprir automaticamente os termos de licenciamento de um repositório de origem.

Este editor é a ferramenta de criação de modelos para o catálogo do [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - consulte esse repositório para o seu próprio licenciamento do lado do servidor, a que a licença deste repositório não se estende, e vice-versa.

Se construir sobre este projeto, tenha em mente a divisão de licenças: as alterações de código aqui devem permanecer GPL-3.0-or-later, os derivados de documentação (este README e as suas traduções) devem permanecer CC BY-SA 4.0, e qualquer ativo de malha que passe por este editor (importado, editado ou exportado) deve permanecer sob a licença que o seu próprio repositório de origem original tiver, com atribuição de volta a essa origem.

