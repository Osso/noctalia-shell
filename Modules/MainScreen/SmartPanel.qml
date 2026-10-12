import QtQuick
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Modules.MainScreen.Backgrounds

/**
* SmartPanel for use within MainScreen
*/
Item {
  id: root

  // Screen property provided by MainScreen
  property ShellScreen screen: null

  // Panel content: Text, icons, etc...
  property Component panelContent: null

  // Panel size properties
  property real preferredWidth: 700
  property real preferredHeight: 900
  property real preferredWidthRatio
  property real preferredHeightRatio
  property color panelBackgroundColor: NColor.mSurface
  property color panelBorderColor: NColor.mOutline
  property Item buttonItem: null
  property bool forceAttachToBar: false

  // Anchoring properties
  property bool panelAnchorHorizontalCenter: false
  property bool panelAnchorVerticalCenter: false
  property bool panelAnchorTop: false
  property bool panelAnchorBottom: false
  property bool panelAnchorLeft: false
  property bool panelAnchorRight: false

  // Button position properties
  property bool useButtonPosition: false
  property point buttonPosition: Qt.point(0, 0)
  property int buttonWidth: 0
  property int buttonHeight: 0

  // Edge snapping: if panel is within this distance (in pixels) from a screen edge, snap
  property real edgeSnapDistance: 50

  // Stable registry key captured before screen bindings can change during output teardown.
  property string registrationKey: ""

  // Track whether panel is open
  property bool isPanelOpen: false

  // Track actual visibility (delayed until content is loaded and sized)
  property bool isPanelVisible: false

  // Track size animation completion for sequential opacity animation
  property bool sizeAnimationComplete: false

  // Derived state: track opening transition
  readonly property bool isOpening: isPanelVisible && !isClosing && !sizeAnimationComplete

  // Track close animation state: fade opacity first, then shrink size
  property bool isClosing: false
  property bool opacityFadeComplete: false
  property bool closeFinalized: false // Prevent double-finalization

  // Safety: Watchdog timers to prevent stuck states
  property bool closeWatchdogActive: false
  property bool openWatchdogActive: false

  // Close with escape key
  property bool closeWithEscape: true

  property bool exclusiveKeyboard: true

  // Keyboard event handlers - override these in specific panels to handle shortcuts
  // These are called from MainScreen's centralized shortcuts
  function onEscapePressed() {
    if (closeWithEscape)
      close();
  }
  function onTabPressed() {
  }
  function onShiftTabPressed() {
  }
  function onUpPressed() {
  }
  function onDownPressed() {
  }
  function onLeftPressed() {
  }
  function onRightPressed() {
  }
  function onReturnPressed() {
  }
  function onHomePressed() {
  }
  function onEndPressed() {
  }
  function onPageUpPressed() {
  }
  function onPageDownPressed() {
  }
  function onCtrlJPressed() {
  }
  function onCtrlKPressed() {
  }

  // Expose actual background geometry for AllBackgrounds and click-through masks.
  readonly property BackgroundRegion panelRegion: panelBackground

  readonly property string barPosition: Settings.data.bar.position
  readonly property bool barIsVertical: barPosition === "left" || barPosition === "right"
  readonly property bool barFloating: Settings.data.bar.floating
  readonly property real barMarginH: barFloating ? Settings.data.bar.marginHorizontal * Style.marginXL : 0
  readonly property real barMarginV: barFloating ? Settings.data.bar.marginVertical * Style.marginXL : 0

  // Helper to detect if any anchor is explicitly set
  readonly property bool hasExplicitHorizontalAnchor: panelAnchorHorizontalCenter || panelAnchorLeft || panelAnchorRight
  readonly property bool hasExplicitVerticalAnchor: panelAnchorVerticalCenter || panelAnchorTop || panelAnchorBottom

  // Effective anchor properties (depend on allowAttach)
  // These are true when:
  // 1. Explicitly anchored, OR
  // 2. Using button position and bar is on that edge, OR
  // 3. Attached to bar with no explicit anchors (default centering behavior)
  readonly property bool effectivePanelAnchorTop: panelAnchorTop || (useButtonPosition && barPosition === "top") || (panelContainer.allowAttach && !hasExplicitVerticalAnchor && barPosition === "top" && !barIsVertical)
  readonly property bool effectivePanelAnchorBottom: panelAnchorBottom || (useButtonPosition && barPosition === "bottom") || (panelContainer.allowAttach && !hasExplicitVerticalAnchor && barPosition === "bottom" && !barIsVertical)
  readonly property bool effectivePanelAnchorLeft: panelAnchorLeft || (useButtonPosition && barPosition === "left") || (panelContainer.allowAttach && !hasExplicitHorizontalAnchor && barPosition === "left" && barIsVertical)
  readonly property bool effectivePanelAnchorRight: panelAnchorRight || (useButtonPosition && barPosition === "right") || (panelContainer.allowAttach && !hasExplicitHorizontalAnchor && barPosition === "right" && barIsVertical)

  signal opened
  signal closed

  Connections {
    target: Style

    function onUiScaleRatioChanged() {
      if (root.isPanelOpen && root.isPanelVisible) {
        root.setPosition();
      }
    }
  }

  // Panel visibility and sizing
  visible: isPanelVisible
  width: parent ? parent.width : 0
  height: parent ? parent.height : 0

  // Panel control functions
  function toggle(buttonItem, buttonName) {
    if (!isPanelOpen) {
      open(buttonItem, buttonName);
    } else {
      close();
    }
  }

  function open(buttonItem, buttonName) {
    if (!buttonItem && buttonName) {
      buttonItem = BarService.lookupWidget(buttonName, screen.name);
    }

    if (buttonItem) {
      root.buttonItem = buttonItem;
      // Map button position to screen coordinates
      const buttonPos = buttonItem.mapToItem(null, 0, 0);
      root.buttonPosition = Qt.point(buttonPos.x, buttonPos.y);
      root.buttonWidth = buttonItem.width;
      root.buttonHeight = buttonItem.height;
      root.useButtonPosition = true;
    } else {
      // No button provided: reset button position mode
      root.buttonItem = null;
      root.useButtonPosition = false;
    }

    // Set isPanelOpen to trigger content loading, but don't show yet
    isPanelOpen = true;

    // Notify PanelService
    PanelService.willOpenPanel(root);

    // Position and visibility will be set by Loader.onLoaded
    // This ensures no flicker from default size to content size
  }

  function close() {
    // Start close sequence: fade opacity first
    isClosing = true;
    sizeAnimationComplete = false;
    closeFinalized = false;

    // Stop the open animation timer if it's still running
    opacityTrigger.stop();
    openWatchdogActive = false;
    openWatchdogTimer.stop();

    // Start close watchdog timer
    closeWatchdogActive = true;
    closeWatchdogTimer.restart();

    // If opacity is already 0 (closed during open animation before fade-in),
    // skip directly to size animation
    if (root.opacity === 0.0) {
      opacityFadeComplete = true;
    } else {
      opacityFadeComplete = false;
    }

    // Opacity will fade out, then size will shrink, then finalizeClose() will complete
    Logger.d("SmartPanel", "Closing panel", objectName);
  }

  function finalizeClose() {
    // Prevent double-finalization
    if (root.closeFinalized) {
      Logger.w("SmartPanel", "finalizeClose called but already finalized - ignoring", objectName);
      return;
    }

    // Complete the close sequence after animations finish
    root.closeFinalized = true;
    root.closeWatchdogActive = false;
    closeWatchdogTimer.stop();

    root.isPanelVisible = false;
    root.isPanelOpen = false;
    root.isClosing = false;
    root.opacityFadeComplete = false;

    // Reset dimensionsInitialized for next opening
    panelBackground.dimensionsInitialized = false;

    PanelService.closedPanel(root);
    closed();

    Logger.d("SmartPanel", "Panel close finalized", objectName);
  }

  function setPosition() {
    // Don't calculate position if parent dimensions aren't available yet
    // This prevents centering around (0,0) when width/height are still 0
    if (!root.width || !root.height) {
      Logger.d("SmartPanel", "Skipping setPosition - dimensions not ready:", root.width, "x", root.height);
      // Retry on next frame when dimensions should be available
      Qt.callLater(setPosition);
      return;
    }

    // Calculate panel dimensions first (needed for positioning)
    var w;
    // Priority 1: Content-driven size (dynamic)
    if (contentLoader.item && contentLoader.item.contentPreferredWidth !== undefined) {
      w = contentLoader.item.contentPreferredWidth;
    } // Priority 2: Ratio-based size
    else if (root.preferredWidthRatio !== undefined) {
      w = Math.round(Math.max(root.width * root.preferredWidthRatio, root.preferredWidth));
    } // Priority 3: Static preferred width
    else {
      w = root.preferredWidth;
    }
    var panelWidth = Math.min(w, root.width - Style.marginL * 2);

    var h;
    // Priority 1: Content-driven size (dynamic)
    if (contentLoader.item && contentLoader.item.contentPreferredHeight !== undefined) {
      h = contentLoader.item.contentPreferredHeight;
    } // Priority 2: Ratio-based size
    else if (root.preferredHeightRatio !== undefined) {
      h = Math.round(Math.max(root.height * root.preferredHeightRatio, root.preferredHeight));
    } // Priority 3: Static preferred height
    else {
      h = root.preferredHeight;
    }
    var panelHeight = Math.min(h, root.height - Style.barHeight - Style.marginL * 2);

    // Update panelBackground target size (will be animated)
    panelBackground.targetWidth = panelWidth;
    panelBackground.targetHeight = panelHeight;

    // Calculate position
    var calculatedX;
    var calculatedY;

    // ===== X POSITIONING =====
    if (root.useButtonPosition && root.width > 0 && panelWidth > 0) {
      if (root.barIsVertical) {
        // For vertical bars
        if (panelContainer.allowAttach) {
          // Attached panels: align with bar edge (left or right side)
          if (root.barPosition === "left") {
            const leftBarEdge = root.barMarginH + Style.barHeight;
            calculatedX = leftBarEdge;
          } else {
            // right
            const rightBarEdge = root.width - root.barMarginH - Style.barHeight;
            calculatedX = rightBarEdge - panelWidth;
          }
        } else {
          // Detached panels: center on button X position
          let panelX = root.buttonPosition.x + root.buttonWidth / 2 - panelWidth / 2;
          const minX = Style.marginL;
          const maxX = root.width - panelWidth - Style.marginL;

          // Account for vertical bar taking up space
          if (root.barPosition === "left") {
            minX = root.barMarginH + Style.barHeight + Style.marginL;
          } else if (root.barPosition === "right") {
            maxX = root.width - root.barMarginH - Style.barHeight - panelWidth - Style.marginL;
          }

          panelX = Math.max(minX, Math.min(panelX, maxX));
          calculatedX = panelX;
        }
      } else {
        // For horizontal bars, center panel on button X position
        let panelX = root.buttonPosition.x + root.buttonWidth / 2 - panelWidth / 2;
        if (panelContainer.allowAttach) {
          const cornerInset = root.barFloating ? Style.radiusL * 2 : 0;
          const barLeftEdge = root.barMarginH + cornerInset;
          const barRightEdge = root.width - root.barMarginH - cornerInset;
          panelX = Math.max(barLeftEdge, Math.min(panelX, barRightEdge - panelWidth));
        } else {
          panelX = Math.max(Style.marginL, Math.min(panelX, root.width - panelWidth - Style.marginL));
        }
        calculatedX = panelX;
      }
    } else {
      // Standard anchor positioning
      if (root.panelAnchorHorizontalCenter) {
        if (root.barIsVertical) {
          if (root.barPosition === "left") {
            const availableStart = root.barMarginH + Style.barHeight;
            const availableWidth = root.width - availableStart;
            calculatedX = availableStart + (availableWidth - panelWidth) / 2;
          } else if (root.barPosition === "right") {
            const availableWidth = root.width - root.barMarginH - Style.barHeight;
            calculatedX = (availableWidth - panelWidth) / 2;
          } else {
            calculatedX = (root.width - panelWidth) / 2;
          }
        } else {
          calculatedX = (root.width - panelWidth) / 2;
        }
      } else if (root.effectivePanelAnchorRight) {
        if (panelContainer.allowAttach && root.barIsVertical && root.barPosition === "right") {
          const rightBarEdge = root.width - root.barMarginH - Style.barHeight;
          calculatedX = rightBarEdge - panelWidth;
        } else if (panelContainer.allowAttach) {
          // Account for corner inset when bar is floating, horizontal, AND panel is on same edge as bar
          const panelOnSameEdgeAsBar = (root.barPosition === "top" && root.effectivePanelAnchorTop) || (root.barPosition === "bottom" && root.effectivePanelAnchorBottom);
          if (!root.barIsVertical && root.barFloating && panelOnSameEdgeAsBar) {
            const rightCornerInset = Style.radiusL * 2;
            calculatedX = root.width - root.barMarginH - rightCornerInset - panelWidth;
          } else {
            calculatedX = root.width - panelWidth;
          }
        } else {
          calculatedX = root.width - panelWidth - Style.marginL;
        }
      } else if (root.effectivePanelAnchorLeft) {
        if (panelContainer.allowAttach && root.barIsVertical && root.barPosition === "left") {
          const leftBarEdge = root.barMarginH + Style.barHeight;
          calculatedX = leftBarEdge;
        } else if (panelContainer.allowAttach) {
          // Account for corner inset when bar is floating, horizontal, AND panel is on same edge as bar
          const panelOnSameEdgeAsBar = (root.barPosition === "top" && root.effectivePanelAnchorTop) || (root.barPosition === "bottom" && root.effectivePanelAnchorBottom);
          if (!root.barIsVertical && root.barFloating && panelOnSameEdgeAsBar) {
            const leftCornerInset = Style.radiusL * 2;
            calculatedX = root.barMarginH + leftCornerInset;
          } else {
            calculatedX = 0;
          }
        } else {
          calculatedX = Style.marginL;
        }
      } else {
        // No explicit anchor: default to centering on bar
        if (root.barIsVertical) {
          if (root.barPosition === "left") {
            const availableStart = root.barMarginH + Style.barHeight;
            const availableWidth = root.width - availableStart - Style.marginL;
            calculatedX = availableStart + (availableWidth - panelWidth) / 2;
          } else {
            const availableWidth = root.width - root.barMarginH - Style.barHeight - Style.marginL;
            calculatedX = Style.marginL + (availableWidth - panelWidth) / 2;
          }
        } else {
          if (panelContainer.allowAttach) {
            const cornerInset = Style.radiusL + (root.barFloating ? Style.radiusL : 0);
            const barLeftEdge = root.barMarginH + cornerInset;
            const barRightEdge = root.width - root.barMarginH - cornerInset;
            const centeredX = (root.width - panelWidth) / 2;
            calculatedX = Math.max(barLeftEdge, Math.min(centeredX, barRightEdge - panelWidth));
          } else {
            calculatedX = (root.width - panelWidth) / 2;
          }
        }
      }
    }

    // Edge snapping for X
    if (panelContainer.allowAttach && !root.barFloating && root.width > 0 && panelWidth > 0) {
      let leftEdgePos = root.barMarginH;
      if (root.barPosition === "left") {
        leftEdgePos = root.barMarginH + Style.barHeight;
      }

      let rightEdgePos = root.width - root.barMarginH - panelWidth;
      if (root.barPosition === "right") {
        rightEdgePos = root.width - root.barMarginH - Style.barHeight - panelWidth;
      }

      // Only snap to left edge if panel is actually meant to be at left (or no explicit anchor)
      const shouldSnapToLeft = root.effectivePanelAnchorLeft || (!root.hasExplicitHorizontalAnchor && root.barPosition === "left");
      // Only snap to right edge if panel is actually meant to be at right (or no explicit anchor)
      const shouldSnapToRight = root.effectivePanelAnchorRight || (!root.hasExplicitHorizontalAnchor && root.barPosition === "right");

      if (shouldSnapToLeft && Math.abs(calculatedX - leftEdgePos) <= root.edgeSnapDistance) {
        calculatedX = leftEdgePos;
      } else if (shouldSnapToRight && Math.abs(calculatedX - rightEdgePos) <= root.edgeSnapDistance) {
        calculatedX = rightEdgePos;
      }
    }

    // ===== Y POSITIONING =====
    if (root.useButtonPosition && root.height > 0 && panelHeight > 0) {
      if (root.barPosition === "top") {
        const topBarEdge = root.barMarginV + Style.barHeight;
        if (panelContainer.allowAttach) {
          calculatedY = topBarEdge;
        } else {
          calculatedY = topBarEdge + Style.marginM;
        }
      } else if (root.barPosition === "bottom") {
        const bottomBarEdge = root.height - root.barMarginV - Style.barHeight;
        if (panelContainer.allowAttach) {
          calculatedY = bottomBarEdge - panelHeight;
        } else {
          calculatedY = bottomBarEdge - panelHeight - Style.marginM;
        }
      } else if (root.barIsVertical) {
        let panelY = root.buttonPosition.y + root.buttonHeight / 2 - panelHeight / 2;
        const extraPadding = (panelContainer.allowAttach && root.barFloating) ? Style.radiusL : 0;
        if (panelContainer.allowAttach) {
          const cornerInset = extraPadding + (root.barFloating ? Style.radiusL : 0);
          const barTopEdge = root.barMarginV + cornerInset;
          const barBottomEdge = root.height - root.barMarginV - cornerInset;
          panelY = Math.max(barTopEdge, Math.min(panelY, barBottomEdge - panelHeight));
        } else {
          panelY = Math.max(Style.marginL + extraPadding, Math.min(panelY, root.height - panelHeight - Style.marginL - extraPadding));
        }
        calculatedY = panelY;
      }
    } else {
      // Standard anchor positioning
      let barOffset = 0;
      if (!panelContainer.allowAttach) {
        if (root.barPosition === "top") {
          barOffset = root.barMarginV + Style.barHeight + Style.marginM;
        } else if (root.barPosition === "bottom") {
          barOffset = root.barMarginV + Style.barHeight + Style.marginM;
        }
      } else {
        if (root.effectivePanelAnchorTop && root.barPosition === "top") {
          calculatedY = root.barMarginV + Style.barHeight;
        } else if (root.effectivePanelAnchorBottom && root.barPosition === "bottom") {
          calculatedY = root.height - root.barMarginV - Style.barHeight - panelHeight;
        } else if (!root.hasExplicitVerticalAnchor) {
          if (root.barPosition === "top") {
            calculatedY = root.barMarginV + Style.barHeight;
          } else if (root.barPosition === "bottom") {
            calculatedY = root.height - root.barMarginV - Style.barHeight - panelHeight;
          }
        }
      }

      if (calculatedY === undefined) {
        if (root.panelAnchorVerticalCenter) {
          if (!root.barIsVertical) {
            if (root.barPosition === "top") {
              const availableStart = root.barMarginV + Style.barHeight;
              const availableHeight = root.height - availableStart;
              calculatedY = availableStart + (availableHeight - panelHeight) / 2;
            } else if (root.barPosition === "bottom") {
              const availableHeight = root.height - root.barMarginV - Style.barHeight;
              calculatedY = (availableHeight - panelHeight) / 2;
            } else {
              calculatedY = (root.height - panelHeight) / 2;
            }
          } else {
            calculatedY = (root.height - panelHeight) / 2;
          }
        } else if (root.effectivePanelAnchorTop) {
          if (panelContainer.allowAttach) {
            calculatedY = 0;
          } else {
            const topBarOffset = (root.barPosition === "top") ? barOffset : 0;
            calculatedY = topBarOffset + Style.marginL;
          }
        } else if (root.effectivePanelAnchorBottom) {
          if (panelContainer.allowAttach) {
            calculatedY = root.height - panelHeight;
          } else {
            const bottomBarOffset = (root.barPosition === "bottom") ? barOffset : 0;
            calculatedY = root.height - panelHeight - bottomBarOffset - Style.marginL;
          }
        } else {
          if (root.barIsVertical) {
            if (panelContainer.allowAttach) {
              const cornerInset = root.barFloating ? Style.radiusL * 2 : 0;
              const barTopEdge = root.barMarginV + cornerInset;
              const barBottomEdge = root.height - root.barMarginV - cornerInset;
              const centeredY = (root.height - panelHeight) / 2;
              calculatedY = Math.max(barTopEdge, Math.min(centeredY, barBottomEdge - panelHeight));
            } else {
              calculatedY = (root.height - panelHeight) / 2;
            }
          } else {
            if (panelContainer.allowAttach && !root.barIsVertical) {
              if (root.barPosition === "top") {
                calculatedY = root.barMarginV + Style.barHeight;
              } else if (root.barPosition === "bottom") {
                calculatedY = root.height - root.barMarginV - Style.barHeight - panelHeight;
              }
            } else {
              if (root.barPosition === "top") {
                calculatedY = barOffset + Style.marginL;
              } else if (root.barPosition === "bottom") {
                calculatedY = Style.marginL;
              } else {
                calculatedY = Style.marginL;
              }
            }
          }
        }
      }
    }

    // Edge snapping for Y
    if (panelContainer.allowAttach && !root.barFloating && root.height > 0 && panelHeight > 0) {
      let topEdgePos = root.barMarginV;
      if (root.barPosition === "top") {
        topEdgePos = root.barMarginV + Style.barHeight;
      }

      let bottomEdgePos = root.height - root.barMarginV - panelHeight;
      if (root.barPosition === "bottom") {
        bottomEdgePos = root.height - root.barMarginV - Style.barHeight - panelHeight;
      }

      // Only snap to top edge if panel is actually meant to be at top (or no explicit anchor)
      const shouldSnapToTop = root.effectivePanelAnchorTop || (!root.hasExplicitVerticalAnchor && root.barPosition === "top");
      // Only snap to bottom edge if panel is actually meant to be at bottom (or no explicit anchor)
      const shouldSnapToBottom = root.effectivePanelAnchorBottom || (!root.hasExplicitVerticalAnchor && root.barPosition === "bottom");

      if (shouldSnapToTop && Math.abs(calculatedY - topEdgePos) <= root.edgeSnapDistance) {
        calculatedY = topEdgePos;
      } else if (shouldSnapToBottom && Math.abs(calculatedY - bottomEdgePos) <= root.edgeSnapDistance) {
        calculatedY = bottomEdgePos;
      }
    }

    // Apply calculated positions (set targets for animation)
    panelBackground.targetX = calculatedX;
    panelBackground.targetY = calculatedY;

    Logger.d("SmartPanel", "Position calculated:", calculatedX, calculatedY);
    Logger.d("SmartPanel", "  Panel size:", panelWidth, "x", panelHeight);
    Logger.d("SmartPanel", "  Parent size:", root.width, "x", root.height);
  }

  // Watch for changes in content-driven sizes and update position
  Connections {
    target: contentLoader.item
    ignoreUnknownSignals: true

    function onContentPreferredWidthChanged() {
      if (root.isPanelOpen && root.isPanelVisible) {
        root.setPosition();
      }
    }

    function onContentPreferredHeightChanged() {
      if (root.isPanelOpen && root.isPanelVisible) {
        root.setPosition();
      }
    }
  }

  // Opacity animation
  // Opening: fade in after size animation reaches 75%
  // Closing: fade out immediately
  opacity: {
    if (isClosing)
      return 0.0; // Fade out when closing
    if (isPanelVisible && sizeAnimationComplete)
      return 1.0; // Fade in when opening
    return 0.0;
  }

  Behavior on opacity {
    NumberAnimation {
      id: opacityAnimation
      duration: root.isClosing ? Style.animationFaster : Style.animationFast
      easing.type: Easing.OutQuad

      onRunningChanged: {
        // Safety: If animation didn't run (zero duration), handle immediately
        if (!running && duration === 0) {
          if (root.isClosing && root.opacity === 0.0) {
            root.opacityFadeComplete = true;
            const shouldFinalizeNow = panelContainer.maskRegion && !panelContainer.maskRegion.shouldAnimateWidth && !panelContainer.maskRegion.shouldAnimateHeight;
            if (shouldFinalizeNow) {
              Logger.d("SmartPanel", "Zero-duration opacity + no size animation - finalizing", root.objectName);
              Qt.callLater(root.finalizeClose);
            }
          } else if (root.isPanelVisible && root.opacity === 1.0) {
            // Open completed with zero duration
            root.openWatchdogActive = false;
            openWatchdogTimer.stop();
          }
          return;
        }

        // When opacity fade completes during close, trigger size animation
        if (!running && root.isClosing && root.opacity === 0.0) {
          root.opacityFadeComplete = true;
          // If no size animation will run (centered attached panels only), finalize immediately
          // Detached panels (allowAttach === false) should always animate from top
          const shouldFinalizeNow = panelContainer.maskRegion && !panelContainer.maskRegion.shouldAnimateWidth && !panelContainer.maskRegion.shouldAnimateHeight;
          if (shouldFinalizeNow) {
            Logger.d("SmartPanel", "No animation - finalizing immediately", root.objectName);
            Qt.callLater(root.finalizeClose);
          } else {
            Logger.d("SmartPanel", "Animation will run - waiting for size animation", root.objectName, "shouldAnimateHeight:", panelContainer.maskRegion.shouldAnimateHeight, "shouldAnimateWidth:", panelContainer.maskRegion.shouldAnimateWidth);
          }
        } // When opacity fade completes during open, stop watchdog
        else if (!running && root.isPanelVisible && root.opacity === 1.0) {
          root.openWatchdogActive = false;
          openWatchdogTimer.stop();
        }
      }
    }
  }

  // Timer to trigger opacity fade at 50% of size animation
  Timer {
    id: opacityTrigger
    interval: Style.animationNormal * 0.5
    repeat: false
    onTriggered: {
      if (root.isPanelVisible) {
        root.sizeAnimationComplete = true;
      }
    }
  }

  // Watchdog timer for open sequence (safety mechanism)
  Timer {
    id: openWatchdogTimer
    interval: Style.animationNormal * 3 // 3x normal animation time
    repeat: false
    onTriggered: {
      if (root.openWatchdogActive) {
        Logger.w("SmartPanel", "Open watchdog timeout - forcing panel visible state", root.objectName);
        root.openWatchdogActive = false;
        // Force completion of open sequence
        if (root.isPanelOpen && !root.isPanelVisible) {
          root.isPanelVisible = true;
          root.sizeAnimationComplete = true;
        }
      }
    }
  }

  // Watchdog timer for close sequence (safety mechanism)
  Timer {
    id: closeWatchdogTimer
    interval: Style.animationFast * 3 // 3x fast animation time
    repeat: false
    onTriggered: {
      if (root.closeWatchdogActive && !root.closeFinalized) {
        Logger.w("SmartPanel", "Close watchdog timeout - forcing panel close", root.objectName);
        // Force finalization
        Qt.callLater(root.finalizeClose);
      }
    }
  }

  // ------------------------------------------------
  // Panel Content
  Item {
    id: panelContainer
    anchors.fill: parent

    // Screen-dependent attachment properties
    readonly property bool allowAttach: Settings.data.ui.panelsAttachedToBar || root.forceAttachToBar
    readonly property bool allowAttachToBar: {
      if (!(Settings.data.ui.panelsAttachedToBar || root.forceAttachToBar) || Settings.data.bar.backgroundOpacity < 1.0) {
        return false;
      }

      // A panel can only be attached to a bar if there is a bar on that screen
      var monitors = Settings.data.bar.monitors || [];
      var screenName = root.screen ? root.screen.name : "";
      var result = monitors.length === 0 || monitors.includes(screenName);
      return result;
    }

    // Edge detection - detect if panel is touching screen edges
    readonly property bool touchingLeftEdge: allowAttach && panelBackground.x <= 1
    readonly property bool touchingRightEdge: allowAttach && (panelBackground.x + panelBackground.width) >= (root.width - 1)
    readonly property bool touchingTopEdge: allowAttach && panelBackground.y <= 1
    readonly property bool touchingBottomEdge: allowAttach && (panelBackground.y + panelBackground.height) >= (root.height - 1)

    // Bar edge detection - detect if panel is touching bar edges (for cases where centered panels snap to bar due to height constraints)
    readonly property bool touchingTopBar: allowAttachToBar && root.barPosition === "top" && !root.barIsVertical && Math.abs(panelBackground.y - (root.barMarginV + Style.barHeight)) <= 1
    readonly property bool touchingBottomBar: allowAttachToBar && root.barPosition === "bottom" && !root.barIsVertical && Math.abs((panelBackground.y + panelBackground.height) - (root.height - root.barMarginV - Style.barHeight)) <= 1
    readonly property bool touchingLeftBar: allowAttachToBar && root.barPosition === "left" && root.barIsVertical && Math.abs(panelBackground.x - (root.barMarginH + Style.barHeight)) <= 1
    readonly property bool touchingRightBar: allowAttachToBar && root.barPosition === "right" && root.barIsVertical && Math.abs((panelBackground.x + panelBackground.width) - (root.width - root.barMarginH - Style.barHeight)) <= 1

    // Expose panelBackground for mask region
    property alias maskRegion: panelBackground

    // The actual panel background - provides geometry for PanelBackground rendering
    BackgroundRegion {
      id: panelBackground

      // Store target dimensions (Initialize to 0, set by setPosition())
      property real targetWidth: 0
      property real targetHeight: 0
      property real targetX: root.x
      property real targetY: root.y

      // Track whether dimensions have been initialized (to prevent initial changes from animating)
      property bool dimensionsInitialized: false

      property var bezierCurve: [0.05, 0, 0.133, 0.06, 0.166, 0.4, 0.208, 0.82, 0.25, 1, 1, 1]

      // Determine which edges the panel is closest to for animation direction
      // Use target position (not animated position) to avoid binding loops
      readonly property bool willTouchTopBar: {
        if (!panelContainer.allowAttachToBar || root.barPosition !== "top" || root.barIsVertical)
          return false;
        var targetTopBarY = root.barMarginV + Style.barHeight;
        return Math.abs(panelBackground.targetY - targetTopBarY) <= 1;
      }
      readonly property bool willTouchBottomBar: {
        if (!panelContainer.allowAttachToBar || root.barPosition !== "bottom" || root.barIsVertical)
          return false;
        var targetBottomBarY = root.height - root.barMarginV - Style.barHeight - panelBackground.targetHeight;
        return Math.abs(panelBackground.targetY - targetBottomBarY) <= 1;
      }
      readonly property bool willTouchLeftBar: {
        if (!panelContainer.allowAttachToBar || root.barPosition !== "left" || !root.barIsVertical)
          return false;
        var targetLeftBarX = root.barMarginH + Style.barHeight;
        return Math.abs(panelBackground.targetX - targetLeftBarX) <= 1;
      }
      readonly property bool willTouchRightBar: {
        if (!panelContainer.allowAttachToBar || root.barPosition !== "right" || !root.barIsVertical)
          return false;
        var targetRightBarX = root.width - root.barMarginH - Style.barHeight - panelBackground.targetWidth;
        return Math.abs(panelBackground.targetX - targetRightBarX) <= 1;
      }
      readonly property bool willTouchTopEdge: panelContainer.allowAttach && panelBackground.targetY <= 1
      readonly property bool willTouchBottomEdge: panelContainer.allowAttach && (panelBackground.targetY + panelBackground.targetHeight) >= (root.height - 1)
      readonly property bool willTouchLeftEdge: panelContainer.allowAttach && panelBackground.targetX <= 1
      readonly property bool willTouchRightEdge: panelContainer.allowAttach && (panelBackground.targetX + panelBackground.targetWidth) >= (root.width - 1)

      readonly property bool isActuallyAttachedToAnyEdge: {
        return willTouchTopBar || willTouchBottomBar || willTouchLeftBar || willTouchRightBar || willTouchTopEdge || willTouchBottomEdge || willTouchLeftEdge || willTouchRightEdge;
      }

      readonly property bool animateFromTop: {
        // When panel is opening, use effective anchors (known before position is calculated)
        if (!root.isPanelVisible) {
          // Attached to horizontal bar at top
          if (panelContainer.allowAttachToBar && root.effectivePanelAnchorTop && !root.barIsVertical) {
            return true;
          }
          // Attached to vertical bar (left/right) - don't animate from top
          if (panelContainer.allowAttachToBar && root.barIsVertical && (root.effectivePanelAnchorLeft || root.effectivePanelAnchorRight)) {
            return false;
          }
          // Default: animate from top
          return true;
        }
        // Panel is visible - use calculated positions
        if (willTouchTopBar) {
          return true;
        }
        if (willTouchTopEdge && !willTouchTopBar && !willTouchBottomBar && !willTouchLeftBar && !willTouchRightBar) {
          return true;
        }
        if (!isActuallyAttachedToAnyEdge) {
          return true;
        }
        return false;
      }
      readonly property bool animateFromBottom: {
        if (!root.isPanelVisible) {
          if (panelContainer.allowAttachToBar && root.effectivePanelAnchorBottom && !root.barIsVertical) {
            return true;
          }
          return false;
        }
        if (willTouchBottomBar) {
          return true;
        }
        if (willTouchBottomEdge && !willTouchTopBar && !willTouchBottomBar && !willTouchLeftBar && !willTouchRightBar) {
          return true;
        }
        return false;
      }
      readonly property bool animateFromLeft: {
        if (!root.isPanelVisible) {
          if (panelContainer.allowAttachToBar && root.effectivePanelAnchorLeft && root.barIsVertical) {
            return true;
          }
          return false;
        }
        if (willTouchTopBar || willTouchBottomBar) {
          return false;
        }
        if (willTouchLeftBar) {
          return true;
        }
        if (willTouchTopEdge || willTouchBottomEdge) {
          return false;
        }
        if (willTouchLeftEdge && !willTouchLeftBar && !willTouchTopBar && !willTouchBottomBar && !willTouchRightBar) {
          return true;
        }
        return false;
      }
      readonly property bool animateFromRight: {
        if (!root.isPanelVisible) {
          if (panelContainer.allowAttachToBar && root.effectivePanelAnchorRight && root.barIsVertical) {
            return true;
          }
          return false;
        }
        if (willTouchTopBar || willTouchBottomBar) {
          return false;
        }
        if (willTouchRightBar) {
          return true;
        }
        if (willTouchTopEdge || willTouchBottomEdge) {
          return false;
        }
        if (willTouchRightEdge && !willTouchLeftBar && !willTouchTopBar && !willTouchBottomBar && !willTouchRightBar) {
          return true;
        }
        return false;
      }

      // Determine animation axis based on which edge is closest
      // Priority: horizontal edges (top/bottom) take precedence over vertical edges (left/right)
      // This prevents diagonal animations when panel is attached to a corner
      readonly property bool shouldAnimateWidth: !shouldAnimateHeight && (animateFromLeft || animateFromRight)
      readonly property bool shouldAnimateHeight: animateFromTop || animateFromBottom

      // Current animated width/height (referenced by x/y for right/bottom positioning)
      readonly property real currentWidth: {
        if (root.isClosing && root.opacityFadeComplete && shouldAnimateWidth)
          return 0;
        if (root.isClosing || root.isPanelVisible)
          return targetWidth;
        // If not animating width, start at target (no visual change)
        // If animating width, start at 0 (will animate to target)
        return shouldAnimateWidth ? 0 : targetWidth;
      }
      readonly property real currentHeight: {
        if (root.isClosing && root.opacityFadeComplete && shouldAnimateHeight)
          return 0;
        if (root.isClosing || root.isPanelVisible)
          return targetHeight;
        // If not animating height, start at target (no visual change)
        // If animating height, start at 0 (will animate to target)
        return shouldAnimateHeight ? 0 : targetHeight;
      }

      width: currentWidth
      height: currentHeight

      x: {
        // Offset x to make panel grow/shrink from the appropriate edge
        if (animateFromRight) {
          // Keep the RIGHT edge fixed at its target position
          if (root.isPanelVisible || root.isClosing) {
            const targetRightEdge = targetX + targetWidth;
            return targetRightEdge - width;
          }
        }
        return targetX;
      }
      y: {
        // Offset y to make panel grow/shrink from the appropriate edge
        if (animateFromBottom) {
          // Keep the BOTTOM edge fixed at its target position
          if (root.isPanelVisible || root.isClosing) {
            const targetBottomEdge = targetY + targetHeight;
            return targetBottomEdge - height;
          }
        }
        return targetY;
      }

      Behavior on width {
        NumberAnimation {
          id: widthAnimation
          // Use 0ms if dimensions not initialized to prevent initial changes from animating
          // During opening: use 0ms if not animating width, otherwise use normal duration
          // During closing: use 0ms if not animating width, otherwise use fast duration
          // During normal content resizing: always use normal duration
          duration: !panelBackground.dimensionsInitialized ? 0 : (root.isOpening && !panelBackground.shouldAnimateWidth) ? 0 : root.isOpening ? Style.animationNormal : (root.isClosing && !panelBackground.shouldAnimateWidth) ? 0 : root.isClosing ? Style.animationFast : Style.animationNormal
          easing.type: Easing.BezierSpline
          easing.bezierCurve: panelBackground.bezierCurve

          onRunningChanged: {
            // Safety: Zero-duration animation handling
            if (!running && duration === 0) {
              if (root.isClosing && panelBackground.width === 0 && panelBackground.shouldAnimateWidth) {
                Logger.d("SmartPanel", "Zero-duration width animation - finalizing", root.objectName);
                Qt.callLater(root.finalizeClose);
              }
              return;
            }

            // When width shrink completes during close, finalize
            if (!running && root.isClosing && panelBackground.width === 0 && panelBackground.shouldAnimateWidth) {
              Qt.callLater(root.finalizeClose);
            }
          }
        }
      }

      Behavior on height {
        NumberAnimation {
          id: heightAnimation
          // Use 0ms if dimensions not initialized to prevent initial changes from animating
          // During opening: use 0ms if not animating height, otherwise use normal duration
          // During closing: use 0ms if not animating height, otherwise use fast duration
          // During normal content resizing: always use normal duration
          duration: !panelBackground.dimensionsInitialized ? 0 : (root.isOpening && !panelBackground.shouldAnimateHeight) ? 0 : root.isOpening ? Style.animationNormal : (root.isClosing && !panelBackground.shouldAnimateHeight) ? 0 : root.isClosing ? Style.animationFast : Style.animationNormal
          easing.type: Easing.BezierSpline
          easing.bezierCurve: panelBackground.bezierCurve

          onRunningChanged: {
            // Safety: Zero-duration animation handling
            if (!running && duration === 0) {
              if (root.isClosing && panelBackground.height === 0 && panelBackground.shouldAnimateHeight) {
                Logger.d("SmartPanel", "Zero-duration height animation - finalizing", root.objectName);
                Qt.callLater(root.finalizeClose);
              }
              return;
            }

            // When height shrink completes during close, finalize
            if (!running && root.isClosing && panelBackground.height === 0 && panelBackground.shouldAnimateHeight) {
              Qt.callLater(root.finalizeClose);
            }
          }
        }
      }

      // Corner states for PanelBackground to read
      // State -1: No radius (flat/square corner)
      // State 0: Normal (inner curve)
      // State 1: Horizontal inversion (outer curve on X-axis)
      // State 2: Vertical inversion (outer curve on Y-axis)

      // Smart corner state calculation based on bar attachment and edge touching
      topLeftCornerState: {
        var barInverted = panelContainer.allowAttachToBar && ((root.barPosition === "top" && !root.barIsVertical && root.effectivePanelAnchorTop) || (root.barPosition === "left" && root.barIsVertical && root.effectivePanelAnchorLeft));
        var barTouchInverted = panelContainer.touchingTopBar || panelContainer.touchingLeftBar;
        // Invert if touching either edge that forms this corner (left OR top), regardless of bar position
        var edgeInverted = panelContainer.allowAttach && (panelContainer.touchingLeftEdge || panelContainer.touchingTopEdge);
        var oppositeEdgeInverted = panelContainer.allowAttach && (panelContainer.touchingTopEdge && !root.barIsVertical && root.barPosition !== "top");

        if (barInverted || barTouchInverted || edgeInverted || oppositeEdgeInverted) {
          // Determine inversion direction based on which edge is touched
          if (panelContainer.touchingLeftEdge && panelContainer.touchingTopEdge)
            return 0; // Both edges: no inversion (normal rounded corner)
          if (panelContainer.touchingLeftEdge)
            return 2; // Left edge: vertical inversion
          if (panelContainer.touchingTopEdge)
            return 1; // Top edge: horizontal inversion
          return root.barIsVertical ? 2 : 1;
        }
        return 0;
      }

      topRightCornerState: {
        var barInverted = panelContainer.allowAttachToBar && ((root.barPosition === "top" && !root.barIsVertical && root.effectivePanelAnchorTop) || (root.barPosition === "right" && root.barIsVertical && root.effectivePanelAnchorRight));
        var barTouchInverted = panelContainer.touchingTopBar || panelContainer.touchingRightBar;
        // Invert if touching either edge that forms this corner (right OR top), regardless of bar position
        var edgeInverted = panelContainer.allowAttach && (panelContainer.touchingRightEdge || panelContainer.touchingTopEdge);
        var oppositeEdgeInverted = panelContainer.allowAttach && (panelContainer.touchingTopEdge && !root.barIsVertical && root.barPosition !== "top");

        if (barInverted || barTouchInverted || edgeInverted || oppositeEdgeInverted) {
          // Determine inversion direction based on which edge is touched
          if (panelContainer.touchingRightEdge && panelContainer.touchingTopEdge)
            return 0; // Both edges: no inversion (normal rounded corner)
          if (panelContainer.touchingRightEdge)
            return 2; // Right edge: vertical inversion
          if (panelContainer.touchingTopEdge)
            return 1; // Top edge: horizontal inversion
          return root.barIsVertical ? 2 : 1;
        }
        return 0;
      }

      bottomLeftCornerState: {
        var barInverted = panelContainer.allowAttachToBar && ((root.barPosition === "bottom" && !root.barIsVertical && root.effectivePanelAnchorBottom) || (root.barPosition === "left" && root.barIsVertical && root.effectivePanelAnchorLeft));
        var barTouchInverted = panelContainer.touchingBottomBar || panelContainer.touchingLeftBar;
        // Invert if touching either edge that forms this corner (left OR bottom), regardless of bar position
        var edgeInverted = panelContainer.allowAttach && (panelContainer.touchingLeftEdge || panelContainer.touchingBottomEdge);
        var oppositeEdgeInverted = panelContainer.allowAttach && (panelContainer.touchingBottomEdge && !root.barIsVertical && root.barPosition !== "bottom");

        if (barInverted || barTouchInverted || edgeInverted || oppositeEdgeInverted) {
          // Determine inversion direction based on which edge is touched
          if (panelContainer.touchingLeftEdge && panelContainer.touchingBottomEdge)
            return 0; // Both edges: no inversion (normal rounded corner)
          if (panelContainer.touchingLeftEdge)
            return 2; // Left edge: vertical inversion
          if (panelContainer.touchingBottomEdge)
            return 1; // Bottom edge: horizontal inversion
          return root.barIsVertical ? 2 : 1;
        }
        return 0;
      }

      bottomRightCornerState: {
        var barInverted = panelContainer.allowAttachToBar && ((root.barPosition === "bottom" && !root.barIsVertical && root.effectivePanelAnchorBottom) || (root.barPosition === "right" && root.barIsVertical && root.effectivePanelAnchorRight));
        var barTouchInverted = panelContainer.touchingBottomBar || panelContainer.touchingRightBar;
        // Invert if touching either edge that forms this corner (right OR bottom), regardless of bar position
        var edgeInverted = panelContainer.allowAttach && (panelContainer.touchingRightEdge || panelContainer.touchingBottomEdge);
        var oppositeEdgeInverted = panelContainer.allowAttach && (panelContainer.touchingBottomEdge && !root.barIsVertical && root.barPosition !== "bottom");

        if (barInverted || barTouchInverted || edgeInverted || oppositeEdgeInverted) {
          // Determine inversion direction based on which edge is touched
          if (panelContainer.touchingRightEdge && panelContainer.touchingBottomEdge)
            return 0; // Both edges: no inversion (normal rounded corner)
          if (panelContainer.touchingRightEdge)
            return 2; // Right edge: vertical inversion
          if (panelContainer.touchingBottomEdge)
            return 1; // Bottom edge: horizontal inversion
          return root.barIsVertical ? 2 : 1;
        }
        return 0;
      }

      // MouseArea to catch clicks on the panel and prevent them from reaching the background
      // This prevents closing the panel when clicking inside it
      MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        z: -1 // Behind content, but on the panel background
        onClicked: mouse => {
          mouse.accepted = true; // Accept and ignore - prevents propagation to background
        }
      }
    }

    // Panel top content: Text, icons, etc...
    Loader {
      id: contentLoader
      active: root.isPanelOpen
      x: panelBackground.x
      y: panelBackground.y
      width: panelBackground.width
      height: panelBackground.height
      sourceComponent: root.panelContent

      onLoaded: {
        // Wait for contentPreferredWidth/Height to be available before making visible
        Qt.callLater(function () {
          // Calculate position with stable contentPreferredWidth/Height values
          root.setPosition();

          // Mark dimensions as initialized to enable animations
          panelBackground.dimensionsInitialized = true;

          // Make panel visible, now only the intended dimension will animate
          root.isPanelVisible = true;
          opacityTrigger.start();

          // Start open watchdog timer
          root.openWatchdogActive = true;
          openWatchdogTimer.start();

          root.opened();
        });
      }
    }
  }

  Component.onCompleted: {
    registrationKey = objectName;
    PanelService.registerPanel(registrationKey, root);
  }

  Component.onDestruction: PanelService.unregisterPanel(registrationKey, root)
}
