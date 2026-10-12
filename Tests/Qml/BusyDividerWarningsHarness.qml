import QtQuick
import QtTest
import qs.Commons
import qs.Widgets

Item {
  id: scene
  width: 240
  height: 180

  Component {
    id: busyComponent
    NBusyIndicator {}
  }

  Component {
    id: dividerComponent
    NDivider {}
  }

  Item {
    id: dividerParent
    width: 120
    height: 80
  }

  TestCase {
    id: tests
    name: "BusyDividerOwners"
    when: windowShown

    function test_busy_geometry_and_style() {
      const busy = createTemporaryObject(busyComponent, scene, {
        running: false
      });
      verify(busy !== null);
      compare(busy.width, 40);
      compare(busy.height, 40);
      compare(busy.strokeWidth, 4);
      compare(busy.duration, 200);
      Style.baseWidgetSize = 56;
      compare(busy.width, 56);
      compare(busy.height, 56);
      busy.size = 64;
      compare(busy.width, 64);
      compare(busy.height, 64);
      Style.baseWidgetSize = 40;
    }

    function test_busy_arc_uses_outer_stroke_width() {
      const busy = createTemporaryObject(busyComponent, scene, {
        running: false
      });
      verify(busy !== null);
      waitForRendering(busy);
      wait(100);
      const image = grabImage(busy);
      compare(image.pixel(20, 2), NColor.mPrimary);
    }

    function test_busy_animation_stop_resume_and_duration() {
      const busy = createTemporaryObject(busyComponent, scene, {
        running: false,
        duration: 800
      });
      verify(busy !== null);
      const spinner = busy.children[0];
      compare(spinner.rotation, 0);
      busy.running = true;
      tryVerify(() => spinner.rotation > 20, 1000);
      busy.running = false;
      const stopped = spinner.rotation;
      wait(120);
      compare(spinner.rotation, stopped);
      busy.duration = 120;
      busy.running = true;
      tryVerify(() => spinner.rotation !== stopped, 1000);
      busy.running = false;
      const resumed = spinner.rotation;
      wait(120);
      compare(spinner.rotation, resumed);
    }

    function test_divider_orientation_resize_and_style() {
      const divider = createTemporaryObject(dividerComponent, dividerParent);
      verify(divider !== null);
      compare(divider.width, 120);
      compare(divider.height, 2);
      compare(divider.gradient.orientation, Gradient.Horizontal);
      divider.vertical = true;
      compare(divider.width, 2);
      compare(divider.height, 80);
      compare(divider.gradient.orientation, Gradient.Vertical);
      dividerParent.height = 110;
      compare(divider.height, 110);
      Style.borderS = 3;
      compare(divider.width, 3);
      divider.vertical = false;
      compare(divider.width, 120);
      compare(divider.height, 3);
      compare(divider.gradient.orientation, Gradient.Horizontal);
      dividerParent.width = 160;
      compare(divider.width, 160);
      Style.borderS = 2;
      dividerParent.width = 120;
      dividerParent.height = 80;
    }
  }
}
