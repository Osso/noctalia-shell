import QtQuick
import QtQuick.Shapes
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Modules.MainScreen.Backgrounds

TestCase {
  id: testCase
  name: "BackgroundPaths"
  width: 400
  height: 300
  visible: true
  when: windowShown

  BackgroundRegion {
    id: panelRegion
  }
  BackgroundRegion {
    id: barRegion
  }
  QtObject {
    id: screenOwner
    property QtObject screen: QtObject {
      property string name: "DP-fixture"
    }
  }
  Shape {
    id: panelShape
    anchors.fill: parent
    containsMode: Shape.FillContains
    PanelBackground {
      id: panelPath
      panel: panelRegion
      shapeContainer: panelShape
      backgroundColor: "#204060"
    }
  }
  Shape {
    id: barShape
    anchors.fill: parent
    containsMode: Shape.FillContains
    BarBackground {
      id: barPath
      bar: barRegion
      shapeContainer: barShape
      windowRoot: screenOwner
      backgroundColor: "#406080"
    }
  }

  function init() {
    panelRegion.visible = true;
    panelPath.panel = panelRegion;
    barPath.bar = barRegion;
    barPath.windowRoot = screenOwner;
    BarService.isVisible = true;
    Settings.data.bar.monitors = [];
    Style.radiusL = 12;
    for (const region of [panelRegion, barRegion]) {
      region.x = 40;
      region.y = 30;
      region.width = 120;
      region.height = 80;
      setCorners(region, 0);
    }
    wait(0);
  }

  function setCorners(region, state) {
    region.topLeftCornerState = state;
    region.topRightCornerState = state;
    region.bottomRightCornerState = state;
    region.bottomLeftCornerState = state;
  }

  function test_layout_tracks_position_and_size() {
    for (const shape of [panelShape, barShape]) {
      verify(shape.contains(Qt.point(100, 70)), "center filled");
      verify(!shape.contains(Qt.point(39, 70)), "outside left empty");
      verify(!shape.contains(Qt.point(161, 70)), "outside right empty");
    }
    for (const region of [panelRegion, barRegion]) {
      region.x = 200;
      region.y = 120;
      region.width = 60;
      region.height = 40;
    }
    wait(0);
    for (const shape of [panelShape, barShape]) {
      verify(!shape.contains(Qt.point(100, 70)), "old center cleared");
      verify(shape.contains(Qt.point(230, 140)), "moved center filled");
      verify(!shape.contains(Qt.point(261, 140)), "new right edge bounded");
    }
  }

  function test_rounded_and_square_edges_data() {
    return [
      {
        tag: "top-left",
        x: 41,
        y: 31
      },
      {
        tag: "top-right",
        x: 159,
        y: 31
      },
      {
        tag: "bottom-right",
        x: 159,
        y: 109
      },
      {
        tag: "bottom-left",
        x: 41,
        y: 109
      }
    ];
  }

  function test_rounded_and_square_edges(data) {
    for (const shape of [panelShape, barShape]) {
      verify(!shape.contains(Qt.point(data.x, data.y)), "rounded corner excludes tip");
      verify(shape.contains(Qt.point(100, 31)), "top edge remains filled");
    }
    setCorners(panelRegion, -1);
    setCorners(barRegion, -1);
    wait(0);
    for (const shape of [panelShape, barShape])
      verify(shape.contains(Qt.point(data.x, data.y)), "square corner includes tip");
  }

  function test_inverted_corner_extends_past_edge_data() {
    return [
      {
        tag: "horizontal",
        state: 1,
        x: 38,
        y: 31
      },
      {
        tag: "vertical",
        state: 2,
        x: 41,
        y: 28
      }
    ];
  }

  function test_inverted_corner_extends_past_edge(data) {
    for (const shape of [panelShape, barShape])
      verify(!shape.contains(Qt.point(data.x, data.y)), "normal corner stays inside");
    panelRegion.topLeftCornerState = data.state;
    barRegion.topLeftCornerState = data.state;
    wait(0);
    for (const shape of [panelShape, barShape])
      verify(shape.contains(Qt.point(data.x, data.y)), "inverted corner fills attachment");
  }

  function test_small_geometry_flattens_radius() {
    panelRegion.width = 16;
    panelRegion.height = 10;
    barRegion.width = 16;
    barRegion.height = 10;
    wait(0);
    compare(panelPath.effectiveRadius, 5);
    compare(barPath.effectiveRadius, 5);
    for (const shape of [panelShape, barShape]) {
      verify(shape.contains(Qt.point(48, 35)), "small center filled");
      verify(!shape.contains(Qt.point(40.5, 30.5)), "small rounded tip empty");
      verify(!shape.contains(Qt.point(57, 35)), "small right edge bounded");
    }
  }

  function test_panel_hidden_null_and_replacement() {
    panelRegion.visible = false;
    wait(0);
    compare(panelPath.panelWidth, 0);
    verify(!panelShape.contains(Qt.point(100, 70)));
    panelRegion.visible = true;
    panelPath.panel = barRegion;
    barRegion.x = 210;
    wait(0);
    verify(!panelShape.contains(Qt.point(100, 70)));
    verify(panelShape.contains(Qt.point(270, 70)));
    panelPath.panel = null;
    wait(0);
    compare(panelPath.panelWidth, 0);
    verify(!panelShape.contains(Qt.point(270, 70)));
  }

  function test_bar_visibility_monitor_and_null() {
    BarService.isVisible = false;
    wait(0);
    verify(!barShape.contains(Qt.point(100, 70)));
    BarService.isVisible = true;
    Settings.data.bar.monitors = ["other"];
    wait(0);
    verify(!barShape.contains(Qt.point(100, 70)));
    Settings.data.bar.monitors = ["DP-fixture"];
    wait(0);
    verify(barShape.contains(Qt.point(100, 70)));
    barPath.windowRoot = null;
    wait(0);
    verify(!barShape.contains(Qt.point(100, 70)));
    Settings.data.bar.monitors = [];
    wait(0);
    verify(barShape.contains(Qt.point(100, 70)));
    barPath.bar = null;
    wait(0);
    verify(!barShape.contains(Qt.point(100, 70)));
  }

  function test_fill_color_updates() {
    panelPath.backgroundColor = "#112233";
    barPath.backgroundColor = "#445566";
    compare(panelPath.fillColor, "#112233");
    tryCompare(barPath, "fillColor", "#445566");
  }
}
