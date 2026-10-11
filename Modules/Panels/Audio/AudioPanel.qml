import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.Pipewire
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.Media
import qs.Widgets

SmartPanel {
  id: root

  property real localOutputVolume: AudioService.volume || 0
  property bool localOutputVolumeChanging: false
  property int lastSinkId: -1

  property real localInputVolume: AudioService.inputVolume || 0
  property bool localInputVolumeChanging: false
  property int lastSourceId: -1

  Component.onCompleted: {
    if (AudioService.sink) {
      root.lastSinkId = AudioService.sink.id;
    }
  }

  preferredWidth: Math.round(340 * Style.uiScaleRatio)
  preferredHeight: Math.round(420 * Style.uiScaleRatio)

  // Reset local volume when device changes - use current device's volume
  Connections {
    target: AudioService
    function onSinkChanged() {
      if (AudioService.sink) {
        const newSinkId = AudioService.sink.id;
        if (newSinkId !== root.lastSinkId) {
          root.lastSinkId = newSinkId;
          // Immediately set local volume to current device's volume
          root.localOutputVolume = AudioService.volume;
        }
      } else {
        root.lastSinkId = -1;
        root.localOutputVolume = 0;
      }
    }
  }

  Connections {
    target: AudioService
    function onSourceChanged() {
      if (AudioService.source) {
        const newSourceId = AudioService.source.id;
        if (newSourceId !== root.lastSourceId) {
          root.lastSourceId = newSourceId;
          // Immediately set local volume to current device's volume
          root.localInputVolume = AudioService.inputVolume;
        }
      } else {
        root.lastSourceId = -1;
        root.localInputVolume = 0;
      }
    }
  }

  // Connections to update local volumes when AudioService changes
  Connections {
    target: AudioService
    function onVolumeChanged() {
      if (!root.localOutputVolumeChanging && AudioService.sink && AudioService.sink.id === root.lastSinkId) {
        root.localOutputVolume = AudioService.volume;
      }
    }
  }

  Connections {
    target: AudioService.sink && AudioService.sink.audio ? AudioService.sink.audio : null
    function onVolumeChanged() {
      if (!root.localOutputVolumeChanging && AudioService.sink && AudioService.sink.id === root.lastSinkId) {
        root.localOutputVolume = AudioService.volume;
      }
    }
  }

  Connections {
    target: AudioService
    function onInputVolumeChanged() {
      if (!root.localInputVolumeChanging && AudioService.source && AudioService.source.id === root.lastSourceId) {
        root.localInputVolume = AudioService.inputVolume;
      }
    }
  }

  Connections {
    target: AudioService.source && AudioService.source.audio ? AudioService.source.audio : null
    function onVolumeChanged() {
      if (!root.localInputVolumeChanging && AudioService.source && AudioService.source.id === root.lastSourceId) {
        root.localInputVolume = AudioService.inputVolume;
      }
    }
  }

  Timer {
    id: volumeSyncTimer
    interval: 100
    running: false
    repeat: false
    onTriggered: root.syncPendingVolumeChanges()
  }

  function scheduleVolumeSync() {
    volumeSyncTimer.restart();
  }

  function syncPendingVolumeChanges() {
    if (AudioService.sink && AudioService.sink.id === root.lastSinkId) {
      if (Math.abs(root.localOutputVolume - AudioService.volume) >= 0.01) {
        AudioService.setVolume(root.localOutputVolume);
      }
    }

    if (AudioService.source && AudioService.source.id === root.lastSourceId) {
      if (Math.abs(root.localInputVolume - AudioService.inputVolume) >= 0.01) {
        AudioService.setInputVolume(root.localInputVolume);
      }
    }
  }

  panelContent: Item {
    // Use implicitHeight from content + margins to avoid binding loops
    property real contentPreferredHeight: mainColumn.implicitHeight + Style.marginL * 2

    // property real contentPreferredHeight: Math.min(screen.height * 0.42, mainColumn.implicitHeight) + Style.marginL * 2
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
            icon: "settings-audio"
            pointSize: Style.fontSizeXXL
            color: NColor.mPrimary
          }

          NText {
            text: I18n.tr("settings.audio.title")
            pointSize: Style.fontSizeL
            font.weight: Style.fontWeightBold
            color: NColor.mOnSurface
            Layout.fillWidth: true
          }

          NIconButton {
            icon: AudioService.getOutputIcon()
            tooltipText: I18n.tr("tooltips.output-muted")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: {
              AudioService.suppressOutputOSD();
              AudioService.setOutputMuted(!AudioService.muted);
            }
          }

          NIconButton {
            icon: AudioService.getInputIcon()
            tooltipText: I18n.tr("tooltips.input-muted")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: {
              AudioService.suppressInputOSD();
              AudioService.setInputMuted(!AudioService.inputMuted);
            }
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

          // -------------------------------
          // Output Devices
          ButtonGroup {
            id: sinks
          }

          NBox {
            Layout.fillWidth: true
            Layout.preferredHeight: outputColumn.implicitHeight + (Style.marginM * 2)

            ColumnLayout {
              id: outputColumn
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.top: parent.top
              anchors.margins: Style.marginM
              spacing: Style.marginS

              NText {
                text: I18n.tr("settings.audio.devices.output-device.label")
                pointSize: Style.fontSizeL
                color: NColor.mPrimary
              }

              // Output Volume Slider
              NValueSlider {
                Layout.fillWidth: true
                from: 0
                to: Settings.data.audio.volumeOverdrive ? 1.5 : 1.0
                value: root.localOutputVolume
                stepSize: 0.01
                heightRatio: 0.5
                onMoved: value => {
                  root.localOutputVolume = value;
                  root.scheduleVolumeSync();
                }
                onPressedChanged: (pressed, value) => {
                  root.localOutputVolumeChanging = pressed;
                  if (!pressed) {
                    root.scheduleVolumeSync();
                  }
                }
                text: Math.round(root.localOutputVolume * 100) + "%"
                Layout.bottomMargin: Style.marginM
              }

              Repeater {
                model: AudioService.sinks
                NRadioButton {
                  ButtonGroup.group: sinks
                  required property PwNode modelData
                  required property int index

                  readonly property string deviceId: modelData ? (modelData.id || "") : ""
                  readonly property string deviceDescription: modelData ? (modelData.description || deviceId) : deviceId

                  pointSize: Style.fontSizeS
                  text: deviceDescription
                  checked: AudioService.sink ? String(AudioService.sink.id) === deviceId : false
                  onClicked: {
                    AudioService.setAudioSink(modelData);
                    root.localOutputVolume = AudioService.volume;
                  }
                  Layout.fillWidth: true
                }
              }
            }
          }

          // -------------------------------
          // Input Devices
          ButtonGroup {
            id: sources
          }

          NBox {
            Layout.fillWidth: true
            Layout.preferredHeight: inputColumn.implicitHeight + (Style.marginM * 2)

            ColumnLayout {
              id: inputColumn
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.top: parent.top
              anchors.bottom: parent.bottom
              anchors.margins: Style.marginM
              spacing: Style.marginS

              NText {
                text: I18n.tr("settings.audio.devices.input-device.label")
                pointSize: Style.fontSizeL
                color: NColor.mPrimary
              }

              // Input Volume Slider
              NValueSlider {
                Layout.fillWidth: true
                from: 0
                to: Settings.data.audio.volumeOverdrive ? 1.5 : 1.0
                value: root.localInputVolume
                stepSize: 0.01
                heightRatio: 0.5
                onMoved: value => {
                  root.localInputVolume = value;
                  root.scheduleVolumeSync();
                }
                onPressedChanged: (pressed, value) => {
                  root.localInputVolumeChanging = pressed;
                  if (!pressed) {
                    root.scheduleVolumeSync();
                  }
                }
                text: Math.round(root.localInputVolume * 100) + "%"
                Layout.bottomMargin: Style.marginM
              }

              Repeater {
                model: AudioService.sources
                NRadioButton {
                  ButtonGroup.group: sources
                  required property PwNode modelData
                  required property int index

                  readonly property string deviceId: modelData ? (modelData.id || "") : ""
                  readonly property string deviceDescription: modelData ? (modelData.description || deviceId) : deviceId

                  pointSize: Style.fontSizeS
                  text: deviceDescription
                  checked: AudioService.source ? AudioService.source.id === deviceId : false
                  onClicked: AudioService.setAudioSource(modelData)
                  Layout.fillWidth: true
                }
              }
            }
          }
        }
      }
    }
  }
}
