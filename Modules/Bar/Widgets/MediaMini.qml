import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Services.Media
import qs.Services.UI
import qs.Widgets
import qs.Widgets.AudioSpectrum

Item {
  id: root

  property ShellScreen screen

  // Widget properties passed from Bar.qml for per-instance settings
  property string widgetId: ""
  property string section: ""
  property int sectionWidgetIndex: -1
  property int sectionWidgetsCount: 0
  property real scaling: 1.0

  property var widgetMetadata: BarWidgetRegistry.widgetMetadata.MediaMini
  property var widgetSettings: {
    if (section && sectionWidgetIndex >= 0) {
      const widgets = Settings.data.bar.widgets[section];
      if (widgets && sectionWidgetIndex < widgets.length) {
        return widgets[sectionWidgetIndex];
      }
    }
    return {};
  }

  readonly property bool isVerticalBar: (Settings.data.bar.position === "left" || Settings.data.bar.position === "right")

  readonly property string hideMode: (widgetSettings.hideMode !== undefined) ? widgetSettings.hideMode : "hidden" // "visible", "hidden", "transparent", "idle"
  // Backward compatibility: honor legacy hideWhenIdle setting if present
  readonly property bool hideWhenIdle: (widgetSettings.hideWhenIdle !== undefined) ? widgetSettings.hideWhenIdle : (widgetMetadata.hideWhenIdle !== undefined ? widgetMetadata.hideWhenIdle : false)
  readonly property bool showAlbumArt: (widgetSettings.showAlbumArt !== undefined) ? widgetSettings.showAlbumArt : widgetMetadata.showAlbumArt
  readonly property bool showArtistFirst: (widgetSettings.showArtistFirst !== undefined) ? widgetSettings.showArtistFirst : widgetMetadata.showArtistFirst
  readonly property bool showVisualizer: (widgetSettings.showVisualizer !== undefined) ? widgetSettings.showVisualizer : widgetMetadata.showVisualizer
  readonly property string visualizerType: (widgetSettings.visualizerType !== undefined && widgetSettings.visualizerType !== "") ? widgetSettings.visualizerType : widgetMetadata.visualizerType
  readonly property string scrollingMode: (widgetSettings.scrollingMode !== undefined) ? widgetSettings.scrollingMode : widgetMetadata.scrollingMode
  readonly property bool showProgressRing: (widgetSettings.showProgressRing !== undefined) ? widgetSettings.showProgressRing : widgetMetadata.showProgressRing

  // Private constants for element sizes
  readonly property int _iconOnlySize: Math.round(18 * scaling)
  readonly property int _artAndProgressSize: Math.round(21 * scaling)

  // Maximum widget width with user settings support
  readonly property real maxWidth: (widgetSettings.maxWidth !== undefined) ? widgetSettings.maxWidth : Math.max(widgetMetadata.maxWidth, screen ? screen.width * 0.06 : 0)
  readonly property bool useFixedWidth: (widgetSettings.useFixedWidth !== undefined) ? widgetSettings.useFixedWidth : widgetMetadata.useFixedWidth

  readonly property bool hasActivePlayer: MediaService.currentPlayer !== null
  property bool mediaPositionRegistered: false
  readonly property string placeholderText: I18n.tr("bar.widget-settings.media-mini.no-active-player")

  readonly property string tooltipText: {
    var title = getTitle();
    var controls = "";
    if (MediaService.canGoNext) {
      controls += "Right click for next.\n";
    }
    if (MediaService.canGoPrevious) {
      controls += "Middle click for previous.";
    }
    if (controls !== "") {
      return title + "\n\n" + controls;
    }
    return title;
  }

  // Hide conditions
  readonly property bool shouldHideIdle: ((hideMode === "idle") || hideWhenIdle) && !MediaService.isPlaying
  readonly property bool isEmptyForHideMode: (!hasActivePlayer) && (hideMode === "hidden")

  implicitHeight: visible ? (isVerticalBar ? ((shouldHideIdle || isEmptyForHideMode) ? 0 : calculatedVerticalDimension()) : Style.capsuleHeight) : 0
  implicitWidth: visible ? (isVerticalBar ? ((shouldHideIdle || isEmptyForHideMode) ? 0 : calculatedVerticalDimension()) : ((shouldHideIdle || isEmptyForHideMode) ? 0 : dynamicWidth)) : 0

  // "visible": Always Visible, "hidden": Hide When Empty, "transparent": Transparent When Empty, "idle": Hide When Idle (not playing)
  visible: shouldHideIdle ? false : (hideMode !== "hidden" || opacity > 0)
  opacity: shouldHideIdle ? 0.0 : (((hideMode !== "hidden" || hasActivePlayer) && (hideMode !== "transparent" || hasActivePlayer)) ? 1.0 : 0.0)
  Behavior on opacity {
    NumberAnimation {
      duration: Style.animationNormal
      easing.type: Easing.InOutCubic
    }
  }

  Behavior on implicitWidth {
    NumberAnimation {
      duration: Style.animationNormal
      easing.type: Easing.InOutCubic
    }
  }
  Behavior on implicitHeight {
    NumberAnimation {
      duration: Style.animationNormal
      easing.type: Easing.InOutCubic
    }
  }

  Component.onCompleted: {
    if (visible && !mediaPositionRegistered) {
      MediaService.beginPositionUpdates(false);
      mediaPositionRegistered = true;
    }
  }

  onVisibleChanged: {
    if (visible && !mediaPositionRegistered) {
      MediaService.beginPositionUpdates(false);
      mediaPositionRegistered = true;
    } else if (!visible && mediaPositionRegistered) {
      MediaService.endPositionUpdates(false);
      mediaPositionRegistered = false;
    }
  }

  Component.onDestruction: {
    if (mediaPositionRegistered) {
      MediaService.endPositionUpdates(false);
      mediaPositionRegistered = false;
    }
  }

  function getTitle() {
    if (showArtistFirst) {
      return (MediaService.trackArtist !== "" ? `${MediaService.trackArtist} - ` : "") + MediaService.trackTitle;
    } else {
      return MediaService.trackTitle + (MediaService.trackArtist !== "" ? ` - ${MediaService.trackArtist}` : "");
    }
  }

  function calculatedVerticalDimension() {
    return Math.round((Style.baseWidgetSize - 5) * scaling);
  }

  function calculateContentWidth() {
    // Calculate the actual content width based on visible elements
    var contentWidth = 0;

    // Icon, progress ring, or album art width
    if (!hasActivePlayer || (!showAlbumArt && !showProgressRing)) {
      // Icon width only
      contentWidth += _iconOnlySize;
    } else if (showProgressRing && hasActivePlayer) {
      // Progress ring width (same as album art width to maintain consistent sizing)
      contentWidth += _artAndProgressSize;
    } else if (showAlbumArt && hasActivePlayer) {
      // Album art width
      contentWidth += _artAndProgressSize;
    }

    // Spacing between icon/art and text; only if there is text
    if (fullTitleMetrics.contentWidth > 0) {
      contentWidth += Style.marginS * scaling;

      // Text width (use the measured width)
      contentWidth += fullTitleMetrics.contentWidth;

      // Additional small margin for text
      contentWidth += Style.marginXXS * 2;
    }

    return Math.ceil(contentWidth);
  }

  // Dynamic width: adapt to content but respect maximum width setting
  readonly property real dynamicWidth: {
    var contentWidth = calculateContentWidth();
    // For vertical bars, there are no horizontal margins to add
    var margins = isVerticalBar ? 0 : (Style.marginS * scaling * 2);
    var totalWidth = contentWidth + margins;

    // If using fixed width mode, always use maxWidth
    if (useFixedWidth) {
      return maxWidth;
    }
    // If there's no active player, the widget should be compact
    if (!hasActivePlayer) {
      return totalWidth;
    }
    // Adapt to content but don't exceed user-set maximum width
    return Math.min(totalWidth, maxWidth);
  }

  //  A hidden text element to safely measure the full title width
  NText {
    id: fullTitleMetrics
    visible: false
    text: titleText.text
    font: titleText.font
    applyUiScale: false
    pointSize: Style.fontSizeS * root.scaling
  }

  NPopupContextMenu {
    id: contextMenu

    model: {
      var items = [];
      if (root.hasActivePlayer && MediaService.canPlay) {
        items.push({
          "label": MediaService.isPlaying ? I18n.tr("context-menu.pause") : I18n.tr("context-menu.play"),
          "action": "play-pause",
          "icon": MediaService.isPlaying ? "media-pause" : "media-play"
        });
      }
      if (root.hasActivePlayer && MediaService.canGoPrevious) {
        items.push({
          "label": I18n.tr("context-menu.previous"),
          "action": "previous",
          "icon": "media-prev"
        });
      }
      if (root.hasActivePlayer && MediaService.canGoNext) {
        items.push({
          "label": I18n.tr("context-menu.next"),
          "action": "next",
          "icon": "media-next"
        });
      }
      items.push({
        "label": I18n.tr("context-menu.widget-settings"),
        "action": "widget-settings",
        "icon": "settings"
      });
      return items;
    }

    onTriggered: action => {
      var popupMenuWindow = PanelService.getPopupMenuWindow(screen);
      if (popupMenuWindow) {
        popupMenuWindow.close();
      }

      if (action === "play-pause") {
        MediaService.playPause();
      } else if (action === "previous") {
        MediaService.previous();
      } else if (action === "next") {
        MediaService.next();
      } else if (action === "widget-settings") {
        BarService.openWidgetSettings(screen, root.section, root.sectionWidgetIndex, root.widgetId, root.widgetSettings);
      }
    }
  }

  Rectangle {
    id: mediaMini
    visible: root.visible
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    width: root.isVerticalBar ? ((root.shouldHideIdle || root.isEmptyForHideMode) ? 0 : root.calculatedVerticalDimension()) : ((root.shouldHideIdle || root.isEmptyForHideMode) ? 0 : root.dynamicWidth)
    height: root.isVerticalBar ? ((root.shouldHideIdle || root.isEmptyForHideMode) ? 0 : root.calculatedVerticalDimension()) : Style.capsuleHeight
    radius: Style.radiusM
    color: Style.capsuleColor

    // Smooth width transition
    Behavior on width {
      NumberAnimation {
        duration: Style.animationNormal
        easing.type: Easing.InOutCubic
      }
    }

    // Smooth height transition for vertical bar
    Behavior on height {
      NumberAnimation {
        duration: Style.animationNormal
        easing.type: Easing.InOutCubic
      }
    }

    Item {
      id: mainContainer
      anchors.fill: parent
      anchors.leftMargin: root.isVerticalBar ? 0 : Style.marginS * root.scaling
      anchors.rightMargin: root.isVerticalBar ? 0 : Style.marginS * root.scaling
      clip: true

      Loader {
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        active: root.showVisualizer && root.visualizerType == "linear"
        width: mainContainer.width - Style.marginS
        height: 20
        z: 0

        sourceComponent: NLinearSpectrum {
          values: CavaService.values
          fillColor: NColor.mPrimary
          opacity: 0.4
        }
      }

      Loader {
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        active: root.showVisualizer && root.visualizerType == "mirrored"
        width: mainContainer.width - Style.marginS
        height: mainContainer.height - Style.marginS
        z: 0

        sourceComponent: NMirroredSpectrum {
          values: CavaService.values
          fillColor: NColor.mPrimary
          opacity: 0.4
        }
      }

      Loader {
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        active: root.showVisualizer && root.visualizerType == "wave"
        width: mainContainer.width - Style.marginS
        height: mainContainer.height - Style.marginS
        z: 0

        sourceComponent: NWaveSpectrum {
          values: CavaService.values
          fillColor: NColor.mPrimary
          opacity: 0.4
        }
      }

      // Horizontal layout for top/bottom bars
      RowLayout {
        id: rowLayout

        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.marginS * root.scaling
        visible: !root.isVerticalBar
        z: 1 // Above the visualizer

        NIcon {
          id: windowIcon
          icon: root.hasActivePlayer ? (MediaService.isPlaying ? "media-pause" : "media-play") : "disc"
          color: root.hasActivePlayer ? NColor.mOnSurface : NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeL * root.scaling
          verticalAlignment: Text.AlignVCenter
          horizontalAlignment: Text.AlignHCenter
          Layout.alignment: Qt.AlignVCenter
          Layout.preferredWidth: root._iconOnlySize
          Layout.preferredHeight: root._iconOnlySize
          visible: !root.hasActivePlayer || (!root.showAlbumArt && !root.showProgressRing)
        }

        ColumnLayout {
          Layout.alignment: Qt.AlignVCenter
          spacing: 0

          // Progress circle (independent of album art)
          Item {
            Layout.preferredWidth: (root.hasActivePlayer && (root.showProgressRing || root.showAlbumArt)) ? root._artAndProgressSize : 0
            Layout.preferredHeight: (root.hasActivePlayer && (root.showProgressRing || root.showAlbumArt)) ? root._artAndProgressSize : 0
            Layout.minimumWidth: (root.hasActivePlayer && root.showProgressRing) ? root._artAndProgressSize : 0
            Layout.minimumHeight: (root.hasActivePlayer && root.showProgressRing) ? root._artAndProgressSize : 0
            Layout.maximumWidth: (root.hasActivePlayer && (root.showProgressRing || root.showAlbumArt)) ? root._artAndProgressSize : 0
            Layout.maximumHeight: (root.hasActivePlayer && (root.showProgressRing || root.showAlbumArt)) ? root._artAndProgressSize : 0
            Layout.fillWidth: false
            Layout.fillHeight: false
            visible: root.hasActivePlayer && (root.showProgressRing || root.showAlbumArt)  // Show container when there's active player and either feature is enabled

            // Progress circle - always available when showProgressRing is true
            Canvas {
              id: progressCanvas
              anchors.fill: parent
              anchors.margins: 0 // Align exactly with parent to avoid clipping
              visible: root.hasActivePlayer && root.showProgressRing // Only show when progress ring is enabled
              z: 0 // Behind the album art or icon

              // Calculate progress ratio: 0 to 1
              property real progressRatio: {
                if (!MediaService.currentPlayer || MediaService.trackLength <= 0)
                  return 0;
                const r = MediaService.currentPosition / MediaService.trackLength;
                if (isNaN(r) || !isFinite(r))
                  return 0;
                return Math.max(0, Math.min(1, r));
              }

              onProgressRatioChanged: requestPaint()

              onPaint: {
                var ctx = getContext("2d");
                // Check if width/height are valid before calculating radius
                if (width <= 0 || height <= 0) {
                  return; // Skip drawing if dimensions are invalid
                }

                var centerX = width / 2;
                var centerY = height / 2;
                var radius = Math.max(0, Math.min(width, height) / 2 - (1.25 * root.scaling)); // Larger radius, accounting for line width to approach edge

                ctx.reset();

                // Background circle (full track, not played yet)
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                ctx.lineWidth = 2.5 * root.scaling; // Thicker line width based on scaling property
                ctx.strokeStyle = Qt.alpha(NColor.mOnSurface, 0.4); // More opaque for better visibility
                ctx.stroke();

                // Progress arc (played portion)
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + progressRatio * 2 * Math.PI);
                ctx.lineWidth = 2.5 * root.scaling; // Thicker line width based on scaling property
                ctx.strokeStyle = NColor.mPrimary; // Use primary color for progress
                ctx.lineCap = "round";
                ctx.stroke();
              }
            }

            // Connection to update progress when media position changes
            Connections {
              target: MediaService
              function onCurrentPositionChanged() {
                progressCanvas.requestPaint();
              }
              function onTrackLengthChanged() {
                progressCanvas.requestPaint();
              }
            }

            // Property to track mPrimary color changes and trigger repaint
            Item {
              id: colorTrackerHorizontal
              property color currentColor: NColor.mPrimary
              onCurrentColorChanged: progressCanvas.requestPaint()
            }

            // Album art or icon - only show album art when enabled and player is active
            Item {
              anchors.fill: parent
              anchors.margins: root.showProgressRing ? (3 * root.scaling) : 0.5 // Adjusted to align with progress circle better

              NImageRounded {
                id: trackArt
                anchors.fill: parent
                anchors.margins: root.showProgressRing ? 0 : -1 * root.scaling // Add negative margin to make album art larger when no progress ring
                radius: Math.min(Style.radiusL, width / 2)
                visible: root.showAlbumArt && root.hasActivePlayer
                imagePath: MediaService.trackArtUrl
                fallbackIcon: MediaService.isPlaying ? "media-pause" : "media-play"
                fallbackIconSize: root.showProgressRing ? 10 : 12 // Larger fallback icon when no progress ring
                borderWidth: 0
                borderColor: NColor.transparent
                z: 1 // In front of the progress circle
              }

              // Fallback icon when no album art or album art not shown
              NIcon {
                anchors.centerIn: parent
                width: parent.width
                height: parent.height
                icon: root.hasActivePlayer ? (MediaService.isPlaying ? "media-pause" : "media-play") : "disc"
                color: root.hasActivePlayer ? NColor.mOnSurface : NColor.mOnSurfaceVariant
                pointSize: (root.showAlbumArt || root.showProgressRing) ? 8 * root.scaling : 12 * root.scaling  // Smaller when inside album art circle or progress ring, larger when alone
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                visible: (!root.showAlbumArt && root.hasActivePlayer) && root.showProgressRing
                z: 1 // In front of the progress circle
              }
            }
          }
        }

        Item {
          id: titleContainer
          Layout.preferredWidth: {
            // Calculate available width based on other elements in the row
            var iconWidth = (windowIcon.visible ? (root._iconOnlySize + Style.marginS * root.scaling) : 0);
            var artWidth = (root.hasActivePlayer && (root.showAlbumArt || root.showProgressRing) ? (root._artAndProgressSize + Style.marginS * root.scaling) : 0);
            var totalMargins = Style.marginXXS * 2;
            var availableWidth = mainContainer.width - iconWidth - artWidth - totalMargins;
            return Math.max(20, availableWidth);
          }
          Layout.maximumWidth: Layout.preferredWidth
          Layout.alignment: Qt.AlignVCenter
          Layout.preferredHeight: titleText.height

          clip: true

          property bool isScrolling: false
          property bool isResetting: false
          property real textWidth: fullTitleMetrics.contentWidth
          property real containerWidth: 0
          property bool needsScrolling: textWidth > containerWidth

          // Timer for "always" mode with delay
          Timer {
            id: scrollStartTimer
            interval: 1000
            repeat: false
            onTriggered: {
              if (root.scrollingMode === "always" && titleContainer.needsScrolling) {
                titleContainer.isScrolling = true;
                titleContainer.isResetting = false;
              }
            }
          }

          // Update scrolling state based on mode
          property var updateScrollingState: function () {
            if (root.scrollingMode === "never") {
              isScrolling = false;
              isResetting = false;
            } else if (root.scrollingMode === "always") {
              if (needsScrolling) {
                if (mouseArea.containsMouse) {
                  isScrolling = false;
                  isResetting = true;
                } else {
                  scrollStartTimer.restart();
                }
              } else {
                scrollStartTimer.stop();
                isScrolling = false;
                isResetting = false;
              }
            } else if (root.scrollingMode === "hover") {
              if (mouseArea.containsMouse && needsScrolling) {
                isScrolling = true;
                isResetting = false;
              } else {
                isScrolling = false;
                if (needsScrolling) {
                  isResetting = true;
                }
              }
            }
          }

          onWidthChanged: {
            containerWidth = width;
            updateScrollingState();
          }

          Component.onCompleted: {
            containerWidth = width;
            updateScrollingState();
          }

          Connections {
            target: mouseArea
            function onContainsMouseChanged() {
              titleContainer.updateScrollingState();
            }
          }

          // Scrolling content
          Item {
            id: scrollContainer
            height: parent.height
            width: parent.width

            property real scrollX: 0
            x: scrollX

            RowLayout {
              spacing: 50 // Gap between text copies

              NText {
                id: titleText
                text: root.hasActivePlayer ? root.getTitle() : root.placeholderText
                pointSize: Style.fontSizeS * root.scaling
                applyUiScale: false
                font.weight: Style.fontWeightMedium
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: root.hasActivePlayer ? Text.AlignLeft : Text.AlignHCenter
                color: root.hasActivePlayer ? NColor.mOnSurface : NColor.mOnSurfaceVariant
                onTextChanged: {
                  titleContainer.isScrolling = false;
                  titleContainer.isResetting = false;
                  scrollContainer.scrollX = 0;
                  if (titleContainer.needsScrolling) {
                    scrollStartTimer.restart();
                  }
                }
              }

              NText {
                text: root.hasActivePlayer ? root.getTitle() : root.placeholderText
                font: titleText.font
                applyUiScale: false
                pointSize: Style.fontSizeS * root.scaling
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: root.hasActivePlayer ? Text.AlignLeft : Text.AlignHCenter
                color: root.hasActivePlayer ? NColor.mOnSurface : NColor.mOnSurfaceVariant
                visible: root.hasActivePlayer && titleContainer.needsScrolling && titleContainer.isScrolling
              }
            }

            // Reset animation
            NumberAnimation on scrollX {
              running: titleContainer.isResetting
              to: 0
              duration: 300
              easing.type: Easing.OutQuad
              onFinished: {
                titleContainer.isResetting = false;
              }
            }

            // Seamless infinite scroll
            NumberAnimation on scrollX {
              id: infiniteScroll
              running: titleContainer.isScrolling && !titleContainer.isResetting
              from: 0
              to: -(titleContainer.textWidth + 50)
              duration: Math.max(4000, root.getTitle().length * 120)
              loops: Animation.Infinite
              easing.type: Easing.Linear
            }
          }
        }
      }

      // Progress circle for vertical layout - follows background radius
      Canvas {
        id: progressCanvasVertical
        anchors.fill: parent
        anchors.margins: 0 // Align with parent container (mainContainer which matches mediaMini)
        visible: root.isVerticalBar && root.showProgressRing // Control visibility with setting
        z: 0 // Behind other content

        // Calculate progress ratio: 0 to 1
        property real progressRatio: {
          if (!MediaService.currentPlayer || MediaService.trackLength <= 0)
            return 0;
          const r = MediaService.currentPosition / MediaService.trackLength;
          if (isNaN(r) || !isFinite(r))
            return 0;
          return Math.max(0, Math.min(1, r));
        }

        onProgressRatioChanged: requestPaint()

        onPaint: {
          var ctx = getContext("2d");
          // Check if width/height are valid before calculating radius
          if (width <= 0 || height <= 0) {
            return; // Skip drawing if dimensions are invalid
          }

          var centerX = width / 2;
          var centerY = height / 2;
          // Align with mediaMini radius which is circular in vertical mode
          var radius = Math.max(0, Math.min(width, height) / 2 - 4); // Position ring near the outer edge of background

          ctx.reset();

          // Background circle (full track, not played yet)
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
          ctx.lineWidth = 2.5 * root.scaling; // Line width based on scaling property, thinner for vertical layout
          ctx.strokeStyle = Qt.alpha(NColor.mOnSurface, 0.4); // More opaque for better visibility
          ctx.stroke();

          // Progress arc (played portion)
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + progressRatio * 2 * Math.PI);
          ctx.lineWidth = 2.5 * root.scaling; // Line width based on scaling property, thinner for vertical layout
          ctx.strokeStyle = NColor.mPrimary; // Use primary color for progress
          ctx.lineCap = "round";
          ctx.stroke();
        }
      }

      // Vertical layout for left/right bars - icon or album art
      Item {
        id: verticalLayout
        anchors.centerIn: parent
        width: root.showProgressRing ? (Style.baseWidgetSize * 0.5 * root.scaling) : (root.calculatedVerticalDimension() - 4 * root.scaling)
        height: width
        visible: root.isVerticalBar
        z: 1 // Above the visualizer and progress ring

        // Album Art
        NImageRounded {
          anchors.fill: parent
          visible: root.showAlbumArt && root.hasActivePlayer
          radius: Math.min(Style.radiusL, width / 2)
          imagePath: MediaService.trackArtUrl
          fallbackIcon: MediaService.isPlaying ? "media-pause" : "media-play"
          fallbackIconSize: 12
          borderWidth: 0
        }

        // Media icon (fallback)
        NIcon {
          id: mediaIconVertical
          anchors.centerIn: parent
          width: parent.width
          height: parent.height
          visible: !root.showAlbumArt || !root.hasActivePlayer
          icon: root.hasActivePlayer ? (MediaService.isPlaying ? "media-pause" : "media-play") : "disc"
          color: root.hasActivePlayer ? NColor.mOnSurface : NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeM * root.scaling
          verticalAlignment: Text.AlignVCenter
          horizontalAlignment: Text.AlignHCenter
        }
      }

      // Connection to update vertical progress when media position changes
      Connections {
        target: MediaService
        function onCurrentPositionChanged() {
          progressCanvasVertical.requestPaint();
        }
        function onTrackLengthChanged() {
          progressCanvasVertical.requestPaint();
        }
      }

      // Property to track mPrimary color changes and trigger repaint for vertical canvas
      Item {
        id: colorTrackerVertical
        property color currentColor: NColor.mPrimary
        onCurrentColorChanged: progressCanvasVertical.requestPaint()
      }

      // Mouse area for hover detection
      MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.hasActivePlayer ? Qt.PointingHandCursor : Qt.ArrowCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        onClicked: mouse => {
          if (mouse.button === Qt.LeftButton) {
            if (!root.hasActivePlayer || !MediaService.currentPlayer || !MediaService.canPlay) {
              return;
            }
            MediaService.playPause();
          } else if (mouse.button === Qt.RightButton) {
            TooltipService.hide();
            const popupMenuWindow = PanelService.getPopupMenuWindow(root.screen);
            if (popupMenuWindow) {
              popupMenuWindow.showContextMenu(contextMenu);
              const pos = BarService.getContextMenuPosition(mediaMini, contextMenu.implicitWidth, contextMenu.implicitHeight);
              contextMenu.openAtItem(mediaMini, pos.x, pos.y);
            }
          } else if (mouse.button === Qt.MiddleButton) {
            if (root.hasActivePlayer && MediaService.canGoPrevious) {
              MediaService.previous();
              TooltipService.hide();
            }
          }
        }

        onEntered: {
          var textToShow = root.hasActivePlayer ? root.tooltipText : root.placeholderText;
          if ((textToShow !== "") && root.isVerticalBar || (root.scrollingMode === "never")) {
            TooltipService.show(root, textToShow, BarService.getTooltipDirection());
          }
        }
        onExited: {
          TooltipService.hide();
        }
      }
    }
  }
}
