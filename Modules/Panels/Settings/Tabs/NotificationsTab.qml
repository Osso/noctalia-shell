import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.Compositor
import qs.Services.System
import qs.Widgets

ColumnLayout {
  id: root

  // Helper functions to update arrays immutably
  function addMonitor(list, name) {
    const arr = (list || []).slice();
    if (!arr.includes(name))
      arr.push(name);
    return arr;
  }
  function removeMonitor(list, name) {
    return (list || []).filter(function (n) {
      return n !== name;
    });
  }

  // General Notification Settings
  ColumnLayout {
    spacing: Style.marginL
    Layout.fillWidth: true

    NHeader {
      label: I18n.tr("settings.notifications.settings.section.label")
      description: I18n.tr("settings.notifications.settings.section.description")
    }

    NToggle {
      label: I18n.tr("settings.notifications.settings.enabled.label")
      description: I18n.tr("settings.notifications.settings.enabled.description")
      checked: Settings.data.notifications.enabled !== false
      onToggled: checked => Settings.data.notifications.enabled = checked
    }

    NToggle {
      label: I18n.tr("settings.notifications.settings.do-not-disturb.label")
      description: I18n.tr("settings.notifications.settings.do-not-disturb.description")
      checked: NotificationService.doNotDisturb
      onToggled: checked => NotificationService.doNotDisturb = checked
    }

    NComboBox {
      label: I18n.tr("settings.notifications.settings.location.label")
      description: I18n.tr("settings.notifications.settings.location.description")
      model: [
        {
          "key": "top",
          "name": I18n.tr("options.launcher.position.top_center")
        },
        {
          "key": "top_left",
          "name": I18n.tr("options.launcher.position.top_left")
        },
        {
          "key": "top_right",
          "name": I18n.tr("options.launcher.position.top_right")
        },
        {
          "key": "bottom",
          "name": I18n.tr("options.launcher.position.bottom_center")
        },
        {
          "key": "bottom_left",
          "name": I18n.tr("options.launcher.position.bottom_left")
        },
        {
          "key": "bottom_right",
          "name": I18n.tr("options.launcher.position.bottom_right")
        }
      ]
      currentKey: Settings.data.notifications.location || "top_right"
      onSelected: key => Settings.data.notifications.location = key
    }

    NToggle {
      label: I18n.tr("settings.notifications.settings.always-on-top.label")
      description: I18n.tr("settings.notifications.settings.always-on-top.description")
      checked: Settings.data.notifications.overlayLayer
      onToggled: checked => Settings.data.notifications.overlayLayer = checked
    }

    // Background Opacity
    ColumnLayout {
      spacing: Style.marginXXS
      Layout.fillWidth: true

      NLabel {
        label: I18n.tr("settings.notifications.settings.background-opacity.label")
        description: I18n.tr("settings.notifications.settings.background-opacity.description")
      }

      NValueSlider {
        Layout.fillWidth: true
        from: 0
        to: 100
        stepSize: 1
        value: Settings.data.notifications.backgroundOpacity * 100
        onMoved: value => Settings.data.notifications.backgroundOpacity = value / 100
        text: Math.round(Settings.data.notifications.backgroundOpacity * 100) + "%"
      }
    }

    // OSD settings moved to the dedicated OSD tab
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
  }

  // Duration
  ColumnLayout {
    spacing: Style.marginL
    Layout.fillWidth: true

    NHeader {
      label: I18n.tr("settings.notifications.duration.section.label")
      description: I18n.tr("settings.notifications.duration.section.description")
    }

    // Respect Expire Timeout (eg. --expire-time flag in notify-send)
    NToggle {
      label: I18n.tr("settings.notifications.duration.respect-expire.label")
      description: I18n.tr("settings.notifications.duration.respect-expire.description")
      checked: Settings.data.notifications.respectExpireTimeout
      onToggled: checked => Settings.data.notifications.respectExpireTimeout = checked
    }

    // Low Urgency Duration
    ColumnLayout {
      spacing: Style.marginXXS
      Layout.fillWidth: true

      NLabel {
        label: I18n.tr("settings.notifications.duration.low-urgency.label")
        description: I18n.tr("settings.notifications.duration.low-urgency.description")
      }

      RowLayout {
        spacing: Style.marginL
        Layout.fillWidth: true

        NValueSlider {
          Layout.fillWidth: true
          from: 1
          to: 30
          stepSize: 1
          value: Settings.data.notifications.lowUrgencyDuration
          onMoved: value => Settings.data.notifications.lowUrgencyDuration = value
          text: Settings.data.notifications.lowUrgencyDuration + "s"
        }
        // Reset button container
        Item {
          Layout.preferredWidth: 30 * Style.uiScaleRatio
          Layout.preferredHeight: 30 * Style.uiScaleRatio

          NIconButton {
            icon: "refresh"
            baseSize: Style.baseWidgetSize * 0.8
            tooltipText: I18n.tr("settings.notifications.duration.reset")
            onClicked: Settings.data.notifications.lowUrgencyDuration = 3
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
          }
        }
      }
    }

    // Normal Urgency Duration
    ColumnLayout {
      spacing: Style.marginXXS
      Layout.fillWidth: true

      NLabel {
        label: I18n.tr("settings.notifications.duration.normal-urgency.label")
        description: I18n.tr("settings.notifications.duration.normal-urgency.description")
      }

      RowLayout {
        spacing: Style.marginL
        Layout.fillWidth: true

        NValueSlider {
          Layout.fillWidth: true
          from: 1
          to: 30
          stepSize: 1
          value: Settings.data.notifications.normalUrgencyDuration
          onMoved: value => Settings.data.notifications.normalUrgencyDuration = value
          text: Settings.data.notifications.normalUrgencyDuration + "s"
        }

        // Reset button container
        Item {
          Layout.preferredWidth: 30 * Style.uiScaleRatio
          Layout.preferredHeight: 30 * Style.uiScaleRatio

          NIconButton {
            icon: "refresh"
            baseSize: Style.baseWidgetSize * 0.8
            tooltipText: I18n.tr("settings.notifications.duration.reset")
            onClicked: Settings.data.notifications.normalUrgencyDuration = 8
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
          }
        }
      }
    }

    // Critical Urgency Duration
    ColumnLayout {
      spacing: Style.marginXXS
      Layout.fillWidth: true

      NLabel {
        label: I18n.tr("settings.notifications.duration.critical-urgency.label")
        description: I18n.tr("settings.notifications.duration.critical-urgency.description")
      }

      RowLayout {
        spacing: Style.marginL
        Layout.fillWidth: true

        NValueSlider {
          Layout.fillWidth: true
          from: 1
          to: 30
          stepSize: 1
          value: Settings.data.notifications.criticalUrgencyDuration
          onMoved: value => Settings.data.notifications.criticalUrgencyDuration = value
          text: Settings.data.notifications.criticalUrgencyDuration + "s"
        }
        // Reset button container
        Item {
          Layout.preferredWidth: 30 * Style.uiScaleRatio
          Layout.preferredHeight: 30 * Style.uiScaleRatio

          NIconButton {
            icon: "refresh"
            baseSize: Style.baseWidgetSize * 0.8
            tooltipText: I18n.tr("settings.notifications.duration.reset")
            onClicked: Settings.data.notifications.criticalUrgencyDuration = 15
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
          }
        }
      }
    }

    NDivider {
      Layout.fillWidth: true
      Layout.topMargin: Style.marginL
      Layout.bottomMargin: Style.marginL
    }

    // Monitor Configuration
    NHeader {
      label: I18n.tr("settings.notifications.monitors.section.label")
      description: I18n.tr("settings.notifications.monitors.section.description")
    }

    Repeater {
      model: Quickshell.screens || []
      delegate: NCheckbox {
        required property ShellScreen modelData
        readonly property string monitorName: modelData ? modelData.name : ""
        readonly property string monitorModel: modelData ? modelData.model : ""
        readonly property int monitorWidth: modelData ? modelData.width : 0
        readonly property int monitorHeight: modelData ? modelData.height : 0

        Layout.fillWidth: true
        label: monitorName || I18n.tr("system.unknown")
        description: {
          const compositorScale = CompositorService.getDisplayScale(monitorName);
          I18n.tr("system.monitor-description", {
                    "model": monitorModel,
                    "width": monitorWidth * compositorScale,
                    "height": monitorHeight * compositorScale,
                    "scale": compositorScale
                  });
        }
        checked: (Settings.data.notifications.monitors || []).indexOf(monitorName) !== -1
        onToggled: checked => {
                     if (checked) {
                       Settings.data.notifications.monitors = addMonitor(Settings.data.notifications.monitors, monitorName);
                     } else {
                       Settings.data.notifications.monitors = removeMonitor(Settings.data.notifications.monitors, monitorName);
                     }
                   }
      }
    }

    NDivider {
      Layout.fillWidth: true
      Layout.topMargin: Style.marginL
      Layout.bottomMargin: Style.marginL
    }

    // Toast Configuration
    NHeader {
      label: I18n.tr("settings.notifications.toast.section.label")
      description: I18n.tr("settings.notifications.toast.section.description")
    }

    NToggle {
      label: I18n.tr("settings.notifications.toast.keyboard.label")
      description: I18n.tr("settings.notifications.toast.keyboard.description")
      checked: Settings.data.notifications.enableKeyboardLayoutToast
      onToggled: checked => Settings.data.notifications.enableKeyboardLayoutToast = checked
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
  }
}
