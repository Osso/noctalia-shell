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
    id: scrollComponent
    NScrollView {
      x: 20
      y: 20
      width: 180
      height: 120
      padding: 8
      flickableDirection: Flickable.HorizontalAndVerticalFlick
      handleColor: "#0000ff"
      handleHoverColor: "#ffff00"
      handlePressedColor: "#ff00ff"
      Rectangle {
        objectName: "content"
        width: 400
        height: 300
        implicitWidth: width
        implicitHeight: height
        color: "#ff0000"
      }
    }
  }

  TestCase {
    id: tests
    name: "ScrollViewWarnings"
    when: windowShown
    property var view

    function init() {
      view = createTemporaryObject(scrollComponent, scene);
      verify(view !== null);
      view.ScrollBar.vertical.padding = 0;
      view.ScrollBar.horizontal.padding = 0;
      wait(20);
    }

    function test_geometry_data() {
      return [
        {
          tag: "small",
          contentWidth: 80,
          contentHeight: 50,
          horizontal: false,
          vertical: false
        },
        {
          tag: "exact",
          contentWidth: 164,
          contentHeight: 104,
          horizontal: false,
          vertical: false
        },
        {
          tag: "tall",
          contentWidth: 80,
          contentHeight: 300,
          horizontal: false,
          vertical: true
        },
        {
          tag: "wide",
          contentWidth: 400,
          contentHeight: 50,
          horizontal: true,
          vertical: false
        },
        {
          tag: "both",
          contentWidth: 400,
          contentHeight: 300,
          horizontal: true,
          vertical: true
        }
      ];
    }

    function test_geometry(data) {
      const content = findChild(view, "content");
      content.width = data.contentWidth;
      content.height = data.contentHeight;
      tryCompare(view, "contentWidth", data.contentWidth);
      tryCompare(view, "contentHeight", data.contentHeight);
      compare(view.contentItem.width, 164);
      compare(view.contentItem.height, 104);
      compare(view.contentItem.x, 8);
      compare(view.contentItem.y, 8);
      compare(view.horizontalScrollable, data.horizontal);
      compare(view.verticalScrollable, data.vertical);
      compare(view.ScrollBar.vertical.x, 174);
      compare(view.ScrollBar.vertical.y, 8);
      compare(view.ScrollBar.vertical.height, 104);
      compare(view.ScrollBar.horizontal.x, 8);
      compare(view.ScrollBar.horizontal.y, 114);
      compare(view.ScrollBar.horizontal.width, 164);
      verify(view.contentItem.clip);
    }

    function test_scroll_and_resize() {
      view.contentItem.contentX = 100;
      view.contentItem.contentY = 150;
      const content = findChild(view, "content");
      const mapped = content.mapToItem(view, 0, 0);
      compare(mapped.x, -92);
      compare(mapped.y, -142);
      verify(view.ScrollBar.vertical.position > 0);
      verify(view.ScrollBar.horizontal.position > 0);
      view.width = 220;
      view.height = 160;
      tryCompare(view.contentItem, "width", 204);
      tryCompare(view.contentItem, "height", 144);
      compare(view.ScrollBar.vertical.height, 144);
      compare(view.ScrollBar.horizontal.width, 204);
    }

    function test_horizontal_disabled() {
      view.horizontalPolicy = ScrollBar.AlwaysOff;
      tryCompare(view.contentItem, "contentWidth", 164);
      compare(view.contentItem.flickableDirection, Flickable.VerticalFlick);
      compare(view.contentItem.boundsBehavior, Flickable.StopAtBounds);
      compare(view.horizontalScrollable, false);
      view.width = 220;
      tryCompare(view.contentItem, "contentWidth", 204);
      compare(view.verticalScrollable, true);
    }

    function test_clipped_render() {
      view.contentItem.contentX = 100;
      view.contentItem.contentY = 150;
      waitForRendering(scene);
      const image = grabImage(scene);
      compare(image.pixel(10, 50), "#00ff00");
      compare(image.pixel(210, 50), "#00ff00");
      compare(image.pixel(50, 10), "#00ff00");
      compare(image.pixel(50, 150), "#00ff00");
      compare(image.pixel(50, 50), "#ff0000");
    }

    function test_scrollbar_palette_data() {
      return [
        {
          tag: "vertical",
          vertical: true
        },
        {
          tag: "horizontal",
          vertical: false
        }
      ];
    }

    function test_scrollbar_palette(data) {
      const bar = data.vertical ? view.ScrollBar.vertical : view.ScrollBar.horizontal;
      bar.policy = ScrollBar.AlwaysOn;
      tryCompare(bar.contentItem, "opacity", 1);
      tryCompare(bar.background, "opacity", 0.3);
      compare(bar.contentItem.color, "#0000ff");
      bar.pressed = true;
      tryCompare(bar.contentItem, "color", "#ff00ff");
      bar.pressed = false;
      tryCompare(bar.contentItem, "color", "#0000ff");
      bar.policy = ScrollBar.AsNeeded;
      bar.active = false;
      tryCompare(bar.contentItem, "opacity", 0);
      tryCompare(bar.background, "opacity", 0);
      bar.active = true;
      tryCompare(bar.contentItem, "opacity", 1);
      tryCompare(bar.background, "opacity", 0.3);
    }
  }
}
