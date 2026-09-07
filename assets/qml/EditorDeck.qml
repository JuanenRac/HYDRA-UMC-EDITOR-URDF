// =============================================================================
// HYDRA-UMC EDITOR-URDF - Qt Quick command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
//
// Faithfully reproduces the classic QMainWindow's own real spatial
// arrangement (see ui/main_window.py's own _build_panels()) rather than
// inventing a nav-sidebar/one-page-at-a-time layout this app never had:
// Source+DOF tabbed on the LEFT, Viewport+Properties side by side filling
// the CENTER/RIGHT, Upload docked across the BOTTOM.
// =============================================================================
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.VectorImage

ApplicationWindow {
    id: window
    width: 1680
    height: 960
    minimumWidth: 1280
    minimumHeight: 760
    visible: true
    title: editorBackend.title
    color: "#07111e"

    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color panelBorder: "#294965"
    property color textPrimary: "#edf7ff"
    property color muted: "#91a8bd"
    property color cyan: "#38d4e6"
    property color emerald: "#43db9b"
    property color rose: "#ee6b80"

    component Card: Rectangle {
        color: window.panel
        radius: 16
        border.width: 1
        border.color: window.panelBorder
    }

    component SectionLabel: Text {
        color: window.cyan
        font.family: "Bahnschrift"
        font.bold: true
        font.pixelSize: 12
    }

    component GameButton: Button {
        id: control
        property color accent: window.cyan
        implicitHeight: 38
        hoverEnabled: true
        font.family: "Bahnschrift"
        font.bold: true
        contentItem: Text {
            text: control.text
            color: control.enabled ? "#f5fbff" : "#6d8294"
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 10
            color: !control.enabled ? "#122031" : (control.down ? Qt.darker(control.accent, 1.35) : (control.hovered ? Qt.lighter(control.accent, 1.13) : control.accent))
            border.width: 1
            border.color: control.enabled ? Qt.lighter(control.accent, 1.12) : "#25384b"
        }
    }

    // Plain validated text fields, not QML's own SpinBox - a real fixed-
    // point *100-style SpinBox (the pattern HYDRA-UMC-SUITE's own
    // DecimalSpinBox uses for 2-decimal mm/degree fields) breaks down for
    // this panel's own real value ranges: inertia tensor components need
    // up to 8 real decimal places (the classic QDoubleSpinBox's own
    // setDecimals(8)), which overflows a *10^n integer-backed control at
    // any believable range. A validated free-text field matches the
    // classic field's actual precision instead of silently truncating it.
    component NumberField: TextField {
        id: control
        property real numberValue: 0
        text: numberValue.toString()
        horizontalAlignment: TextInput.AlignRight
        color: window.textPrimary
        font.family: "Consolas"
        selectByMouse: true
        validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
    }

    header: ToolBar {
        // Explicit, not left implicit - this exact real bug (Basic-style
        // ToolBar collapsing to 0 height, header content overlapping at
        // the top-left) already bit HYDRA-UMC-SUITE, then URTC-TESTER/
        // URTC-FLASHER before the fix was propagated to them too. Sized
        // from day one here instead of waiting to find it visually: the
        // 50px icon box plus this Card's own 7px and this RowLayout's
        // own 10px margins top and bottom (50 + 2*7 + 2*10).
        height: 84
        background: Rectangle { color: "#07111e" }
        Card {
            anchors.fill: parent
            anchors.margins: 7
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    radius: 12
                    color: "#0e3045"
                    border.width: 1
                    border.color: "#2d7695"
                    VectorImage { anchors.fill: parent; anchors.margins: 7; source: editorBackend.iconSource }
                }
                ColumnLayout {
                    Layout.preferredWidth: 260
                    spacing: 0
                    Text { text: "HYDRA-UMC"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 10 }
                    Text { text: "EDITOR-URDF"; color: textPrimary; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 17 }
                    Text { text: editorBackend.uiText("QT_TAGLINE"); color: muted; font.family: "Bahnschrift"; font.pixelSize: 8 }
                }
                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; Layout.topMargin: 4; Layout.bottomMargin: 4; color: panelBorder }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text { text: editorBackend.deckSummaryText; color: editorBackend.dofHasRobot ? (editorBackend.dofFeasible ? emerald : rose) : muted; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                    Text { text: editorBackend.statusMessage; color: muted; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                }
                GameButton { text: editorBackend.uiText("QT_EXPORT"); accent: "#b86a35"; enabled: editorBackend.canExport; onClicked: exportDialog.open() }
                GameButton { text: editorBackend.uiText("MENU_ABOUT"); accent: "#24465e"; onClicked: aboutDialog.open() }
                ColumnLayout {
                    spacing: 0
                    Text { text: "v" + editorBackend.version; color: muted; font.pixelSize: 10 }
                }
            }
        }
    }

    FolderDialog {
        id: folderDialog
        title: editorBackend.uiText("SOURCE_BROWSE_DIALOG_TITLE")
        onAccepted: localPathField.text = editorBackend.toLocalPath(selectedFolder.toString())
    }

    FileDialog {
        id: exportDialog
        title: editorBackend.uiText("QT_EXPORT")
        fileMode: FileDialog.SaveFile
        nameFilters: ["URDF (*.urdf)"]
        onAccepted: {
            var err = editorBackend.exportUrdf(selectedFile.toString())
            if (err) exportErrorDialog.openWith(err)
        }
    }

    Dialog {
        id: exportErrorDialog
        anchors.centerIn: parent
        modal: true
        width: 420
        title: editorBackend.uiText("MENU_EXPORT_URDF")
        standardButtons: Dialog.Ok
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        property string message: ""
        function openWith(msg) { message = msg; open() }
        contentItem: Text { text: exportErrorDialog.message; color: window.rose; wrapMode: Text.WordWrap; Layout.preferredWidth: 360 }
    }

    Dialog {
        id: aboutDialog
        anchors.centerIn: parent
        modal: true
        width: 440
        standardButtons: Dialog.NoButton
        background: Rectangle { color: window.panel; radius: 18; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 8
            VectorImage { source: editorBackend.iconSource; Layout.preferredWidth: 84; Layout.preferredHeight: 84; Layout.alignment: Qt.AlignHCenter }
            Row {
                Layout.alignment: Qt.AlignHCenter
                Text { text: "HYDRA"; color: window.textPrimary; font.bold: true; font.pixelSize: 20 }
                Text { text: "-UM"; color: window.emerald; font.bold: true; font.pixelSize: 20 }
                Text { text: "C"; color: window.rose; font.bold: true; font.pixelSize: 20 }
                Text { text: " EDITOR-URDF"; color: window.cyan; font.bold: true; font.pixelSize: 20 }
            }
            Text { text: editorBackend.uiText("ABOUT_TAGLINE"); color: window.muted; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.preferredWidth: 380; Layout.alignment: Qt.AlignHCenter }
            Text { text: editorBackend.uiText("ABOUT_DESCRIPTION"); color: window.textPrimary; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.preferredWidth: 380; Layout.alignment: Qt.AlignHCenter }
            Item { height: 6 }
            RowLayout { Layout.fillWidth: true; Text { text: editorBackend.uiText("ABOUT_VERSION").toUpperCase(); color: window.muted; Layout.fillWidth: true } Text { text: editorBackend.version; color: window.textPrimary } }
            RowLayout { Layout.fillWidth: true; Text { text: editorBackend.uiText("ABOUT_AUTHOR").toUpperCase(); color: window.muted; Layout.fillWidth: true } Text { text: editorBackend.aboutAuthor; color: window.textPrimary } }
            RowLayout { Layout.fillWidth: true; Text { text: editorBackend.uiText("ABOUT_EMAIL").toUpperCase(); color: window.muted; Layout.fillWidth: true } Text { text: editorBackend.aboutEmail; color: window.cyan } }
            RowLayout { Layout.fillWidth: true; Text { text: editorBackend.uiText("ABOUT_LICENSE").toUpperCase(); color: window.muted; Layout.fillWidth: true } Text { text: editorBackend.aboutLicense; color: window.textPrimary } }
            GameButton { text: editorBackend.uiText("BTN_CLOSE"); Layout.alignment: Qt.AlignHCenter; Layout.topMargin: 6; onClicked: aboutDialog.close() }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            // --- Source / DOF (tabbed, left - mirrors the classic
            // dock_source/dock_dof tabifyDockWidget() pair) ---------------
            Card {
                Layout.preferredWidth: 380
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    TabBar {
                        id: sourceTabs
                        Layout.fillWidth: true
                        background: Rectangle { color: "transparent" }
                        TabButton { text: editorBackend.uiText("DOCK_SOURCE") }
                        TabButton { text: editorBackend.uiText("DOCK_DOF") }
                    }
                    StackLayout {
                        currentIndex: sourceTabs.currentIndex
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        // -- Source ---------------------------------------
                        ColumnLayout {
                            spacing: 6
                            SectionLabel { text: editorBackend.uiText("SOURCE_GALLERY_LABEL") }
                            ComboBox {
                                id: galleryCombo
                                Layout.fillWidth: true
                                model: editorBackend.gallery
                                textRole: "name"
                                onActivated: {
                                    // Only FILLS the URL field, same real
                                    // reasoning as the classic combo's own
                                    // _on_gallery_selection_changed() -
                                    // never fetches on its own.
                                    githubField.text = editorBackend.gallery[currentIndex].url
                                    galleryDescription.text = editorBackend.gallery[currentIndex].description
                                }
                            }
                            Text { id: galleryDescription; color: muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                            SectionLabel { text: editorBackend.uiText("SOURCE_GITHUB_LABEL"); Layout.topMargin: 6 }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: githubField
                                    Layout.fillWidth: true
                                    placeholderText: editorBackend.uiText("SOURCE_GITHUB_PLACEHOLDER")
                                    color: textPrimary
                                    background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder }
                                }
                                GameButton { text: editorBackend.uiText("SOURCE_FETCH_BUTTON"); enabled: !editorBackend.sourceBusy; onClicked: editorBackend.fetchGithub(githubField.text) }
                            }

                            SectionLabel { text: editorBackend.uiText("SOURCE_LOCAL_LABEL"); Layout.topMargin: 6 }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: localPathField
                                    Layout.fillWidth: true
                                    placeholderText: editorBackend.uiText("SOURCE_LOCAL_PLACEHOLDER")
                                    color: textPrimary
                                    background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder }
                                }
                                GameButton { text: editorBackend.uiText("SOURCE_BROWSE_BUTTON"); accent: "#24465e"; onClicked: folderDialog.open() }
                                GameButton { text: editorBackend.uiText("SOURCE_OPEN_BUTTON"); onClicked: editorBackend.openLocalFolder(localPathField.text) }
                            }

                            SectionLabel { text: editorBackend.uiText("SOURCE_FOUND_URDF_LABEL"); Layout.topMargin: 6 }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: editorBackend.foundUrdfCandidates
                                spacing: 4
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 34
                                    radius: 8
                                    color: candidateArea.containsMouse ? panelAlt : "transparent"
                                    border.width: 1
                                    border.color: panelBorder
                                    Text { anchors.fill: parent; anchors.margins: 8; text: modelData; color: textPrimary; font.pixelSize: 11; elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter }
                                    MouseArea { id: candidateArea; anchors.fill: parent; hoverEnabled: true; onClicked: editorBackend.pickFoundUrdf(index) }
                                }
                            }
                        }

                        // -- DOF -------------------------------------------
                        ColumnLayout {
                            spacing: 8
                            Text { text: editorBackend.dofRangeText; color: muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Text {
                                text: editorBackend.dofVerdictText
                                color: editorBackend.dofHasRobot ? (editorBackend.dofFeasible ? emerald : rose) : muted
                                font.bold: true
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            SectionLabel { text: editorBackend.uiText("DOF_ISSUES_LABEL") }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: editorBackend.dofIssues
                                spacing: 4
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: issueText.implicitHeight + 14
                                    radius: 8
                                    color: panelAlt
                                    Text { id: issueText; anchors.fill: parent; anchors.margins: 8; text: modelData; color: textPrimary; font.pixelSize: 11; wrapMode: Text.WordWrap }
                                }
                            }
                        }
                    }
                }
            }

            // --- Viewport (center, large - mirrors dock_viewport) --------
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    ColumnLayout {
                        Layout.preferredWidth: 170
                        Layout.fillHeight: true
                        spacing: 6
                        SectionLabel { text: editorBackend.uiText("VIEWPORT_LINKS_LABEL") }
                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: editorBackend.linkTree
                            spacing: 2
                            delegate: Rectangle {
                                width: ListView.view.width
                                height: 28
                                radius: 6
                                color: modelData.name === editorBackend.selectedLink ? "#1a4967" : (linkArea.containsMouse ? panelAlt : "transparent")
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 8 + modelData.depth * 14
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.name
                                    color: textPrimary
                                    font.pixelSize: 11
                                }
                                MouseArea { id: linkArea; anchors.fill: parent; hoverEnabled: true; onClicked: editorBackend.selectLink(modelData.name) }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 0
                        Item {
                            id: viewportHost
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            onWidthChanged: editorBackend.viewportResize(width, height)
                            onHeightChanged: editorBackend.viewportResize(width, height)

                            Image {
                                anchors.fill: parent
                                visible: editorBackend.viewportSupported
                                source: "image://viewportFrame/" + editorBackend.viewportFrameVersion
                                cache: false
                                fillMode: Image.PreserveAspectFit
                            }
                            Text {
                                // anchors.fill + margins, not anchors.centerIn
                                // plus an arithmetic `width: parent.width *
                                // 0.8` - a real on-screen check showed that
                                // expression freezing at whatever
                                // viewportHost's own width happened to be at
                                // component-completion (before the RowLayout
                                // it lives in ever assigned it a real
                                // fillWidth value) and never re-evaluating
                                // afterward, wrapping this entire message one
                                // word per line in a sliver a few pixels
                                // wide. Anchoring directly to the real,
                                // continuously-updated parent geometry
                                // doesn't have that failure mode.
                                anchors.fill: parent
                                anchors.margins: 20
                                visible: !editorBackend.viewportSupported
                                text: editorBackend.viewportUnsupportedMessage
                                color: muted
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: editorBackend.viewportSupported
                                acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                                property real lastX: 0
                                property real lastY: 0
                                onPressed: (mouse) => { lastX = mouse.x; lastY = mouse.y }
                                onPositionChanged: (mouse) => {
                                    var dx = mouse.x - lastX
                                    var dy = mouse.y - lastY
                                    lastX = mouse.x
                                    lastY = mouse.y
                                    if (mouse.buttons & Qt.LeftButton) editorBackend.viewportOrbit(dx, dy)
                                    else if (mouse.buttons & (Qt.RightButton | Qt.MiddleButton)) editorBackend.viewportPan(dx, dy)
                                }
                                onWheel: (wheel) => editorBackend.viewportZoom(wheel.angleDelta.y > 0 ? 0.9 : 1.1)
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.preferredWidth: 220
                        Layout.fillHeight: true
                        spacing: 6
                        SectionLabel { text: editorBackend.uiText("VIEWPORT_JOG_LABEL") }
                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: editorBackend.jointSliders
                            spacing: 10
                            delegate: ColumnLayout {
                                width: ListView.view.width
                                spacing: 2
                                Text { text: modelData.name + " (" + modelData.unit + ")"; color: textPrimary; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                Slider {
                                    Layout.fillWidth: true
                                    from: modelData.lower
                                    to: modelData.upper
                                    value: modelData.value
                                    onMoved: editorBackend.setJointValue(modelData.name, value)
                                }
                            }
                        }
                    }
                }
            }

            // --- Properties (right - mirrors dock_properties) ------------
            Card {
                Layout.preferredWidth: 340
                Layout.fillHeight: true

                // NumberField's own `text` binding to `numberValue` only
                // holds until the operator types into it once (a plain
                // QML TextField breaks a declarative binding on direct
                // edit, same as every other bound TextField in this
                // ecosystem's own QML decks) - without this, switching
                // the selected link after editing, say, scaleX once would
                // keep showing the PREVIOUS link's stale scale value
                // instead of the newly-selected one's real value. Forcing
                // every field back to the bridge's own current state on
                // every real change (selection, tree edit, calc) is the
                // same real fix the classic QDoubleSpinBox panel gets for
                // free (PropertiesPanel._on_selection_changed() calls
                // setValue() on every field unconditionally).
                Connections {
                    target: editorBackend
                    function onChanged() {
                        scaleX.text = editorBackend.propsScale[0].toString()
                        scaleY.text = editorBackend.propsScale[1].toString()
                        scaleZ.text = editorBackend.propsScale[2].toString()
                        jointTypeCombo.currentIndex = editorBackend.propsJointTypeIndex
                        jointLower.text = editorBackend.propsJointLower.toString()
                        jointUpper.text = editorBackend.propsJointUpper.toString()
                        inertialMass.text = editorBackend.propsInertialMass.toString()
                        inertialIxx.text = editorBackend.propsInertialIxx.toString()
                        inertialIyy.text = editorBackend.propsInertialIyy.toString()
                        inertialIzz.text = editorBackend.propsInertialIzz.toString()
                    }
                }

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 14
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: 12
                        Text { text: editorBackend.propsTitleText; color: textPrimary; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                        // Color
                        ColumnLayout {
                            Layout.fillWidth: true
                            enabled: editorBackend.propsColorEnabled
                            opacity: enabled ? 1.0 : 0.4
                            SectionLabel { text: editorBackend.uiText("PROPS_COLOR_GROUP") }
                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle { width: 32; height: 32; radius: 8; color: editorBackend.propsColorHex; border.width: 1; border.color: panelBorder }
                                GameButton { text: editorBackend.uiText("PROPS_PICK_COLOR"); Layout.fillWidth: true; onClicked: { colorDialog.selectedColor = editorBackend.propsColorHex; colorDialog.open() } }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }

                        // Scale
                        ColumnLayout {
                            Layout.fillWidth: true
                            enabled: editorBackend.propsIsMesh
                            opacity: enabled ? 1.0 : 0.4
                            SectionLabel { text: editorBackend.uiText("PROPS_SCALE_GROUP") }
                            RowLayout {
                                Layout.fillWidth: true
                                NumberField { id: scaleX; Layout.fillWidth: true; numberValue: editorBackend.propsScale[0] }
                                NumberField { id: scaleY; Layout.fillWidth: true; numberValue: editorBackend.propsScale[1] }
                                NumberField { id: scaleZ; Layout.fillWidth: true; numberValue: editorBackend.propsScale[2] }
                            }
                            GameButton { text: editorBackend.uiText("PROPS_APPLY_SCALE"); Layout.fillWidth: true; onClicked: editorBackend.applyScale(Number(scaleX.text), Number(scaleY.text), Number(scaleZ.text)) }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }

                        // Joint
                        ColumnLayout {
                            Layout.fillWidth: true
                            enabled: editorBackend.propsHasJoint
                            opacity: enabled ? 1.0 : 0.4
                            SectionLabel { text: editorBackend.uiText("PROPS_JOINT_GROUP") }
                            Text { text: editorBackend.uiText("PROPS_JOINT_TYPE"); color: muted; font.pixelSize: 10 }
                            ComboBox { id: jointTypeCombo; Layout.fillWidth: true; model: editorBackend.propsJointTypeNames; currentIndex: editorBackend.propsJointTypeIndex }
                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: editorBackend.uiText("PROPS_JOINT_LOWER"); color: muted; font.pixelSize: 10 }
                                    NumberField { id: jointLower; Layout.fillWidth: true; numberValue: editorBackend.propsJointLower }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: editorBackend.uiText("PROPS_JOINT_UPPER"); color: muted; font.pixelSize: 10 }
                                    NumberField { id: jointUpper; Layout.fillWidth: true; numberValue: editorBackend.propsJointUpper }
                                }
                            }
                            GameButton { text: editorBackend.uiText("PROPS_APPLY_JOINT"); Layout.fillWidth: true; onClicked: editorBackend.applyJoint(jointTypeCombo.currentIndex, Number(jointLower.text), Number(jointUpper.text)) }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }

                        // Mass & inertia
                        ColumnLayout {
                            Layout.fillWidth: true
                            enabled: editorBackend.propsColorEnabled
                            opacity: enabled ? 1.0 : 0.4
                            SectionLabel { text: editorBackend.uiText("PROPS_INERTIAL_GROUP") }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: editorBackend.uiText("PROPS_INERTIAL_MASS"); color: muted; font.pixelSize: 10; Layout.fillWidth: true }
                                NumberField { id: inertialMass; Layout.preferredWidth: 100; numberValue: editorBackend.propsInertialMass }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Ixx"; color: muted; font.pixelSize: 10; Layout.fillWidth: true }
                                NumberField { id: inertialIxx; Layout.preferredWidth: 100; numberValue: editorBackend.propsInertialIxx }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Iyy"; color: muted; font.pixelSize: 10; Layout.fillWidth: true }
                                NumberField { id: inertialIyy; Layout.preferredWidth: 100; numberValue: editorBackend.propsInertialIyy }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Izz"; color: muted; font.pixelSize: 10; Layout.fillWidth: true }
                                NumberField { id: inertialIzz; Layout.preferredWidth: 100; numberValue: editorBackend.propsInertialIzz }
                            }
                            Text { text: editorBackend.propsInertialNote; color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true; visible: text.length > 0 }
                            GameButton { text: editorBackend.uiText("PROPS_CALC_INERTIAL"); accent: "#24465e"; Layout.fillWidth: true; onClicked: editorBackend.calcInertial(Number(inertialMass.text)) }
                            GameButton { text: editorBackend.uiText("PROPS_APPLY_INERTIAL"); Layout.fillWidth: true; onClicked: editorBackend.applyInertial(Number(inertialMass.text), Number(inertialIxx.text), Number(inertialIyy.text), Number(inertialIzz.text)) }
                        }
                    }
                }
            }
        }

        // --- Upload (bottom, full width - mirrors dock_upload) -----------
        Card {
            Layout.fillWidth: true
            Layout.preferredHeight: 190
            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 16

                ColumnLayout {
                    Layout.preferredWidth: 460
                    Layout.fillHeight: true
                    spacing: 6
                    SectionLabel { text: editorBackend.uiText("UPLOAD_SERVER_LABEL"); wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: hostField; text: "192.168.1.100"; Layout.preferredWidth: 150; color: textPrimary; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        SpinBox { id: portField; from: 1; to: 65535; value: 3000; editable: true; Layout.preferredWidth: 120 }
                        TextField { id: userField; text: "admin"; Layout.preferredWidth: 90; color: textPrimary; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        TextField { id: passField; text: "admin"; echoMode: TextInput.Password; Layout.preferredWidth: 90; color: textPrimary; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: editorBackend.uiText("UPLOAD_CONNECT_BUTTON"); enabled: !editorBackend.uploadConnecting; onClicked: editorBackend.connectToServer(hostField.text, portField.value, userField.text, passField.text) }
                    }
                    Text { text: editorBackend.uploadStatusText; color: editorBackend.uploadConnected ? emerald : muted; font.pixelSize: 10 }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: panelBorder }

                ColumnLayout {
                    Layout.preferredWidth: 240
                    Layout.fillHeight: true
                    spacing: 6
                    SectionLabel { text: editorBackend.uiText("UPLOAD_CATEGORY_LABEL") }
                    ComboBox { id: categoryCombo; Layout.fillWidth: true; model: editorBackend.uploadCategories }
                    // A CheckBox with its OWN custom contentItem/indicator
                    // (the previous version of this row) is a real, already
                    // -documented gotcha in this ecosystem's own Qt Quick
                    // decks: it misplaces the indicator box. The proven fix
                    // (already used by HYDRA-UMC-SUITE's own equivalent
                    // checkboxes) is a plain, un-styled CheckBox plus a
                    // separate label - but SUITE's own real labels there are
                    // short, single-line text, which sidesteps a second real
                    // issue this one's own long label actually hits: a
                    // RowLayout still doesn't reserve real height for a
                    // wrapped Text sibling, even with the fillWidth fix
                    // pattern used above (the row's own height, the fillWidth
                    // Text's width, and that Text's own wrapped implicitHeight
                    // form a real ordering problem a plain Math.max() binding
                    // doesn't reliably resolve - confirmed with a real
                    // on-screen check, not just a theory). Putting the label
                    // on its OWN full-width row below the checkbox instead -
                    // a direct ColumnLayout child, never sharing a row's width
                    // with another sibling - sidesteps the ordering problem
                    // entirely, the same way every OTHER real wrapped label in
                    // this deck already does.
                    RowLayout {
                        spacing: 6
                        CheckBox { id: overwriteCheck }
                    }
                    Text {
                        text: editorBackend.uiText("UPLOAD_OVERWRITE_CHECKBOX")
                        color: muted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        MouseArea { anchors.fill: parent; onClicked: overwriteCheck.toggle() }
                    }
                    GameButton { text: editorBackend.uiText("UPLOAD_PUSH_BUTTON"); enabled: editorBackend.uploadCanPush; Layout.fillWidth: true; onClicked: editorBackend.pushToServer(categoryCombo.currentIndex, overwriteCheck.checked) }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: panelBorder }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        // Explicit, not left implicit - a real on-screen check
                        // showed this row's own wrapped 2-line label
                        // overflowing past the RowLayout's own implicit
                        // height (a Text's wrapped implicitHeight isn't known
                        // until AFTER the layout has already assigned it a
                        // fillWidth-stretched width, so the row sizes itself
                        // off the label's un-wrapped single-line height) and
                        // spilling down over the GameButton/ListView below
                        // it. Binding the row's own height to the label's
                        // real implicitHeight keeps the row - and everything
                        // below it - correctly out of the way.
                        Layout.preferredHeight: Math.max(modelsLabel.implicitHeight, refreshButton.implicitHeight)
                        SectionLabel { id: modelsLabel; text: editorBackend.uiText("UPLOAD_SERVER_MODELS_LABEL"); wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        GameButton { id: refreshButton; text: editorBackend.uiText("UPLOAD_REFRESH_BUTTON"); accent: "#24465e"; enabled: editorBackend.uploadConnected; onClicked: editorBackend.refreshModels() }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        orientation: ListView.Horizontal
                        model: editorBackend.uploadModels
                        spacing: 6
                        delegate: Rectangle {
                            width: 200
                            height: ListView.view.height
                            radius: 8
                            color: modelArea.containsMouse ? "#1a4967" : panelAlt
                            border.width: 1
                            border.color: panelBorder
                            Text { anchors.fill: parent; anchors.margins: 8; text: modelData; color: textPrimary; font.pixelSize: 11; wrapMode: Text.WordWrap }
                            MouseArea { id: modelArea; anchors.fill: parent; hoverEnabled: true; onClicked: editorBackend.pullModel(index) }
                        }
                    }
                }
            }
        }
    }

    ColorDialog {
        id: colorDialog
        onAccepted: editorBackend.applyColor(selectedColor)
    }
}
