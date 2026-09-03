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
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="URDF">
</p>


### 🖌️ 面向 HYDRA-UMC-STUDIO 模型目录的图形化 URDF 创建/编辑工具

**当前版本：** 0.0.2（`MAJOR.MINOR.PATCH`——该编号的变化方式见下方“生产构建”一节）

---

## 🎯 概述

**HYDRA-UMC EDITOR-URDF** 是一款桌面工具，将“把一个新机器人移植进 [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 的模型目录”这件事，从一次性的、逐机器人的人工调查，变成了一套可重复的图形化工作流程。STUDIO 目录中的每一个真实机器人型号，过去都是通过同样的方式进入的：在 GitHub 上找到一个描述仓库、弄清楚其网格引用如何解析、数清其运动学链中的自由度数量、检查 STUDIO 是否真的能驱动这么多自由度，然后手动将结果放入 `public/models/`。本应用将整个流程自动化——从一个 GitHub URL 或一个已下载的本地文件夹拉取源文件，针对磁盘上的真实文件解析每一个 `<mesh filename="...">` 引用（包括 `package://` URI），根据 STUDIO 当前运动学所支持的范围验证该链条的自由度数量，通过实时 3D 预览编辑颜色/比例/关节限位/关节类型，并将完成的结果直接推送到一个正在运行的 STUDIO 服务器。

使用 **Python** 和 **PySide6/Qt6** 构建，采用与本生态系统中另一款桌面工具 [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE) 中已经验证过的相同架构模式：类 Photoshop/Fusion-360 的可停靠工作区（`QDockWidget`）、一个手写的 OpenGL 3D 视口（`QOpenGLWidget` + GLSL 3.3 核心配置着色器，不使用 `glBegin`/`glEnd` 遗留路径），以及一个持有状态的中央控制器对象，每个 UI 面板都通过 Qt 信号监听它。在本生态系统的同类工具上复用这一模式——而非为其探索一套新的 UI/渲染技术栈——是一个刻意的选择，而非疏忽。

**诚实说明，与本生态系统其余文档所采用的惯例一致：** 本应用不展开 [xacro](http://wiki.ros.org/xacro) 宏，也不加载 COLLADA（`.dae`）网格。两者都是明确命名的限制（一条清晰的错误信息，而非静默的解析错误或视口中缺失的连杆），而非半成品式的尝试——具体原因见下方“URDF 解析”和“网格加载”两节。

---

## 📥 源加载——GitHub 或本地文件夹

有两种方式将本应用指向一个机器人的源文件，两者最终都进入同一条导入路径：

- **从 GitHub URL** —— 接受完整的 `https://github.com/owner/repo` URL（带或不带 `/tree/<branch>`）、SSH 风格的 `git@github.com:owner/repo.git`，或简写的 `owner/repo`。刻意**不**调用外部的 `git clone`，那会让 `git` 安装成为 Windows 和 Linux 上一个硬性的运行时依赖，而这本可以通过纯 HTTPS 下载完成：GitHub 会从 `codeload.github.com` 提供任意分支/标签/提交的 zip 压缩包，对公开仓库无需任何身份验证，因此本应用只使用标准库自身的 `urllib.request` + `zipfile`，别无其他。仅支持公开仓库——没有令牌/凭证处理，私有仓库的 zip 包会像不存在的仓库一样返回 404。
- **从本地文件夹** —— 适用于已经手动下载的仓库，或操作员正在此应用之外主动编辑的工作副本。
- **从 Gallery** —— GitHub URL 输入框上方的 "Gallery" 下拉菜单（`hydra_editor_urdf/gallery.py`）列出了一小份经人工核实的真实机器人描述仓库起始清单（ROS-Industrial 的 `universal_robot`、ROBOTIS 的 `open_manipulator`）。选择一项只会填入 URL 并显示其描述——不会自行发起下载，操作员仍需自己点击 Fetch，与手动输入 URL 一样。

无论哪种方式，本应用随后都会递归查找所选文件夹下的每一个 `*.urdf`/`*.xacro` 文件，列出全部（一个真实的机器人描述仓库通常不止一个文件——一个裸机械臂加上一个“带夹爪”变体是常见组合），并按文件大小自动选取最大的一个作为“主文件”的合理默认值——之后切换到另一个候选文件只需在源面板中双击一次，无需重新拉取。

**网格引用解析**是本生态系统过去每一次人工移植机器人时实际做的、不那么光鲜的工作：一个 URDF 的 `<mesh filename="package://some_pkg/meshes/link1.stl"/>`，一旦文件位于一个普通的下载文件夹中而非一个实时的 ROS 工作区（在那里 `package://` 通过 ROS 包索引解析），基本上就不再是一个可以直接打开的路径了。解析器依次尝试：（1）将该引用视为相对于 URDF 自身文件夹的路径，（2）去掉开头 `package://` 风格包名片段后的同一引用，（3）如果它本身恰好已经是绝对路径，则作为绝对路径处理，以及（4）在源文件夹下任意位置按纯文件名匹配——这才是真正处理一个真实 `package://` URI 的方式，因为该 scheme 和包名在实时 ROS 工作区之外毫无意义，但网格自身的文件名依然是可以找到的。

---

## ✅ 自由度可行性验证

这是本生态系统过去每一次为 STUDIO 目录添加机器人时都要手动做出的同一个判断的自动化版本：**STUDIO 自身的运动学目前支持 3、4、5 和 6 自由度的串联链**（其 `RobotState.joints` 是一个固定的 `j1..j6` 映射）——过去调研过的一些真实、许可证清晰的候选机械臂,最终被发现是 7、8 或 9 自由度,正是因为这个原因被放弃的,而不是假设性的。每次导入时（以及每次可能改变自由度数量的实时编辑之后——例如重新指定某个关节的类型），本应用都会遍历实际的父/子关节图并报告：

- **自由度数量** —— 只有 `revolute`/`continuous`/`prismatic` 关节才计为一个真正的、可控的自由度;`fixed` 不贡献任何自由度。
- **不受支持的关节类型** —— 链条中任意位置的一个 `floating` 或 `planar` 关节都会使整个机器人不可行,无论自由度数量如何,因为 STUDIO 的关节模型对这两者都没有表示方式。
- **树结构完整性** —— 要求恰好有一个根连杆（一棵真正的树,而非森林或环）;任何无法通过关节链从根连杆到达的连杆都会被标记为断开连接,任何完全没有关节引用的连杆则被标记为孤立。
- **缺失 `<limit>`** —— URDF 规范要求除 `continuous` 关节外的所有关节都必须有此项;缺失时会逐关节标记。

判定结果及背后的每一条原因都会实时呈现在自由度面板中，上传面板会拒绝将一个不可行的机器人推送到服务器。

---

## 🎨 带真实 3D 预览的实时编辑

属性面板会编辑视口面板连杆树中当前选中的连杆，每一次编辑都会就地修改已加载的模型，并通过一个信号（`EditorController.notify_tree_changed`）重新验证/重新渲染——没有任何面板需要知道视口或自由度报告是如何响应自己那次编辑的：

- **重新着色** —— 通过标准颜色对话框选择的连杆视觉材质。一个按名称在多个连杆间共享的材质（一个真实 URDF 顶层的 `<material name="...">` 声明被多个 `<visual>` 引用）会一起重新着色所有共享它的连杆，与该共享材质语法在规范中的真实含义一致。
- **重新缩放** —— 对网格几何体自身的 `<mesh scale="...">` 变换按轴（X/Y/Z）应用缩放因子，而非破坏性地重写网格的三角面数据本身——同一次编辑之后再次应用时，每次都从原始未修改的网格开始。
- **重新指定关节类型与限位** —— 更改一个关节的类型（URDF 规范定义的 6 种之一）及其上/下限，自由度面板的判定会立即更新，因为重新指定类型可能改变自由度数量或引入不受支持的类型。
- **质量与惯量** —— "Auto-calculate" 使用 `inertia_calc.py` 中均匀密度的闭式公式，根据所选连杆自身的几何体填入质量/Ixx/Iyy/Izz（对 Box/Cylinder/Sphere 精确，对 Mesh 则是包围盒近似值）；手动输入的质量始终优先于基于密度的估算，若尚未输入质量，则假定为通用铝密度（2700 kg/m³）并在提示中说明。"Apply" 将这些字段提交到 `Link.inertial`——与上面 Scale/Joint 相同的“先计算后应用”两步模式。

**视口面板**托管着真正的 OpenGL 3D 视图，以及每个可移动关节对应的一个点动滑块，让操作员可以在触碰 STUDIO 之前，预览 URDF 在其自身真实范围内的运动。正向运动学（`render/kinematics.py`）对刚刚导入的任意树都是通用的——与 HYDRA-UMC SUITE 自身的运动学模块（驱动一个固定的、包含数十个已知、经手工验证的机器人型号的注册表）不同，本应用必须为一个任意的、此前从未见过的 URDF 摆姿，因此它通过遍历实际的父/子关节图，组合每个关节的真实 `<origin>`/`<axis>`（对任意旋转轴使用罗德里格斯旋转公式，而不仅仅是固定注册表可以依赖的基本方向捷径）。

**Z 轴朝上，而非 Y 轴朝上**——与 HYDRA-UMC SUITE 自身视口惯例的唯一刻意差异：URDF 本身就是一种 Z 轴朝上的格式（重力方向是 `-Z`，源文件中的每一个 `<origin>`/`<axis>` 都是基于此假设编写的），本应用的任务是忠实地按其自身惯例显示和编辑一个 URDF，而不是将其重新定向到某个下游查看器（STUDIO 的 Three.js 场景、SUITE 自身的 OpenGL 场景）碰巧偏好的方向。

---

## 🗂️ 网格加载

`.stl`（通过 `numpy-stl`）和 `.obj`（一个小型的手写 Wavefront 加载器——仅支持 `v`/`vn`/`f`，n 边形面被三角化）都是一等公民。**不支持 COLLADA（`.dae`）**——它是一种更为庞大的 XML 场景图格式（骨骼动画、多重坐标系、内嵌材质/纹理），若要诚实处理，需要一个真正的解析器，而非对某个“简单”`.dae` 恰好使用的标签进行尽力猜测；引用了此类文件的连杆会得到一条清晰的、具名的错误提示，而不是在视口中静默缺失或使整个导入崩溃。每一个已加载的网格也会应用与 HYDRA-UMC STUDIO 自身的 `useRealScaleSTL()` 和 HYDRA-UMC SUITE 自身网格加载器相同的防御性毫米/米判断：任意轴上大于 5 个真实世界米的连杆，更可能是一个没有单位元数据的毫米级导出文件，而不是一个真正的巨型机器人零件，会自动按 0.001 重新缩放。

---

## 📜 URDF 解析与导出

通过标准库自身的 `xml.etree.ElementTree` 进行纯 XML 处理——对于这样一种简单的格式，不需要 `lxml` 依赖。内存中的模型（`hydra_editor_urdf/models.py`）是一棵刻意保持简单、可变、自研的数据类树，而非对现有 Python URDF 库（如 `urdfpy` 或 `yourdfpy`）的包装：本应用需要以交互方式*编辑*这棵树并实时重新渲染每一次更改，这不是一个以只读解析为主的库所擅长的场景，完全拥有这个模型能让它保持小巧、可检查，且不受第三方依赖自身发布节奏的影响。字段名称和默认值紧密遵循真实的 [URDF XML 规范](http://wiki.ros.org/urdf/XML)，因此解析器/写入器这一对始终是一个薄而直观的 XML↔对象映射。

**xacro 不会被展开。** [xacro](http://wiki.ros.org/xacro) 是一个拥有自己 ROS 包和依赖链的 Python/XML 宏预处理器，一个真实的 xacro 文件只有在它编写时所针对的那个 ROS 包环境内部才能被可靠地解析（宏参数、`$(find pkg)` 风格的引入等）——这是本应用无法诚实复现的。使用了 `<xacro:...>` 标签或声明了 xacro 命名空间的文件会得到一条清晰的错误信息，解释这一限制并指向 ROS 的 `xacro` 命令行工具进行预处理，而不是静默解析错误。

导出（`urdf/writer.py`）会从头重新序列化当前的内存树，而非修补原始的源 XML 文本，因此每一次实时编辑——无论由哪个面板做出——都会通过同一条代码路径，恰好一次地反映在“导出 URDF”菜单操作和发送到 STUDIO 服务器的负载中。

---

## 🖥️ 可停靠工作区

真正的 `QDockWidget` 面板——拖动使其浮动、拖回停靠、合并为标签页、拆分工作区——与 HYDRA-UMC SUITE 自身主窗口已经采用的机制和理由相同：Qt 自身的停靠系统已经完全实现了类 Photoshop/Fusion-360 工作区所需的功能，一个手写实现只会带来更多的 bug 而重新发明它。5 个面板，以一种合理的默认布局排列，之后可以完全重新排列：

- **来源**——GitHub URL / 本地文件夹输入，找到的 `.urdf` 列表。
- **自由度**——可行性判定及其背后的每一条原因。
- **视口**——实时 3D 视图、连杆树、点动滑块。
- **属性**——针对所选连杆的重新着色/重新缩放/重新指定类型与限位。
- **上传**——连接到 STUDIO 服务器，推送或拉取。

---

## ☁️ 服务器往返

使用标准库自身的 `urllib.request` 与 HYDRA-UMC-SERVER 自身的模型提交契约通信（该项目自身 `server.ts` 中的 `POST /api/models/submit`、`GET /api/models`、`GET /api/models/:category/:slug/download`，受其自身的 **Config > Models > "Accept model submissions"** 开关控制）——为一个只需要 4 个端点、而非一条持久实时连接的项目引入 `httpx`/`requests` 不值得。每次调用都在后台 `QThread` 上运行，因此一个缓慢或不可达的服务器永远不会冻结 UI。这个契约曾经存在于 HYDRA-UMC-STUDIO 自身进程内部，后来该项目拆分为一个纯前端（STUDIO）加一个独立的无头式后端（HYDRA-UMC-SERVER，见下方“相关项目”）——本应用不硬编码任何一个名字，操作员只需将**上传**面板的主机/端口字段指向真实后端实际运行的位置即可。

- **登录** —— `POST /api/login`；只有 `admin` 角色的令牌才能实际到达服务端的 `POST /api/models/submit`，因此本应用实际上只能配合管理员账户使用，与其他每一个仅限管理员的 STUDIO 功能一样。
- **推送** —— 将当前机器人重新序列化为 URDF XML，并将其视觉部分引用的每一个网格文件（通过导入时构建的同一个网格解析器解析）以 base64 编码内联到请求体中，并标记上操作员选择的类别（对应 STUDIO 自身 Config > UI > Module Visibility 的类别：Robot 3-6DOF、CNC、Pick & Place、Laser、Vacuum Table、XY Table、Heated Bed、ATC Tools——一个 URDF 本身没有任何字段能说明它属于其中哪一类）。名称冲突会以服务器自身的 409 响应返回；由操作员决定是勾选**覆盖**重新提交还是重命名，本应用从不自行猜测。
- **拉取** —— 将一个已提交模型的 URDF + 网格重新下载到本地工作文件夹，并直接加载进编辑器中——这是本应用自身用途的“提取、编辑、重新发送”往返流程的另一半，让一个已存在的目录条目可以在无需重新回到其原始源仓库的情况下进行修饰。

---

## 🌐 多语言界面

界面在**英语、西班牙语、意大利语、法语、德语、简体中文和日语**（`language/*.lng`）之间全面翻译，使用与本生态系统中每一个其他 Python 工具（URTC Flasher、URTC Tester、HYDRA-UMC SUITE）完全相同的纯 `KEY=Value` 文件机制——此处并未重新发明，因为该机制本身不带有任何项目特定的逻辑。语言切换在应用重启后生效，而非实时重新翻译每一个已构建的控件，遵循同样的惯例。`language/` 位于可执行文件**旁边**，而非通过 PyInstaller 的 `--add-data` 打包进其内部，因此翻译者无需重新构建即可编辑或添加一个 `.lng` 文件。

---

## 🎛️ 主题

可停靠工作区顶部工具栏是一个真正的 `QToolBar`/`QLabel`/`QToolButton` 命令控制台，
而不是独立的 Qt Quick/QML 界面——早期通过 QQuickWidget 嵌入的版本（与
HYDRA-UMC-UPDATER 和 HYDRA-UMC-SUITE 相同的渲染引擎）一旦放入这个
`QMainWindow` 真正的 `QDockWidget` 布局中，就会渲染成一整块黑色、且控制台没有
任何报错，因此被还原为普通控件；完整经过见 `CHANGELOG.md`。Source、DOF、
Viewport、Properties 和 Upload 按钮只会显示既有停靠面板；Export 与 About 复用
既有操作，且 Export 在模型真正加载之前保持禁用。加载 URDF 后（以及每次实时属性
编辑后），其状态标签会显示已加载模型的名称、DOF 数量和当前可行性判定结果。
它不替代 OpenGL 视口、编辑器、解析器或服务器上传实现。

原样复用 HYDRA-UMC SUITE 自身的 `assets/qss/industrial_dark.qss`（相同的相对路径，相同的文件），而不是为本生态系统中的同类桌面工具设计一套新的视觉主题。

---

## 📂 仓库结构

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # 入口点——QApplication、主题、最大化启动、F11 全屏切换
├── run.bat / run.sh                # 便捷启动脚本——若存在 .venv 则激活，运行 main.py，不会自行关闭窗口
├── requirements.txt                # PySide6、PyOpenGL、numpy-stl、numpy（已锁定版本）
├── build_exe.bat / build_exe.sh    # Windows/Linux 独立可执行文件构建脚本（PyInstaller）——先递增版本号
├── build-test.bat / build-test.sh  # 不递增版本号的构建/编译检查
├── HYDRA-UMC_EDITOR-URDF.spec      # build_exe.bat/.sh 使用的 PyInstaller 构建规格
├── bump_version.py                 # 里程表式版本递增，在每次真正构建前由 build_exe.bat/.sh 调用
├── bump_manifest_version.py        # 将 hydra-umc.project.json 的版本与原生版本同步（--sync）
├── CHANGELOG.md                    # 版本历史
├── README.md                       # 本文件
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  # <- 翻译
├── LICENSE                         # GPL-3.0
├── assets/
│   ├── HYDRA_UMC_ICON.svg          # 工具栏命令面板使用的动画 HYDRA-UMC 标志
│   └── qss/industrial_dark.qss     # 原样复用自 HYDRA-UMC-SUITE
├── images/
│   └── HYDRA_UMC_BANNER.svg        # 媒体与图示
├── language/                       # english/spanish/italian/french/german/chinese/japanese.lng —— 位于 exe 旁边，未打包
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ —— 唯一权威来源，由 About 对话框读取，由 bump_version.py 重写
│   ├── app.py                      # EditorController —— “当前加载了什么”的唯一持有者，每个面板监听的 Qt 信号
│   ├── models.py                   # 自研的 URDF 对象树（Robot/Link/Joint/Visual/Geometry/Material/…）
│   ├── gallery.py                  # 经过验证的真实公开机器人描述仓库的初始列表
│   ├── inertia_calc.py             # 基本几何体的闭式转动惯量公式
│   ├── i18n.py                     # language/*.lng 加载器、配置持久化——从 HYDRA-UMC-SUITE 自身的 i18n.py 移植
│   ├── urdf/
│   │   ├── parser.py               # URDF XML -> models.py 树（ElementTree，检测到 xacro 并以清晰错误拒绝）
│   │   ├── writer.py                # models.py 树 -> URDF XML 字符串（导出 + 服务器上传负载）
│   │   └── dof.py                  # 自由度计数，针对 STUDIO 3-6 自由度上限的可行性验证
│   ├── render/
│   │   ├── mesh.py                 # STL/OBJ 加载、盒体/圆柱体/球体基本几何体生成、毫米/米判断
│   │   ├── kinematics.py           # 针对任意已导入树的通用正向运动学（Z 轴朝上，URDF 自身的惯例）
│   │   └── viewport.py             # QOpenGLWidget —— GLSL 3.3 核心着色器、环绕相机、逐连杆 GPU 缓冲区
│   ├── source/
│   │   ├── scan.py                 # 查找 .urdf/.xacro 文件，构建感知 package:// 的网格文件名解析器
│   │   ├── github_fetcher.py       # GitHub zip 包下载与解压（urllib + zipfile，无 git 依赖）
│   │   └── local_folder.py         # 本地文件夹验证——github_fetcher.py 的薄型对应物
│   ├── server/
│   │   └── client.py               # StudioClient —— 针对 HYDRA-UMC-SERVER 的 server.ts（两个仓库拆分前是 STUDIO 自身的后端）进行 login/list_models/push_model/pull_model
│   └── ui/
│       ├── main_window.py          # QMainWindow —— 可停靠工作区、菜单栏、语言切换器、状态栏
│       ├── about_dialog.py         # 真实的 About 对话框，对应 STUDIO 自身的 About.tsx 和 SUITE 自身的 about_dialog.py
│       ├── theme.py                 # 应用 assets/qss/industrial_dark.qss
│       └── panels/
│           ├── source_panel.py     # GitHub URL / 本地文件夹输入，找到的 URDF 列表
│           ├── dof_panel.py        # 可行性判定读出
│           ├── viewport_panel.py   # 3D 视口宿主、连杆树、点动滑块
│           ├── properties_panel.py # 重新着色 / 重新缩放 / 重新指定类型与限位编辑器
│           └── upload_panel.py     # 服务器连接/推送/拉取
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   └── INTEGRATION_CONTRACT.md
├── tools/
│   ├── build_test.py               # 不递增版本号的构建/编译检查
│   └── ci_validate.py              # CI 使用的 manifest/CHANGELOG/docs 校验
├── build/                           # PyInstaller 自身的中间构建目录（已加入 gitignore）
├── dist/                            # 编译后的独立可执行文件（build_exe.bat/.sh 的输出，已加入 gitignore）
└── work/                            # 已拉取的 GitHub 仓库和已拉取的服务器模型的运行时暂存空间（已加入 gitignore）
```

说明：Qt Quick 命令面板（`assets/qml/CommandDeck.qml`、
`ui/qtquick_deck.py`）已被回退——嵌入此 `QMainWindow` 真实
`QDockWidget` 布局中的 `QQuickWidget` 始终无法正确合成（纯黑显示，
控制台无报错）。工具栏命令面板如今由纯粹的
`QToolBar`/`QLabel`/`QToolButton` 部件组成；完整经过见 `CHANGELOG.md`。

---

## 🛠️ 开发环境

### 系统要求
- [Python](https://www.python.org/) 3.11 或更高版本
- pip

### 安装

```bash
pip install -r requirements.txt
```

这会拉取已锁定版本的依赖集：**PySide6**（Qt6 界面）、**PyOpenGL**（3D 视口渲染）、**numpy** / **numpy-stl**（网格数学与 STL 加载）。无需安装 `git`——GitHub 源加载路径通过 HTTPS 下载一个纯粹的 zip 压缩包。

### 开发模式

```bash
python main.py
```

或者使用便捷脚本——`run.bat`（Windows）/ `run.sh`（Linux/Mac），若旁边存在 `.venv` 则会激活它，并将参数转发给 `main.py`；双击运行时两者都不会自行关闭终端窗口。

以最大化方式启动（并非真正的操作系统级全屏，因此原生窗口标题栏和控件保持可见）——按 **F11** 切换真正的无边框全屏及返回。

### 生产构建

通过 PyInstaller 编译一个独立的可执行文件（运行它无需安装 Python）：

- **Windows：** 运行 `build_exe.bat` → 生成 `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux：** 运行 `./build_exe.sh`（首次需先 `chmod +x build_exe.sh`）→ 生成 `dist/HYDRA-UMC_EDITOR-URDF`

两个脚本都会创建/激活自己的 `.venv`，安装 `requirements.txt` 加上 `pyinstaller`，清理任何先前的 `build`/`dist`，**递增版本号**，编译，最后将 `README.md`、`LICENSE` 以及整个 `language/` 文件夹复制到生成的二进制文件旁边（`language/` 刻意**不**通过 `--add-data` 打包进可执行文件内部，因此之后可以编辑或添加一个 `.lng` 文件而无需重新构建）。

**版本管理：** 本应用的版本（`hydra_editor_urdf/__version__`，显示在 Help → About 对话框中）遵循 `MAJOR.MINOR.PATCH`。每次真正运行 `build_exe.bat`/`build_exe.sh` 都会先调用 `bump_version.py`，应用一种里程表式的递增：`PATCH` 加 1；一旦 `PATCH` 会超过 9，就重置为 0 并将 `MINOR` 加 1（例如 `0.0.9` → `0.1.0`）。`MAJOR` 从不自动修改——那始终是一个刻意的手动决定。版本历史见 `CHANGELOG.md`。

如果你更愿意手动执行等效步骤而非使用脚本——这对于在脚本未覆盖的平台上适配构建，或调试某个 PyInstaller 标志很有用——手动流程如下：

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. 安装依赖 + PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# 3. 定位 PySide6 自身的安装目录（其 Qt 插件位于其下）
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> 即下方的 $PYSIDE_DIR

# 4. 编译——仅显式暂存了 4 个 Qt 插件子文件夹
#    （platforms/styles/imageformats/iconengines），而非
#    --collect-all PySide6，那样会拉入 Qt6WebEngineCore.dll 及其他
#    数百 MB 级、本应用从未使用过的组件。PyInstaller 自身的依赖分析器
#    通过跟随 main.py 的真实导入图找到实际的 Qt6Core/Gui/Widgets/OpenGL
#    DLL——只有插件文件夹需要手动添加。
#
#    Windows（插件直接位于 PySide6/plugins/ 下）：
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux（插件位于 PySide6/Qt/plugins/ 下——与 Windows 不同的布局，
#    通过阅读 PyInstaller 自身的运行时钩子 pyi_rth_pyside6.py 确认）：
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. 复制必须位于二进制文件旁边、而非其内部的文件
cp README.md LICENSE dist/
cp -r language dist/language
```

在 Linux 上，运行编译好的二进制文件需要系统自身的 OpenGL 运行时（`libGL.so.1`——例如 Debian/Ubuntu 上的 `libgl1`、Fedora 上的 `mesa-libGL`、Arch 上的 `libglvnd`），加上 Qt 自身 XCB 平台插件所需的 `libxkbcommon-x11-0`/`xcb-util-cursor`；`build_exe.sh` 会预先检查 `libGL.so.1`，如果缺失会为每个发行版打印正确的安装命令，而不是让失败深藏在一次 PyInstaller 运行内部。

---

## 🔗 相关项目

本项目是同一作者（JuanenRac / Electro Hobby 3D）打造的更大规模机器人生态系统的一部分。值得了解，因为某个请求实际所指的可能正是这些项目之一，而非本仓库：

**HYDRA-UMC 平台** —— 多机器人微工厂单元
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 主板本体：Raspberry Pi CM5 主机 + 双核 STM32H745 实时协处理器，通过 CAN-OTA/SPI-OTA 协调最多 8 个分布式机器人手臂。自有硬件 + 固件，GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0。
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** —— HYDRA-UMC 的网页控制仪表盘：多机器人 3D 可视化、运动学/轨迹记录、面向整个平台的 CAN-OTA 刷写与测试。React + Vite + Three.js。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— 曾经打包在 HYDRA-UMC-STUDIO 自身进程内的无头式后端（Node/Express/WebSocket）。拥有机器人控制 REST/WS API（包括 `POST /api/models/submit`——本编辑器推送完成模型所使用的端点）、settings.json 持久化、JWT 身份验证和 mDNS 发现。HYDRA-UMC-STUDIO 现在是一个纯静态前端客户端，通过网络与之通信。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** —— 通过 Wi-Fi/蓝牙控制 HYDRA-UMC 的 Android 应用。真实可用的应用——完整的远程控制功能集、JWT 身份验证、加密凭证存储。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** —— 通过 Wi-Fi 控制 HYDRA-UMC 的 iOS/iPadOS 应用，基于 Flutter 构建（跨平台，可在 Windows 上验证，无需 Mac；最终 `.ipa` 打包仍需 Xcode）。真实可用的应用——功能集与 Android 应用相同。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** —— 桌面端（Python/PySide6）集群指挥中心：多控制器网络发现、实时双向同步、真实的 3D 机器人视口、类 Photoshop 的可停靠工作区。真实可用，并非占位程序。
- **HYDRA-UMC-EDITOR-URDF**（本仓库）—— 桌面端（Python/PySide6）图形化 URDF 创建/编辑工具，服务于 HYDRA-UMC-STUDIO 自身的模型目录：从 GitHub 或本地文件夹拉取源文件，验证自由度可行性，通过实时 3D 预览编辑颜色/比例/运动学，并将完成的结果推送到一个正在运行的 STUDIO 服务器。真实可用，并非占位程序。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** —— 面向 HYDRA-UMC 自身 5"/7" DSI 触摸屏（两种尺寸分辨率均为 1280×720）的原生 Flutter 触控界面，运行于 Compute Module 5 上，直接从主板控制同一台服务器。真实可用的雏形，全部 6 个目录界面（仪表盘、手动控制、摄像头、简化 3D 视图、系统指标、登录）均已连接到实时服务器；真正的 Linux 目标构建尚未在真实硬件上运行过（目前仅在 Windows 环境下可用——参见该项目自身的 README）。

**URTC 平台** —— 每个 HYDRA-UMC 机器人手臂所携带的工具头控制器
- **[URTC](https://github.com/JuanenRac/URTC)** —— 通用机器人工具控制器：基于 STM32F303 的 CAN 总线工具头控制器，25 个已完整实现的工具配置文件，支持 CAN-OTA 固件更新。
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** —— 面向 URTC 板卡的桌面端 CAN-OTA + 全芯片 SWD/JTAG 刷写工具（Windows/Linux）。
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** —— 面向 URTC 板卡的桌面端实时 CAN 总线诊断工具，每个工具配置文件对应一个面板（Windows/Linux）。
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** —— 上述两款桌面工具的浏览器端替代方案（Web Serial API + SLCAN），无需本地安装。

**与本仓库直接相关**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** —— 本编辑器存在的目的正是填充这个模型目录;完成的结果会直接推送到正在运行的 STUDIO 服务器。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— 拥有本编辑器推送完成模型所用的真实 `POST /api/models/submit` 端点。
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** —— 消费这里创建的 URDF 模型来驱动其物理仿真。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** —— 消费这里创建的 URDF 模型来驱动其物理仿真。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** —— 从这里创建的模型生成训练数据。

**生态系统的其余部分** —— 本项目所处的更广泛的众多项目集合，按领域分组：
- 👁️ **视觉 AI 节点（Hailo-8）：** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)、[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)、[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)、[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)、[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **认知 AI 节点（Hailo-10）：** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)、[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)、[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)、[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)、[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **编排与集群：** [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)、[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)、[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)、[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)、[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **数字孪生与仿真：** [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- 📊 **数据与分析：** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)、[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)、[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)、[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **工业网关：** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)、[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)、[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)、[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **配套工具：** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)、[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)、[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)、[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)、[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 📚 文档与社区

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** —— 编辑器自身的内部结构：为什么解析、可行性校验、网格解析和 3D 预览是相互独立的通路，以及本应用刻意**不**做的事情（不会自行连接机器人、上传 URDF 或下达运动指令）。
- **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** —— 非破坏性的 `build-test.bat`/`.sh` 校验流程与真正打包的 `build_exe.bat`/`.sh` 之间的区别，以及命令控制台如今究竟是什么（`QToolBar`，而非 Qt Quick/QML —— 参见上方**主题**一节）。
- **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** —— 下游消费一个已导出 URDF 文件的一方必须自行校验的内容；本项目自身不提供任何网络端点或硬件控制权限。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— 提交 Pull Request 所需的技术栈和编码规范。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— 本社区所期望的行为准则。
- **[SECURITY.md](SECURITY.md)** —— 如何报告漏洞，以及本项目真实的安全关注重点。
- **[SUPPORT.md](SUPPORT.md)** —— 在哪里提问和报告缺陷。
- **[LICENSE.md](LICENSE.md)** —— 本项目自身的许可证。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 许可证

HYDRA-UMC EDITOR-URDF 版权所有 (c) 2026 JuanenRac（Electro Hobby 3D）。分发本项目或其衍生作品时必须包含此声明。

本项目由源代码及其自身的文档组成，两者依据不同的许可证提供——各自适合其实际所涵盖的内容：

1. 源代码（`hydra_editor_urdf/`、`main.py`，以及通过 `build_exe.bat`/`build_exe.sh` 从中构建的任何二进制文件）依据 **GNU 通用公共许可证 v3.0（GPL-3.0）** 提供。完整文本见 https://www.gnu.org/licenses/gpl-3.0.html。

2. 文档（本 README 及其自身的翻译版本——`README_spa.md`、`README_ita.md`、`README_fra.md`、`README_deu.md`、`README_zho.md`、`README_jpn.md`）依据 **知识共享 署名-相同方式共享 4.0 国际许可协议（CC BY-SA 4.0）** 提供。完整文本见 https://creativecommons.org/licenses/by-sa/4.0/。

本应用自身不附带任何第三方机器人网格资产——与 HYDRA-UMC STUDIO 的 `public/models/` 不同，本编辑器加载的每一个网格都来自操作员所指向的任意源仓库或本地文件夹，遵循该来源自身的原始许可证。在将一个模型提交到一个正在运行的 STUDIO 服务器之前（本编辑器的导出功能所对接的正是该服务器自身 `public/models/<slug>/ATTRIBUTION.txt` 的惯例），审查并保留该上游许可证/署名信息，仍然是操作员自己的责任——本应用无法自动检测或强制执行某个源仓库的许可条款。

本编辑器是 [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 目录的模型创作工具——其自身服务端的许可事宜参见该仓库，本仓库自身的许可证并不延伸至该仓库,反之亦然。

如果你基于本项目进行开发，请留意这种许可证划分：这里的代码更改应保持 GPL-3.0，文档衍生品（本 README 及其翻译版本）应保持 CC BY-SA 4.0，任何经过本编辑器（导入、编辑或导出）的网格资产都应保持在其自身原始源仓库所携带的许可证之下，并附带指向该来源的署名。
