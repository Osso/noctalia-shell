import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Services.Compositor
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

  property var widgetMetadata: BarWidgetRegistry.widgetMetadata[root.widgetId]
  property var widgetSettings: {
    if (root.section && root.sectionWidgetIndex >= 0) {
      var widgets = Settings.data.bar.widgets[root.section];
      if (widgets && root.sectionWidgetIndex < widgets.length) {
        return widgets[root.sectionWidgetIndex];
      }
    }
    return {};
  }

  readonly property string barPosition: Settings.data.bar.position
  readonly property bool isVertical: root.barPosition === "left" || root.barPosition === "right"
  readonly property bool density: Settings.data.bar.density
  readonly property real baseDimensionRatio: {
    const b = (root.density === "compact") ? 0.85 : 0.65;
    if (root.widgetSettings.labelMode === "none") {
      return b * 0.75;
    }
    return b;
  }

  readonly property string labelMode: (root.widgetSettings.labelMode !== undefined) ? root.widgetSettings.labelMode : root.widgetMetadata.labelMode
  readonly property bool hideUnoccupied: (root.widgetSettings.hideUnoccupied !== undefined) ? root.widgetSettings.hideUnoccupied : root.widgetMetadata.hideUnoccupied
  readonly property bool followFocusedScreen: (root.widgetSettings.followFocusedScreen !== undefined) ? root.widgetSettings.followFocusedScreen : root.widgetMetadata.followFocusedScreen
  readonly property int characterCount: root.isVertical ? 2 : ((root.widgetSettings.characterCount !== undefined) ? root.widgetSettings.characterCount : root.widgetMetadata.characterCount)

  property bool isDestroying: false
  property bool hovered: false

  property ListModel localWorkspaces: ListModel {}
  property real masterProgress: 0.0
  property bool effectsActive: false
  property color effectColor: NColor.mPrimary

  property int horizontalPadding: Style.marginS
  property int spacingBetweenPills: Style.marginXS
  property string focusedWorkspaceKey: ""
  property var displayedUrgencyByWorkspace: ({})

  // Wheel scroll handling
  property int wheelAccumulatedDelta: 0
  property bool wheelCooldown: false

  signal workspaceChanged(int workspaceId, color accentColor)

  function workspaceUrgencyKey(workspace) {
    if (!workspace)
      return "";

    const workspaceId = workspace.id !== undefined ? workspace.id : workspace.idx;
    const output = workspace.output || (root.screen ? root.screen.name : "");
    return output + ":" + workspaceId;
  }

  function displayedUrgentForWorkspace(workspace) {
    const key = root.workspaceUrgencyKey(workspace);
    if (!key || root.displayedUrgencyByWorkspace[key] === undefined)
      return workspace && workspace.isUrgent === true;

    return root.displayedUrgencyByWorkspace[key] === true;
  }

  function setDisplayedUrgency(workspace, urgent) {
    const key = root.workspaceUrgencyKey(workspace);
    if (!key)
      return;

    const nextUrgency = Object.assign({}, root.displayedUrgencyByWorkspace);
    nextUrgency[key] = urgent === true;
    root.displayedUrgencyByWorkspace = nextUrgency;
  }

  implicitWidth: root.isVertical ? Style.barHeight : root.computeWidth()
  implicitHeight: root.isVertical ? root.computeHeight() : Style.barHeight

  function getWorkspaceWidth(ws) {
    const d = Style.capsuleHeight * root.baseDimensionRatio;
    const factor = ws.isActive ? 2.2 : 1;

    // Don't calculate text width if labels are off
    if (root.labelMode === "none") {
      return d * factor;
    }

    var displayText = ws.idx.toString();

    if (ws.name && ws.name.length > 0) {
      if (root.labelMode === "name") {
        displayText = ws.name.substring(0, root.characterCount);
      } else if (root.labelMode === "index+name") {
        displayText = ws.idx.toString() + " " + ws.name.substring(0, root.characterCount);
      }
    }

    const textWidth = displayText.length * (d * 0.4); // Approximate width per character
    const padding = d * 0.6;
    return Math.max(d * factor, textWidth + padding);
  }

  function getWorkspaceHeight(ws) {
    const d = Style.capsuleHeight * root.baseDimensionRatio;
    const factor = ws.isActive ? 2.2 : 1;
    return d * factor;
  }

  function computeWidth() {
    let total = 0;
    for (var i = 0; i < root.localWorkspaces.count; i++) {
      const ws = root.localWorkspaces.get(i);
      total += root.getWorkspaceWidth(ws);
    }
    total += Math.max(root.localWorkspaces.count - 1, 0) * root.spacingBetweenPills;
    total += root.horizontalPadding * 2;
    return Math.round(total);
  }

  function computeHeight() {
    let total = 0;
    for (var i = 0; i < root.localWorkspaces.count; i++) {
      const ws = root.localWorkspaces.get(i);
      total += root.getWorkspaceHeight(ws);
    }
    total += Math.max(root.localWorkspaces.count - 1, 0) * root.spacingBetweenPills;
    total += root.horizontalPadding * 2;
    return Math.round(total);
  }

  function getFocusedLocalIndex() {
    for (var i = 0; i < root.localWorkspaces.count; i++) {
      if (root.localWorkspaces.get(i).isFocused === true)
        return i;
    }
    return -1;
  }

  function switchByOffset(offset) {
    if (root.localWorkspaces.count === 0)
      return;
    var current = root.getFocusedLocalIndex();
    if (current < 0)
      current = 0;
    var next = (current + offset) % root.localWorkspaces.count;
    if (next < 0)
      next = root.localWorkspaces.count - 1;
    const ws = root.localWorkspaces.get(next);
    if (ws && ws.idx !== undefined)
      CompositorService.switchToWorkspace(ws);
  }

  Component.onCompleted: {
    root.refreshWorkspaces();
  }

  Component.onDestruction: {
    root.isDestroying = true;
  }

  onScreenChanged: root.refreshWorkspaces()
  onHideUnoccupiedChanged: root.refreshWorkspaces()

  Connections {
    target: CompositorService
    function onWorkspacesChanged() {
      root.refreshWorkspaces();
    }
  }

  function refreshWorkspaces() {
    root.localWorkspaces.clear();

    var focusedOutput = null;
    if (root.followFocusedScreen) {
      for (var i = 0; i < CompositorService.workspaces.count; i++) {
        const ws = CompositorService.workspaces.get(i);
        if (ws.isFocused)
          focusedOutput = ws.output.toLowerCase();
      }
    }

    if (root.screen !== null) {
      for (var i = 0; i < CompositorService.workspaces.count; i++) {
        const ws = CompositorService.workspaces.get(i);
        if ((root.followFocusedScreen && ws.output.toLowerCase() == focusedOutput) || (!root.followFocusedScreen && ws.output.toLowerCase() == root.screen.name.toLowerCase())) {
          if (root.hideUnoccupied && !ws.isOccupied && !ws.isFocused) {
            continue;
          }
          root.localWorkspaces.append(ws);
        }
      }
    }
    workspaceRepeaterHorizontal.model = root.localWorkspaces;
    workspaceRepeaterVertical.model = root.localWorkspaces;
    root.updateWorkspaceFocus();
  }

  function triggerUnifiedWave() {
    root.effectColor = NColor.mPrimary;
    masterAnimation.restart();
  }

  function updateWorkspaceFocus() {
    for (var i = 0; i < root.localWorkspaces.count; i++) {
      const ws = root.localWorkspaces.get(i);
      if (ws.isFocused === true) {
        const key = root.workspaceUrgencyKey(ws);
        if (key === root.focusedWorkspaceKey)
          return;
        root.focusedWorkspaceKey = key;
        root.triggerUnifiedWave();
        root.workspaceChanged(ws.id, NColor.mPrimary);
        break;
      }
    }
  }

  SequentialAnimation {
    id: masterAnimation
    PropertyAction {
      target: root
      property: "effectsActive"
      value: true
    }
    NumberAnimation {
      target: root
      property: "masterProgress"
      from: 0.0
      to: 1.0
      duration: Style.animationSlow * 2
      easing.type: Easing.OutQuint
    }
    PropertyAction {
      target: root
      property: "effectsActive"
      value: false
    }
    PropertyAction {
      target: root
      property: "masterProgress"
      value: 0.0
    }
  }

  NPopupContextMenu {
    id: contextMenu

    model: [
      {
        "label": I18n.tr("context-menu.widget-settings"),
        "action": "widget-settings",
        "icon": "settings"
      },
    ]

    onTriggered: action => {
      var popupMenuWindow = PanelService.getPopupMenuWindow(root.screen);
      if (popupMenuWindow) {
        popupMenuWindow.close();
      }

      if (action === "widget-settings") {
        BarService.openWidgetSettings(root.screen, root.section, root.sectionWidgetIndex, root.widgetId, root.widgetSettings);
      }
    }
  }

  Rectangle {
    id: workspaceBackground
    width: root.isVertical ? Style.capsuleHeight : parent.width
    height: root.isVertical ? parent.height : Style.capsuleHeight
    radius: Style.radiusM
    color: Style.capsuleColor

    anchors.horizontalCenter: parent.horizontalCenter
    anchors.verticalCenter: parent.verticalCenter

    MouseArea {
      anchors.fill: parent
      acceptedButtons: Qt.RightButton
      onClicked: mouse => {
        if (mouse.button === Qt.RightButton) {
          var popupMenuWindow = PanelService.getPopupMenuWindow(root.screen);
          if (popupMenuWindow) {
            popupMenuWindow.showContextMenu(contextMenu);
            const pos = BarService.getContextMenuPosition(workspaceBackground, contextMenu.implicitWidth, contextMenu.implicitHeight);
            contextMenu.openAtItem(workspaceBackground, pos.x, pos.y);
          }
        }
      }
    }
  }

  // Debounce timer for wheel interactions
  Timer {
    id: wheelDebounce
    interval: 150
    repeat: false
    onTriggered: {
      root.wheelCooldown = false;
      root.wheelAccumulatedDelta = 0;
    }
  }

  // Scroll to switch workspaces
  WheelHandler {
    id: wheelHandler
    target: root
    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    onWheel: function (event) {
      if (root.wheelCooldown)
        return;
      // Prefer vertical delta, fall back to horizontal if needed
      var dy = event.angleDelta.y;
      var dx = event.angleDelta.x;
      var useDy = Math.abs(dy) >= Math.abs(dx);
      var delta = useDy ? dy : dx;
      // One notch is typically 120
      root.wheelAccumulatedDelta += delta;
      var step = 120;
      if (Math.abs(root.wheelAccumulatedDelta) >= step) {
        var direction = root.wheelAccumulatedDelta > 0 ? -1 : 1;
        // For vertical layout, natural mapping: wheel up -> previous, down -> next (already handled by sign)
        // For horizontal layout, same mapping using vertical wheel
        root.switchByOffset(direction);
        root.wheelCooldown = true;
        wheelDebounce.restart();
        root.wheelAccumulatedDelta = 0;
        event.accepted = true;
      }
    }
  }

  component WorkspaceLabel: NText {
    id: workspaceLabel

    required property var model
    required property string labelMode
    required property int characterCount
    required property real pillWidth
    required property real pillHeight
    required property real fontDimension
    required property bool displayedUrgent
    required property bool vertical

    x: (workspaceLabel.pillWidth - workspaceLabel.width) / 2
    y: (workspaceLabel.pillHeight - workspaceLabel.height) / 2 + (workspaceLabel.height - workspaceLabel.contentHeight) / 2
    text: {
      if (workspaceLabel.model.name && workspaceLabel.model.name.length > 0) {
        if (workspaceLabel.labelMode === "name")
          return workspaceLabel.model.name.substring(0, workspaceLabel.characterCount);
        if (workspaceLabel.labelMode === "index+name") {
          if (workspaceLabel.vertical)
            return workspaceLabel.model.idx.toString() + workspaceLabel.model.name.substring(0, 1);
          return workspaceLabel.model.idx.toString() + " " + workspaceLabel.model.name.substring(0, workspaceLabel.characterCount);
        }
      }
      return workspaceLabel.model.idx.toString();
    }
    family: Settings.data.ui.fontFixed
    pointSize: workspaceLabel.fontDimension * (workspaceLabel.model.isActive ? 0.45 : 0.42)
    applyUiScale: false
    font.capitalization: Font.AllUppercase
    font.weight: Style.fontWeightBold
    wrapMode: Text.Wrap
    color: {
      if (workspaceLabel.model.isFocused)
        return NColor.mOnPrimary;
      if (workspaceLabel.displayedUrgent)
        return NColor.mOnError;
      if (workspaceLabel.model.isOccupied)
        return NColor.mOnSecondary;
      return workspaceLabel.vertical ? NColor.mOnSurface : NColor.mOnSecondary;
    }
  }

  // Horizontal layout for top/bottom bars
  Row {
    id: pillRow
    spacing: root.spacingBetweenPills
    anchors.verticalCenter: workspaceBackground.verticalCenter
    x: root.horizontalPadding
    visible: !root.isVertical

    Repeater {
      id: workspaceRepeaterHorizontal
      model: root.localWorkspaces
      Item {
        id: workspacePillContainer
        required property var model
        property Workspace workspaceOwner: root
        property bool urgent: workspacePillContainer.model.isUrgent === true
        property bool displayedUrgent: workspacePillContainer.workspaceOwner.displayedUrgentForWorkspace(workspacePillContainer.model)

        width: workspacePillContainer.workspaceOwner.getWorkspaceWidth(workspacePillContainer.model)
        height: Style.capsuleHeight * workspacePillContainer.workspaceOwner.baseDimensionRatio

        onUrgentChanged: {
          if (workspacePillContainer.urgent) {
            workspacePillContainer.workspaceOwner.setDisplayedUrgency(workspacePillContainer.model, true);
          }
          horizontalUrgencyCooldown.restart();
        }

        Component.onCompleted: {
          if (workspacePillContainer.displayedUrgent) {
            horizontalUrgencyCooldown.restart();
          }
        }

        Timer {
          id: horizontalUrgencyCooldown
          interval: 5000
          repeat: false
          onTriggered: workspacePillContainer.workspaceOwner.setDisplayedUrgency(workspacePillContainer.model, workspacePillContainer.urgent)
        }

        Rectangle {
          id: pill
          anchors.fill: parent

          Loader {
            active: (workspacePillContainer.workspaceOwner.labelMode !== "none")
            sourceComponent: WorkspaceLabel {
              model: workspacePillContainer.model
              labelMode: workspacePillContainer.workspaceOwner.labelMode
              characterCount: workspacePillContainer.workspaceOwner.characterCount
              pillWidth: pill.width
              pillHeight: pill.height
              fontDimension: workspacePillContainer.height
              displayedUrgent: workspacePillContainer.displayedUrgent
              vertical: false
            }
          }

          radius: Style.radiusM
          color: {
            if (workspacePillContainer.model.isFocused)
              return NColor.mPrimary;
            if (workspacePillContainer.displayedUrgent)
              return NColor.mError;
            if (workspacePillContainer.model.isOccupied)
              return NColor.mSecondary;

            return Qt.alpha(NColor.mSecondary, 0.3);
          }
          scale: workspacePillContainer.model.isActive ? 1.0 : 0.9
          z: 0

          MouseArea {
            id: pillMouseArea
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
              CompositorService.switchToWorkspace(workspacePillContainer.model);
            }
            hoverEnabled: true
          }
          // Material 3-inspired smooth animation for width, height, scale, color, opacity, and radius
          Behavior on width {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
          Behavior on height {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
          Behavior on scale {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
          Behavior on color {
            ColorAnimation {
              duration: Style.animationFast
              easing.type: Easing.InOutCubic
            }
          }
          Behavior on opacity {
            NumberAnimation {
              duration: Style.animationFast
              easing.type: Easing.InOutCubic
            }
          }
          Behavior on radius {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
        }

        Behavior on width {
          NumberAnimation {
            duration: Style.animationNormal
            easing.type: Easing.OutBack
          }
        }
        Behavior on height {
          NumberAnimation {
            duration: Style.animationNormal
            easing.type: Easing.OutBack
          }
        }
        // Burst effect overlay for focused pill (smaller outline)
        Rectangle {
          id: pillBurst
          anchors.centerIn: workspacePillContainer
          width: workspacePillContainer.width + 18 * workspacePillContainer.workspaceOwner.masterProgress * scale
          height: workspacePillContainer.height + 18 * workspacePillContainer.workspaceOwner.masterProgress * scale
          radius: width / 2
          color: NColor.transparent
          border.color: workspacePillContainer.workspaceOwner.effectColor
          border.width: Math.max(1, Math.round((2 + 6 * (1.0 - workspacePillContainer.workspaceOwner.masterProgress))))
          opacity: workspacePillContainer.workspaceOwner.effectsActive && workspacePillContainer.model.isFocused ? (1.0 - workspacePillContainer.workspaceOwner.masterProgress) * 0.7 : 0
          visible: workspacePillContainer.workspaceOwner.effectsActive && workspacePillContainer.model.isFocused
          z: 1
        }
      }
    }
  }

  // Vertical layout for left/right bars
  Column {
    id: pillColumn
    spacing: root.spacingBetweenPills
    anchors.horizontalCenter: workspaceBackground.horizontalCenter
    y: root.horizontalPadding
    visible: root.isVertical

    Repeater {
      id: workspaceRepeaterVertical
      model: root.localWorkspaces
      Item {
        id: workspacePillContainerVertical
        required property var model
        property Workspace workspaceOwner: root
        property bool urgent: workspacePillContainerVertical.model.isUrgent === true
        property bool displayedUrgent: workspacePillContainerVertical.workspaceOwner.displayedUrgentForWorkspace(workspacePillContainerVertical.model)

        width: Style.capsuleHeight * workspacePillContainerVertical.workspaceOwner.baseDimensionRatio
        height: workspacePillContainerVertical.workspaceOwner.getWorkspaceHeight(workspacePillContainerVertical.model)

        onUrgentChanged: {
          if (workspacePillContainerVertical.urgent) {
            workspacePillContainerVertical.workspaceOwner.setDisplayedUrgency(workspacePillContainerVertical.model, true);
          }
          verticalUrgencyCooldown.restart();
        }

        Component.onCompleted: {
          if (workspacePillContainerVertical.displayedUrgent) {
            verticalUrgencyCooldown.restart();
          }
        }

        Timer {
          id: verticalUrgencyCooldown
          interval: 5000
          repeat: false
          onTriggered: workspacePillContainerVertical.workspaceOwner.setDisplayedUrgency(workspacePillContainerVertical.model, workspacePillContainerVertical.urgent)
        }

        Rectangle {
          id: pillVertical
          anchors.fill: parent

          Loader {
            active: (workspacePillContainerVertical.workspaceOwner.labelMode !== "none")
            sourceComponent: WorkspaceLabel {
              model: workspacePillContainerVertical.model
              labelMode: workspacePillContainerVertical.workspaceOwner.labelMode
              characterCount: workspacePillContainerVertical.workspaceOwner.characterCount
              pillWidth: pillVertical.width
              pillHeight: pillVertical.height
              fontDimension: workspacePillContainerVertical.width
              displayedUrgent: workspacePillContainerVertical.displayedUrgent
              vertical: true
            }
          }

          radius: Style.radiusM
          color: {
            if (workspacePillContainerVertical.model.isFocused)
              return NColor.mPrimary;
            if (workspacePillContainerVertical.displayedUrgent)
              return NColor.mError;
            if (workspacePillContainerVertical.model.isOccupied)
              return NColor.mSecondary;

            return NColor.mOutline;
          }
          scale: workspacePillContainerVertical.model.isActive ? 1.0 : 0.9
          z: 0

          MouseArea {
            id: pillMouseAreaVertical
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
              CompositorService.switchToWorkspace(workspacePillContainerVertical.model);
            }
            hoverEnabled: true
          }
          // Material 3-inspired smooth animation for width, height, scale, color, opacity, and radius
          Behavior on width {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
          Behavior on height {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
          Behavior on scale {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
          Behavior on color {
            ColorAnimation {
              duration: Style.animationFast
              easing.type: Easing.InOutCubic
            }
          }
          Behavior on opacity {
            NumberAnimation {
              duration: Style.animationFast
              easing.type: Easing.InOutCubic
            }
          }
          Behavior on radius {
            NumberAnimation {
              duration: Style.animationNormal
              easing.type: Easing.OutBack
            }
          }
        }

        Behavior on width {
          NumberAnimation {
            duration: Style.animationNormal
            easing.type: Easing.OutBack
          }
        }
        Behavior on height {
          NumberAnimation {
            duration: Style.animationNormal
            easing.type: Easing.OutBack
          }
        }
        // Burst effect overlay for focused pill (smaller outline)
        Rectangle {
          id: pillBurstVertical
          anchors.centerIn: workspacePillContainerVertical
          width: workspacePillContainerVertical.width + 18 * workspacePillContainerVertical.workspaceOwner.masterProgress * scale
          height: workspacePillContainerVertical.height + 18 * workspacePillContainerVertical.workspaceOwner.masterProgress * scale
          radius: width / 2
          color: NColor.transparent
          border.color: workspacePillContainerVertical.workspaceOwner.effectColor
          border.width: Math.max(1, Math.round((2 + 6 * (1.0 - workspacePillContainerVertical.workspaceOwner.masterProgress))))
          opacity: workspacePillContainerVertical.workspaceOwner.effectsActive && workspacePillContainerVertical.model.isFocused ? (1.0 - workspacePillContainerVertical.workspaceOwner.masterProgress) * 0.7 : 0
          visible: workspacePillContainerVertical.workspaceOwner.effectsActive && workspacePillContainerVertical.model.isFocused
          z: 1
        }
      }
    }
  }
}
