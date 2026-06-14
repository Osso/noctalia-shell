import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import "../../../Helpers/CustomButtonContent.js" as CustomButtonContent
import qs.Modules.Bar.Extras
import qs.Modules.Panels.Settings
import qs.Services.UI
import qs.Widgets

Item {
  id: root

  property ShellScreen screen

  // Widget properties passed from Bar.qml for per-instance settings
  property string widgetId: ""
  property string section: ""
  property int sectionWidgetIndex: -1
  property int sectionWidgetsCount: 0

  property var widgetMetadata: BarWidgetRegistry.widgetMetadata[widgetId]
  property var widgetSettings: {
    if (section && sectionWidgetIndex >= 0) {
      var widgets = Settings.data.bar.widgets[section];
      if (widgets && sectionWidgetIndex < widgets.length) {
        return widgets[sectionWidgetIndex];
      }
    }
    return {};
  }

  readonly property bool isVerticalBar: Settings.data.bar.position === "left" || Settings.data.bar.position === "right"

  readonly property string customIcon: widgetSettings.icon || widgetMetadata.icon
  readonly property string leftClickExec: widgetSettings.leftClickExec || widgetMetadata.leftClickExec
  readonly property bool leftClickUpdateText: widgetSettings.leftClickUpdateText ?? widgetMetadata.leftClickUpdateText
  readonly property string rightClickExec: widgetSettings.rightClickExec || widgetMetadata.rightClickExec
  readonly property bool rightClickUpdateText: widgetSettings.rightClickUpdateText ?? widgetMetadata.rightClickUpdateText
  readonly property string middleClickExec: widgetSettings.middleClickExec || widgetMetadata.middleClickExec
  readonly property bool middleClickUpdateText: widgetSettings.middleClickUpdateText ?? widgetMetadata.middleClickUpdateText
  readonly property string wheelExec: widgetSettings.wheelExec || widgetMetadata.wheelExec
  readonly property string wheelUpExec: widgetSettings.wheelUpExec || widgetMetadata.wheelUpExec
  readonly property string wheelDownExec: widgetSettings.wheelDownExec || widgetMetadata.wheelDownExec
  readonly property string wheelMode: widgetSettings.wheelMode || widgetMetadata.wheelMode
  readonly property bool wheelUpdateText: widgetSettings.wheelUpdateText ?? widgetMetadata.wheelUpdateText
  readonly property bool wheelUpUpdateText: widgetSettings.wheelUpUpdateText ?? widgetMetadata.wheelUpUpdateText
  readonly property bool wheelDownUpdateText: widgetSettings.wheelDownUpdateText ?? widgetMetadata.wheelDownUpdateText
  readonly property string textCommand: widgetSettings.textCommand !== undefined ? widgetSettings.textCommand : (widgetMetadata.textCommand || "")
  readonly property bool textStream: widgetSettings.textStream !== undefined ? widgetSettings.textStream : (widgetMetadata.textStream || false)
  readonly property int textIntervalMs: widgetSettings.textIntervalMs !== undefined ? widgetSettings.textIntervalMs : (widgetMetadata.textIntervalMs || 3000)
  readonly property string textCollapse: widgetSettings.textCollapse !== undefined ? widgetSettings.textCollapse : (widgetMetadata.textCollapse || "")
  readonly property bool parseJson: widgetSettings.parseJson !== undefined ? widgetSettings.parseJson : (widgetMetadata.parseJson || false)
  readonly property bool hasExec: (leftClickExec || rightClickExec || middleClickExec || (wheelMode === "unified" && wheelExec) || (wheelMode === "separate" && (wheelUpExec || wheelDownExec)))

  implicitWidth: pill.width
  implicitHeight: pill.height

  BarPill {
    id: pill

    screen: root.screen
    oppositeDirection: BarService.getPillDirection(root)
    icon: _dynamicIcon !== "" ? _dynamicIcon : customIcon
    text: (!isVerticalBar || currentMaxTextLength > 0) ? _dynamicText : ""
    density: Settings.data.bar.density
    rotateText: isVerticalBar && currentMaxTextLength > 0
    autoHide: false
    forceOpen: _dynamicText !== ""
    tooltipText: {
      var tooltipLines = [];

      if (hasExec) {
        if (leftClickExec !== "") {
          tooltipLines.push(`Left click: ${leftClickExec}.`);
        }
        if (rightClickExec !== "") {
          tooltipLines.push(`Right click: ${rightClickExec}.`);
        }
        if (middleClickExec !== "") {
          tooltipLines.push(`Middle click: ${middleClickExec}.`);
        }
        if (wheelMode === "unified" && wheelExec !== "") {
          tooltipLines.push(`Wheel: ${wheelExec}.`);
        } else if (wheelMode === "separate") {
          if (wheelUpExec !== "") {
            tooltipLines.push(`Wheel up: ${wheelUpExec}.`);
          }
          if (wheelDownExec !== "") {
            tooltipLines.push(`Wheel down: ${wheelDownExec}.`);
          }
        }
      }

      if (_dynamicTooltip !== "") {
        if (tooltipLines.length > 0) {
          tooltipLines.push("");
        }
        tooltipLines.push(_dynamicTooltip);
      }

      if (tooltipLines.length === 0) {
        return "Custom button, configure in settings.";
      } else {
        return tooltipLines.join("\n");
      }
    }

    onClicked: root.onClicked()
    onRightClicked: root.onRightClicked()
    onMiddleClicked: root.onMiddleClicked()
    onWheel: delta => root.onWheel(delta)
  }

  // Internal state for dynamic text
  property string _dynamicText: ""
  property string _dynamicIcon: ""
  property string _dynamicTooltip: ""

  // Maximum length for text display before scrolling (different values for horizontal and vertical)
  readonly property var maxTextLength: {
    "horizontal": ((widgetSettings && widgetSettings.maxTextLength && widgetSettings.maxTextLength.horizontal !== undefined) ? widgetSettings.maxTextLength.horizontal : ((widgetMetadata && widgetMetadata.maxTextLength && widgetMetadata.maxTextLength.horizontal !== undefined) ? widgetMetadata.maxTextLength.horizontal : 10)),
    "vertical": ((widgetSettings && widgetSettings.maxTextLength && widgetSettings.maxTextLength.vertical !== undefined) ? widgetSettings.maxTextLength.vertical : ((widgetMetadata && widgetMetadata.maxTextLength && widgetMetadata.maxTextLength.vertical !== undefined) ? widgetMetadata.maxTextLength.vertical : 10))
  }
  readonly property int _staticDuration: 6  // How many cycles to stay static at start/end

  // Encapsulated state for scrolling text implementation
  property var _scrollState: {
    "originalText": "",
    "needsScrolling": false,
    "offset": 0,
    "phase": 0 // 0=static start, 1=scrolling, 2=static end
        ,
    "phaseCounter": 0
  }

  // Current max text length based on bar orientation
  readonly property int currentMaxTextLength: isVerticalBar ? maxTextLength.vertical : maxTextLength.horizontal

  // Periodically run the text command (if set)
  Timer {
    id: refreshTimer
    interval: Math.max(250, textIntervalMs)
    repeat: true
    running: (!isVerticalBar || currentMaxTextLength > 0) && !textStream && textCommand && textCommand.length > 0
    triggeredOnStart: true
    onTriggered: root.runTextCommand()
  }

  // Restart exited text stream commands after a delay
  Timer {
    id: restartTimer
    interval: 1000
    running: (!isVerticalBar || currentMaxTextLength > 0) && textStream && !textProc.running
    onTriggered: root.runTextCommand()
  }

  // Timer for scrolling text display
  Timer {
    id: scrollTimer
    interval: 300
    repeat: true
    running: false
    onTriggered: {
      if (_scrollState.needsScrolling && _scrollState.originalText.length > currentMaxTextLength) {
        // Traditional marquee with pause at beginning and end
        if (_scrollState.phase === 0) {
          // Static at beginning
          _dynamicText = _scrollState.originalText.substring(0, Math.min(currentMaxTextLength, _scrollState.originalText.length));
          _scrollState.phaseCounter++;
          if (_scrollState.phaseCounter >= _staticDuration) {
            _scrollState.phaseCounter = 0;
            _scrollState.phase = 1;  // Move to scrolling
          }
        } else if (_scrollState.phase === 1) {
          // Scrolling
          _scrollState.offset++;
          var start = _scrollState.offset;
          var end = start + currentMaxTextLength;

          if (start >= _scrollState.originalText.length - currentMaxTextLength) {
            // Reached or passed the end, ensure we show the last part
            var textEnd = _scrollState.originalText.length;
            var textStart = Math.max(0, textEnd - currentMaxTextLength);
            _dynamicText = _scrollState.originalText.substring(textStart, textEnd);
            _scrollState.phase = 2;  // Move to static end phase
            _scrollState.phaseCounter = 0;
          } else {
            _dynamicText = _scrollState.originalText.substring(start, end);
          }
        } else if (_scrollState.phase === 2) {
          // Static at end
          // Ensure end text is displayed correctly
          var textEnd = _scrollState.originalText.length;
          var textStart = Math.max(0, textEnd - currentMaxTextLength);
          _dynamicText = _scrollState.originalText.substring(textStart, textEnd);
          _scrollState.phaseCounter++;
          if (_scrollState.phaseCounter >= _staticDuration) {
            // Do NOT loop back to start, just stop scrolling
            scrollTimer.stop();
          }
        }
      } else {
        scrollTimer.stop();
      }
    }
  }

  SplitParser {
    id: textStdoutSplit
    onRead: line => root.parseDynamicContent(line)
  }

  StdioCollector {
    id: textStdoutCollect
    onStreamFinished: () => root.parseDynamicContent(this.text)
  }

  Process {
    id: textProc
    stdout: textStream ? textStdoutSplit : textStdoutCollect
    stderr: StdioCollector {}
    onExited: (exitCode, exitStatus) => {
                if (textStream) {
                  Logger.w("CustomButton", `Streaming text command exited (code: ${exitCode}), restarting...`);
                  return;
                }
              }
  }

  function parseDynamicContent(content) {
    const parserOptions = {
      "parseJson": parseJson,
      "textStream": textStream,
      "textCollapse": textCollapse,
      "maxTextLength": currentMaxTextLength
    };
    const result = CustomButtonContent.parseDynamicContent(content, parserOptions);

    if (result.parseFailed) {
      Logger.w("CustomButton", `Failed to parse JSON. Content: "${String(content || "").trim()}"`);
    }

    _scrollState.originalText = result.originalText;
    _scrollState.needsScrolling = result.needsScrolling;
    _dynamicText = result.visibleText;
    _dynamicIcon = result.icon;
    _dynamicTooltip = result.tooltip;
    _scrollState.phase = 0;
    _scrollState.phaseCounter = 0;
    _scrollState.offset = 0;

    if (result.needsScrolling) {
      scrollTimer.start();
    } else {
      scrollTimer.stop();
    }
  }

  function onClicked() {
    if (leftClickExec) {
      Quickshell.execDetached(["sh", "-c", leftClickExec]);
      Logger.i("CustomButton", `Executing command: ${leftClickExec}`);
    } else if (!leftClickUpdateText) {
      // No left click script was defined, open settings
      var settingsPanel = PanelService.getPanel("settingsPanel", screen);
      settingsPanel.requestedTab = SettingsPanel.Tab.Bar;
      settingsPanel.open();
    }
    if (!textStream && leftClickUpdateText) {
      runTextCommand();
    }
  }

  function onRightClicked() {
    if (rightClickExec) {
      Quickshell.execDetached(["sh", "-c", rightClickExec]);
      Logger.i("CustomButton", `Executing command: ${rightClickExec}`);
    }
    if (!textStream && rightClickUpdateText) {
      runTextCommand();
    }
  }

  function onMiddleClicked() {
    if (middleClickExec) {
      Quickshell.execDetached(["sh", "-c", middleClickExec]);
      Logger.i("CustomButton", `Executing command: ${middleClickExec}`);
    }
    if (!textStream && middleClickUpdateText) {
      runTextCommand();
    }
  }

  function runTextCommand() {
    if (!textCommand || textCommand.length === 0)
      return;
    if (textProc.running)
      return;
    textProc.command = ["sh", "-lc", textCommand];
    textProc.running = true;
  }

  function onWheel(delta) {
    if (wheelMode === "unified" && wheelExec) {
      let normalizedDelta = delta > 0 ? 1 : -1;

      let command = wheelExec.replace(/\$delta([+\-*/]\d+)?/g, function (match, operation) {
        if (operation) {
          try {
            let operator = operation.charAt(0);
            let operand = parseInt(operation.substring(1));

            let result;
            switch (operator) {
            case '+':
              result = normalizedDelta + operand;
              break;
            case '-':
              result = normalizedDelta - operand;
              break;
            case '*':
              result = normalizedDelta * operand;
              break;
            case '/':
              result = Math.floor(normalizedDelta / operand);
              break;
            default:
              result = normalizedDelta;
            }

            return result.toString();
          } catch (e) {
            Logger.w("CustomButton", `Error evaluating expression: ${match}, using normalized value ${normalizedDelta}`);
            return normalizedDelta.toString();
          }
        } else {
          return normalizedDelta.toString();
        }
      });

      Quickshell.execDetached(["sh", "-c", command]);
      Logger.i("CustomButton", `Executing command: ${command}`);
    } else if (wheelMode === "separate") {
      if ((delta > 0 && wheelUpExec) || (delta < 0 && wheelDownExec)) {
        let commandExec = delta > 0 ? wheelUpExec : wheelDownExec;
        let normalizedDelta = delta > 0 ? 1 : -1;

        let command = commandExec.replace(/\$delta([+\-*/]\d+)?/g, function (match, operation) {
          if (operation) {
            try {
              let operator = operation.charAt(0);
              let operand = parseInt(operation.substring(1));

              let result;
              switch (operator) {
              case '+':
                result = normalizedDelta + operand;
                break;
              case '-':
                result = normalizedDelta - operand;
                break;
              case '*':
                result = normalizedDelta * operand;
                break;
              case '/':
                result = Math.floor(normalizedDelta / operand);
                break;
              default:
                result = normalizedDelta;
              }

              return result.toString();
            } catch (e) {
              Logger.w("CustomButton", `Error evaluating expression: ${match}, using normalized value ${normalizedDelta}`);
              return normalizedDelta.toString();
            }
          } else {
            return normalizedDelta.toString();
          }
        });

        Quickshell.execDetached(["sh", "-c", command]);
        Logger.i("CustomButton", `Executing command: ${command}`);
      }
    }

    if (!textStream) {
      if (wheelMode === "unified" && wheelUpdateText) {
        runTextCommand();
      } else if (wheelMode === "separate") {
        if ((delta > 0 && wheelUpUpdateText) || (delta < 0 && wheelDownUpdateText)) {
          runTextCommand();
        }
      }
    }
  }
}
