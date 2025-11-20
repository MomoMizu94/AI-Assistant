import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 8
    Layout.margins: 12

    ListModel {
        id: chatModel
    }

    // Chat display area
    ListView {
        id: chatList
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: chatModel
        clip: true

        delegate: Column {
            width: parent.width
            spacing: 4

            Text {
                text: model.role + ":"
                color: model.role === "user" ? "#41e1ff" : "#ffb347"
                font.bold: true
                font.pixelSize: 24
            }
            Text {
                text: model.message
                color: "white"
                wrapMode: Text.Wrap
                font.pixelSize: 16
            }
        }
    }

    // Input field
    TextField {
        id: inputField
        Layout.fillWidth: true
        placeholderText: "Type a message and press Enter..."

        onAccepted: {
            if (backend) {
                backend.sendMessage(text)
            }
            console.log("Tekstin pitäis kadota.")
            inputField.text = ""
        }
    }

    Component.onCompleted: {
        if (backend) {
            backend.newMessage.connect(function(role, message) {
                chatModel.append({ "role": role, "message": message })
                chatList.positionViewAtEnd()
            })
        }
    }
}
