import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.OSD
import qs.Services.Compositor
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
  function addType(list, type) {
    const arr = (list || []).slice();
    if (!arr.includes(type))
      arr.push(type);
    return arr;
  }
  function removeType(list, type) {
    return (list || []).filter(function (t) {
      return t !== type;
    });
  }

  // Display
  ColumnLayout {
    spacing: Style.marginL
    Layout.fillWidth: true

    NComboBox {
      label: I18n.tr("settings.osd.location.label")
      description: I18n.tr("settings.osd.location.description")
      model: [
        {
          "key": "top",
          "name": I18n.tr("options.osd.position.top_center")
        },
        {
          "key": "top_left",
          "name": I18n.tr("options.osd.position.top_left")
        },
        {
          "key": "top_right",
          "name": I18n.tr("options.osd.position.top_right")
        },
        {
          "key": "bottom",
          "name": I18n.tr("options.osd.position.bottom_center")
        },
        {
          "key": "bottom_left",
          "name": I18n.tr("options.osd.position.bottom_left")
        },
        {
          "key": "bottom_right",
          "name": I18n.tr("options.osd.position.bottom_right")
        },
        {
          "key": "left",
          "name": I18n.tr("options.osd.position.center_left")
        },
        {
          "key": "right",
          "name": I18n.tr("options.osd.position.center_right")
        }
      ]
      currentKey: Settings.data.osd.location || "top_right"
      onSelected: key => Settings.data.osd.location = key
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
  }

  // General
  ColumnLayout {
    spacing: Style.marginL
    Layout.fillWidth: true

    NHeader {
      label: I18n.tr("settings.osd.section.general.label")
      description: I18n.tr("settings.osd.section.general.description")
    }

    NToggle {
      label: I18n.tr("settings.osd.enabled.label")
      description: I18n.tr("settings.osd.enabled.description")
      checked: Settings.data.osd.enabled
      onToggled: checked => Settings.data.osd.enabled = checked
    }

    NToggle {
      label: I18n.tr("settings.osd.always-on-top.label")
      description: I18n.tr("settings.osd.always-on-top.description")
      checked: Settings.data.osd.overlayLayer
      onToggled: checked => Settings.data.osd.overlayLayer = checked
    }

    NLabel {
      label: I18n.tr("settings.osd.background-opacity.label", "Background opacity")
      description: I18n.tr("settings.osd.background-opacity.description", "Controls the transparency of the OSD background.")
    }

    NValueSlider {
      Layout.fillWidth: true
      from: 0
      to: 100
      stepSize: 1
      value: Settings.data.osd.backgroundOpacity * 100
      onMoved: value => Settings.data.osd.backgroundOpacity = value / 100
      text: Math.round(Settings.data.osd.backgroundOpacity * 100) + "%"
    }

    NLabel {
      label: I18n.tr("settings.osd.duration.auto-hide.label")
      description: I18n.tr("settings.osd.duration.auto-hide.description")
    }

    NValueSlider {
      Layout.fillWidth: true
      from: 500
      to: 5000
      stepSize: 100
      value: Settings.data.osd.autoHideMs
      onMoved: value => Settings.data.osd.autoHideMs = value
      text: Math.round(Settings.data.osd.autoHideMs / 1000 * 10) / 10 + "s"
    }
  }

  NDivider {
    Layout.fillWidth: true
    Layout.topMargin: Style.marginL
    Layout.bottomMargin: Style.marginL
  }

  // OSD Types Configuration
  ColumnLayout {
    spacing: Style.marginL
    Layout.fillWidth: true

    NHeader {
      label: I18n.tr("settings.osd.types.section.label")
      description: I18n.tr("settings.osd.types.section.description")
    }

    Repeater {
      model: [
        {
          type: OSD.Type.Volume,
          key: "volume"
        },
        {
          type: OSD.Type.InputVolume,
          key: "input-volume"
        },
        {
          type: OSD.Type.Brightness,
          key: "brightness"
        },
        {
          type: OSD.Type.LockKey,
          key: "lockkey"
        }
      ]
      delegate: NCheckbox {
        required property int type
        required property string key

        Layout.fillWidth: true
        label: I18n.tr("settings.osd.types." + key + ".label")
        description: I18n.tr("settings.osd.types." + key + ".description")
        checked: (Settings.data.osd.enabledTypes || []).includes(type)
        onToggled: checked => {
                     if (checked) {
                       Settings.data.osd.enabledTypes = addType(Settings.data.osd.enabledTypes, type);
                     } else {
                       Settings.data.osd.enabledTypes = removeType(Settings.data.osd.enabledTypes, type);
                     }
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
  ColumnLayout {
    spacing: Style.marginL
    Layout.fillWidth: true

    NHeader {
      label: I18n.tr("settings.osd.monitors.section.label")
      description: I18n.tr("settings.osd.monitors.section.description")
    }

    Repeater {
      model: Quickshell.screens || []
      delegate: NCheckbox {
        required property ShellScreen modelData
        readonly property string monitorName: modelData.name
        readonly property string monitorModel: modelData.model
        readonly property int monitorWidth: modelData.width
        readonly property int monitorHeight: modelData.height

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
        checked: (Settings.data.osd.monitors || []).indexOf(monitorName) !== -1
        onToggled: checked => {
                     if (checked) {
                       Settings.data.osd.monitors = addMonitor(Settings.data.osd.monitors, monitorName);
                     } else {
                       Settings.data.osd.monitors = removeMonitor(Settings.data.osd.monitors, monitorName);
                     }
                   }
      }
    }
  }
}
