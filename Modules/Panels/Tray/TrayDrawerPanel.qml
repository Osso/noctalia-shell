pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.SystemTray
import Quickshell.Widgets
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.UI
import qs.Widgets

// A compact grid panel listing all tray items, opened from the Tray widget
SmartPanel {
  id: root

  // Do not give exclusive focus to the TrayDrawer or it will prevent the dropdown menu to request it.
  exclusiveKeyboard: false

  // Widget info for menu functionality
  property string widgetSection: ""
  property int widgetIndex: -1

  // Trigger refresh when settings change
  property int settingsVersion: 0

  // Read widget settings for reactivity
  readonly property var widgetSettings: {
    // Reference settingsVersion to force recalculation when it changes
    var _ = root.settingsVersion;
    if (root.widgetSection === "" || root.widgetIndex < 0)
      return {};
    var widgets = Settings.data.bar.widgets[root.widgetSection];
    if (!widgets || root.widgetIndex >= widgets.length)
      return {};
    var settings = widgets[root.widgetIndex];
    if (!settings || settings.id !== "Tray")
      return {};
    return settings;
  }

  // Read pinned list directly from settings for reactivity
  readonly property var pinnedList: root.widgetSettings.pinned || []

  function wildCardMatch(str, rule) {
    if (!str || !rule)
      return false;
    // First, convert '*' to a placeholder to preserve it, then escape other special regex characters
    // Use a unique placeholder that won't appear in normal strings
    const placeholder = '\uE000'; // Private use character
    let processedRule = rule.replace(/\*/g, placeholder);
    // Escape all special regex characters (but placeholder won't match this)
    let escaped = processedRule.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    // Convert placeholder back to '.*' for wildcard matching
    let pattern = '^' + escaped.replace(new RegExp(placeholder, 'g'), '.*') + '$';
    try {
      return new RegExp(pattern, 'i').test(str);
    } catch (e) {
      return false;
    }
  }

  function isPinned(item) {
    if (!root.pinnedList || root.pinnedList.length === 0)
      return false;
    const title = item ? (item.tooltipTitle || item.name || item.id || "") : "";
    for (var i = 0; i < root.pinnedList.length; i++) {
      if (root.wildCardMatch(title, root.pinnedList[i]))
        return true;
    }
    return false;
  }

  // Dynamic sizing based on item count
  // Show items that are NOT pinned (unpinned items go to drawer)
  readonly property var trayValuesAll: (SystemTray.items && SystemTray.items.values) ? SystemTray.items.values : []
  readonly property var trayValues: root.trayValuesAll.filter(function (it) {
    return !root.isPinned(it);
  })
  readonly property int itemCount: root.trayValues.length
  readonly property int maxColumns: 8
  readonly property real cellSize: Math.round(Style.capsuleHeight * 0.65)
  readonly property real outerPadding: Style.marginM
  readonly property real innerSpacing: Style.marginM
  readonly property int columns: Math.max(1, Math.min(root.maxColumns, root.itemCount))
  readonly property int rows: Math.max(1, Math.ceil(root.itemCount / Math.max(1, root.columns)))

  // Static fallback sizes
  preferredWidth: (root.columns * root.cellSize) + ((root.columns - 1) * root.innerSpacing) + (2 * root.outerPadding)
  preferredHeight: (root.rows * root.cellSize) + ((root.rows - 1) * root.innerSpacing) + (2 * root.outerPadding)

  // Positioning is handled automatically by SmartPanel when toggle(buttonItem) is called

  // Watch for settings changes to refresh the dropdown
  Connections {
    target: Settings
    function onSettingsSaved() {
      // Force refresh by incrementing settingsVersion, which triggers recalculation of pinnedList
      root.settingsVersion++;
    }
  }

  // Auto-close drawer when all items are pinned (drawer becomes empty)
  onTrayValuesChanged: {
    if (root.visible && root.trayValues.length === 0) {
      root.close();
    }
  }

  // Trigger re-evaluation when window is registered
  property int popupMenuUpdateTrigger: 0

  // Get the trayMenu window and loader from PanelService (reactive to trigger changes)
  readonly property PopupMenuWindow popupMenuWindow: {
    // Reference trigger to force re-evaluation
    var _ = root.popupMenuUpdateTrigger;
    return PanelService.getPopupMenuWindow(root.screen);
  }

  readonly property Loader trayMenu: root.popupMenuWindow ? root.popupMenuWindow.trayMenuLoader : null
  readonly property var trayMenuItem: root.trayMenu ? root.trayMenu.item : null

  Connections {
    target: PanelService
    function onPopupMenuWindowRegistered(registeredScreen) {
      if (registeredScreen === root.screen) {
        root.popupMenuUpdateTrigger++;
      }
    }
  }

  panelContent: Component {
    Item {
      id: content
      property TrayDrawerPanel drawer: root

      // Dynamic content sizing that SmartPanel will watch for changes
      property real contentPreferredWidth: (content.drawer.columns * content.drawer.cellSize) + ((content.drawer.columns - 1) * content.drawer.innerSpacing) + (2 * content.drawer.outerPadding)
      property real contentPreferredHeight: (content.drawer.rows * content.drawer.cellSize) + ((content.drawer.rows - 1) * content.drawer.innerSpacing) + (2 * content.drawer.outerPadding)

      Grid {
        id: grid
        anchors.fill: parent
        anchors.margins: content.drawer.outerPadding
        spacing: content.drawer.innerSpacing
        columns: content.drawer.columns
        rowSpacing: content.drawer.innerSpacing
        columnSpacing: content.drawer.innerSpacing

        Repeater {
          id: repeater
          model: content.drawer.trayValues

          delegate: Component {
            Item {
              id: trayDelegate
              property TrayDrawerPanel drawer: content.drawer
              required property var modelData

              width: trayDelegate.drawer.cellSize
              height: trayDelegate.drawer.cellSize

              IconImage {
                id: trayIcon
                anchors.fill: parent
                asynchronous: true
                backer.fillMode: Image.PreserveAspectFit
                source: {
                  let icon = trayDelegate.modelData ? (trayDelegate.modelData.icon || "") : "";
                  if (!icon)
                    return "";
                  if (icon.includes("?path=")) {
                    const chunks = icon.split("?path=");
                    const name = chunks[0];
                    const path = chunks[1];
                    const fileName = name.substring(name.lastIndexOf("/") + 1);
                    return `file://${path}/${fileName}`;
                  }
                  return icon;
                }

                layer.enabled: trayDelegate.drawer.widgetSettings.colorizeIcons !== false
                layer.effect: ShaderEffect {
                  property color targetColor: Settings.data.colorSchemes.darkMode ? NColor.mOnSurface : NColor.mSurfaceVariant
                  property real colorizeMode: 1.0
                  fragmentShader: Qt.resolvedUrl(Quickshell.shellDir + "/Shaders/qsb/appicon_colorize.frag.qsb")
                }

                MouseArea {
                  anchors.fill: parent
                  cursorShape: Qt.PointingHandCursor
                  hoverEnabled: true
                  acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

                  onClicked: mouse => {
                    if (!trayDelegate.modelData)
                      return;
                    if (mouse.button === Qt.LeftButton) {
                      // Left click: activate tray item
                      if (!trayDelegate.modelData.onlyMenu) {
                        trayDelegate.modelData.activate();
                      }
                      if ((PanelService.openedPanel !== null) && !PanelService.openedPanel.isClosing) {
                        PanelService.openedPanel.close();
                      }
                    } else if (mouse.button === Qt.MiddleButton) {
                      // Middle click: activate with middle button
                      trayDelegate.modelData.secondaryActivate && trayDelegate.modelData.secondaryActivate();
                      if ((PanelService.openedPanel !== null) && !PanelService.openedPanel.isClosing) {
                        PanelService.openedPanel.close();
                      }
                    } else if (mouse.button === Qt.RightButton) {
                      // Right click: open context menu
                      TooltipService.hideImmediately();

                      // Close menu if already visible
                      if (trayDelegate.drawer.popupMenuWindow && trayDelegate.drawer.popupMenuWindow.visible) {
                        trayDelegate.drawer.popupMenuWindow.close();
                        return;
                      }

                      if (trayDelegate.modelData.hasMenu && trayDelegate.modelData.menu && trayDelegate.drawer.popupMenuWindow && trayDelegate.drawer.trayMenuItem) {
                        trayDelegate.drawer.popupMenuWindow.open();

                        // Position menu at the tray icon
                        const barPosition = Settings.data.bar.position;
                        let menuX, menuY;

                        if (barPosition === "left") {
                          menuX = trayIcon.width + Style.marginM;
                          menuY = 0;
                        } else if (barPosition === "right") {
                          menuX = -trayDelegate.drawer.trayMenuItem.width - Style.marginM;
                          menuY = 0;
                        } else {
                          // Horizontal bars
                          menuX = (trayIcon.width / 2) - (trayDelegate.drawer.trayMenuItem.width / 2);
                          menuY = trayIcon.height + Style.marginS;
                        }

                        trayDelegate.drawer.trayMenuItem.trayItem = trayDelegate.modelData;
                        trayDelegate.drawer.trayMenuItem.widgetSection = trayDelegate.drawer.widgetSection;
                        trayDelegate.drawer.trayMenuItem.widgetIndex = trayDelegate.drawer.widgetIndex;
                        trayDelegate.drawer.trayMenuItem.showAt(trayIcon, menuX, menuY);
                      }
                    }
                  }

                  onWheel: wheel => {
                    if (!trayDelegate.modelData) {
                      return;
                    }
                    if (wheel.angleDelta.y > 0) {
                      trayDelegate.modelData.scrollUp();
                    } else if (wheel.angleDelta.y < 0) {
                      trayDelegate.modelData.scrollDown();
                    }
                  }

                  onEntered: {
                    if (trayDelegate.drawer.popupMenuWindow) {
                      trayDelegate.drawer.popupMenuWindow.close();
                    }
                    TooltipService.show(trayIcon, trayDelegate.modelData.tooltipTitle || trayDelegate.modelData.name || trayDelegate.modelData.id || "Tray Item", BarService.getTooltipDirection());
                  }
                  onExited: TooltipService.hide()
                }
              }
            }
          }
        }
      }
    }
  }
}
