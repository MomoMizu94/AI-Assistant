import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: root
    width: 900
    height: 700
    visible: true
    title: "AI Assistant"

    Component.onCompleted: {
        console.log("MainWindow1 backend =", backend)
    }

    // Background color
    color: "#111217"

    ColumnLayout {
        id: layoutRoot
        anchors.fill: parent
        spacing: 0

        Component.onCompleted: {
                console.log("MainWindow2 backend =", backend)
            }

        // ───────── AVATAR (top) ─────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.height * 0.35
            color: "#111217"

            Component.onCompleted: {
                console.log("MainWindow3 backend =", backend)
            }

            AvatarVisualizer {
                id: avatar
                anchors.centerIn: parent
                width: parent.width * 0.3
                height: width
            }
        }

        // ───────── CHAT (middle) ─────────
        ChatView {
            id: chatView
            Layout.fillWidth: true
            Layout.fillHeight: true
            Component.onCompleted: {
                console.log("MainWindow4 backend =", backend)
            }
        }

        // ───────── CONTROLS (bottom) ─────────
        Controls {
            id: controls
            Component.onCompleted: {
                console.log("MainWindow5 backend =", backend)
            }
            Layout.fillWidth: true
            Layout.preferredHeight: 70
        }
    }
}
