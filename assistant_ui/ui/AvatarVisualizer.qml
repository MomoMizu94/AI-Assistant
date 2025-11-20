import QtQuick

Item {
    id: avatarRoot
    width: 220
    height: 220

    Rectangle {
        id: orb
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.7
        height: width
        radius: width / 2

        color: "#ff3b3f"         // bright red core
        border.color: "#ffd34d"  // warm border
        border.width: 2
        opacity: 0.9
        scale: 1.0

        // Pulsating animation
        SequentialAnimation on scale {
            loops: Animation.Infinite
            running: true

            NumberAnimation {
                from: 0.95
                to: 1.05
                duration: 600
                easing.type: Easing.InOutQuad
            }
            NumberAnimation {
                from: 1.05
                to: 0.95
                duration: 600
                easing.type: Easing.InOutQuad
            }
        }

        SequentialAnimation on opacity {
            loops: Animation.Infinite
            running: true

            NumberAnimation {
                from: 0.75
                to: 1.0
                duration: 600
                easing.type: Easing.InOutQuad
            }
            NumberAnimation {
                from: 1.0
                to: 0.75
                duration: 600
                easing.type: Easing.InOutQuad
            }
        }
    }
}
