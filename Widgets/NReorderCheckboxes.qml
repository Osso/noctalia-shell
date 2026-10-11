pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Widgets

Item {
  id: root

  // Public API
  property var model: []
  property var disabledIds: []
  property color activeColor: NColor.mPrimary
  property color activeOnColor: NColor.mOnPrimary
  property color dragHandleColor: NColor.mOutline
  property int baseSize: Style.baseWidgetSize * 0.7
  property int spacing: Style.marginM
  property ChecklistItem draggedItem: null

  signal itemToggled(int index, bool enabled)
  signal itemsReordered(int fromIndex, int toIndex)
  signal dragPotentialStarted
  signal dragPotentialEnded

  implicitHeight: listView.contentHeight

  function toggleItem(index) {
    if (index < 0 || index >= root.model.length)
      return;
    var item = root.model[index];
    if (item.required)
      return;

    // Create a new array to trigger binding update
    var newModel = root.model.slice();
    newModel[index] = Object.assign({}, item, {
                                      "enabled": !item.enabled
                                    });
    root.model = newModel;

    root.itemToggled(index, newModel[index].enabled);
  }

  function moveItem(fromIndex, toIndex) {
    if (fromIndex === toIndex)
      return;
    if (fromIndex < 0 || fromIndex >= root.model.length)
      return;
    if (toIndex < 0 || toIndex >= root.model.length)
      return;

    // Create a new array with item moved
    var newModel = root.model.slice();
    var item = newModel.splice(fromIndex, 1)[0];
    newModel.splice(toIndex, 0, item);
    root.model = newModel;

    root.itemsReordered(fromIndex, toIndex);
  }

  ListView {
    id: listView

    anchors.fill: parent
    spacing: root.spacing
    interactive: false
    clip: true
    model: root.model

    delegate: ChecklistItem {
      widgetOwner: root
      ownerView: listView
    }
  }

  component HandleDot: Rectangle {
    id: handleDot
    required property NReorderCheckboxes widgetOwner
    Layout.preferredWidth: handleDot.widgetOwner.baseSize * 0.4
    Layout.preferredHeight: 2
    radius: 1
    color: handleDot.widgetOwner.dragHandleColor
  }

  component ChecklistItem: Item {
    id: delegateItem
    required property NReorderCheckboxes widgetOwner
    required property ListView ownerView

    width: delegateItem.ownerView.width
    height: checkboxRow.height

    required property int index
    required property var modelData
    required property string id
    required property string text

    readonly property bool itemEnabled: modelData ? modelData.enabled === true : false
    readonly property bool required: modelData ? modelData.required === true : false
    readonly property bool isDisabled: (delegateItem.widgetOwner.disabledIds || []).indexOf(id) !== -1
    readonly property bool canDrag: !delegateItem.isDisabled
    property bool dragging: false
    property int dragStartY: 0
    property int dragStartIndex: -1
    property int dragTargetIndex: -1
    property int itemSpacing: delegateItem.widgetOwner.spacing

    RowLayout {
      id: checkboxRow

      width: parent.width
      spacing: Style.marginS
      opacity: delegateItem.isDisabled ? 0.5 : 1.0

      // Drag handle
      Rectangle {
        id: dragHandle

        Layout.preferredWidth: delegateItem.widgetOwner.baseSize
        Layout.preferredHeight: delegateItem.widgetOwner.baseSize
        radius: Style.radiusXS
        color: dragHandleMouseArea.containsMouse ? NColor.mSurfaceVariant : NColor.transparent

        Behavior on color {
          ColorAnimation {
            duration: Style.animationFast
          }
        }

        ColumnLayout {
          anchors.centerIn: parent
          spacing: Style.marginS

          Repeater {
            model: 3
            delegate: HandleDot {
              widgetOwner: delegateItem.widgetOwner
            }
          }
        }

        MouseArea {
          id: dragHandleMouseArea

          anchors.fill: parent
          cursorShape: delegateItem.canDrag ? Qt.SizeVerCursor : Qt.ArrowCursor
          hoverEnabled: true
          preventStealing: false
          enabled: delegateItem.canDrag
          z: 1000

          onPressed: mouse => {
            if (!delegateItem.canDrag) {
              return;
            }
            delegateItem.dragStartIndex = delegateItem.index;
            delegateItem.dragTargetIndex = delegateItem.index;
            delegateItem.dragStartY = delegateItem.y;
            delegateItem.dragging = true;
            delegateItem.widgetOwner.draggedItem = delegateItem;
            delegateItem.z = 999;

            // Signal that interaction started (prevents panel close)
            dragHandleMouseArea.preventStealing = true;
            delegateItem.widgetOwner.dragPotentialStarted();
          }

          onPositionChanged: mouse => {
            if (delegateItem.dragging) {
              const dy = mouse.y - dragHandle.height / 2;
              let newY = delegateItem.y + dy;

              // Constrain within bounds
              newY = Math.max(0, Math.min(newY, delegateItem.ownerView.contentHeight - delegateItem.height));
              delegateItem.y = newY;

              // Calculate target index (but don't apply yet)
              let targetIndex = Math.floor((newY + delegateItem.height / 2) / (delegateItem.height + delegateItem.itemSpacing));
              targetIndex = Math.max(0, Math.min(targetIndex, delegateItem.ownerView.count - 1));

              delegateItem.dragTargetIndex = targetIndex;
            }
          }

          onReleased: {
            // Always signal end of interaction
            delegateItem.widgetOwner.draggedItem = null;
            dragHandleMouseArea.preventStealing = false;
            delegateItem.widgetOwner.dragPotentialEnded();

            // Apply the model change now that drag is complete
            if (delegateItem.dragStartIndex !== -1 && delegateItem.dragTargetIndex !== -1 && delegateItem.dragStartIndex !== delegateItem.dragTargetIndex) {
              delegateItem.widgetOwner.moveItem(delegateItem.dragStartIndex, delegateItem.dragTargetIndex);
            }

            delegateItem.dragging = false;
            delegateItem.dragStartIndex = -1;
            delegateItem.dragTargetIndex = -1;
            delegateItem.z = 0;
          }

          onCanceled: {
            // Handle cancel (e.g., ESC key pressed during drag)
            delegateItem.widgetOwner.draggedItem = null;
            dragHandleMouseArea.preventStealing = false;
            delegateItem.widgetOwner.dragPotentialEnded();

            delegateItem.dragging = false;
            delegateItem.dragStartIndex = -1;
            delegateItem.dragTargetIndex = -1;
            delegateItem.z = 0;
          }
        }
      }

      // Checkbox
      Rectangle {
        id: box

        Layout.preferredWidth: delegateItem.widgetOwner.baseSize
        Layout.preferredHeight: delegateItem.widgetOwner.baseSize
        radius: Style.radiusXS
        color: delegateItem.itemEnabled ? delegateItem.widgetOwner.activeColor : NColor.mSurface
        border.color: delegateItem.required ? delegateItem.widgetOwner.activeColor : NColor.mOutline
        border.width: Style.borderS
        opacity: delegateItem.required ? 0.7 : 1.0

        Behavior on color {
          ColorAnimation {
            duration: Style.animationFast
          }
        }

        Behavior on border.color {
          ColorAnimation {
            duration: Style.animationFast
          }
        }

        NIcon {
          visible: delegateItem.itemEnabled
          anchors.centerIn: parent
          anchors.horizontalCenterOffset: -1
          icon: "check"
          color: delegateItem.widgetOwner.activeOnColor
          pointSize: Math.max(Style.fontSizeXS, delegateItem.widgetOwner.baseSize * 0.5)
        }

        MouseArea {
          anchors.fill: parent
          cursorShape: (!delegateItem.required && !delegateItem.isDisabled) ? Qt.PointingHandCursor : Qt.ArrowCursor
          enabled: !delegateItem.required && !delegateItem.isDisabled

          onClicked: {
            if (!delegateItem.required && !delegateItem.isDisabled) {
              delegateItem.widgetOwner.toggleItem(delegateItem.index);
            }
          }
        }
      }

      // Label
      NText {
        Layout.fillWidth: true
        text: delegateItem.text
        color: NColor.mOnSurface
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
      }

      // Required indicator
      NText {
        visible: delegateItem.required
        text: "(required)"
        color: NColor.mOnSurfaceVariant
        verticalAlignment: Text.AlignVCenter
      }
    }

    // Position binding for non-dragging state
    y: {
      if (delegateItem.dragging) {
        return delegateItem.y;
      }

      const draggedItem = delegateItem.widgetOwner.draggedItem;
      const draggedIndex = draggedItem ? draggedItem.dragStartIndex : -1;
      const targetIndex = draggedItem ? draggedItem.dragTargetIndex : -1;

      // If an item is being dragged, adjust positions
      if (draggedIndex !== -1 && targetIndex !== -1 && draggedIndex !== targetIndex) {
        const currentIndex = delegateItem.index;

        if (draggedIndex < targetIndex) {
          // Dragging down: shift items up between draggedIndex and targetIndex
          if (currentIndex > draggedIndex && currentIndex <= targetIndex) {
            return (currentIndex - 1) * (delegateItem.height + delegateItem.itemSpacing);
          }
        } else {
          // Dragging up: shift items down between targetIndex and draggedIndex
          if (currentIndex >= targetIndex && currentIndex < draggedIndex) {
            return (currentIndex + 1) * (delegateItem.height + delegateItem.itemSpacing);
          }
        }
      }

      return delegateItem.index * (delegateItem.height + delegateItem.itemSpacing);
    }

    Behavior on y {
      enabled: !delegateItem.dragging
      NumberAnimation {
        duration: Style.animationNormal
        easing.type: Easing.OutQuad
      }
    }
  }
}
