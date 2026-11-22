pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Widgets
import qs.Commons

Item {
  id: root

  property real radius: 0
  property string imagePath: ""
  property string fallbackIcon: ""
  property real fallbackIconSize: Style.fontSizeXXL
  property real borderWidth: 0
  property color borderColor: NColor.transparent
  property int imageFillMode: Image.PreserveAspectCrop

  readonly property bool showFallback: (fallbackIcon !== undefined && fallbackIcon !== "") && (imagePath === undefined || imagePath === "")
  readonly property bool isSoftwareBackend: root.GraphicsInfo.api === GraphicsInfo.Software

  signal statusChanged(int status)

  function shouldLoadImage() {
    if (!visible || showFallback) {
      return false;
    }
    return imagePath !== "" && width > 0 && height > 0;
  }

  function targetDecodeSize() {
    const scale = Screen.devicePixelRatio || 1;
    return {
      "width": Math.ceil(width * scale),
      "height": Math.ceil(height * scale)
    };
  }

  Rectangle {
    anchors.fill: parent
    radius: root.radius
    color: NColor.transparent
    border.width: root.borderWidth
    border.color: root.borderColor

    Image {
      id: imageSource
      anchors.fill: parent
      anchors.margins: root.borderWidth
      visible: false
      source: root.shouldLoadImage() ? root.imagePath : ""
      sourceSize.width: root.shouldLoadImage() ? root.targetDecodeSize().width : 0
      sourceSize.height: root.shouldLoadImage() ? root.targetDecodeSize().height : 0
      mipmap: false
      smooth: true
      asynchronous: true
      antialiasing: true
      fillMode: root.imageFillMode
      onStatusChanged: root.statusChanged(status)
    }

    Loader {
      anchors.fill: parent
      anchors.margins: root.borderWidth
      active: root.shouldLoadImage()
      sourceComponent: roundedShaderComponent
    }

    Loader {
      id: softwareRoundedLoader
      anchors.fill: parent
      anchors.margins: root.borderWidth
      active: root.isSoftwareBackend && root.shouldLoadImage()
      sourceComponent: softwareRoundedComponent
    }

    Component {
      id: roundedShaderComponent

      ShaderEffect {
        visible: !root.showFallback
        property variant source: imageSource
        property real itemWidth: width
        property real itemHeight: height
        property real sourceWidth: imageSource.sourceSize.width
        property real sourceHeight: imageSource.sourceSize.height
        property real cornerRadius: Math.max(0, root.radius - root.borderWidth)
        property real imageOpacity: 1.0
        property int fillMode: root.imageFillMode

        fragmentShader: Qt.resolvedUrl(Quickshell.shellDir + "/Shaders/qsb/rounded_image.frag.qsb")
        supportsAtlasTextures: false
        blending: true
      }
    }

    Component {
      id: softwareRoundedComponent

      Canvas {
        id: roundedCanvas
        visible: !root.showFallback
        antialiasing: true

        property string activeUrl: ""
        readonly property string requestedUrl: imageSource.source.toString()
        readonly property real cornerRadius: Math.max(0, root.radius - root.borderWidth)
        readonly property int fillMode: root.imageFillMode

        function syncImageUrl() {
          if (roundedCanvas.activeUrl === roundedCanvas.requestedUrl) {
            return;
          }
          if (roundedCanvas.activeUrl !== "") {
            roundedCanvas.unloadImage(roundedCanvas.activeUrl);
          }
          roundedCanvas.activeUrl = roundedCanvas.requestedUrl;
          if (roundedCanvas.activeUrl !== "") {
            roundedCanvas.loadImage(roundedCanvas.activeUrl);
          }
          roundedCanvas.requestPaint();
        }

        Component.onCompleted: roundedCanvas.syncImageUrl()
        Component.onDestruction: {
          if (roundedCanvas.activeUrl !== "") {
            roundedCanvas.unloadImage(roundedCanvas.activeUrl);
            roundedCanvas.activeUrl = "";
          }
        }
        onRequestedUrlChanged: roundedCanvas.syncImageUrl()
        onImageLoaded: roundedCanvas.requestPaint()
        onWidthChanged: roundedCanvas.requestPaint()
        onHeightChanged: roundedCanvas.requestPaint()
        onCornerRadiusChanged: roundedCanvas.requestPaint()
        onFillModeChanged: roundedCanvas.requestPaint()

        onPaint: {
          const ctx = roundedCanvas.getContext("2d");
          ctx.reset();
          const url = roundedCanvas.activeUrl;
          if (url === "" || !roundedCanvas.isImageLoaded(url) || roundedCanvas.width <= 0 || roundedCanvas.height <= 0) {
            return;
          }

          const r = Math.min(roundedCanvas.cornerRadius, roundedCanvas.width / 2, roundedCanvas.height / 2);
          ctx.beginPath();
          ctx.roundedRect(0, 0, roundedCanvas.width, roundedCanvas.height, r, r);
          ctx.clip();

          let dx = 0;
          let dy = 0;
          let dw = roundedCanvas.width;
          let dh = roundedCanvas.height;
          const sw = imageSource.implicitWidth;
          const sh = imageSource.implicitHeight;
          if (sw > 0 && sh > 0 && (roundedCanvas.fillMode === Image.PreserveAspectCrop || roundedCanvas.fillMode === Image.PreserveAspectFit)) {
            const itemAspect = roundedCanvas.width / roundedCanvas.height;
            const sourceAspect = sw / sh;
            const fitWidth = roundedCanvas.fillMode === Image.PreserveAspectCrop ? (sourceAspect < itemAspect) : (sourceAspect > itemAspect);
            if (fitWidth) {
              dh = roundedCanvas.width / sourceAspect;
              dy = (roundedCanvas.height - dh) / 2;
            } else {
              dw = roundedCanvas.height * sourceAspect;
              dx = (roundedCanvas.width - dw) / 2;
            }
          }
          ctx.drawImage(url, dx, dy, dw, dh);
        }
      }
    }

    NIcon {
      anchors.fill: parent
      anchors.margins: root.borderWidth
      visible: root.showFallback
      icon: root.fallbackIcon
      pointSize: root.fallbackIconSize
    }
  }
}
