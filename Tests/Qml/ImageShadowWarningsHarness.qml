import QtQuick
import QtTest
import qs.Commons
import qs.Services.Power
import qs.Widgets

Item {
  id: scene
  width: 400
  height: 300

  Component {
    id: imageFactory
    NImageRounded {}
  }
  Component {
    id: shadowFactory
    NDropShadow {}
  }
  Rectangle {
    id: firstSource
    width: 60
    height: 30
    color: "red"
  }
  Rectangle {
    id: secondSource
    width: 90
    height: 50
    color: "blue"
  }

  TestCase {
    id: tests
    name: "ImageShadow"
    when: windowShown
    // Runtime fixture permits replacement; production Settings.data is read-only.
    property var fixtureSettings: Settings

    SignalSpy {
      id: statusSpy
      signalName: "statusChanged"
    }

    function init() {
      fixtureSettings.data = {
        general: {
          enableShadows: true,
          shadowOffsetX: 2,
          shadowOffsetY: 3
        }
      };
      PowerProfileService.noctaliaPerformanceMode = false;
    }

    function createImage(properties) {
      const widget = createTemporaryObject(imageFactory, scene, properties);
      verify(widget !== null);
      statusSpy.target = widget;
      statusSpy.clear();
      return widget;
    }

    function imageChild(widget) {
      const children = widget.children[0].children;
      for (let index = 0; index < children.length; index++) {
        if (children[index].sourceSize !== undefined)
          return children[index];
      }
      fail("image child absent");
    }

    function test_geometry_and_decode_resize() {
      const widget = createImage({
        width: 80,
        height: 40,
        borderWidth: 3,
        radius: 12
      });
      const image = imageChild(widget);
      compare(widget.shouldLoadImage(), false);
      compare(image.width, 74);
      compare(image.height, 34);
      compare(image.x, 3);
      compare(image.y, 3);
      widget.imagePath = Qt.resolvedUrl("red.svg");
      tryCompare(image, "status", Image.Ready);
      compare(widget.shouldLoadImage(), true);
      compare(image.sourceSize.width, widget.targetDecodeSize().width);
      compare(image.sourceSize.height, widget.targetDecodeSize().height);
      widget.width = 121;
      widget.height = 63;
      widget.borderWidth = 5;
      tryCompare(image, "width", 111);
      compare(image.height, 53);
      compare(image.sourceSize.width, widget.targetDecodeSize().width);
      compare(image.sourceSize.height, widget.targetDecodeSize().height);
      widget.width = 0;
      tryCompare(image, "status", Image.Null);
      compare(widget.shouldLoadImage(), false);
      widget.width = 90;
      tryCompare(image, "status", Image.Ready);
    }

    function test_source_visibility_fallback_and_status() {
      const widget = createImage({
        width: 80,
        height: 40,
        fallbackIcon: "disc"
      });
      const image = imageChild(widget);
      compare(widget.showFallback, true);
      compare(widget.shouldLoadImage(), false);
      widget.imagePath = Qt.resolvedUrl("red.svg");
      tryCompare(image, "status", Image.Ready);
      compare(widget.showFallback, false);
      verify(statusSpy.count > 0);
      compare(statusSpy.signalArguments[statusSpy.count - 1][0], Image.Ready);
      widget.imagePath = Qt.resolvedUrl("blue.svg");
      tryCompare(image, "source", Qt.resolvedUrl("blue.svg"));
      tryCompare(image, "status", Image.Ready);
      widget.visible = false;
      tryCompare(image, "status", Image.Null);
      compare(widget.shouldLoadImage(), false);
      widget.visible = true;
      tryCompare(image, "status", Image.Ready);
      widget.imagePath = "";
      tryCompare(image, "status", Image.Null);
      compare(widget.showFallback, true);
      compare(statusSpy.signalArguments[statusSpy.count - 1][0], Image.Null);
    }

    function test_rounded_effect_geometry_transitions() {
      const widget = createImage({
        width: 80,
        height: 40,
        borderWidth: 3,
        radius: 12,
        imagePath: Qt.resolvedUrl("red.svg")
      });
      const loader = widget.children[0].children[1];
      tryVerify(function () {
        return loader.item !== null;
      });
      compare(loader.item.itemWidth, 74);
      compare(loader.item.itemHeight, 34);
      compare(loader.item.cornerRadius, 9);
      widget.width = 100;
      widget.radius = 2;
      widget.imageFillMode = Image.Stretch;
      compare(loader.item.itemWidth, 94);
      compare(loader.item.cornerRadius, 0);
      compare(loader.item.fillMode, Image.Stretch);
      widget.imagePath = "";
      tryCompare(loader, "active", false);
      compare(loader.item, null);
      widget.imagePath = Qt.resolvedUrl("blue.svg");
      tryVerify(function () {
        return loader.item !== null;
      });
      compare(loader.item.itemWidth, 94);
      compare(loader.item.fillMode, Image.Stretch);
    }

    function test_shadow_component_owner_and_source_transitions() {
      const widget = createTemporaryObject(shadowFactory, scene, {
        source: firstSource,
        width: 60,
        height: 30
      });
      verify(widget !== null);
      const effect = createTemporaryObject(widget.layer.effect, scene);
      verify(effect !== null);
      compare(effect.source, firstSource);
      compare(effect.shadowHorizontalOffset, 2);
      compare(effect.shadowVerticalOffset, 3);
      compare(effect.shadowOpacity, 0.4);
      compare(effect.shadowBlur, 0.6);
      compare(effect.autoPaddingEnabled, false);
      widget.source = secondSource;
      widget.shadowHorizontalOffset = -4;
      widget.shadowVerticalOffset = 8;
      widget.shadowOpacity = 0.7;
      widget.shadowBlur = 0.2;
      widget.shadowColor = "blue";
      widget.autoPaddingEnabled = true;
      compare(effect.source, secondSource);
      compare(effect.shadowHorizontalOffset, -4);
      compare(effect.shadowVerticalOffset, 8);
      compare(effect.shadowOpacity, 0.7);
      compare(effect.shadowBlur, 0.2);
      compare(effect.shadowColor, "#0000ff");
      compare(effect.autoPaddingEnabled, true);
      widget.source = firstSource;
      compare(effect.source, firstSource);
    }

    function test_image_instances_keep_creation_context() {
      const first = createImage({
        width: 80,
        height: 40,
        radius: 12,
        borderWidth: 3,
        imagePath: Qt.resolvedUrl("red.svg")
      });
      const second = createImage({
        width: 120,
        height: 60,
        radius: 24,
        borderWidth: 4,
        imagePath: Qt.resolvedUrl("blue.svg")
      });
      const firstLoader = first.children[0].children[1];
      const secondLoader = second.children[0].children[1];
      tryVerify(function () {
        return firstLoader.item !== null && secondLoader.item !== null;
      });
      compare(firstLoader.item.cornerRadius, 9);
      compare(secondLoader.item.cornerRadius, 20);
      compare(firstLoader.item.source, imageChild(first));
      compare(secondLoader.item.source, imageChild(second));
      first.radius = 18;
      compare(firstLoader.item.cornerRadius, 15);
      compare(secondLoader.item.cornerRadius, 20);
      first.imagePath = "";
      tryCompare(firstLoader, "active", false);
      compare(secondLoader.item.source, imageChild(second));
      first.imagePath = Qt.resolvedUrl("blue.svg");
      tryVerify(function () {
        return firstLoader.item !== null;
      });
      compare(firstLoader.item.cornerRadius, 15);
      compare(firstLoader.item.source, imageChild(first));
    }

    function test_shadow_instances_keep_creation_context() {
      const first = createTemporaryObject(shadowFactory, scene, {
        source: firstSource,
        shadowBlur: 0.2
      });
      const second = createTemporaryObject(shadowFactory, scene, {
        source: secondSource,
        shadowBlur: 0.8
      });
      verify(first !== null && second !== null);
      const firstEffect = createTemporaryObject(first.layer.effect, scene);
      const secondEffect = createTemporaryObject(second.layer.effect, scene);
      verify(firstEffect !== null && secondEffect !== null);
      compare(firstEffect.source, firstSource);
      compare(secondEffect.source, secondSource);
      compare(firstEffect.shadowBlur, 0.2);
      compare(secondEffect.shadowBlur, 0.8);
      first.source = secondSource;
      first.shadowBlur = 0.4;
      compare(firstEffect.source, secondSource);
      compare(firstEffect.shadowBlur, 0.4);
      compare(secondEffect.shadowBlur, 0.8);
    }

    function test_shadow_enable_settings_and_performance() {
      const widget = createTemporaryObject(shadowFactory, scene, {
        source: firstSource
      });
      verify(widget !== null);
      compare(widget.layer.enabled, true);
      PowerProfileService.noctaliaPerformanceMode = true;
      compare(widget.layer.enabled, false);
      PowerProfileService.noctaliaPerformanceMode = false;
      compare(widget.layer.enabled, true);
      fixtureSettings.data = {
        general: {
          enableShadows: false,
          shadowOffsetX: 5,
          shadowOffsetY: -2
        }
      };
      compare(widget.layer.enabled, false);
      compare(widget.shadowHorizontalOffset, 5);
      compare(widget.shadowVerticalOffset, -2);
      fixtureSettings.data = {
        general: {
          enableShadows: true,
          shadowOffsetX: 1,
          shadowOffsetY: 9
        }
      };
      compare(widget.layer.enabled, true);
      compare(widget.shadowHorizontalOffset, 1);
      compare(widget.shadowVerticalOffset, 9);
    }
  }
}
