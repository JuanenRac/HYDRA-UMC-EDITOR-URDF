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
  🇯🇵 <b>日本語</b>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="URDF">
</p>


### 🖌️ HYDRA-UMC-STUDIO モデルカタログ向けグラフィカル URDF 作成/編集ツール

**現在のバージョン：** 0.0.2（`MAJOR.MINOR.PATCH` —— この番号がどう変化するかは下記「プロダクションビルド」セクションを参照）

---

## 🎯 概要

**HYDRA-UMC EDITOR-URDF** は、「新しいロボットを [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) のモデルカタログへ移植する」という作業を、手作業でロボットごとに調査する一回限りの作業から、再現可能なグラフィカルワークフローへと変えるデスクトップツールです。STUDIO のカタログにあるすべての実在するロボットモデルは、これまで同じ方法でそこにたどり着きました：GitHub 上で記述リポジトリを見つけ、そのメッシュ参照がどう解決されるかを把握し、その運動学チェーンの自由度を数え、STUDIO が実際にそれだけの数を駆動できるかを確認し、結果を手作業で `public/models/` に配置する、というものです。本アプリはそのプロセス全体を自動化します——GitHub の URL またはすでにダウンロード済みのローカルフォルダからソースファイルを取得し、ディスク上の実際のファイルに対してすべての `<mesh filename="...">` 参照（`package://` URI を含む）を解決し、STUDIO の現在の運動学がサポートする範囲に対してそのチェーンの自由度数を検証し、リアルタイム 3D プレビューで色/スケール/関節限位/関節タイプを編集し、完成した結果を稼働中の STUDIO サーバーへ直接プッシュします。

**Python** と **PySide6/Qt6** で構築されており、本エコシステムの他のデスクトップツールである [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE) ですでに検証済みの同じアーキテクチャパターンを使用しています：Photoshop/Fusion 360 風のドッキング可能なワークスペース（`QDockWidget`）、手書きの OpenGL 3D ビューポート（`QOpenGLWidget` + GLSL 3.3 コアプロファイルシェーダー、`glBegin`/`glEnd` のレガシーパスなし）、そして状態を保持し各 UI パネルが Qt シグナル経由でリッスンする 1 つの中心的なコントローラーオブジェクト。同一エコシステム内の姉妹ツール向けに新しい UI/レンダースタックを模索するのではなく、ここでこのパターンを再利用することは、見落としではなく意図的な選択です。

