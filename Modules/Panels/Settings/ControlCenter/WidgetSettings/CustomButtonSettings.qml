pragma ComponentBehavior: Bound

import QtQml.Models
import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Widgets

ColumnLayout {
  id: root

  property var widgetData: null
  property var widgetMetadata: null

  QtObject {
    id: _settings

    property string icon: (root.widgetData && root.widgetData.icon !== undefined) ? root.widgetData.icon : root.widgetMetadata.icon
    property string onClicked: (root.widgetData && root.widgetData.onClicked !== undefined) ? root.widgetData.onClicked : root.widgetMetadata.onClicked
    property string onRightClicked: (root.widgetData && root.widgetData.onRightClicked !== undefined) ? root.widgetData.onRightClicked : root.widgetMetadata.onRightClicked
    property string onMiddleClicked: (root.widgetData && root.widgetData.onMiddleClicked !== undefined) ? root.widgetData.onMiddleClicked : root.widgetMetadata.onMiddleClicked
    property ListModel _stateChecksListModel: ListModel {}
    property string stateChecksJson: "[]"
    property string generalTooltipText: (root.widgetData && root.widgetData.generalTooltipText !== undefined) ? root.widgetData.generalTooltipText : root.widgetMetadata.generalTooltipText
    property bool enableOnStateLogic: (root.widgetData && root.widgetData.enableOnStateLogic !== undefined) ? root.widgetData.enableOnStateLogic : root.widgetMetadata.enableOnStateLogic

    Component.onCompleted: {
      stateChecksJson = (root.widgetData && root.widgetData.stateChecksJson !== undefined) ? root.widgetData.stateChecksJson : root.widgetMetadata.stateChecksJson || "[]";
      try {
        var initialChecks = JSON.parse(stateChecksJson);
        if (initialChecks && Array.isArray(initialChecks)) {
          for (var i = 0; i < initialChecks.length; i++) {
            var item = initialChecks[i];
            if (item && typeof item === "object") {
              _settings._stateChecksListModel.append({
                "command": item.command || "",
                "icon": item.icon || ""
              });
            } else {
              console.warn("⚠️ Invalid stateChecks entry at index " + i + ":", item);
            }
          }
        }
      } catch (e) {
        console.error("CustomButtonSettings: Failed to parse stateChecksJson:", e.message);
      }
    }
  }

  function saveSettings() {
    var savedStateChecksArray = [];
    for (var i = 0; i < _settings._stateChecksListModel.count; i++) {
      savedStateChecksArray.push(_settings._stateChecksListModel.get(i));
    }
    _settings.stateChecksJson = JSON.stringify(savedStateChecksArray);

    return {
      "id": root.widgetData.id,
      "icon": _settings.icon,
      "onClicked": _settings.onClicked,
      "onRightClicked": _settings.onRightClicked,
      "onMiddleClicked": _settings.onMiddleClicked,
      "stateChecksJson": _settings.stateChecksJson,
      "generalTooltipText": _settings.generalTooltipText,
      "enableOnStateLogic": _settings.enableOnStateLogic
    };
  }

  RowLayout {
    spacing: Style.marginM

    NLabel {
      label: I18n.tr("settings.control-center.shortcuts.custom-button.icon.label")
      description: I18n.tr("settings.control-center.shortcuts.custom-button.icon.description")
    }

    NIcon {
      Layout.alignment: Qt.AlignVCenter
      icon: _settings.icon || root.widgetMetadata.icon
      pointSize: Style.fontSizeXL
      visible: (_settings.icon || root.widgetMetadata.icon) !== ""
    }

    NButton {
      text: I18n.tr("settings.control-center.shortcuts.custom-button.browse")
      onClicked: iconPicker.open()
    }
  }

  NIconPicker {
    id: iconPicker
    initialIcon: _settings.icon
    onIconSelected: function (iconName) {
      _settings.icon = iconName;
    }
  }

  NTextInput {
    Layout.fillWidth: true
    label: I18n.tr("settings.control-center.shortcuts.custom-button.general-tooltip-text.label")
    description: I18n.tr("settings.control-center.shortcuts.custom-button.general-tooltip-text.description")
    placeholderText: I18n.tr("placeholders.enter-tooltip")
    text: _settings.generalTooltipText
    onTextChanged: _settings.generalTooltipText = text
  }

  NTextInput {
    Layout.fillWidth: true
    label: I18n.tr("settings.control-center.shortcuts.custom-button.on-clicked.label")
    description: I18n.tr("settings.control-center.shortcuts.custom-button.on-clicked.description")
    placeholderText: I18n.tr("placeholders.enter-command")
    text: _settings.onClicked
    onTextChanged: _settings.onClicked = text
  }

  NTextInput {
    Layout.fillWidth: true
    label: I18n.tr("settings.control-center.shortcuts.custom-button.on-right-clicked.label")
    description: I18n.tr("settings.control-center.shortcuts.custom-button.on-right-clicked.description")
    placeholderText: I18n.tr("placeholders.enter-command")
    text: _settings.onRightClicked
    onTextChanged: _settings.onRightClicked = text
  }

  NTextInput {
    Layout.fillWidth: true
    label: I18n.tr("settings.control-center.shortcuts.custom-button.on-middle-clicked.label")
    description: I18n.tr("settings.control-center.shortcuts.custom-button.on-middle-clicked.description")
    placeholderText: I18n.tr("placeholders.enter-command")
    text: _settings.onMiddleClicked
    onTextChanged: _settings.onMiddleClicked = text
  }

  NDivider {}

  NToggle {
    id: enableOnStateLogicToggle
    Layout.fillWidth: true
    label: I18n.tr("settings.control-center.shortcuts.custom-button.enable-on-state-logic.label")
    description: I18n.tr("settings.control-center.shortcuts.custom-button.enable-on-state-logic.description")
    checked: _settings.enableOnStateLogic
    onToggled: checked => _settings.enableOnStateLogic = checked
  }

  ColumnLayout {
    Layout.fillWidth: true
    visible: _settings.enableOnStateLogic
    spacing: Style.marginM * 2

    NLabel {
      label: I18n.tr("settings.control-center.shortcuts.custom-button.state-checks.label")
    }

    Repeater {
      model: _settings._stateChecksListModel
      delegate: Item {
        id: stateCheckDelegate

        required property string command
        required property string icon
        required property int index

        implicitHeight: contentRow.implicitHeight + ((divider.visible) ? divider.height : 0)
        Layout.fillWidth: true

        RowLayout {
          id: contentRow
          anchors.fill: parent
          spacing: Style.marginM

          NTextInput {
            id: stateCommandInput

            Layout.fillWidth: true
            placeholderText: I18n.tr("settings.control-center.shortcuts.custom-button.state-checks.command")
            text: stateCheckDelegate.command
            onEditingFinished: _settings._stateChecksListModel.set(stateCheckDelegate.index, {
              "command": stateCommandInput.text,
              "icon": stateCheckDelegate.icon
            })
          }

          RowLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: Style.marginS

            NIcon {
              icon: stateCheckDelegate.icon
              pointSize: Style.fontSizeL
              visible: stateCheckDelegate.icon !== ""
            }

            NIconButton {
              icon: "folder"
              tooltipText: I18n.tr("settings.control-center.shortcuts.custom-button.state-checks.browse-icon")
              baseSize: Style.baseWidgetSize
              onClicked: iconPickerDelegate.open()
            }

            NIconButton {
              icon: "close"
              tooltipText: I18n.tr("settings.control-center.shortcuts.custom-button.state-checks.remove")
              baseSize: Style.baseWidgetSize
              colorBorder: Qt.alpha(NColor.mOutline, Style.opacityLight)
              colorBg: NColor.mError
              colorFg: NColor.mOnError
              colorBgHover: Qt.alpha(NColor.mError, Style.opacityMedium)
              colorFgHover: NColor.mOnError
              onClicked: _settings._stateChecksListModel.remove(stateCheckDelegate.index)
            }
          }
        }

        NIconPicker {
          id: iconPickerDelegate
          initialIcon: stateCheckDelegate.icon
          onIconSelected: function (iconName) {
            _settings._stateChecksListModel.set(stateCheckDelegate.index, {
              "command": stateCheckDelegate.command,
              "icon": iconName
            });
          }
        }

        NDivider {
          id: divider
          anchors.bottom: parent.bottom
          visible: stateCheckDelegate.index < _settings._stateChecksListModel.count - 1
        }
      }
    }

    RowLayout {
      Layout.fillWidth: true
      spacing: Style.marginM

      NButton {
        text: I18n.tr("settings.control-center.shortcuts.custom-button.state-checks.add")
        onClicked: _settings._stateChecksListModel.append({
          "command": "",
          "icon": ""
        })
      }

      Item {
        Layout.fillWidth: true
      }
    }
  }

  NDivider {}
}
