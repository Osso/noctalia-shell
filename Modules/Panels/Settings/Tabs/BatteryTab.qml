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
  readonly property var battery: UPower.displayDevice
  readonly property bool isReady: battery && battery.ready && battery.percentage !== undefined
  readonly property int percent: isReady ? Math.round(battery.percentage * 100) : -1
  readonly property bool charging: isReady ? battery.state === UPowerDeviceState.Charging : false
  readonly property bool healthAvailable: isReady && battery.healthSupported
  readonly property int healthPercent: healthAvailable ? Math.round(battery.healthPercentage) : -1

  // Charge threshold values read from sysfs
  property int chargeStartThreshold: 0
  property int chargeStopThreshold: 100
  property bool thresholdsSupported: false
  property bool thresholdsLoading: true

  // Cycle count
  property int cycleCount: -1
  property bool cycleCountSupported: false

  // Local values for sliders (to avoid writing on every drag)
  property int localStartThreshold: chargeStartThreshold
  property int localStopThreshold: chargeStopThreshold

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
      const val = parseInt(text().trim());
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
      const val = parseInt(text().trim());
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
      const val = parseInt(text().trim());
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

    command: ["pkexec", "bash", "-c",
      `echo ${thresholdValue} > /sys/class/power_supply/BAT0/charge_control_${thresholdType}_threshold`]
    running: false

    onExited: exitCode => {
      if (exitCode === 0) {
        Logger.i("BatteryTab", `Set charge ${thresholdType} threshold to ${thresholdValue}`);
        // Reload to confirm
        if (thresholdType === "start") {
          startThresholdReader.reload();
        } else {
          stopThresholdReader.reload();
        }
      } else {
        Logger.w("BatteryTab", `Failed to set charge ${thresholdType} threshold, exit code: ${exitCode}`);
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
    visible: isReady

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
          icon: BatteryService.getIcon(percent, charging, isReady)
          pointSize: Style.fontSizeXXL
          color: charging ? Color.mPrimary : Color.mOnSurface
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.marginXS

          RowLayout {
            Layout.fillWidth: true

            NText {
              text: I18n.tr("battery.battery-level")
              color: Color.mOnSurface
              pointSize: Style.fontSizeM
            }

            Item { Layout.fillWidth: true }

            NText {
              text: percent >= 0 ? `${percent}%` : "--"
              color: Color.mOnSurface
              pointSize: Style.fontSizeM
              font.weight: Style.fontWeightBold
            }
          }

          Rectangle {
            Layout.fillWidth: true
            height: Math.round(8 * Style.uiScaleRatio)
            radius: Math.min(Style.radiusL, height / 2)
            color: Color.mSurfaceVariant

            Rectangle {
              anchors.verticalCenter: parent.verticalCenter
              height: parent.height
              radius: parent.radius
              width: parent.width * Math.max(0, Math.min(1, percent / 100))
              color: charging ? Color.mPrimary : (percent <= 20 ? Color.mError : Color.mSecondary)

              Behavior on width {
                NumberAnimation { duration: Style.animationMedium }
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
          color: Color.mOnSurfaceVariant
          pointSize: Style.fontSizeS
        }
        NText {
          text: charging ? I18n.tr("battery.charging") :
                (battery.state === UPowerDeviceState.FullyCharged ? I18n.tr("battery.plugged-in") :
                I18n.tr("battery.discharging"))
          color: Color.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
        }

        // Time remaining
        NText {
          text: I18n.tr("settings.battery.status.time-remaining")
          color: Color.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: (charging && battery.timeToFull > 0) || (!charging && battery.timeToEmpty > 0)
        }
        NText {
          text: {
            if (charging && battery.timeToFull > 0) {
              return Time.formatVagueHumanReadableDuration(battery.timeToFull);
            } else if (!charging && battery.timeToEmpty > 0) {
              return Time.formatVagueHumanReadableDuration(battery.timeToEmpty);
            }
            return "";
          }
          color: Color.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: (charging && battery.timeToFull > 0) || (!charging && battery.timeToEmpty > 0)
        }

        // Health (if available)
        NText {
          text: I18n.tr("settings.battery.status.health")
          color: Color.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: healthAvailable
        }
        NText {
          text: healthPercent >= 0 ? `${healthPercent}%` : "--"
          color: healthPercent >= 80 ? Color.mOnSurface :
                 (healthPercent >= 50 ? Color.mWarning : Color.mError)
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: healthAvailable
        }

        // Energy rate (power consumption)
        NText {
          text: I18n.tr("settings.battery.status.power")
          color: Color.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: battery.energyRate !== undefined && battery.energyRate > 0
        }
        NText {
          text: battery.energyRate !== undefined ? `${battery.energyRate.toFixed(1)} W` : "--"
          color: Color.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: battery.energyRate !== undefined && battery.energyRate > 0
        }

        // Cycle count
        NText {
          text: I18n.tr("settings.battery.status.cycles")
          color: Color.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          visible: cycleCountSupported
        }
        NText {
          text: cycleCount >= 0 ? cycleCount.toString() : "--"
          color: Color.mOnSurface
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightMedium
          visible: cycleCountSupported
        }
      }
    }
  }

  // No battery message
  NBox {
    Layout.fillWidth: true
    implicitHeight: noBatteryText.implicitHeight + Style.marginL * 2
    visible: !isReady

    NText {
      id: noBatteryText
      anchors.centerIn: parent
      text: I18n.tr("battery.no-battery-detected")
      color: Color.mOnSurfaceVariant
      pointSize: Style.fontSizeM
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
    visible: thresholdsSupported
  }

  // ============================================
  // Charge Thresholds Section
  // ============================================
  NHeader {
    label: I18n.tr("settings.battery.thresholds.section.label")
    description: I18n.tr("settings.battery.thresholds.section.description")
    visible: thresholdsSupported
  }

  // Info box about thresholds
  NBox {
    Layout.fillWidth: true
    implicitHeight: thresholdInfoLayout.implicitHeight + Style.marginM * 2
    visible: thresholdsSupported

    RowLayout {
      id: thresholdInfoLayout
      anchors.fill: parent
      anchors.margins: Style.marginM
      spacing: Style.marginM

      NIcon {
        icon: "info-circle"
        pointSize: Style.fontSizeL
        color: Color.mPrimary
      }

      NText {
        text: I18n.tr("settings.battery.thresholds.info")
        color: Color.mOnSurfaceVariant
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
    visible: thresholdsSupported

    NLabel {
      label: I18n.tr("settings.battery.thresholds.start.label")
      description: I18n.tr("settings.battery.thresholds.start.description")
    }

    NValueSlider {
      Layout.fillWidth: true
      from: 0
      to: 100
      value: localStartThreshold
      stepSize: 5
      text: `${localStartThreshold}%`
      onMoved: value => {
        // Ensure start < stop
        if (value >= localStopThreshold) {
          localStartThreshold = localStopThreshold - 5;
        } else {
          localStartThreshold = value;
        }
      }
      onPressedChanged: {
        if (!pressed && localStartThreshold !== chargeStartThreshold) {
          setStartThreshold(localStartThreshold);
        }
      }
    }
  }

  // Stop threshold slider
  ColumnLayout {
    spacing: Style.marginXS
    Layout.fillWidth: true
    visible: thresholdsSupported

    NLabel {
      label: I18n.tr("settings.battery.thresholds.stop.label")
      description: I18n.tr("settings.battery.thresholds.stop.description")
    }

    NValueSlider {
      Layout.fillWidth: true
      from: 0
      to: 100
      value: localStopThreshold
      stepSize: 5
      text: `${localStopThreshold}%`
      onMoved: value => {
        // Ensure stop > start
        if (value <= localStartThreshold) {
          localStopThreshold = localStartThreshold + 5;
        } else {
          localStopThreshold = value;
        }
      }
      onPressedChanged: {
        if (!pressed && localStopThreshold !== chargeStopThreshold) {
          setStopThreshold(localStopThreshold);
        }
      }
    }
  }

  // Current thresholds display
  NBox {
    Layout.fillWidth: true
    implicitHeight: currentThresholdsRow.implicitHeight + Style.marginM * 2
    visible: thresholdsSupported

    RowLayout {
      id: currentThresholdsRow
      anchors.fill: parent
      anchors.margins: Style.marginM
      spacing: Style.marginL

      NText {
        text: I18n.tr("settings.battery.thresholds.current")
        color: Color.mOnSurfaceVariant
        pointSize: Style.fontSizeS
      }

      Item { Layout.fillWidth: true }

      NText {
        text: `${chargeStartThreshold}% - ${chargeStopThreshold}%`
        color: Color.mOnSurface
        pointSize: Style.fontSizeM
        font.weight: Style.fontWeightBold
      }
    }
  }

  // Thresholds not supported message
  NBox {
    Layout.fillWidth: true
    implicitHeight: notSupportedText.implicitHeight + Style.marginL * 2
    visible: !thresholdsSupported && !thresholdsLoading

    NText {
      id: notSupportedText
      anchors.centerIn: parent
      text: I18n.tr("settings.battery.thresholds.not-supported")
      color: Color.mOnSurfaceVariant
      pointSize: Style.fontSizeM
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
  }
}
