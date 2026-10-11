pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.Compositor
import qs.Services.Hardware
import qs.Widgets

SmartPanel {
  id: root

  preferredWidth: Math.round(340 * Style.uiScaleRatio)
  preferredHeight: Math.round(420 * Style.uiScaleRatio)

  function getIcon(brightness) {
    return brightness <= 0.5 ? "brightness-low" : "brightness-high";
  }

  panelContent: Item {
    property real contentPreferredHeight: mainColumn.implicitHeight + Style.marginL * 2

    ColumnLayout {
      id: mainColumn
      anchors.fill: parent
      anchors.margins: Style.marginL
      spacing: Style.marginM

      // HEADER
      NBox {
        Layout.fillWidth: true
        implicitHeight: headerRow.implicitHeight + (Style.marginM * 2)

        RowLayout {
          id: headerRow
          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginM

          NIcon {
            icon: "settings-display"
            pointSize: Style.fontSizeXXL
            color: NColor.mPrimary
          }

          NText {
            text: I18n.tr("settings.display.title")
            pointSize: Style.fontSizeL
            font.weight: Style.fontWeightBold
            color: NColor.mOnSurface
            Layout.fillWidth: true
          }

          NIconButton {
            icon: "close"
            tooltipText: I18n.tr("tooltips.close")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: {
              root.close();
            }
          }
        }
      }

      NScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        horizontalPolicy: ScrollBar.AlwaysOff
        verticalPolicy: ScrollBar.AsNeeded
        clip: true
        contentWidth: availableWidth

        // AudioService Devices
        ColumnLayout {
          spacing: Style.marginM
          width: parent.width

          Repeater {
            model: Quickshell.screens || []
            delegate: NBox {
              id: monitorBox
              required property ShellScreen modelData
              readonly property string monitorName: modelData ? modelData.name : ""
              readonly property string monitorModel: modelData ? modelData.model : ""
              readonly property int monitorWidth: modelData ? modelData.width : 0
              readonly property int monitorHeight: modelData ? modelData.height : 0

              Layout.fillWidth: true
              Layout.preferredHeight: outputColumn.implicitHeight + (Style.marginM * 2)

              property QtObject brightnessMonitor: BrightnessService.getMonitorForScreen(modelData)

              ColumnLayout {
                id: outputColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.marginM
                spacing: Style.marginS

                NLabel {
                  label: monitorBox.monitorName || "Unknown"
                  labelColor: NColor.mPrimary
                  description: {
                    const compositorScale = CompositorService.getDisplayScale(monitorBox.monitorName);
                    I18n.tr("system.monitor-description", {
                      "model": monitorBox.monitorModel,
                      "width": monitorBox.monitorWidth * compositorScale,
                      "height": monitorBox.monitorHeight * compositorScale,
                      "scale": compositorScale
                    });
                  }
                }

                RowLayout {

                  Layout.fillWidth: true
                  spacing: Style.marginS
                  NIcon {
                    icon: root.getIcon(monitorBox.brightnessMonitor ? monitorBox.brightnessMonitor.brightness : 0)
                    pointSize: Style.fontSizeXL
                    color: NColor.mOnSurface
                  }

                  NValueSlider {
                    id: brightnessSlider
                    from: 0
                    to: 1
                    value: monitorBox.brightnessMonitor ? monitorBox.brightnessMonitor.brightness : 0.5
                    stepSize: 0.01
                    enabled: monitorBox.brightnessMonitor ? monitorBox.brightnessMonitor.brightnessControlAvailable : false
                    onMoved: value => {
                      if (monitorBox.brightnessMonitor && monitorBox.brightnessMonitor.brightnessControlAvailable) {
                        monitorBox.brightnessMonitor.setBrightness(value);
                      }
                    }
                    onPressedChanged: (pressed, value) => {
                      if (monitorBox.brightnessMonitor && monitorBox.brightnessMonitor.brightnessControlAvailable) {
                        monitorBox.brightnessMonitor.setBrightness(value);
                      }
                    }
                    Layout.fillWidth: true
                    text: monitorBox.brightnessMonitor ? Math.round(brightnessSlider.value * 100) + "%" : "N/A"
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
