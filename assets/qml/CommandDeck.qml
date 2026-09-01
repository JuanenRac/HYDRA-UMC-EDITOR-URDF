// =============================================================================
// HYDRA-UMC EDITOR-URDF - Qt Quick command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.VectorImage

Rectangle {
    id: deck
    required property var deckBackend
    color: "#07111e"
    radius: 16
    border.width: 1
    border.color: "#294965"

    component DeckButton: Button {
        id: control
        implicitHeight: 34
        hoverEnabled: true
        font.family: "Bahnschrift"
        font.bold: true
        contentItem: Text { text: control.text; color: control.enabled ? "#edf7ff" : "#71869b"; font: control.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle {
            radius: 10
            color: control.down ? "#15677a" : (control.hovered ? "#17465e" : "#14253b")
            border.width: 1
            border.color: control.hovered ? "#38d4e6" : "#294965"
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 9
        Rectangle {
            Layout.preferredWidth: 46
            Layout.preferredHeight: 46
            radius: 12
            color: "#0e3045"
            border.width: 1
            border.color: "#2d7695"
            VectorImage { anchors.fill: parent; anchors.margins: 7; source: deck.deckBackend.logoSource }
        }
        ColumnLayout {
            Layout.preferredWidth: 245
            spacing: 0
            Text { text: "HYDRA-UMC"; color: "#38d4e6"; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 10 }
            Text { text: "EDITOR-URDF"; color: "#edf7ff"; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 18 }
            Text { text: deck.deckBackend.modelName; color: "#91a8bd"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
        }
        Item { Layout.fillWidth: true }
        Repeater {
            model: [
                ["SOURCE", "source"], ["DOF", "dof"], ["VIEWPORT", "viewport"],
                ["PROPERTIES", "properties"], ["UPLOAD", "upload"]
            ]
            delegate: DeckButton { required property var modelData; text: modelData[0]; onClicked: deck.deckBackend.navigate(modelData[1]) }
        }
        DeckButton { text: "EXPORT"; enabled: deck.deckBackend.canExport; onClicked: deck.deckBackend.exportUrdf() }
        DeckButton { text: "?"; Layout.preferredWidth: 36; onClicked: deck.deckBackend.showAbout() }
        Text { text: deck.deckBackend.status + "  v" + deck.deckBackend.version; color: "#43db9b"; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 10 }
    }
}