**本エコシステムの他のドキュメントと同じ慣例に従った正直な注記：** 本アプリは [xacro](http://wiki.ros.org/xacro) マクロを展開せず、COLLADA（`.dae`）メッシュも読み込みません。どちらも明示的に名前を挙げた制限事項です（半端な試みではなく、明確なエラーメッセージであり、サイレントな解析ミスやビューポートでのリンク欠落ではありません）——具体的な理由は下記「URDF パース」および「メッシュ読み込み」セクションを参照してください。

---

## 📥 ソースの読み込み——GitHub またはローカルフォルダ

本アプリをロボットのソースファイルに向ける方法は 2 通りあり、どちらも同じインポートパスに行き着きます：

- **GitHub URL から** —— 完全な `https://github.com/owner/repo` URL（`/tree/<branch>` の有無いずれも）、SSH 形式の `git@github.com:owner/repo.git`、または短縮形の `owner/repo` を受け付けます。意図的に外部の `git clone` は呼び出しません——それは、プレーンな HTTPS ダウンロードですでに実現できることのために、Windows と Linux の両方で `git` のインストールをハードな実行時依存にしてしまうからです。GitHub は公開リポジトリであれば認証不要で `codeload.github.com` から任意のブランチ/タグ/コミットの zip アーカイブを提供するため、本アプリは標準ライブラリ自身の `urllib.request` + `zipfile` のみを使用します。サポートされるのは公開リポジトリのみです——トークン/資格情報の処理はなく、プライベートリポジトリの zip アーカイブは、存在しないリポジトリと同様に 404 を返します。
- **ローカルフォルダから** —— すでに手動でダウンロード済みのリポジトリ、またはオペレーターが本アプリの外で積極的に編集している作業コピー向けです。

いずれの場合も、本アプリはその後選択されたフォルダ下にあるすべての `*.urdf`/`*.xacro` ファイルを再帰的に検索し、それらすべてを一覧表示し（実際のロボット記述リポジトリはしばしば複数のファイルを同梱しています——裸のアームと「グリッパー付き」バリアントの組み合わせがよくあるパターンです）、「メインのもの」の妥当なデフォルトとしてファイルサイズが最大のものを自動選択します——後で別の候補に切り替えるのは、ソースパネルでのダブルクリック 1 回で済み、再取得は不要です。

**メッシュ参照解決**は、本エコシステムの過去のすべての手作業によるロボット移植セッションが実際に行ってきた、地味だが本質的な作業です：URDF の `<mesh filename="package://some_pkg/meshes/link1.stl"/>` は、`package://` が ROS パッケージインデックスを通じて解決されるライブな ROS ワークスペースではなく、単なるダウンロード済みフォルダにファイルが置かれている場合、事実上ほぼ確実に直接開けるパスではなくなります。リゾルバーは順に：（1）URDF 自身のフォルダに対する相対パスとしてその参照、（2）先頭の `package://` 形式のパッケージ名セグメントを取り除いた同じ参照、（3）それがすでに絶対パスであった場合はそのまま絶対パスとして、（4）ソースフォルダ下の任意の場所での裸のベース名一致、を試みます——これが実際に本物の `package://` URI を処理する方法です。スキームとパッケージ名はライブな ROS ワークスペースの外では意味を持ちませんが、メッシュ自身のファイル名は依然として見つけられるためです。

---

## ✅ 自由度実現可能性検証

これは、STUDIO のカタログに追加されたすべてのロボットに対して本エコシステムの過去のセッションが手作業で下していたのと同じ判断の自動化版です：**STUDIO 自身の運動学は現在、3、4、5、6 自由度のシリアルチェーンをサポートしています**（その `RobotState.joints` は固定の `j1..j6` マップです）——過去に調査された実在の、ライセンスが明確な候補アームのうち、いくつかは 7、8、あるいは 9 自由度であることが判明し、まさにこの理由で仮の話ではなく実際に破棄されました。インポートのたびに（そして自由度数を変え得るすべてのライブ編集の後——例えば関節のタイプを打ち直した後）、本アプリは実際の親/子関節グラフを走査し、以下を報告します：

- **自由度数** —— `revolute`/`continuous`/`prismatic` の関節のみが実際の制御可能な自由度としてカウントされます。`fixed` は一切貢献しません。
- **サポートされない関節タイプ** —— チェーン内のどこか 1 か所にでも `floating` または `planar` 関節があると、自由度数にかかわらずロボット全体が実現不可能になります。STUDIO の関節モデルはどちらの表現も持たないためです。
- **ツリーの整合性** —— ちょうど 1 つのルートリンクが必要です（森でも循環でもない、正しいツリー）。そのルートから関節チェーンで到達できないリンクは切断されているとフラグが立てられ、どの関節からも参照されていないリンクは孤立としてフラグが立てられます。
- **`<limit>` の欠落** —— `continuous` 関節以外のあらゆる関節に対して URDF 仕様が必須としているもので、存在しない場合は関節ごとにフラグが立てられます。

判定結果とその背後にあるすべての理由は DOF パネルにリアルタイムで表示され、アップロードパネルは実現不可能なロボットをサーバーへプッシュすることを拒否します。

---

## 🎨 実際の 3D プレビューによるライブ編集

プロパティパネルは、ビューポートパネルのリンクツリーで選択されているリンクを編集し、すべての編集は読み込み済みのモデルをその場で変更し、1 つのシグナル（`EditorController.notify_tree_changed`）を通じて再検証/再レンダリングを行います——どのパネルも、ビューポートや自由度レポートが自分自身の編集にどう反応するかを知る必要はありません：

- **色の変更** —— 標準のカラーダイアログで選択されるリンクのビジュアルマテリアル。複数のリンク間で名前によって共有されるマテリアル（実際の URDF のトップレベルの `<material name="...">` 宣言が複数の `<visual>` から参照されている場合）は、それを共有するすべてのリンクをまとめて再着色します。これは、その共有マテリアル構文が仕様上実際に意味するところと一致しています。
- **スケール変更** —— メッシュの三角形データ自体を破壊的に書き換えるのではなく、メッシュジオメトリ自身の `<mesh scale="...">` 変換に対する軸ごと（X/Y/Z）のスケール係数。同じ編集を後で再適用しても、毎回元の未変更のメッシュから開始します。
- **関節タイプと限位の再設定** —— 関節のタイプ（URDF 仕様が定義する 6 種類のいずれか）とその上限/下限を変更でき、タイプの再設定は自由度数を変えたりサポートされないタイプを導入したりする可能性があるため、DOF パネルの判定は即座に更新されます。

**ビューポートパネル**は、実際の OpenGL 3D ビューと、可動関節ごとのジョグスライダーをホストしており、オペレーターは STUDIO に触れる前に、URDF がその実際の可動範囲を通じてどう動くかをプレビューできます。正運動学（`render/kinematics.py`）は、たった今インポートされたどのようなツリーに対しても汎用的です——数十の既知の、手作業で検証済みのロボットモデルの固定レジストリを駆動する HYDRA-UMC SUITE 自身の運動学モジュールとは異なり、本アプリは任意の、これまで見たことのない URDF にポーズを取らせなければならないため、実際の親/子グラフを走査しながら各関節の実際の `<origin>`/`<axis>` を合成します（固定レジストリが頼れるような基本方向のショートカットだけでなく、任意の回転軸に対するロドリゲスの回転公式）。

**Y 軸上ではなく Z 軸上**——HYDRA-UMC SUITE 自身のビューポート規約からの唯一の意図的な相違点です：URDF そのものが Z 軸上のフォーマットであり（重力は `-Z`、ソースファイル内のすべての `<origin>`/`<axis>` はそれを前提として記述されています）、本アプリの仕事は URDF をその自身の規約に忠実に表示・編集することであり、下流のビューア（STUDIO の Three.js シーン、SUITE 自身の OpenGL シーン）がたまたま好む向きに再配向することではありません。

---

## 🗂️ メッシュの読み込み

`.stl`（`numpy-stl` 経由）と `.obj`（小さな手作りの Wavefront ローダー——`v`/`vn`/`f` のみ、n 角形の面はファン三角形分割）は両方とも第一級のサポートです。**COLLADA（`.dae`）はサポートされていません**——これは、骨格アニメーション、複数の座標系、埋め込みマテリアル/テクスチャを持つ、はるかに大規模な XML シーングラフフォーマットであり、正直に扱うには、ある「シンプルな」`.dae` がたまたま使用しているタグへのベストエフォートの推測ではなく、本物のパーサーが必要になります。これを参照するリンクは、ビューポートからサイレントに欠落したりインポート全体をクラッシュさせたりするのではなく、明確で具体的なエラーを受け取ります。読み込まれたすべてのメッシュにも、HYDRA-UMC STUDIO 自身の `useRealScaleSTL()` と HYDRA-UMC SUITE 自身のメッシュローダーが適用しているのと同じ防御的なミリメートル対メートルのガードが適用されます：いずれかの軸で実世界の 5 メートルを超えるリンクは、実際の巨大なロボット部品であるよりも、単位メタデータのないミリメートルスケールのエクスポートである可能性がはるかに高く、自動的に 0.001 倍で再スケールされます。

---

## 📜 URDF のパースとエクスポート

標準ライブラリ自身の `xml.etree.ElementTree` によるプレーンな XML 処理——これほどシンプルなフォーマットには `lxml` 依存は不要です。メモリ内モデル（`hydra_editor_urdf/models.py`）は、`urdfpy` や `yourdfpy` のような既存の Python URDF ライブラリのラッパーではなく、意図的にシンプルで可変な自社製のデータクラスツリーです：本アプリはそのツリーをインタラクティブに*編集*し、すべての変更をライブで再レンダリングする必要があり、読み取り中心のパースライブラリはそのような用途には向いていません。モデルを完全に自前で持つことで、それを小さく、検査可能で、サードパーティ依存関係自身のリリースサイクルから自由な状態に保てます。フィールド名とデフォルト値は実際の [URDF XML スキーマ](http://wiki.ros.org/urdf/XML) に忠実に従っているため、パーサー/ライターのペアは薄く自明な XML↔オブジェクトのマッピングであり続けます。

**xacro は展開されません。** [xacro](http://wiki.ros.org/xacro) は、独自の ROS パッケージと依存関係チェーンを持つ Python/XML マクロプリプロセッサであり、実際の xacro ファイルは、それが作成された同じ ROS パッケージ環境の内部でしか確実に解決できません（マクロ引数、`$(find pkg)` 形式のインクルードなど）——これは本アプリが正直に再現する方法を持たないものです。`<xacro:...>` タグを使用しているか xacro 名前空間を宣言しているファイルは、サイレントな解析ミスではなく、その制限を説明し、まずそれを前処理するための ROS の `xacro` コマンドラインツールを指し示す明確なエラーを受け取ります。

エクスポート（`urdf/writer.py`）は、元のソース XML テキストにパッチを当てるのではなく、現在のメモリ内ツリーをゼロから再シリアライズします。そのため、どのパネルによって行われたかにかかわらず、すべてのライブ編集は、「URDF をエクスポート」メニューアクションと STUDIO サーバーへ送信されるペイロードの両方に、1 つのコードパスを通じて正確に 1 回反映されます。

---

## 🖥️ ドッキング可能なワークスペース

本物の `QDockWidget` パネル——ドラッグして浮遊させる、ドラッグして戻してドッキングする、タブに統合する、ワークスペースを分割する——これは、HYDRA-UMC SUITE 自身のメインウィンドウがすでに適用しているのと同じ仕組みと理由です：Qt 自身のドッキングシステムは、Photoshop/Fusion 360 風のワークスペースが必要とすることをまさに実現しており、手作りのものはそれをより多くのバグとともに再発明するだけです。5 つのパネルが、後から完全に再配置可能な、妥当なデフォルトレイアウトで配置されています：

- **ソース** —— GitHub URL / ローカルフォルダの入力、見つかった `.urdf` の一覧。
- **DOF** —— 実現可能性の判定とその背後にあるすべての理由。
- **ビューポート** —— ライブ 3D ビュー、リンクツリー、ジョグスライダー。
- **プロパティ** —— 選択されたリンクの色変更/スケール変更/タイプと限位の再設定。
- **アップロード** —— STUDIO サーバーへの接続、プッシュ、またはプル。

---

## ☁️ サーバーとの往復

標準ライブラリ自身の `urllib.request` を使用して、HYDRA-UMC-SERVER 自身のモデル提出契約（同プロジェクト自身の `server.ts` にある `POST /api/models/submit`、`GET /api/models`、`GET /api/models/:category/:slug/download`、その自身の **Config > Models > "Accept model submissions"** トグルの背後にゲートされています）と通信します——4 つのエンドポイントしか必要とせず、永続的なライブ接続を必要としないプロジェクトのために、もう 1 つの HTTP 呼び出しのために `httpx`/`requests` を導入する正当性はありませんでした。すべての呼び出しはバックグラウンドの `QThread` 上で実行されるため、遅い、あるいは到達不能なサーバーが UI をフリーズさせることは決してありません。この契約は、そのプロジェクトが純粋なフロントエンド（STUDIO）と別個のヘッドレスバックエンド（HYDRA-UMC-SERVER、下記「関連プロジェクト」参照）に分割される前は、HYDRA-UMC-STUDIO 自身のプロセス内部にありました——本アプリはどちらの名前もハードコードしておらず、オペレーターは**アップロード**パネルのホスト/ポートフィールドを、実際のバックエンドが実際に稼働している場所へ向けるだけです。

- **ログイン** —— `POST /api/login`；`admin` ロールのトークンのみが実際にサーバー側の `POST /api/models/submit` に到達できるため、本アプリは実質的に管理者アカウントに対してのみ使用可能です。他のすべての管理者専用 STUDIO 機能と同様です。
- **プッシュ** —— 現在のロボットを URDF XML へ再シリアライズし、そのビジュアルが参照するすべてのメッシュファイル（インポート時に構築された同じメッシュリゾルバーで解決）をリクエストボディにインラインで base64 エンコードし、オペレーターが選んだカテゴリでタグ付けします（STUDIO 自身の Config > UI > Module Visibility のカテゴリ——Robot 3-6DOF、CNC、Pick & Place、Laser、Vacuum Table、XY Table、Heated Bed、ATC Tools——をミラーリングしています。URDF 自体にはこれらのどれに該当するかを示す固有のフィールドはありません）。名前の衝突はサーバー自身の 409 レスポンスとして返され、**上書き**にチェックを入れて再送信するか、名前を変更するかはオペレーターが判断します。本アプリは決して推測しません。
- **プル** —— すでに提出されたモデルの URDF + メッシュをローカルの作業フォルダへダウンロードし直し、エディターへ直接読み込みます——「取り出し、編集し、再送信する」という往復の半分は、本アプリ自身の目的そのものであり、既存のカタログエントリを、元のソースリポジトリから再度始めることなく手直しできるようにします。

---

## 🌐 多言語インターフェース

**英語、スペイン語、イタリア語、フランス語、ドイツ語、簡体字中国語、日本語**（`language/*.lng`）にわたる完全なインターフェース翻訳。本エコシステム内の他のすべての Python ツール（URTC Flasher、URTC Tester、HYDRA-UMC SUITE）とまったく同じ、プレーンな `KEY=Value` ファイル方式を使用しています——この仕組み自体にプロジェクト固有のロジックはなく、ここで再発明する理由はないため、そのまま採用しています。言語の切り替えは、すでに構築されたすべてのウィジェットをライブで再翻訳するのではなく、アプリの再起動後に有効になり、同じ慣例に一致しています。`language/` は PyInstaller の `--add-data` でその内部にバンドルされるのではなく、実行ファイルの**隣**に置かれるため、翻訳者は再ビルドなしに `.lng` ファイルを編集または追加できます。

---

## 🎛️ テーマ

同一エコシステム内の姉妹デスクトップツール向けに新しい視覚テーマを設計するのではなく、HYDRA-UMC SUITE 自身の `assets/qss/industrial_dark.qss` をそのまま（同じ相対パス、同じファイル）再利用しています。

---

## 📂 リポジトリ構成

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # エントリポイント——QApplication、テーマ、最大化起動、F11 フルスクリーン切替
├── requirements.txt                # PySide6、PyOpenGL、numpy-stl、numpy（バージョン固定）
├── build_exe.bat / build_exe.sh    # Windows/Linux 独立実行ファイルビルドスクリプト（PyInstaller）——最初にバージョンを加算
├── bump_version.py                 # オドメーター方式のバージョン加算、毎回の実際のビルド前に build_exe.bat/.sh から呼び出される
├── CHANGELOG.md                    # バージョン履歴
├── README.md                       # 本ファイル
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  # <- 翻訳
├── LICENSE                         # GPL-3.0
├── assets/
│   └── qss/industrial_dark.qss     # HYDRA-UMC-SUITE からそのまま再利用
├── language/                       # english/spanish/italian/french/german/chinese/japanese.lng —— exe の隣に置かれ、バンドルされない
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ —— 唯一の権威ある情報源、About ダイアログが読み取り、bump_version.py が書き換える
│   ├── app.py                      # EditorController —— 「何が読み込まれているか」の唯一の保持者、各パネルがリッスンする Qt シグナル
│   ├── models.py                   # 自社製の URDF オブジェクトツリー（Robot/Link/Joint/Visual/Geometry/Material/…）
│   ├── i18n.py                     # language/*.lng ローダー、設定の永続化——HYDRA-UMC-SUITE 自身の i18n.py から移植
│   ├── urdf/
│   │   ├── parser.py               # URDF XML -> models.py ツリー（ElementTree、xacro を検出して明確なエラーで拒否）
│   │   ├── writer.py                # models.py ツリー -> URDF XML 文字列（エクスポート + サーバーアップロードペイロード）
│   │   └── dof.py                  # 自由度カウント、STUDIO の 3-6 自由度上限に対する実現可能性検証
│   ├── render/
│   │   ├── mesh.py                 # STL/OBJ 読み込み、ボックス/円柱/球のプリミティブ生成、mm 対 m ガード
│   │   ├── kinematics.py           # 任意のインポート済みツリーに対する汎用正運動学（Z 軸上、URDF 自身の規約）
│   │   └── viewport.py             # QOpenGLWidget —— GLSL 3.3 コアシェーダー、オービットカメラ、リンクごとの GPU バッファ
│   ├── source/
│   │   ├── scan.py                 # .urdf/.xacro ファイルを検索、package:// を認識するメッシュファイル名リゾルバーを構築
│   │   ├── github_fetcher.py       # GitHub zip アーカイブのダウンロードと展開（urllib + zipfile、git 依存なし）
│   │   └── local_folder.py         # ローカルフォルダの検証——github_fetcher.py の薄い対応物
│   ├── server/
│   │   └── client.py               # StudioClient —— HYDRA-UMC-SERVER の server.ts（2 つのリポジトリが分割される前は STUDIO 自身のバックエンド）に対する login/list_models/push_model/pull_model
│   └── ui/
│       ├── main_window.py          # QMainWindow —— ドッキング可能なワークスペース、メニューバー、言語切り替え、ステータスバー
│       ├── theme.py                 # assets/qss/industrial_dark.qss を適用
│       └── panels/
│           ├── source_panel.py     # GitHub URL / ローカルフォルダ入力、見つかった URDF の一覧
│           ├── dof_panel.py        # 実現可能性判定の読み出し
│           ├── viewport_panel.py   # 3D ビューポートホスト、リンクツリー、ジョグスライダー
│           ├── properties_panel.py # 色変更/スケール変更/タイプと限位の再設定エディター
│           └── upload_panel.py     # サーバーの接続/プッシュ/プル
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   └── INTEGRATION_CONTRACT.md
└── work/                            # 取得した GitHub リポジトリとプルしたサーバーモデルのランタイム作業領域（gitignore 対象）
```

---

## 🛠️ 開発環境

### 必要環境
- [Python](https://www.python.org/) 3.11 以上
- pip

### インストール

```bash
pip install -r requirements.txt
```

これにより、バージョン固定された依存関係セットが導入されます：**PySide6**（Qt6 UI）、**PyOpenGL**（3D ビューポートレンダリング）、**numpy** / **numpy-stl**（メッシュ計算と STL 読み込み）。`git` のインストールは不要です——GitHub ソース読み込みパスは、プレーンな zip アーカイブを HTTPS でダウンロードします。

### 開発モード

```bash
python main.py
```

最大化された状態で起動します（真の OS レベルのフルスクリーンではないため、ネイティブなウィンドウのタイトルバーとコントロールは表示されたままです）——**F11** を押すと、本物のボーダーレスフルスクリーンとの切り替えができます。

### プロダクションビルド

PyInstaller を通じて、独立した実行ファイル（実行に Python のインストールが不要）をコンパイルします：

- **Windows：** `build_exe.bat` を実行 → `dist\HYDRA-UMC_EDITOR-URDF.exe` を生成
- **Linux：** `./build_exe.sh` を実行（初回のみ先に `chmod +x build_exe.sh`）→ `dist/HYDRA-UMC_EDITOR-URDF` を生成

どちらのスクリプトも、自身の `.venv` を作成/有効化し、`requirements.txt` に加えて `pyinstaller` をインストールし、以前の `build`/`dist` があれば削除し、**バージョン番号を加算**し、コンパイルし、最後に `README.md`、`LICENSE`、そして `language/` フォルダ全体を、生成されたバイナリの隣にコピーします（`language/` は意図的に `--add-data` で実行ファイルの内部にバンドルされていないため、後から再ビルドなしに `.lng` ファイルを編集または追加できます）。

**バージョン管理：** 本アプリのバージョン（`hydra_editor_urdf/__version__`、Help → About ダイアログに表示）は `MAJOR.MINOR.PATCH` に従います。`build_exe.bat`/`build_exe.sh` の実際の実行のたびに、最初に `bump_version.py` が呼び出され、オドメーター方式の加算が適用されます：`PATCH` が 1 増加し；`PATCH` が 9 を超えると 0 にリセットされ、代わりに `MINOR` が 1 増加します（例：`0.0.9` → `0.1.0`）。`MAJOR` は自動的には決して変更されません——それは常に意図的な手動の判断です。バージョン履歴は `CHANGELOG.md` を参照してください。

スクリプトの代わりに手動で等価な手順を実行したい場合——スクリプトがカバーしていないプラットフォームでビルドを調整する場合や、PyInstaller のフラグをデバッグする場合に便利です——手動プロセスは次のとおりです：

```bash
# 1. 仮想環境を作成して有効化
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. 依存関係 + PyInstaller をインストール
pip install -r requirements.txt
pip install pyinstaller

# 3. PySide6 自身のインストールディレクトリを特定（その Qt プラグインはその下にあります）
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> 以下の $PYSIDE_DIR

# 4. コンパイル——明示的にステージングされるのは 4 つの Qt プラグイン
#    サブフォルダ（platforms/styles/imageformats/iconengines）のみで、
#    --collect-all PySide6 ではありません。それをすると、
#    本アプリが決して使用しない Qt6WebEngineCore.dll などの数百 MB 級の
#    部品まで引き込まれてしまいます。PyInstaller 自身の依存関係アナライザーは、
#    main.py の実際のインポートグラフを追跡して、実際の
#    Qt6Core/Gui/Widgets/OpenGL DLL を見つけます——プラグインフォルダのみ
#    手動で追加する必要があります。
#
#    Windows（プラグインは PySide6/plugins/ 直下にあります）：
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux（プラグインは PySide6/Qt/plugins/ の下にあります——Windows とは
#    異なるレイアウトで、PyInstaller 自身のランタイムフック
#    pyi_rth_pyside6.py を読んで確認済み）：
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. バイナリの内部ではなく、隣に置く必要があるファイルをコピー
cp README.md LICENSE dist/
cp -r language dist/language
```

Linux では、コンパイル済みバイナリの実行に、システム自身の OpenGL ランタイム（`libGL.so.1`——例：Debian/Ubuntu では `libgl1`、Fedora では `mesa-libGL`、Arch では `libglvnd`）に加えて、Qt 自身の XCB プラットフォームプラグイン向けの `libxkbcommon-x11-0`/`xcb-util-cursor` が必要です。`build_exe.sh` は事前に `libGL.so.1` の有無を確認し、それが見つからない場合、PyInstaller の実行の奥深くで失敗させるのではなく、ディストリビューションごとの正しいインストールコマンドを表示します。

---

## 🔗 関連プロジェクト

本プロジェクトは、同一著者（JuanenRac / Electro Hobby 3D）による、より大きなロボティクスエコシステムの一部です。ご要望が実際にはこれらのプロジェクトのいずれかに関するものであり、本リポジトリのものではない可能性もあるため、知っておく価値があります：

**HYDRA-UMC プラットフォーム** —— マルチロボット・マイクロファクトリーセル
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— マザーボード本体：Raspberry Pi CM5 ホスト + デュアルコア STM32H745 リアルタイムコプロセッサ、CAN-OTA/SPI-OTA 経由で最大 8 台の分散ロボットアームを統括します。自社ハードウェア + ファームウェア、GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0。
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** —— HYDRA-UMC 向けの Web ベース制御ダッシュボード：マルチロボット 3D 可視化、運動学／軌道記録、プラットフォーム全体の CAN-OTA 書き込みとテスト。React + Vite + Three.js。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— かつて HYDRA-UMC-STUDIO 自身のプロセス内にバンドルされていたヘッドレスバックエンド（Node/Express/WebSocket）。ロボット制御 REST/WS API（本エディターが完成したモデルをプッシュする先である `POST /api/models/submit` を含む）、settings.json の永続化、JWT 認証、mDNS ディスカバリーを保持します。HYDRA-UMC-STUDIO は現在、ネットワーク越しにこれと通信する純粋な静的フロントエンドクライアントです。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** —— Wi-Fi／Bluetooth 経由で HYDRA-UMC を制御する Android アプリ。実際に動作するアプリです——完全なリモート制御機能セット、JWT 認証、暗号化された資格情報の保存。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** —— Wi-Fi 経由で HYDRA-UMC を制御する iOS/iPadOS アプリ、Flutter 製（クロスプラットフォーム、Mac なしで Windows 上でも検証可能。最終的な `.ipa` パッケージングには Xcode が必要）。実際に動作するアプリです——Android アプリと同じ機能セット。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** —— デスクトップ（Python/PySide6）製の群制御コマンドセンター：マルチコントローラーのネットワークディスカバリー、リアルタイムの双方向同期、実際の 3D ロボットビューポート、Photoshop 風のドッキング可能なワークスペース。実際に動作します、プレースホルダーではありません。
- **HYDRA-UMC-EDITOR-URDF**（本リポジトリ）—— デスクトップ（Python/PySide6）製のグラフィカル URDF 作成／編集ツール。HYDRA-UMC-STUDIO 自身のモデルカタログ向け：GitHub またはローカルフォルダからソースファイルを取得し、自由度の実現可能性を検証し、リアルタイム 3D プレビューで色／スケール／運動学を編集し、完成した結果を稼働中の STUDIO サーバーへプッシュします。実際に動作します、プレースホルダーではありません。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** —— HYDRA-UMC 自身の 5"/7" DSI タッチスクリーン（両サイズとも解像度は 1280×720）向けのネイティブ Flutter タッチ UI。Compute Module 5 上で動作し、ボードから直接この同じサーバーを制御します。実際に動作する雛形で、全 6 のカタログ画面（ダッシュボード、手動制御、カメラ、簡易 3D ビュー、システム指標、ログイン）がすべて実際のサーバーに接続済みです。実際の Linux ターゲットビルドはまだ実機で実行されていません（今のところ Windows 専用の動作環境——同プロジェクト自身の README を参照）。

**URTC プラットフォーム** —— HYDRA-UMC の各ロボットアームが搭載するツールヘッドコントローラー
- **[URTC](https://github.com/JuanenRac/URTC)** —— 汎用ロボットツールコントローラー：STM32F303 ベースの CAN バスツールヘッドコントローラー、25 種の完全実装済みツールプロファイル、CAN-OTA ファームウェア更新に対応。
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** —— URTC ボード向けのデスクトップ製 CAN-OTA + フルチップ SWD/JTAG 書き込みツール（Windows/Linux）。
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** —— URTC ボード向けのデスクトップ製リアルタイム CAN バス診断ツール、ツールプロファイルごとに 1 つのパネル（Windows/Linux）。
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** —— 上記 2 つのデスクトップツールに代わるブラウザベースの選択肢（Web Serial API + SLCAN）、ローカルインストール不要。

**本リポジトリと直接関連**
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** —— ここで作成された URDF モデルを消費して、その物理シミュレーションを駆動します。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** —— ここで作成された URDF モデルを消費して、その物理シミュレーションを駆動します。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** —— ここで作成されたモデルから学習データを生成します。

**エコシステムのその他のプロジェクト** —— 本プロジェクトが位置づけられる、より広範な多数のプロジェクト群、分野別：
- 👁️ **Vision AI Node (Hailo-8)：** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)、[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)、[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)、[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)、[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Cognitive AI Node (Hailo-10)：** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)、[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)、[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)、[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)、[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestration & Swarm：** [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)、[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)、[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)、[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)、[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Digital Twin & Simulation：** [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- 📊 **Data & Analytics：** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)、[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)、[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)、[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Industrial Gateway：** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)、[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)、[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)、[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Complementary Tools：** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)、[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)、[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)、[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)、[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 作者

**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 ライセンスと著作権表示

HYDRA-UMC EDITOR-URDF の著作権は (c) 2026 JuanenRac（Electro Hobby 3D）に帰属します。本プロジェクトまたはその派生物を配布する際は、この表示を必ず含めてください。

本プロジェクトはソースコードとそれ自身のドキュメントで構成されており、それぞれ実際にカバーする内容に適した異なるライセンスの下で提供されています：

1. ソースコード（`hydra_editor_urdf/`、`main.py`、および `build_exe.bat`/`build_exe.sh` を通じてそこから構築されるあらゆるバイナリ）は、**GNU General Public License v3.0（GPL-3.0）** の下で提供されます。全文は https://www.gnu.org/licenses/gpl-3.0.html を参照してください。

2. ドキュメント（本 README およびその自身の翻訳版——`README_spa.md`、`README_ita.md`、`README_fra.md`、`README_deu.md`、`README_zho.md`、`README_jpn.md`）は、**クリエイティブ・コモンズ 表示-継承 4.0 国際（CC BY-SA 4.0）** の下で提供されます。全文は https://creativecommons.org/licenses/by-sa/4.0/ を参照してください。

本アプリはそれ自身のサードパーティ製ロボットメッシュアセットを一切同梱していません——HYDRA-UMC STUDIO の `public/models/` とは異なり、本エディターが読み込むすべてのメッシュは、オペレーターがそれを向けたどのソースリポジトリまたはローカルフォルダから来たものであれ、そのソース自身の原本ライセンスの下にあります。稼働中の STUDIO サーバーへモデルを提出する前に（本エディターのエクスポート機能がそのまま流し込む先である、そのサーバー自身の `public/models/<slug>/ATTRIBUTION.txt` の慣例）、そのアップストリームのライセンス/帰属表示を確認し保持することは、引き続きオペレーター自身の責任です——本アプリには、あるソースリポジトリのライセンス条件を自動的に検出したり強制したりする方法はありません。

本エディターは [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) カタログのためのモデル作成ツールです——その自身のサーバー側ライセンスは同リポジトリを参照してください。本リポジトリ自身のライセンスはそちらには及ばず、その逆も同様です。

本プロジェクトを基に開発を行う際は、このライセンス区分を念頭に置いてください：ここでのコードの変更は GPL-3.0 を維持し、ドキュメントの派生物（本 README およびその翻訳版）は CC BY-SA 4.0 を維持し、本エディターを通過した（インポート、編集、またはエクスポートされた）あらゆるメッシュアセットは、その自身の原本ソースリポジトリが携えているライセンスの下に維持され、そのソースへの帰属表示を伴う必要があります。

## 🛠️ BUILD & RUN

リリースビルドの前に、バージョンを変更しないビルドチェックを使用してください。

| 操作 | Windows | Linux / macOS |
|---|---|---|
| ビルドチェック（バージョンと CHANGELOG を変更しない） | `build-test.bat` | `./build-test.sh` |
| 実行 / 開発（提供されている場合） | `run*.bat` または `dev*.bat` | `./run*.sh` または `./dev*.sh` |

`build-test.bat` と `build-test.sh` は、`hydra-umc.project.json` をインクリメントせず、`CHANGELOG.md` も変更せずにプロジェクトのスタックをコンパイルまたは検証します。通常のコンパイラ出力だけが作成される場合があります。既存の `build*.bat`、`build*.sh`、`run*`、`dev*` は、各プロジェクト固有のバージョン化または実行時の動作を維持します。その動作が必要な場合はそれらを使用してください。