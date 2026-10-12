import QtQuick
import QtQuick.Controls
import QtTest
import qs.Widgets

Rectangle {
  id: scene
  width: 260
  height: 200
  color: "#00ff00"

  Component {
    id: gridComponent
    NGridView {
      x: 20
      y: 20
      width: 180
      height: 120
      cellWidth: 60
      cellHeight: 30
      handleColor: "#0000ff"
      handleHoverColor: "#ffff00"
      handlePressedColor: "#ff00ff"
      delegate: Rectangle {
        required property int index
        readonly property GridView view: GridView.view
        width: 60
        height: 30
        color: "#ff0000"
        MouseArea {
          anchors.fill: parent
          onClicked: parent.view.currentIndex = parent.index
        }
      }
    }
  }

  Component {
    id: listComponent
    NListView {
      x: 20
      y: 20
      width: 180
      height: 120
      spacing: 0
      handleColor: "#0000ff"
      handleHoverColor: "#ffff00"
      handlePressedColor: "#ff00ff"
      delegate: Rectangle {
        required property int index
        readonly property ListView view: ListView.view
        width: view.width
        height: 30
        color: "#ff0000"
        MouseArea {
          anchors.fill: parent
          onClicked: parent.view.currentIndex = parent.index
        }
      }
    }
  }

  TestCase {
    id: tests
    name: "GridListWarnings"
    when: windowShown
    property var widget

    function kinds() {
      return [
        {
          tag: "grid",
          grid: true
        },
        {
          tag: "list",
          grid: false
        }
      ];
    }

    function createView(grid, count) {
      widget = createTemporaryObject(grid ? gridComponent : listComponent, scene, {
        model: count
      });
      verify(widget !== null);
      widget.forceLayout();
      tryCompare(widget, "count", count);
      wait(20);
    }

    function test_repeat_geometry_data() {
      return kinds();
    }

    function test_repeat_geometry(data) {
      createView(data.grid, 0);
      const capacity = data.grid ? 12 : 4;
      for (const count of [1, capacity, capacity + 1, 30, 0, 30]) {
        widget.model = count;
        widget.forceLayout();
        tryCompare(widget, "count", count);
        const rows = data.grid ? Math.ceil(count / 3) : count;
        tryCompare(widget, "contentHeight", rows * 30);
        compare(widget.verticalScrollBarActive, count > capacity);
        compare(widget.scrollBarWidth, count > capacity ? 6 : 0);
        if (count > 0) {
          widget.currentIndex = 0;
          const view = widget.currentItem.view;
          compare(view.width, data.grid || count <= capacity ? 180 : 170);
          compare(view.height, 120);
          verify(view.clip);
          compare(widget.currentItem.x, 0);
          compare(widget.currentItem.y, 0);
          compare(widget.currentItem.height, 30);
        }
      }
    }

    function test_selection_scroll_data() {
      return kinds();
    }

    function test_selection_scroll(data) {
      createView(data.grid, 30);
      widget.currentIndex = 1;
      widget.incrementCurrentIndex();
      compare(widget.currentIndex, 2);
      widget.decrementCurrentIndex();
      compare(widget.currentIndex, 1);
      const item = widget.itemAtIndex(0);
      verify(item !== null);
      mouseClick(item, 10, 10);
      compare(widget.currentIndex, 0);
      compare(widget.indexAt(10, 10), 0);
      compare(widget.itemAt(10, 10), item);
      widget.positionViewAtEnd();
      tryVerify(() => widget.contentY > 0);
      const end = widget.contentHeight - 120;
      tryCompare(widget, "contentY", end);
      widget.currentIndex = 29;
      widget.forceLayout();
      tryVerify(() => widget.currentItem !== null);
      compare(widget.currentItem.index, 29);
      compare(widget.currentItem.y, data.grid ? 270 : 870);
      compare(widget.currentItem.x, data.grid ? 120 : 0);
      widget.positionViewAtBeginning();
      tryCompare(widget, "contentY", 0);
      widget.positionViewAtIndex(29, data.grid ? GridView.End : ListView.End);
      tryCompare(widget, "contentY", end);
      widget.cancelFlick();
      compare(widget.flicking, false);
    }

    function test_index_boundaries_data() {
      return kinds();
    }

    function test_index_boundaries(data) {
      createView(data.grid, 3);
      widget.keyNavigationWraps = false;
      widget.currentIndex = 2;
      widget.incrementCurrentIndex();
      compare(widget.currentIndex, 2);
      widget.currentIndex = 0;
      widget.decrementCurrentIndex();
      compare(widget.currentIndex, 0);
      widget.keyNavigationWraps = true;
      widget.decrementCurrentIndex();
      compare(widget.currentIndex, 2);
      widget.incrementCurrentIndex();
      compare(widget.currentIndex, 0);
      widget.model = 0;
      widget.forceLayout();
      widget.incrementCurrentIndex();
      widget.decrementCurrentIndex();
      compare(widget.currentIndex, -1);
    }

    function test_rtl_geometry_data() {
      return kinds();
    }

    function test_rtl_geometry(data) {
      createView(data.grid, 30);
      widget.layoutDirection = Qt.RightToLeft;
      widget.forceLayout();
      const bar = widget.currentItem.view.ScrollBar.vertical;
      bar.padding = 0;
      tryCompare(widget, "effectiveLayoutDirection", Qt.RightToLeft);
      tryCompare(bar, "x", 0);
      widget.layoutDirection = Qt.LeftToRight;
      tryCompare(bar, "x", 174);
      widget.width = 240;
      tryCompare(bar, "x", 234);
    }

    function test_palette_policy_data() {
      return kinds();
    }

    function test_palette_policy(data) {
      createView(data.grid, 30);
      const bar = widget.currentItem.view.ScrollBar.vertical;
      bar.padding = 0;
      widget.verticalPolicy = ScrollBar.AlwaysOn;
      tryCompare(bar.contentItem, "opacity", 1);
      tryCompare(bar.background, "opacity", 0.3);
      compare(bar.x, 174);
      compare(bar.height, 120);
      compare(bar.contentItem.width, 6);
      compare(bar.contentItem.color, "#0000ff");
      bar.pressed = true;
      tryCompare(bar.contentItem, "color", "#ff00ff");
      bar.pressed = false;
      tryCompare(bar.contentItem, "color", "#0000ff");
      widget.verticalPolicy = ScrollBar.AsNeeded;
      bar.active = false;
      tryCompare(bar.contentItem, "opacity", 0);
      bar.active = true;
      tryCompare(bar.contentItem, "opacity", 1);
      widget.verticalPolicy = ScrollBar.AlwaysOff;
      tryCompare(widget, "scrollBarWidth", 0);
      tryCompare(bar.contentItem, "opacity", 0);
    }

    function test_clipped_render_data() {
      return kinds();
    }

    function test_clipped_render(data) {
      createView(data.grid, 30);
      widget.contentY = 45;
      waitForRendering(scene);
      const image = grabImage(scene);
      compare(image.pixel(10, 50), "#00ff00");
      compare(image.pixel(210, 50), "#00ff00");
      compare(image.pixel(50, 10), "#00ff00");
      compare(image.pixel(50, 150), "#00ff00");
      compare(image.pixel(50, 50), "#ff0000");
    }

    function test_list_wheel_repeat() {
      createView(false, 30);
      for (let index = 0; index < 3; index++) {
        mouseWheel(widget, 60, 60, 0, -120);
      }
      tryCompare(widget, "contentY", 45);
      const bar = widget.currentItem.view.ScrollBar.vertical;
      compare(bar.active, true);
      mouseWheel(widget, 60, 60, 0, 960);
      tryCompare(widget, "contentY", 0);
      mouseWheel(widget, 60, 60, 0, -9600);
      tryCompare(widget, "contentY", 780);
    }
  }
}
