import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Panels.Settings.Tabs
import qs.Services.Hardware
import qs.Services.Location
import qs.Services.UI

TestCase {
  id: testCase
  name: "DisplayTabWarnings"
  width: 900
  height: 1800
  visible: true
  when: windowShown

  Component {
    id: tabComponent
    DisplayTab {
      width: 900
    }
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function control(tab, property, value) {
    const matches = descendants(tab).filter(item => item[property] === value && (property !== "label" || item.toggled !== undefined || item.changeValue !== undefined));
    compare(matches.length, 1, property + "=" + value);
    return matches[0];
  }

  function init() {
    Settings.data.nightLight.enabled = true;
    Settings.data.nightLight.autoSchedule = false;
    Settings.data.nightLight.forced = false;
    Settings.data.nightLight.dayTemp = 6500;
    Settings.data.nightLight.nightTemp = 4000;
    Settings.data.nightLight.manualSunrise = "06:30";
    Settings.data.nightLight.manualSunset = "18:00";
    BrightnessService.laptop.brightness = 0.4;
    BrightnessService.external.brightness = 0.7;
    BrightnessService.laptop.writes = [];
    BrightnessService.external.writes = [];
    Quickshell.screens = [Quickshell.laptop, Quickshell.external, Quickshell.unavailable, Quickshell.missing];
  }

  function test_monitorRendering_data() {
    return [
          {
            tag: "scale-1",
            scale: 1
          },
          {
            tag: "scale-1.5",
            scale: 1.5
          }
        ];
  }

  function test_monitorRendering(data) {
    Style.uiScaleRatio = data.scale;
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(100);
    const cards = descendants(tab).filter(item => item.monitorName !== undefined);
    compare(cards.length, 4);
    compare(cards.map(item => item.monitorName).join(","), "eDP-1,DP-1,HDMI-1,DP-2");
    const descriptions = ["Laptop:1920x1080@1", "External:3840x2160@1.5", "ReadOnly:1280x720@1", "NoBrightness:800x600@1"];
    for (let index = 0; index < cards.length; index++) {
      const card = cards[index];
      verify(card.width > 800);
      verify(card.height > 0);
      verify(descendants(card).some(item => item.text === descriptions[index]), descriptions[index]);
      const column = card.children[0];
      compare(column.x, Style.marginL);
      compare(column.y, Style.marginL);
      fuzzyCompare(column.width, card.width - 2 * Style.marginL, 0.01);
      fuzzyCompare(card.height, column.implicitHeight + 2 * Style.marginL, 0.01);
      if (index > 0)
        verify(card.y >= cards[index - 1].y + cards[index - 1].height);
    }
    verify(descendants(cards[0]).some(item => item.visible && item.text === "40%"));
    verify(descendants(cards[1]).some(item => item.visible && item.text === "70%"));
    const unavailable = descendants(cards[2]).filter(item => item.from === 0 && item.to === 1 && item.moved !== undefined);
    verify(unavailable.length > 0);
    compare(unavailable[0].enabled, false);
    verify(descendants(cards[2]).some(item => item.visible && typeof item.text === "string" && item.text.startsWith("settings.display.monitors.brightness-unavailable.")));
    verify(!descendants(cards[3]).some(item => item.visible && item.text === "N/A"));
    compare(BrightnessService.laptop.writes.length, 0);
    compare(BrightnessService.external.writes.length, 0);
    // Render the actual production subtree into an offscreen image.
    let imageReady = false;
    verify(tab.grabToImage(image => {
      const path = Qt.resolvedUrl("display-scale-" + data.scale + ".png").toString().replace("file://", "");
      verify(image.saveToFile(path));
      imageReady = true;
    }));
    tryVerify(() => imageReady);
  }

  function test_brightnessAndRoleRepopulation() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(100);
    let cards = descendants(tab).filter(item => item.monitorName !== undefined);
    const laptopSlider = descendants(cards[0]).find(item => item.pressedChanged !== undefined && item.moved !== undefined && item.stepSize === 0.01);
    verify(laptopSlider !== undefined);
    laptopSlider.moved(0.55);
    laptopSlider.pressedChanged(false, 0.62);
    compare(BrightnessService.laptop.brightness, 0.62);
    compare(BrightnessService.laptop.writes.join(","), "0.55,0.62");
    compare(BrightnessService.external.writes.length, 0);
    Quickshell.screens = [Quickshell.external, Quickshell.laptop];
    wait(100);
    cards = descendants(tab).filter(item => item.monitorName !== undefined);
    compare(cards.length, 2);
    compare(cards[0].monitorName, "DP-1");
    compare(cards[1].monitorName, "eDP-1");
    const externalSlider = descendants(cards[0]).find(item => item.pressedChanged !== undefined && item.moved !== undefined && item.stepSize === 0.01);
    externalSlider.moved(0.81);
    compare(BrightnessService.external.brightness, 0.81);
    compare(BrightnessService.laptop.brightness, 0.62);
  }

  function test_selectionAndEditLifecycle() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(100);
    const sunrise = control(tab, "placeholder", "settings.display.night-light.manual-schedule.select-start");
    const sunset = control(tab, "placeholder", "settings.display.night-light.manual-schedule.select-stop");
    compare(sunrise.itemCount(), 48);
    compare(sunrise.getItem(0).key, "00:00");
    compare(sunrise.getItem(47).key, "23:30");
    compare(sunrise.findIndexByKey("06:30"), 13);
    verify(sunrise.width >= 120);
    verify(sunrise.height > 0);
    sunrise.activateCurrentIndex(15);
    sunset.activateCurrentIndex(40);
    compare(Settings.data.nightLight.manualSunrise, "07:30");
    compare(Settings.data.nightLight.manualSunset, "20:00");
    compare(sunrise.currentKey, "07:30");
    compare(sunset.currentKey, "20:00");
    const spin = control(tab, "label", "settings.display.monitors.brightness-step.label");
    spin.changeValue(1, 1);
    compare(Settings.data.brightness.brightnessStep, spin.value);
    const minimum = control(tab, "label", "settings.display.monitors.enforce-minimum.label");
    minimum.toggled(false);
    compare(Settings.data.brightness.enforceMinimum, false);
    // The production tab has immediate edits, not a Save/Cancel transaction.
    // Serialize only fake settings; cancel means destroying the tab, not rollback.
    const saved = JSON.stringify({
                                   sunrise: Settings.data.nightLight.manualSunrise,
                                   sunset: Settings.data.nightLight.manualSunset
                                 });
    compare(saved, '{"sunrise":"07:30","sunset":"20:00"}');
    tab.destroy();
    wait(0);
    compare(Settings.data.nightLight.manualSunrise, "07:30");
    const reopened = createTemporaryObject(tabComponent, testCase);
    verify(reopened !== null);
    wait(100);
    compare(control(reopened, "placeholder", "settings.display.night-light.manual-schedule.select-start").currentKey, "07:30");
  }

  function test_nightLightAvailabilityAndToasts() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(100);
    const checks = Array.from(tab.resources).filter(item => item.command !== undefined);
    compare(checks.length, 1);
    const check = checks[0];
    compare(check.command.join(","), "which,wlsunset");
    ToastService.notices = [];
    ToastService.warnings = [];
    const before = NightLightService.applies;
    Settings.data.nightLight.enabled = false;
    const enabled = control(tab, "label", "settings.display.night-light.enable.label");
    enabled.toggled(true);
    compare(check.running, true);
    check.running = false;
    check.exited(1);
    compare(Settings.data.nightLight.enabled, false);
    compare(ToastService.warnings.join(","), "toast.night-light.not-installed");
    compare(NightLightService.applies, before);
    enabled.toggled(true);
    check.running = false;
    check.exited(0);
    compare(Settings.data.nightLight.enabled, true);
    compare(NightLightService.applies, before + 1);
    compare(ToastService.notices.join(","), "toast.night-light.enabled");
  }

  function test_temperatureReleaseAndScheduleVisibility() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(100);
    const sliders = descendants(tab).filter(item => item.from === 1000 && item.to === 6500);
    compare(sliders.length, 2);
    const night = sliders[0];
    const day = sliders[1];
    night.value = 6400;
    compare(night.value, 6000);
    compare(Settings.data.nightLight.nightTemp, 4000);
    night.pressedChanged();
    compare(Settings.data.nightLight.nightTemp, 6000);
    day.value = 1000;
    compare(day.value, 6500);
    day.pressedChanged();
    compare(Settings.data.nightLight.dayTemp, 6500);
    const sunrise = control(tab, "placeholder", "settings.display.night-light.manual-schedule.select-start");
    const automatic = control(tab, "label", "settings.display.night-light.auto-schedule.label");
    automatic.toggled(true);
    compare(sunrise.visible, false);
    automatic.toggled(false);
    compare(sunrise.visible, true);
    const enabled = control(tab, "label", "settings.display.night-light.enable.label");
    enabled.toggled(false);
    compare(Settings.data.nightLight.enabled, false);
    compare(sunrise.visible, false);
  }
}
