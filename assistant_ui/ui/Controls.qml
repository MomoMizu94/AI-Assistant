import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCore

RowLayout {
    id: root
    spacing: 16
    Layout.alignment: Qt.AlignHCenter
    Layout.margins: 12

    Component.onCompleted: {
        console.log("Controls backend:", backend)
    }


    // ───────── Mic toggle ─────────
    Button {
        id: micButton
        property bool micActive: false

        text: backend && backend.isRecording ? "Stop Mic" : "Start Mic"

        onClicked: {
            if (backend) {
                backend.toggleMic()
            }
        }

        background: Rectangle {
            implicitWidth: 110
            implicitHeight: 32
            radius: 8
            color: backend && backend.isRecording ? "#FF932020" : "#FF0E1018"
            border.color: "#41e1ff"
            border.width: 1
        }

        contentItem: Text {
            text: micButton.text
            color: "#f8f8f2"
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    // ───────── Mute toggle ─────────
    Button {
        id: muteButton

        text: backend && backend.isMuted ? "Unmute" : "Mute"

        onClicked: {
            if (backend) {
                backend.toggleMute()
            }
        }

        background: Rectangle {
            implicitWidth: 90
            implicitHeight: 32
            radius: 8
            color: backend && backend.isMuted ? "#FF3B3F55" : "#FF0E1018"
            border.color: "#41e1ff"
            border.width: 1
        }

        contentItem: Text {
            text: muteButton.text
            color: "#f8f8f2"
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    // ───────── Status indicator ─────────
    Rectangle {
        width: 14
        height: 14
        radius: 7

        property string status: backend && backend.status ? backend.status : "idle"

        color: status === "listening" ? "#42ff7b"
              : status === "thinking" ? "#ffd34d"
              : status === "speaking" ? "#41e1ff"
              : "#444444"

        border.color: "#202530"
        border.width: 1

    }
}
