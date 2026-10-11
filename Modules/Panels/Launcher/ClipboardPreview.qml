import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../Helpers/TextFormatter.js" as TextFormatter
import qs.Commons
import qs.Services.Keyboard
import qs.Widgets

Item {
  id: previewPanel

  property var currentItem: null
  property string fullContent: ""
  property string imageDataUrl: ""
  property bool loadingFullContent: false
  property bool isImageContent: false

  implicitHeight: contentColumn.implicitHeight + Style.marginL * 2

  Connections {
    target: previewPanel
    function onCurrentItemChanged() {
      previewPanel.fullContent = "";
      previewPanel.imageDataUrl = "";
      previewPanel.loadingFullContent = false;
      previewPanel.isImageContent = previewPanel.currentItem && previewPanel.currentItem.isImage;

      if (previewPanel.currentItem && previewPanel.currentItem.clipboardId) {
        if (previewPanel.isImageContent) {
          previewPanel.imageDataUrl = ClipboardService.getImageData(previewPanel.currentItem.clipboardId) || "";
          previewPanel.loadingFullContent = !previewPanel.imageDataUrl;

          if (!previewPanel.imageDataUrl && previewPanel.currentItem.mime) {
            ClipboardService.decodeToDataUrl(previewPanel.currentItem.clipboardId, previewPanel.currentItem.mime, null);
          }
        } else {
          previewPanel.loadingFullContent = true;
          ClipboardService.decode(previewPanel.currentItem.clipboardId, function (content) {
            previewPanel.fullContent = TextFormatter.wrapTextForDisplay(content);
            previewPanel.loadingFullContent = false;
          });
        }
      }
    }
  }

  readonly property int _rev: ClipboardService.revision

  Timer {
    id: imageUpdateTimer
    interval: 200
    running: previewPanel.currentItem && previewPanel.currentItem.isImage && previewPanel.imageDataUrl === ""
    repeat: previewPanel.currentItem && previewPanel.currentItem.isImage && previewPanel.imageDataUrl === ""

    onTriggered: {
      if (previewPanel.currentItem && previewPanel.currentItem.clipboardId) {
        const newData = ClipboardService.getImageData(previewPanel.currentItem.clipboardId) || "";
        if (newData !== previewPanel.imageDataUrl) {
          previewPanel.imageDataUrl = newData;
          if (newData) {
            previewPanel.loadingFullContent = false;
          }
        }
      }
    }
  }

  Rectangle {
    anchors.fill: parent
    color: NColor.mSurface || "#f5f5f5"
    border.color: NColor.mOutline
    border.width: 1
    radius: Style.radiusM

    ColumnLayout {
      id: contentColumn
      anchors.fill: parent
      anchors.margins: Style.marginS
      spacing: Style.marginS

      Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: NColor.mSurfaceVariant || "#e0e0e0"
        border.color: NColor.mOutline || "#aaaaaa"
        border.width: 1
        radius: Style.radiusS

        BusyIndicator {
          anchors.centerIn: parent
          running: previewPanel.loadingFullContent
          visible: previewPanel.loadingFullContent
          width: Style.baseWidgetSize
          height: width
        }

        Item {
          anchors.fill: parent
          anchors.margins: Style.marginS

          NImageRounded {
            anchors.fill: parent
            imagePath: previewPanel.imageDataUrl
            visible: previewPanel.isImageContent && !previewPanel.loadingFullContent && previewPanel.imageDataUrl !== ""
            radius: Style.radiusS
            imageFillMode: Image.PreserveAspectFit
          }

          ScrollView {
            anchors.fill: parent
            clip: true
            visible: !previewPanel.isImageContent && !previewPanel.loadingFullContent

            TextArea {
              text: previewPanel.fullContent
              readOnly: true
              wrapMode: Text.Wrap
              textFormat: TextArea.RichText // Enable HTML rendering
              font.pointSize: Style.fontSizeM // Adjust font size for readability
              color: NColor.mOnSurface // Consistent text color
            }
          }
        }
      }
    }
  }
}
