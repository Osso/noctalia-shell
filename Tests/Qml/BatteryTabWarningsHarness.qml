import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell.Services.UPower
import qs.Commons
import qs.Tabs

TestCase {
  id: testCase
  name: "BatteryTabWarnings"
  visible: true
  width: 800
  height: 1800
  when: windowShown

  Component {
    id: tabComponent
    BatteryTab {
      width: 800
    }
  }

  function descendants(item) {
    let result = [item];
    for (const child of item.children || []) {
      result = result.concat(descendants(child));
    }
    return result;
  }

  function texts(tab) {
    return descendants(tab).filter(item => typeof item.text === "string" && item.visible).map(item => item.text);
  }

  function progressTrack(tab) {
    const candidates = descendants(tab).filter(item => item.color !== undefined && item.color.toString() === NColor.mSurfaceVariant.toString() && item.children.length === 1 && item.children[0].radius !== undefined);
    compare(candidates.length, 1, "One observable progress track");
    return candidates[0];
  }

  function process(tab) {
    const candidates = Array.from(tab.resources).filter(item => item.command !== undefined);
    compare(candidates.length, 1, "One isolated threshold process");
    return candidates[0];
  }

  function test_tab_data() {
    return [
          {
            tag: "scale-1",
            scale: 1
          },
          {
            tag: "scale-1.25",
            scale: 1.25
          }
        ];
  }

  function test_tab(data) {
    Style.uiScaleRatio = data.scale;
    UPower.displayDevice.ready = true;
    UPower.displayDevice.percentage = 0.65;
    UPower.displayDevice.state = UPowerDeviceState.Discharging;
    UPower.displayDevice.healthSupported = true;
    UPower.displayDevice.healthPercentage = 85;
    UPower.displayDevice.timeToFull = 0;
    UPower.displayDevice.timeToEmpty = 7200;
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(100);
    compare(tab.isReady, true);
    compare(tab.percent, 65);
    compare(tab.charging, false);
    compare(tab.healthPercent, 85);
    compare(tab.thresholdsSupported, true);
    compare(tab.thresholdsLoading, false);
    compare(tab.chargeStartThreshold, 20);
    compare(tab.chargeStopThreshold, 80);
    compare(tab.cycleCount, 123);
    compare(tab.cycleCountSupported, true);
    verify(texts(tab).includes("65%"));
    verify(texts(tab).includes("85%"));
    verify(texts(tab).includes("7200 seconds"));
    verify(texts(tab).includes("12.5 W"));
    verify(texts(tab).includes("123"));
    verify(texts(tab).includes("20% - 80%"));
    const track = progressTrack(tab);
    const fill = track.children[0];
    compare(track.height, Math.round(8 * data.scale));
    verify(track.width > 100);
    compare(fill.height, track.height);
    compare(fill.y, 0);
    fuzzyCompare(fill.width, track.width * 0.65, 0.01);
    compare(fill.radius, track.radius);
    compare(fill.color, NColor.mSecondary);
    const snapshot = {
      scale: data.scale,
      texts: texts(tab),
      track: {
        x: track.x,
        y: track.y,
        width: track.width,
        height: track.height,
        radius: track.radius
      },
      fill: {
        x: fill.x,
        y: fill.y,
        width: fill.width,
        height: fill.height,
        radius: fill.radius
      },
      tabHeight: tab.implicitHeight
    };
    console.log("BATTERY_SNAPSHOT " + JSON.stringify(snapshot));

    UPower.displayDevice.percentage = 0.15;
    wait(50);
    compare(tab.percent, 15);
    fuzzyCompare(fill.width, track.width * 0.15, 0.01);
    compare(fill.color, NColor.mError);
    UPower.displayDevice.state = UPowerDeviceState.Charging;
    UPower.displayDevice.timeToFull = 1800;
    wait(50);
    compare(tab.charging, true);
    verify(texts(tab).includes("1800 seconds"));
    verify(texts(tab).includes("battery.charging"));
    compare(fill.color, NColor.mPrimary);
    UPower.displayDevice.healthSupported = false;
    compare(tab.healthAvailable, false);
    compare(tab.healthPercent, -1);
    UPower.displayDevice.percentage = 1.2;
    wait(50);
    compare(fill.width, track.width);
    UPower.displayDevice.percentage = -0.1;
    wait(50);
    compare(fill.width, 0);
    UPower.displayDevice.ready = false;
    wait(50);
    compare(tab.isReady, false);
    compare(tab.percent, -1);
    verify(texts(tab).includes("battery.no-battery-detected"));
    verify(!texts(tab).includes("battery.battery-level"));

    const sliders = descendants(tab).filter(item => item.from === 0 && item.to === 100 && typeof item.text === "string");
    compare(sliders.length, 2);
    sliders[0].moved(90);
    compare(tab.localStartThreshold, 75);
    sliders[0].moved(25);
    compare(tab.localStartThreshold, 25);
    const writer = process(tab);
    compare(writer.running, false, "Dragging does not write");
    sliders[0].pressedChanged(false, 25);
    compare(writer.running, true);
    compare(writer.command, ["pkexec", "bash", "-c", "echo 25 > /sys/class/power_supply/BAT0/charge_control_start_threshold"]);
    writer.running = false;
    sliders[1].moved(10);
    compare(tab.localStopThreshold, 30);
    sliders[1].moved(85);
    compare(tab.localStopThreshold, 85);
    compare(writer.running, false);
    sliders[1].pressedChanged(false, 85);
    compare(writer.running, true);
    compare(writer.command, ["pkexec", "bash", "-c", "echo 85 > /sys/class/power_supply/BAT0/charge_control_end_threshold"]);
    writer.running = false;
    writer.exited(0);
    compare(tab.chargeStopThreshold, 80, "Successful write reloads fixture sysfs");
    tab.setStartThreshold(35);
    compare(writer.command[2], "-c");
    verify(writer.command[3].includes("echo 35 >"));
    writer.running = false;
    writer.exited(0);
    compare(tab.localStartThreshold, 20);
    tab.thresholdsSupported = false;
    tab.thresholdsLoading = false;
    wait(50);
    verify(texts(tab).includes("settings.battery.thresholds.not-supported"));
    verify(!texts(tab).includes("20% - 80%"));
  }
}
