import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import qs.Commons
import qs.Services.Hardware
import qs.Widgets

ColumnLayout {
  id: root
  spacing: Style.marginL

  // Battery device (using UPower displayDevice)
  readonly property UPowerDevice battery: UPower.displayDevice
  readonly property bool isReady: root.battery && root.battery.ready && root.battery.percentage !== undefined
  readonly property int percent: root.isReady ? Math.round(root.battery.percentage * 100) : -1
  readonly property bool charging: root.isReady ? root.battery.state === UPowerDeviceState.Charging : false
  readonly property bool healthAvailable: root.isReady && root.battery.healthSupported
  readonly property int healthPercent: root.healthAvailable ? Math.round(root.battery.healthPercentage) : -1

  // Charge threshold values read from sysfs
  property int chargeStartThreshold: 0
  property int chargeStopThreshold: 100
  property bool thresholdsSupported: false
  property bool thresholdsLoading: true

  // Cycle count
  property int cycleCount: -1
  property bool cycleCountSupported: false

  // Local values for sliders (to avoid writing on every drag)
  property int localStartThreshold: root.chargeStartThreshold
  property int localStopThreshold: root.chargeStopThreshold

  Component.onCompleted: {
    startThresholdReader.reload();
    stopThresholdReader.reload();
    cycleCountReader.reload();
  }

  // Read charge_control_start_threshold
  FileView {
    id: startThresholdReader
    path: "/sys/class/power_supply/BAT0/charge_control_start_threshold"
    printErrors: false

    onLoaded: {
      const val = parseInt(startThresholdReader.text().trim());
      if (!isNaN(val)) {
        root.chargeStartThreshold = val;
        root.localStartThreshold = val;
        root.thresholdsSupported = true;
      }
      root.thresholdsLoading = false;
    }

    onLoadFailed: {
      root.thresholdsLoading = false;
    }
  }

  // Read charge_control_end_threshold
  FileView {
    id: stopThresholdReader
    path: "/sys/class/power_supply/BAT0/charge_control_end_threshold"
    printErrors: false

    onLoaded: {
      const val = parseInt(stopThresholdReader.text().trim());
      if (!isNaN(val)) {
        root.chargeStopThreshold = val;
        root.localStopThreshold = val;
        root.thresholdsSupported = true;
      }
    }
  }

  // Read cycle_count
  FileView {
    id: cycleCountReader
    path: "/sys/class/power_supply/BAT0/cycle_count"
    printErrors: false

    onLoaded: {
      const val = parseInt(cycleCountReader.text().trim());
      if (!isNaN(val) && val >= 0) {
        root.cycleCount = val;
        root.cycleCountSupported = true;
      }
    }
  }

  // Process to write thresholds (requires root via pkexec)
  Process {
    id: writeThresholdProcess
    property string thresholdType: ""
    property int thresholdValue: 0

    command: ["pkexec", "bash", "-c", `echo ${writeThresholdProcess.thresholdValue} > /sys/class/power_supply/BAT0/charge_control_${writeThresholdProcess.thresholdType}_threshold`]
    running: false

    onExited: exitCode => {
      if (exitCode === 0) {
        Logger.i("BatteryTab", `Set charge ${writeThresholdProcess.thresholdType} threshold to ${writeThresholdProcess.thresholdValue}`);
        // Reload to confirm
        if (writeThresholdProcess.thresholdType === "start") {
          startThresholdReader.reload();
        } else {
          stopThresholdReader.reload();
        }
      } else {
        Logger.w("BatteryTab", `Failed to set charge ${writeThresholdProcess.thresholdType} threshold, exit code: ${exitCode}`);
      }
    }
  }

  function setStartThreshold(value) {
    writeThresholdProcess.thresholdType = "start";
    writeThresholdProcess.thresholdValue = value;
    writeThresholdProcess.running = true;
  }

  function setStopThreshold(value) {
    writeThresholdProcess.thresholdType = "end";
    writeThresholdProcess.thresholdValue = value;
    writeThresholdProcess.running = true;
  }

  // ============================================
  // Battery Status Section
  // ============================================
  NHeader {
    label: I18n.tr("settings.battery.status.section.label")
    description: I18n.tr("settings.battery.status.section.description")
  }

  // Status box
  NBox {
    Layout.fillWidth: true
    implicitHeight: statusLayout.implicitHeight + Style.marginL * 2
    visible: root.isReady

    ColumnLayout {
      id: statusLayout
      anchors.fill: parent
      anchors.margins: Style.marginL
      spacing: Style.marginM

      // Battery level with progress bar
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        NIcon {
          icon: BatteryService.getIcon(root.percent, root.charging, root.isReady)
          pointSize: Style.fontSizeXXL
          color: root.charging ? NColor.mPrimary : NColor.mOnSurface
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.marginXS

          RowLayout {
            Layout.fillWidth: true

            NText {
              text: I18n.tr("battery.battery-level")
              color: NColor.mOnSurface
              pointSize: Style.fontSizeM
            }

            Item {
              Layout.fillWidth: true
            }

            NText {
              text: root.percent >= 0 ? `${root.percent}%` : "--"
              color: NColor.mOnSurface
              pointSize: Style.fontSizeM
              font.weight: Style.fontWeightBold
            }
          }

          Rectangle {
            id: progressTrack
            Layout.fillWidth: true
            Layout.preferredHeight: Math.round(8 * Style.uiScaleRatio)
            radius: Math.min(Style.radiusL, progressTrack.height / 2)
            color: NColor.mSurfaceVariant

            Rectangle {
              anchors.verticalCenter: parent.verticalCenter
              height: parent.height
              radius: parent.radius
              width: parent.width * Math.max(0, Math.min(1, root.percent / 100))
              color: root.charging ? NColor.mPrimary : (root.percent <= 20 ? NColor.mError : NColor.mSecondary)

              Behavior on width {
                NumberAnimation {
                  duration: Style.animationNormal
                }
              }
            }
          }
        }
      }

      // Status details grid
      GridLayout {
        Layout.fillWidth: true
        columns: 2
        rowSpacing: Style.marginS
        columnSpacing: Style.marginL

        // Status
        NText {
          text: I18n.tr("settings.battery.status.state")
          color: NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeS
        }
        NText {
          text: root.charging ? I18n.tr("battery.charging") : (root.battery.state === UPowerDeviceState.FullyCharged ? I18n.tr("battery.plugged-in") : I18n.tr("battery.discharging"))
          color: NColor.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
        }

        // Time remaining
        NText {
          text: I18n.tr("settings.battery.status.time-remaining")
          color: NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: (root.charging && root.battery.timeToFull > 0) || (!root.charging && root.battery.timeToEmpty > 0)
        }
        NText {
          text: {
            if (root.charging && root.battery.timeToFull > 0) {
              return Time.formatVagueHumanReadableDuration(root.battery.timeToFull);
            } else if (!root.charging && root.battery.timeToEmpty > 0) {
              return Time.formatVagueHumanReadableDuration(root.battery.timeToEmpty);
            }
            return "";
          }
          color: NColor.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: (root.charging && root.battery.timeToFull > 0) || (!root.charging && root.battery.timeToEmpty > 0)
        }

        // Health (if available)
        NText {
          text: I18n.tr("settings.battery.status.health")
          color: NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: root.healthAvailable
        }
        NText {
          text: root.healthPercent >= 0 ? `${root.healthPercent}%` : "--"
          color: root.healthPercent >= 80 ? NColor.mOnSurface : (root.healthPercent >= 50 ? NColor.mTertiary : NColor.mError)
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: root.healthAvailable
        }

        // Energy rate (power consumption)
        NText {
          text: I18n.tr("settings.battery.status.power")
          color: NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: Math.abs(root.battery.changeRate) > 0
        }
        NText {
          text: `${Math.abs(root.battery.changeRate).toFixed(1)} W`
          color: NColor.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: Math.abs(root.battery.changeRate) > 0
        }

        // Cycle count
        NText {
          text: I18n.tr("settings.battery.status.cycles")
          color: NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: root.cycleCountSupported
        }
        NText {
          text: root.cycleCount >= 0 ? root.cycleCount.toString() : "--"
          color: NColor.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: root.cycleCountSupported
        }
      }
    }
  }

  // No battery message
  NBox {
    Layout.fillWidth: true
    implicitHeight: noBatteryText.implicitHeight + Style.marginL * 2
    visible: !root.isReady

    NText {
      id: noBatteryText
      anchors.centerIn: parent
      text: I18n.tr("battery.no-battery-detected")
      color: NColor.mOnSurfaceVariant
      pointSize: Style.fontSizeM
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
    visible: root.thresholdsSupported
  }

  // ============================================
  // Charge Thresholds Section
  // ============================================
  NHeader {
    label: I18n.tr("settings.battery.thresholds.section.label")
    description: I18n.tr("settings.battery.thresholds.section.description")
    visible: root.thresholdsSupported
  }

  // Info box about thresholds
  NBox {
    Layout.fillWidth: true
    implicitHeight: thresholdInfoLayout.implicitHeight + Style.marginM * 2
    visible: root.thresholdsSupported

    RowLayout {
      id: thresholdInfoLayout
      anchors.fill: parent
      anchors.margins: Style.marginM
      spacing: Style.marginM

      NIcon {
        icon: "info-circle"
        pointSize: Style.fontSizeL
        color: NColor.mPrimary
      }

      NText {
        text: I18n.tr("settings.battery.thresholds.info")
        color: NColor.mOnSurfaceVariant
        pointSize: Style.fontSizeS
        wrapMode: Text.Wrap
        Layout.fillWidth: true
      }
    }
  }

  // Start threshold slider
  ColumnLayout {
    spacing: Style.marginXS
    Layout.fillWidth: true
    visible: root.thresholdsSupported

    NLabel {
      label: I18n.tr("settings.battery.thresholds.start.label")
      description: I18n.tr("settings.battery.thresholds.start.description")
    }

    NValueSlider {
      Layout.fillWidth: true
      from: 0
      to: 100
      value: root.localStartThreshold
      stepSize: 5
      text: `${root.localStartThreshold}%`
      onMoved: value => {
        // Ensure start < stop
        if (value >= root.localStopThreshold) {
          root.localStartThreshold = root.localStopThreshold - 5;
        } else {
          root.localStartThreshold = value;
        }
      }
      onPressedChanged: pressed => {
        if (!pressed && root.localStartThreshold !== root.chargeStartThreshold) {
          root.setStartThreshold(root.localStartThreshold);
        }
      }
    }
  }

  // Stop threshold slider
  ColumnLayout {
    spacing: Style.marginXS
    Layout.fillWidth: true
    visible: root.thresholdsSupported

    NLabel {
      label: I18n.tr("settings.battery.thresholds.stop.label")
      description: I18n.tr("settings.battery.thresholds.stop.description")
    }

    NValueSlider {
      Layout.fillWidth: true
      from: 0
      to: 100
      value: root.localStopThreshold
      stepSize: 5
      text: `${root.localStopThreshold}%`
      onMoved: value => {
        // Ensure stop > start
        if (value <= root.localStartThreshold) {
          root.localStopThreshold = root.localStartThreshold + 5;
        } else {
          root.localStopThreshold = value;
        }
      }
      onPressedChanged: pressed => {
        if (!pressed && root.localStopThreshold !== root.chargeStopThreshold) {
          root.setStopThreshold(root.localStopThreshold);
        }
      }
    }
  }

  // Current thresholds display
  NBox {
    Layout.fillWidth: true
    implicitHeight: currentThresholdsRow.implicitHeight + Style.marginM * 2
    visible: root.thresholdsSupported

    RowLayout {
      id: currentThresholdsRow
      anchors.fill: parent
      anchors.margins: Style.marginM
      spacing: Style.marginL

      NText {
        text: I18n.tr("settings.battery.thresholds.current")
        color: NColor.mOnSurfaceVariant
        pointSize: Style.fontSizeS
      }

      Item {
        Layout.fillWidth: true
      }

      NText {
        text: `${root.chargeStartThreshold}% - ${root.chargeStopThreshold}%`
        color: NColor.mOnSurface
        pointSize: Style.fontSizeM
        font.weight: Style.fontWeightBold
      }
    }
  }

  // Thresholds not supported message
  NBox {
    Layout.fillWidth: true
    implicitHeight: notSupportedText.implicitHeight + Style.marginL * 2
    visible: !root.thresholdsSupported && !root.thresholdsLoading

    NText {
      id: notSupportedText
      anchors.centerIn: parent
      text: I18n.tr("settings.battery.thresholds.not-supported")
      color: NColor.mOnSurfaceVariant
      pointSize: Style.fontSizeM
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
  }
}
