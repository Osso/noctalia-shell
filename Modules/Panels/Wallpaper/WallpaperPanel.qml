pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import "../../../Helpers/FuzzySort.js" as FuzzySort
import qs.Commons
import qs.Modules.MainScreen
import qs.Modules.Panels.Settings
import qs.Services.UI
import qs.Widgets

SmartPanel {
  id: root

  preferredWidth: 800 * Style.uiScaleRatio
  preferredHeight: 600 * Style.uiScaleRatio
  preferredWidthRatio: 0.5
  preferredHeightRatio: 0.45

  // Positioning
  readonly property string panelPosition: {
    if (Settings.data.wallpaper.panelPosition === "follow_bar") {
      if (Settings.data.bar.position === "left" || Settings.data.bar.position === "right") {
        return `center_${Settings.data.bar.position}`;
      } else {
        return `${Settings.data.bar.position}_center`;
      }
    } else {
      return Settings.data.wallpaper.panelPosition;
    }
  }
  panelAnchorHorizontalCenter: panelPosition === "center" || panelPosition.endsWith("_center")
  panelAnchorVerticalCenter: panelPosition === "center"
  panelAnchorLeft: panelPosition !== "center" && panelPosition.endsWith("_left")
  panelAnchorRight: panelPosition !== "center" && panelPosition.endsWith("_right")
  panelAnchorBottom: panelPosition.startsWith("bottom_")
  panelAnchorTop: panelPosition.startsWith("top_")

  // Store direct reference to content for instant access
  property Item contentItem: null

  function currentWallpaperView() {
    if (!contentItem) {
      return null;
    }
    return contentItem.screenRepeater.itemAt(contentItem.currentScreenIndex);
  }

  function currentGridView() {
    let view = currentWallpaperView();
    return view && view.gridView ? view.gridView : null;
  }

  // Override keyboard handlers to enable grid navigation
  function onDownPressed() {
    let gridView = currentGridView();
    if (!gridView) {
      return;
    }
    if (!gridView.activeFocus) {
      gridView.forceActiveFocus();
      if (gridView.currentIndex < 0) {
        gridView.currentIndex = 0;
      }
    } else {
      gridView.moveCurrentIndexDown();
    }
  }

  function onUpPressed() {
    let gridView = currentGridView();
    if (gridView && gridView.activeFocus) {
      gridView.moveCurrentIndexUp();
    }
  }

  function onLeftPressed() {
    let gridView = currentGridView();
    if (gridView && gridView.activeFocus) {
      gridView.moveCurrentIndexLeft();
    }
  }

  function onRightPressed() {
    let gridView = currentGridView();
    if (gridView && gridView.activeFocus) {
      gridView.moveCurrentIndexRight();
    }
  }

  function onReturnPressed() {
    let view = currentWallpaperView();
    let gridView = view && view.gridView ? view.gridView : null;
    if (gridView && gridView.activeFocus) {
      if (gridView.currentIndex >= 0 && gridView.currentIndex < gridView.model.length) {
        let path = gridView.model[gridView.currentIndex];
        if (Settings.data.wallpaper.setWallpaperOnAllMonitors) {
          WallpaperService.changeWallpaper(path, undefined);
        } else {
          WallpaperService.changeWallpaper(path, view.targetScreen.name);
        }
      }
    }
  }

  panelContent: Rectangle {
    id: wallpaperPanel

    property int currentScreenIndex: {
      if (screen !== null) {
        for (var i = 0; i < Quickshell.screens.length; i++) {
          if (Quickshell.screens[i].name == screen.name) {
            return i;
          }
        }
      }
      return 0;
    }
    property ShellScreen currentScreen: Quickshell.screens[currentScreenIndex]
    property string filterText: ""
    property alias screenRepeater: screenRepeater

    Component.onCompleted: {
      root.contentItem = wallpaperPanel;
    }

    // Function to update Wallhaven resolution filter
    function updateWallhavenResolution() {
      if (typeof WallhavenService === "undefined") {
        return;
      }

      var width = Settings.data.wallpaper.wallhavenResolutionWidth || "";
      var height = Settings.data.wallpaper.wallhavenResolutionHeight || "";
      var mode = Settings.data.wallpaper.wallhavenResolutionMode || "atleast";

      if (width && height) {
        var resolution = width + "x" + height;
        if (mode === "atleast") {
          WallhavenService.minResolution = resolution;
          WallhavenService.resolutions = "";
        } else {
          WallhavenService.minResolution = "";
          WallhavenService.resolutions = resolution;
        }
      } else {
        WallhavenService.minResolution = "";
        WallhavenService.resolutions = "";
      }

      // Trigger new search with updated resolution
      if (Settings.data.wallpaper.useWallhaven) {
        if (wallhavenView) {
          wallhavenView.loading = true;
        }
        WallhavenService.search(Settings.data.wallpaper.wallhavenQuery || "", 1);
      }
    }

    color: NColor.transparent

    // Wallhaven settings popup
    Loader {
      id: wallhavenSettingsPopup
      source: "WallhavenSettingsPopup.qml"
      onLoaded: {
        if (item) {
          item.screen = screen;
        }
      }
    }

    // Focus management
    Connections {
      target: root
      function onOpened() {
        // Ensure contentItem is set
        if (!root.contentItem) {
          root.contentItem = wallpaperPanel;
        }
        // Give initial focus to search input
        Qt.callLater(() => {
          if (searchInput.inputItem) {
            searchInput.inputItem.forceActiveFocus();
          }
        });
      }
    }

    // Debounce timer for search
    Timer {
      id: searchDebounceTimer
      interval: 150
      onTriggered: {
        wallpaperPanel.filterText = searchInput.text;
        // Trigger update on all screen views
        for (var i = 0; i < screenRepeater.count; i++) {
          let item = screenRepeater.itemAt(i) as WallpaperScreenView;
          if (item) {
            item.updateFiltered();
          }
        }
      }
    }

    ColumnLayout {
      anchors.fill: parent
      anchors.margins: Style.marginL
      spacing: Style.marginM

      // Header
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        NIcon {
          icon: "settings-wallpaper-selector"
          pointSize: Style.fontSizeXXL
          color: NColor.mPrimary
        }

        NText {
          text: I18n.tr("wallpaper.panel.title")
          pointSize: Style.fontSizeL
          font.weight: Style.fontWeightBold
          color: NColor.mOnSurface
          Layout.fillWidth: true
        }

        NIconButton {
          icon: "settings"
          tooltipText: I18n.tr("settings.wallpaper.settings.section.label")
          baseSize: Style.baseWidgetSize * 0.8
          onClicked: {
            var settingsPanel = PanelService.getPanel("settingsPanel", root.screen);
            settingsPanel.requestedTab = SettingsPanel.Tab.Wallpaper;
            settingsPanel.open();
          }
        }

        NIconButton {
          icon: "refresh"
          tooltipText: Settings.data.wallpaper.useWallhaven ? I18n.tr("tooltips.refresh-wallhaven") : I18n.tr("tooltips.refresh-wallpaper-list")
          baseSize: Style.baseWidgetSize * 0.8
          onClicked: {
            if (Settings.data.wallpaper.useWallhaven) {
              if (typeof WallhavenService !== "undefined") {
                WallhavenService.search(Settings.data.wallpaper.wallhavenQuery, 1);
              }
            } else {
              WallpaperService.refreshWallpapersList();
            }
          }
        }

        NIconButton {
          icon: "close"
          tooltipText: I18n.tr("tooltips.close")
          baseSize: Style.baseWidgetSize * 0.8
          onClicked: root.close()
        }
      }

      NDivider {
        Layout.fillWidth: true
      }

      // Debounce timer for Wallhaven search
      Timer {
        id: wallhavenSearchDebounceTimer
        interval: 500
        onTriggered: {
          Settings.data.wallpaper.wallhavenQuery = searchInput.text;
          if (typeof WallhavenService !== "undefined") {
            wallhavenView.loading = true;
            WallhavenService.search(searchInput.text, 1);
          }
        }
      }

      NToggle {
        label: I18n.tr("wallpaper.panel.apply-all-monitors.label")
        description: I18n.tr("wallpaper.panel.apply-all-monitors.description")
        checked: Settings.data.wallpaper.setWallpaperOnAllMonitors
        onToggled: checked => Settings.data.wallpaper.setWallpaperOnAllMonitors = checked
        Layout.fillWidth: true
      }

      // Monitor tabs
      NTabBar {
        id: screenTabBar
        visible: (!Settings.data.wallpaper.setWallpaperOnAllMonitors || Settings.data.wallpaper.enableMultiMonitorDirectories)
        Layout.fillWidth: true
        currentIndex: wallpaperPanel.currentScreenIndex
        onCurrentIndexChanged: wallpaperPanel.currentScreenIndex = currentIndex
        spacing: Style.marginM

        Repeater {
          model: Quickshell.screens
          ScreenTab {
            tabs: screenTabBar
          }
        }
      }

      // Unified search input and source
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        NTextInput {
          id: searchInput
          placeholderText: Settings.data.wallpaper.useWallhaven ? I18n.tr("placeholders.search-wallhaven") : I18n.tr("placeholders.search-wallpapers")
          Layout.fillWidth: true

          property bool initializing: true
          Component.onCompleted: {
            // Initialize text based on current mode
            if (Settings.data.wallpaper.useWallhaven) {
              searchInput.text = Settings.data.wallpaper.wallhavenQuery || "";
            } else {
              searchInput.text = wallpaperPanel.filterText || "";
            }
            // Give focus to search input
            if (searchInput.inputItem && searchInput.inputItem.visible) {
              searchInput.inputItem.forceActiveFocus();
            }
            // Mark initialization as complete after a short delay
            Qt.callLater(function () {
              searchInput.initializing = false;
            });
          }

          Connections {
            target: Settings.data.wallpaper
            function onUseWallhavenChanged() {
              // Update text when mode changes
              if (Settings.data.wallpaper.useWallhaven) {
                searchInput.text = Settings.data.wallpaper.wallhavenQuery || "";
              } else {
                searchInput.text = wallpaperPanel.filterText || "";
              }
            }
          }

          onTextChanged: {
            // Don't trigger search during initialization - Component.onCompleted will handle initial search
            if (initializing) {
              return;
            }
            if (Settings.data.wallpaper.useWallhaven) {
              wallhavenSearchDebounceTimer.restart();
            } else {
              searchDebounceTimer.restart();
            }
          }

          onEditingFinished: {
            if (Settings.data.wallpaper.useWallhaven) {
              wallhavenSearchDebounceTimer.stop();
              Settings.data.wallpaper.wallhavenQuery = text;
              if (typeof WallhavenService !== "undefined") {
                wallhavenView.loading = true;
                WallhavenService.search(text, 1);
              }
            }
          }

          Keys.onDownPressed: {
            if (Settings.data.wallpaper.useWallhaven) {
              if (wallhavenView && wallhavenView.gridView) {
                wallhavenView.gridView.forceActiveFocus();
              }
            } else {
              let currentView = screenRepeater.itemAt(wallpaperPanel.currentScreenIndex) as WallpaperScreenView;
              if (currentView && currentView.gridView) {
                currentView.gridView.forceActiveFocus();
              }
            }
          }
        }

        NComboBox {
          id: sourceComboBox
          Layout.fillWidth: false

          model: [
            {
              "key": "local",
              "name": I18n.tr("wallpaper.panel.source.local")
            },
            {
              "key": "wallhaven",
              "name": I18n.tr("wallpaper.panel.source.wallhaven")
            }
          ]
          currentKey: Settings.data.wallpaper.useWallhaven ? "wallhaven" : "local"
          property bool skipNextSelected: false
          Component.onCompleted: {
            // Skip the first onSelected if it fires during initialization
            skipNextSelected = true;
            Qt.callLater(function () {
              skipNextSelected = false;
            });
          }
          onSelected: key => {
            if (skipNextSelected) {
              return;
            }
            var useWallhaven = (key === "wallhaven");
            Settings.data.wallpaper.useWallhaven = useWallhaven;
            // Update search input text based on mode
            if (useWallhaven) {
              searchInput.text = Settings.data.wallpaper.wallhavenQuery || "";
            } else {
              searchInput.text = wallpaperPanel.filterText || "";
            }
            if (useWallhaven && typeof WallhavenService !== "undefined") {
              // Update service properties when switching to Wallhaven
              // Don't search here - Component.onCompleted will handle it when the component is created
              // This prevents duplicate searches
              WallhavenService.categories = Settings.data.wallpaper.wallhavenCategories;
              WallhavenService.purity = Settings.data.wallpaper.wallhavenPurity;
              WallhavenService.sorting = Settings.data.wallpaper.wallhavenSorting;
              WallhavenService.order = Settings.data.wallpaper.wallhavenOrder;

              // Update resolution settings
              wallpaperPanel.updateWallhavenResolution();

              // If the view is already initialized, trigger a new search when switching to it
              if (wallhavenView && wallhavenView.initialized && !WallhavenService.fetching) {
                wallhavenView.loading = true;
                WallhavenService.search(Settings.data.wallpaper.wallhavenQuery || "", 1);
              }
            }
          }
        }

        // Settings button (only visible for Wallhaven)
        NIconButton {
          id: wallhavenSettingsButton
          icon: "settings"
          tooltipText: I18n.tr("wallpaper.panel.wallhaven-settings.title")
          baseSize: Style.baseWidgetSize * 0.8
          visible: Settings.data.wallpaper.useWallhaven
          onClicked: {
            if (searchInput.inputItem) {
              searchInput.inputItem.focus = false;
            }
            const popup = wallhavenSettingsPopup.item as WallhavenSettingsPopup;
            if (popup) {
              popup.showAt(wallhavenSettingsButton);
            }
          }
        }
      }

      // Content stack: Wallhaven or Local
      StackLayout {
        id: contentStack
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: Settings.data.wallpaper.useWallhaven ? 1 : 0

        // Local wallpapers
        StackLayout {
          id: screenStack
          currentIndex: wallpaperPanel.currentScreenIndex

          Repeater {
            id: screenRepeater
            model: Quickshell.screens
            delegate: WallpaperScreenView {
              required property ShellScreen modelData

              filterText: wallpaperPanel.filterText
              panelScreen: root.screen
              targetScreen: modelData
            }
          }
        }

        // Wallhaven wallpapers
        WallhavenView {
          id: wallhavenView
          currentScreenIndex: wallpaperPanel.currentScreenIndex
          panelScreen: root.screen
        }
      }
    }
  }

  component ScreenTab: NTabButton {
    required property ShellScreen modelData
    required property int index
    required property NTabBar tabs
    readonly property string screenName: modelData ? modelData.name : ""

    text: screenName || `Screen ${index + 1}`
    tabIndex: index
    checked: {
      tabs.currentIndex === index;
    }
  }

  component LocalGrid: GridView {
    required property WallpaperScreenView screenView
  }

  component LocalWallpaperDelegate: ColumnLayout {
    id: wallpaperItem
    readonly property LocalGrid owningGrid: GridView.view as LocalGrid
    readonly property int itemSize: owningGrid.cellWidth
    readonly property WallpaperScreenView screenView: owningGrid.screenView

    required property string modelData
    required property int index
    property string wallpaperPath: modelData
    property bool isSelected: (wallpaperPath === wallpaperItem.screenView.currentWallpaper)
    property string filename: wallpaperPath.split('/').pop()

    width: wallpaperItem.itemSize
    spacing: Style.marginXS

    Rectangle {
      id: imageContainer
      Layout.fillWidth: true
      Layout.preferredHeight: Math.round(wallpaperItem.itemSize * 0.67)
      color: NColor.transparent

      NImageCached {
        id: img
        imagePath: wallpaperItem.wallpaperPath
        cacheFolder: Settings.cacheDirImagesWallpapers
        anchors.fill: parent
      }

      Rectangle {
        anchors.fill: parent
        color: NColor.transparent
        border.color: {
          if (wallpaperItem.isSelected) {
            return NColor.mSecondary;
          }
          if (wallpaperItem.owningGrid.currentIndex === wallpaperItem.index) {
            return NColor.mHover;
          }
          return NColor.mSurface;
        }
        border.width: Math.max(1, Style.borderL * 1.5)
      }

      Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Style.marginS
        width: 28
        height: 28
        radius: width / 2
        color: NColor.mSecondary
        border.color: NColor.mOutline
        border.width: Style.borderS
        visible: wallpaperItem.isSelected

        NIcon {
          icon: "check"
          pointSize: Style.fontSizeM
          color: NColor.mOnSecondary
          anchors.centerIn: parent
        }
      }

      Rectangle {
        anchors.fill: parent
        color: NColor.mSurface
        opacity: (hoverHandler.hovered || wallpaperItem.isSelected || wallpaperItem.owningGrid.currentIndex === wallpaperItem.index) ? 0 : 0.3
        radius: parent.radius
        Behavior on opacity {
          NumberAnimation {
            duration: Style.animationFast
          }
        }
      }

      // More efficient hover handling
      HoverHandler {
        id: hoverHandler
      }

      TapHandler {
        onTapped: {
          wallpaperItem.owningGrid.forceActiveFocus();
          wallpaperItem.owningGrid.currentIndex = wallpaperItem.index;
          if (Settings.data.wallpaper.setWallpaperOnAllMonitors) {
            WallpaperService.changeWallpaper(wallpaperItem.wallpaperPath, undefined);
          } else {
            WallpaperService.changeWallpaper(wallpaperItem.wallpaperPath, wallpaperItem.screenView.targetScreen.name);
          }
        }
      }
    }

    NText {
      text: wallpaperItem.filename
      visible: !Settings.data.wallpaper.hideWallpaperFilenames
      color: (hoverHandler.hovered || wallpaperItem.isSelected || wallpaperItem.owningGrid.currentIndex === wallpaperItem.index) ? NColor.mOnSurface : NColor.mOnSurfaceVariant
      pointSize: Style.fontSizeXS
      Layout.fillWidth: true
      Layout.leftMargin: Style.marginS
      Layout.rightMargin: Style.marginS
      Layout.alignment: Qt.AlignHCenter
      horizontalAlignment: Text.AlignHCenter
      elide: Text.ElideRight
    }
  }

  // Component for each screen's wallpaper view
  component WallpaperScreenView: Item {
    id: wallpaperScreenView
    required property string filterText
    required property ShellScreen panelScreen
    property ShellScreen targetScreen
    property alias gridView: wallpaperGridView

    // Local reactive state for this screen
    property var wallpapersList: []
    property string currentWallpaper: ""
    property var filteredWallpapers: []
    property var wallpapersWithNames: [] // Cached basenames

    // Expose updateFiltered as a proper function property
    function updateFiltered() {
      if (!filterText || filterText.trim().length === 0) {
        filteredWallpapers = wallpapersList;
        return;
      }

      const results = FuzzySort.go(filterText.trim(), wallpapersWithNames, {
        "key": 'name',
        "limit": 200
      });
      // Map back to path list
      filteredWallpapers = results.map(function (r) {
        return r.obj.path;
      });
    }

    Component.onCompleted: {
      refreshWallpaperScreenData();
    }

    Connections {
      target: WallpaperService
      function onWallpaperChanged(screenName, path) {
        if (wallpaperScreenView.targetScreen !== null && screenName === wallpaperScreenView.targetScreen.name) {
          wallpaperScreenView.currentWallpaper = WallpaperService.getWallpaper(wallpaperScreenView.targetScreen.name);
        }
      }
      function onWallpaperDirectoryChanged(screenName, directory) {
        if (wallpaperScreenView.targetScreen !== null && screenName === wallpaperScreenView.targetScreen.name) {
          wallpaperScreenView.refreshWallpaperScreenData();
        }
      }
      function onWallpaperListChanged(screenName, count) {
        if (wallpaperScreenView.targetScreen !== null && screenName === wallpaperScreenView.targetScreen.name) {
          wallpaperScreenView.refreshWallpaperScreenData();
        }
      }
    }

    function refreshWallpaperScreenData() {
      if (targetScreen === null) {
        return;
      }
      wallpapersList = WallpaperService.getWallpapersList(targetScreen.name);
      Logger.d("WallpaperPanel", "Got", wallpapersList.length, "wallpapers for screen", targetScreen.name);

      // Pre-compute basenames once for better performance
      wallpapersWithNames = wallpapersList.map(function (p) {
        return {
          "path": p,
          "name": p.split('/').pop()
        };
      });

      currentWallpaper = WallpaperService.getWallpaper(targetScreen.name);
      updateFiltered();
    }

    ColumnLayout {
      anchors.fill: parent
      spacing: Style.marginM

      LocalGrid {
        id: wallpaperGridView
        screenView: wallpaperScreenView

        Layout.fillWidth: true
        Layout.fillHeight: true

        visible: !WallpaperService.scanning
        interactive: true
        clip: true
        focus: true
        keyNavigationEnabled: true
        keyNavigationWraps: false

        model: wallpaperScreenView.filteredWallpapers

        // Capture clicks on empty areas to give focus to GridView
        MouseArea {
          anchors.fill: parent
          z: -1
          onClicked: {
            wallpaperGridView.forceActiveFocus();
            if (wallpaperGridView.currentIndex < 0 && wallpaperScreenView.filteredWallpapers.length > 0) {
              wallpaperGridView.currentIndex = 0;
            }
          }
        }

        property int columns: (wallpaperScreenView.panelScreen.width > 1920) ? 5 : 4
        property int itemSize: cellWidth

        cellWidth: Math.floor((width - leftMargin - rightMargin) / columns)
        cellHeight: Math.floor(itemSize * 0.7) + Style.marginXS + Style.fontSizeXS + Style.marginM

        leftMargin: Style.marginS
        rightMargin: Style.marginS
        topMargin: Style.marginS
        bottomMargin: Style.marginS

        onCurrentIndexChanged: {
          // Synchronize scroll with current item position
          if (currentIndex >= 0) {
            let row = Math.floor(currentIndex / columns);
            let itemY = row * cellHeight;
            let viewportTop = contentY;
            let viewportBottom = viewportTop + height;

            // If item is out of view, scroll
            if (itemY < viewportTop) {
              contentY = Math.max(0, itemY - cellHeight);
            } else if (itemY + cellHeight > viewportBottom) {
              contentY = itemY + cellHeight - height + cellHeight;
            }
          }
        }

        Keys.onPressed: event => {
          if (event.key === Qt.Key_Return || event.key === Qt.Key_Space) {
            if (currentIndex >= 0 && currentIndex < wallpaperScreenView.filteredWallpapers.length) {
              let path = wallpaperScreenView.filteredWallpapers[currentIndex];
              if (Settings.data.wallpaper.setWallpaperOnAllMonitors) {
                WallpaperService.changeWallpaper(path, undefined);
              } else {
                WallpaperService.changeWallpaper(path, wallpaperScreenView.targetScreen.name);
              }
            }
            event.accepted = true;
          }
        }

        ScrollBar.vertical: ScrollBar {
          id: localScrollBar
          policy: ScrollBar.AsNeeded
          parent: wallpaperGridView
          LayoutMirroring.enabled: wallpaperGridView.LayoutMirroring.enabled
          x: localScrollBar.mirrored ? 0 : wallpaperGridView.width - width
          y: 0
          height: wallpaperGridView.height

          property color handleColor: Qt.alpha(NColor.mHover, 0.8)
          property color handleHoverColor: handleColor
          property color handlePressedColor: handleColor
          property real handleWidth: 6
          property real handleRadius: Style.radiusM

          contentItem: Rectangle {
            implicitWidth: localScrollBar.handleWidth
            implicitHeight: 100
            radius: localScrollBar.handleRadius
            color: localScrollBar.pressed ? localScrollBar.handlePressedColor : localScrollBar.hovered ? localScrollBar.handleHoverColor : localScrollBar.handleColor
            opacity: localScrollBar.policy === ScrollBar.AlwaysOn || localScrollBar.active ? 1.0 : 0.0

            Behavior on opacity {
              NumberAnimation {
                duration: Style.animationFast
              }
            }

            Behavior on color {
              ColorAnimation {
                duration: Style.animationFast
              }
            }
          }

          background: Rectangle {
            implicitWidth: localScrollBar.handleWidth
            implicitHeight: 100
            color: NColor.transparent
            opacity: localScrollBar.policy === ScrollBar.AlwaysOn || localScrollBar.active ? 0.3 : 0.0
            radius: localScrollBar.handleRadius / 2

            Behavior on opacity {
              NumberAnimation {
                duration: Style.animationFast
              }
            }
          }
        }

        delegate: LocalWallpaperDelegate {}
      }

      // Empty / scanning state
      Rectangle {
        color: NColor.mSurface
        radius: Style.radiusM
        border.color: NColor.mOutline
        border.width: Style.borderS
        visible: (wallpaperScreenView.filteredWallpapers.length === 0 && !WallpaperService.scanning) || WallpaperService.scanning
        Layout.fillWidth: true
        Layout.preferredHeight: 130

        ColumnLayout {
          anchors.fill: parent
          visible: WallpaperService.scanning
          NBusyIndicator {
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
          }
        }

        ColumnLayout {
          anchors.fill: parent
          visible: wallpaperScreenView.filteredWallpapers.length === 0 && !WallpaperService.scanning
          Item {
            Layout.fillHeight: true
          }
          NIcon {
            icon: "folder-open"
            pointSize: Style.fontSizeXXL
            color: NColor.mOnSurface
            Layout.alignment: Qt.AlignHCenter
          }
          NText {
            text: (wallpaperScreenView.filterText && wallpaperScreenView.filterText.length > 0) ? I18n.tr("wallpaper.no-match") : I18n.tr("wallpaper.no-wallpaper")
            color: NColor.mOnSurface
            font.weight: Style.fontWeightBold
            Layout.alignment: Qt.AlignHCenter
          }
          NText {
            text: (wallpaperScreenView.filterText && wallpaperScreenView.filterText.length > 0) ? I18n.tr("wallpaper.try-different-search") : I18n.tr("wallpaper.configure-directory")
            color: NColor.mOnSurfaceVariant
            wrapMode: Text.WordWrap
            Layout.alignment: Qt.AlignHCenter
          }
          Item {
            Layout.fillHeight: true
          }
        }
      }
    }
  }

  component WallhavenGrid: GridView {
    required property WallhavenView screenView
  }

  component WallhavenWallpaperDelegate: ColumnLayout {
    id: wallhavenItem
    readonly property WallhavenGrid owningGrid: GridView.view as WallhavenGrid
    readonly property int itemSize: owningGrid.cellWidth
    readonly property WallhavenView screenView: owningGrid.screenView

    required property var modelData
    required property int index
    readonly property string thumbnailUrl: (modelData && typeof WallhavenService !== "undefined") ? WallhavenService.getThumbnailUrl(modelData, "large") : ""
    readonly property string wallpaperId: (modelData && modelData.id) || ""

    width: wallhavenItem.itemSize
    spacing: Style.marginXS

    Rectangle {
      id: imageContainer
      Layout.fillWidth: true
      Layout.preferredHeight: Math.round(wallhavenItem.itemSize * 0.67)
      color: NColor.transparent

      Image {
        id: img
        source: wallhavenItem.thumbnailUrl
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        smooth: true
        sourceSize.width: Math.round(wallhavenItem.itemSize * 0.67)
        sourceSize.height: Math.round(wallhavenItem.itemSize * 0.67)
      }

      Rectangle {
        anchors.fill: parent
        color: NColor.transparent
        border.color: wallhavenItem.owningGrid.currentIndex === wallhavenItem.index ? NColor.mHover : NColor.mSurface
        border.width: Math.max(1, Style.borderL * 1.5)
      }

      Rectangle {
        anchors.fill: parent
        color: NColor.mSurface
        opacity: hoverHandler.hovered || wallhavenItem.owningGrid.currentIndex === wallhavenItem.index ? 0 : 0.3
        Behavior on opacity {
          NumberAnimation {
            duration: Style.animationFast
          }
        }
      }

      HoverHandler {
        id: hoverHandler
      }

      TapHandler {
        onTapped: {
          wallhavenItem.owningGrid.currentIndex = wallhavenItem.index;
          wallhavenItem.screenView.wallhavenDownloadAndApply(wallhavenItem.modelData);
        }
      }
    }

    NText {
      text: wallhavenItem.wallpaperId || I18n.tr("wallpaper.unknown")
      visible: !Settings.data.wallpaper.hideWallpaperFilenames
      color: hoverHandler.hovered || wallhavenItem.owningGrid.currentIndex === wallhavenItem.index ? NColor.mOnSurface : NColor.mOnSurfaceVariant
      pointSize: Style.fontSizeXS
      Layout.fillWidth: true
      Layout.leftMargin: Style.marginS
      Layout.rightMargin: Style.marginS
      Layout.alignment: Qt.AlignHCenter
      horizontalAlignment: Text.AlignHCenter
      elide: Text.ElideRight
    }
  }

  // Component for Wallhaven wallpapers view
  component WallhavenView: Item {
    id: wallhavenViewRoot
    required property int currentScreenIndex
    required property ShellScreen panelScreen
    property alias gridView: wallhavenGridView

    property var wallpapers: []
    property bool loading: false
    property string errorMessage: ""
    property bool initialized: false
    property bool searchScheduled: false

    Connections {
      target: typeof WallhavenService !== "undefined" ? WallhavenService : null
      function onSearchCompleted(results, meta) {
        wallhavenViewRoot.wallpapers = results || [];
        wallhavenViewRoot.loading = false;
        wallhavenViewRoot.errorMessage = "";
        wallhavenViewRoot.searchScheduled = false;
      }
      function onSearchFailed(error) {
        wallhavenViewRoot.loading = false;
        wallhavenViewRoot.errorMessage = error || "";
        wallhavenViewRoot.searchScheduled = false;
      }
    }

    Component.onCompleted: {
      // Initialize service properties and perform initial search if Wallhaven is active
      if (typeof WallhavenService !== "undefined" && Settings.data.wallpaper.useWallhaven && !initialized) {
        // Set flags immediately to prevent race conditions
        if (WallhavenService.initialSearchScheduled) {
          // Another instance already scheduled the search, just initialize properties
          initialized = true;
          return;
        }

        // We're the first one - claim the search
        initialized = true;
        WallhavenService.initialSearchScheduled = true;
        WallhavenService.categories = Settings.data.wallpaper.wallhavenCategories;
        WallhavenService.purity = Settings.data.wallpaper.wallhavenPurity;
        WallhavenService.sorting = Settings.data.wallpaper.wallhavenSorting;
        WallhavenService.order = Settings.data.wallpaper.wallhavenOrder;

        // Initialize resolution settings
        var width = Settings.data.wallpaper.wallhavenResolutionWidth || "";
        var height = Settings.data.wallpaper.wallhavenResolutionHeight || "";
        var mode = Settings.data.wallpaper.wallhavenResolutionMode || "atleast";
        if (width && height) {
          var resolution = width + "x" + height;
          if (mode === "atleast") {
            WallhavenService.minResolution = resolution;
            WallhavenService.resolutions = "";
          } else {
            WallhavenService.minResolution = "";
            WallhavenService.resolutions = resolution;
          }
        } else {
          WallhavenService.minResolution = "";
          WallhavenService.resolutions = "";
        }

        // Now check if we can actually search (fetching check is in WallhavenService.search)
        loading = true;
        WallhavenService.search(Settings.data.wallpaper.wallhavenQuery || "", 1);
      }
    }

    ColumnLayout {
      anchors.fill: parent
      spacing: Style.marginM

      Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        WallhavenGrid {
          id: wallhavenGridView
          screenView: wallhavenViewRoot

          anchors.fill: parent

          visible: !wallhavenViewRoot.loading && wallhavenViewRoot.errorMessage === "" && (wallhavenViewRoot.wallpapers && wallhavenViewRoot.wallpapers.length > 0)
          interactive: true
          clip: true
          focus: true
          keyNavigationEnabled: true
          keyNavigationWraps: false

          model: wallhavenViewRoot.wallpapers || []

          property int columns: (wallhavenViewRoot.panelScreen.width > 1920) ? 5 : 4
          property int itemSize: cellWidth

          cellWidth: Math.floor((width - leftMargin - rightMargin) / columns)
          cellHeight: Math.floor(itemSize * 0.7) + Style.marginXS + (Settings.data.wallpaper.hideWallpaperFilenames ? 0 : Style.fontSizeXS + Style.marginM)

          leftMargin: Style.marginS
          rightMargin: Style.marginS
          topMargin: Style.marginS
          bottomMargin: Style.marginS

          onCurrentIndexChanged: {
            if (currentIndex >= 0) {
              let row = Math.floor(currentIndex / columns);
              let itemY = row * cellHeight;
              let viewportTop = contentY;
              let viewportBottom = viewportTop + height;

              if (itemY < viewportTop) {
                contentY = Math.max(0, itemY - cellHeight);
              } else if (itemY + cellHeight > viewportBottom) {
                contentY = itemY + cellHeight - height + cellHeight;
              }
            }
          }

          Keys.onPressed: event => {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Space) {
              if (currentIndex >= 0 && currentIndex < wallhavenViewRoot.wallpapers.length) {
                let wallpaper = wallhavenViewRoot.wallpapers[currentIndex];
                wallhavenViewRoot.wallhavenDownloadAndApply(wallpaper);
              }
              event.accepted = true;
            }
          }

          ScrollBar.vertical: ScrollBar {
            id: wallhavenScrollBar
            policy: ScrollBar.AsNeeded
            parent: wallhavenGridView
            LayoutMirroring.enabled: wallhavenGridView.LayoutMirroring.enabled
            x: wallhavenScrollBar.mirrored ? 0 : wallhavenGridView.width - width
            y: 0
            height: wallhavenGridView.height

            property color handleColor: Qt.alpha(NColor.mHover, 0.8)
            property color handleHoverColor: handleColor
            property color handlePressedColor: handleColor
            property real handleWidth: 6
            property real handleRadius: Style.radiusM

            contentItem: Rectangle {
              implicitWidth: wallhavenScrollBar.handleWidth
              implicitHeight: 100
              radius: wallhavenScrollBar.handleRadius
              color: wallhavenScrollBar.pressed ? wallhavenScrollBar.handlePressedColor : wallhavenScrollBar.hovered ? wallhavenScrollBar.handleHoverColor : wallhavenScrollBar.handleColor
              opacity: wallhavenScrollBar.policy === ScrollBar.AlwaysOn || wallhavenScrollBar.active ? 1.0 : 0.0

              Behavior on opacity {
                NumberAnimation {
                  duration: Style.animationFast
                }
              }

              Behavior on color {
                ColorAnimation {
                  duration: Style.animationFast
                }
              }
            }

            background: Rectangle {
              implicitWidth: wallhavenScrollBar.handleWidth
              implicitHeight: 100
              color: NColor.transparent
              opacity: wallhavenScrollBar.policy === ScrollBar.AlwaysOn || wallhavenScrollBar.active ? 0.3 : 0.0
              radius: wallhavenScrollBar.handleRadius / 2

              Behavior on opacity {
                NumberAnimation {
                  duration: Style.animationFast
                }
              }
            }
          }

          delegate: WallhavenWallpaperDelegate {}
        }

        // Loading overlay - fills same space as GridView to prevent jumping
        Rectangle {
          anchors.fill: parent
          color: NColor.mSurface
          radius: Style.radiusM
          border.color: NColor.mOutline
          border.width: Style.borderS
          visible: wallhavenViewRoot.loading
          z: 10

          ColumnLayout {
            anchors.fill: parent
            anchors.margins: Style.marginL
            spacing: Style.marginM

            Item {
              Layout.fillHeight: true
            }

            NBusyIndicator {
              size: Style.baseWidgetSize * 1.5
              color: NColor.mPrimary
              Layout.alignment: Qt.AlignHCenter
            }

            NText {
              text: I18n.tr("wallpaper.wallhaven.loading")
              color: NColor.mOnSurfaceVariant
              pointSize: Style.fontSizeM
              Layout.alignment: Qt.AlignHCenter
            }

            Item {
              Layout.fillHeight: true
            }
          }
        }

        // Error overlay
        Rectangle {
          anchors.fill: parent
          color: NColor.mSurface
          radius: Style.radiusM
          border.color: NColor.mOutline
          border.width: Style.borderS
          visible: wallhavenViewRoot.errorMessage !== "" && !wallhavenViewRoot.loading
          z: 10

          ColumnLayout {
            anchors.fill: parent
            anchors.margins: Style.marginL
            spacing: Style.marginM

            Item {
              Layout.fillHeight: true
            }

            NIcon {
              icon: "alert-circle"
              pointSize: Style.fontSizeXXL
              color: NColor.mError
              Layout.alignment: Qt.AlignHCenter
            }

            NText {
              text: wallhavenViewRoot.errorMessage
              color: NColor.mOnSurface
              wrapMode: Text.WordWrap
              Layout.alignment: Qt.AlignHCenter
              Layout.fillWidth: true
              horizontalAlignment: Text.AlignHCenter
            }

            Item {
              Layout.fillHeight: true
            }
          }
        }

        // Empty state overlay
        Rectangle {
          anchors.fill: parent
          color: NColor.mSurface
          radius: Style.radiusM
          border.color: NColor.mOutline
          border.width: Style.borderS
          visible: (!wallhavenViewRoot.wallpapers || wallhavenViewRoot.wallpapers.length === 0) && !wallhavenViewRoot.loading && wallhavenViewRoot.errorMessage === ""
          z: 10

          ColumnLayout {
            anchors.fill: parent
            anchors.margins: Style.marginL
            spacing: Style.marginM

            Item {
              Layout.fillHeight: true
            }

            NIcon {
              icon: "image"
              pointSize: Style.fontSizeXXL
              color: NColor.mOnSurfaceVariant
              Layout.alignment: Qt.AlignHCenter
            }

            NText {
              text: I18n.tr("wallpaper.wallhaven.no-results")
              color: NColor.mOnSurface
              wrapMode: Text.WordWrap
              Layout.alignment: Qt.AlignHCenter
              Layout.fillWidth: true
              horizontalAlignment: Text.AlignHCenter
            }

            Item {
              Layout.fillHeight: true
            }
          }
        }
      }

      // Pagination
      RowLayout {
        Layout.fillWidth: true
        visible: !wallhavenViewRoot.loading && wallhavenViewRoot.errorMessage === "" && typeof WallhavenService !== "undefined"
        spacing: Style.marginS

        Item {
          Layout.fillWidth: true
        }

        NIconButton {
          icon: "chevron-left"
          enabled: WallhavenService.currentPage > 1 && !WallhavenService.fetching
          onClicked: WallhavenService.previousPage()
        }

        NText {
          text: I18n.tr("wallpaper.wallhaven.page").replace("{current}", WallhavenService.currentPage).replace("{total}", WallhavenService.lastPage)
          color: NColor.mOnSurface
          horizontalAlignment: Text.AlignHCenter
        }

        NIconButton {
          icon: "chevron-right"
          enabled: WallhavenService.currentPage < WallhavenService.lastPage && !WallhavenService.fetching
          onClicked: WallhavenService.nextPage()
        }

        Item {
          Layout.fillWidth: true
        }
      }
    }

    // -------------------------------
    function wallhavenDownloadAndApply(wallpaper, targetScreen) {
      if (typeof WallhavenService !== "undefined") {
        WallhavenService.downloadWallpaper(wallpaper, function (success, localPath) {
          if (success) {
            if (!Settings.data.wallpaper.setWallpaperOnAllMonitors && wallhavenViewRoot.currentScreenIndex < Quickshell.screens.length) {
              WallpaperService.changeWallpaper(localPath, Quickshell.screens[wallhavenViewRoot.currentScreenIndex].name);
            } else {
              WallpaperService.changeWallpaper(localPath, undefined);
            }
          }
        });
      }
    }
  }
}
