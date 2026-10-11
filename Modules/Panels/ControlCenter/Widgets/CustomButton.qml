import QtQuick
import Quickshell
import Quickshell.Io
import qs.Widgets

Item {
  id: root

  property string widgetId: "CustomButton"
  property var widgetSettings: null

  property string onClickedCommand: ""
  property string onRightClickedCommand: ""
  property string onMiddleClickedCommand: ""
  property string stateChecksJson: "[]" // Store state checks as JSON string

  property string generalTooltipText: "Custom Button"
  property bool enableOnStateLogic: false

  property string _currentIcon: "heart" // Default icon
  property bool _isHot: false
  property var _parsedStateChecks: [] // Local array for parsed state checks

  property int _currentStateCheckIndex: -1
  property string _activeStateIcon: ""
  property int _stateGeneration: 0

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Connections {
    id: settingsConnections
    target: root

    function _updatePropertiesFromSettings() {
      if (!root.widgetSettings) {
        return;
      }

      root.onClickedCommand = root.widgetSettings.onClicked || "";
      root.onRightClickedCommand = root.widgetSettings.onRightClicked || "";
      root.onMiddleClickedCommand = root.widgetSettings.onMiddleClicked || "";
      root.stateChecksJson = root.widgetSettings.stateChecksJson || "[]";
      try {
        const checks = JSON.parse(root.stateChecksJson);
        if (!Array.isArray(checks)) {
          throw new Error("State checks must be an array");
        }
        root._parsedStateChecks = checks;
      } catch (e) {
        console.error("CustomButton: Failed to parse stateChecksJson:", e.message);
        root._parsedStateChecks = [];
      }
      root.generalTooltipText = root.widgetSettings.generalTooltipText || "Custom Button";
      root.enableOnStateLogic = root.widgetSettings.enableOnStateLogic || false;

      root.updateState();
    }

    function onWidgetSettingsChanged() {
      if (root.widgetSettings) {
        settingsConnections._updatePropertiesFromSettings();
      }
    }
  }

  Process {
    id: stateCheckProcessExecutor
    running: false
    property int generation: -1
    property string stateIcon: ""
    onExited: function (exitCode) {
      if (stateCheckProcessExecutor.generation !== root._stateGeneration) {
        root._checkNextState();
        return;
      }
      if (exitCode === 0) {
        root._isHot = true;
        root._activeStateIcon = stateCheckProcessExecutor.stateIcon;
      } else {
        root._currentStateCheckIndex++;
        root._checkNextState();
      }
    }
  }

  Timer {
    id: stateUpdateTimer
    interval: 200
    running: false
    repeat: false
    onTriggered: {
      root._currentStateCheckIndex = 0;
      root._checkNextState();
    }
  }

  function _checkNextState() {
    if (_currentStateCheckIndex < 0 || stateCheckProcessExecutor.running) {
      return;
    }
    if (_currentStateCheckIndex < _parsedStateChecks.length) {
      const currentCheckItem = _parsedStateChecks[_currentStateCheckIndex];
      if (currentCheckItem && currentCheckItem.command) {
        stateCheckProcessExecutor.command = ["sh", "-c", currentCheckItem.command];
        stateCheckProcessExecutor.generation = _stateGeneration;
        stateCheckProcessExecutor.stateIcon = currentCheckItem.icon || widgetSettings.icon || "heart";
        stateCheckProcessExecutor.running = true;
      } else {
        _currentStateCheckIndex++;
        _checkNextState();
      }
    } else {
      // All checks failed
      _isHot = false;
      _activeStateIcon = widgetSettings.icon || "heart";
    }
  }

  function updateState() {
    _stateGeneration++;
    _currentStateCheckIndex = -1;
    stateUpdateTimer.stop();
    if (!enableOnStateLogic || _parsedStateChecks.length === 0) {
      _isHot = false;
      _activeStateIcon = widgetSettings.icon || "heart";
      return;
    }
    stateUpdateTimer.restart();
  }

  function _buildTooltipText() {
    let tooltip = generalTooltipText;
    if (onClickedCommand) {
      tooltip += `\nLeft click: ${onClickedCommand}`;
    }
    if (onRightClickedCommand) {
      tooltip += `\nRight click: ${onRightClickedCommand}`;
    }
    if (onMiddleClickedCommand) {
      tooltip += `\nMiddle click: ${onMiddleClickedCommand}`;
    }

    return tooltip;
  }

  NIconButtonHot {
    id: button
    icon: root._activeStateIcon
    hot: root._isHot
    tooltipText: root._buildTooltipText()
    onClicked: {
      if (root.onClickedCommand) {
        Quickshell.execDetached(["sh", "-c", root.onClickedCommand]);
        root.updateState();
      }
    }
    onRightClicked: {
      if (root.onRightClickedCommand) {
        Quickshell.execDetached(["sh", "-c", root.onRightClickedCommand]);
        root.updateState();
      }
    }
    onMiddleClicked: {
      if (root.onMiddleClickedCommand) {
        Quickshell.execDetached(["sh", "-c", root.onMiddleClickedCommand]);
        root.updateState();
      }
    }
  }
}
