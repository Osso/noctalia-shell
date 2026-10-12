import QtQuick
import QtTest
import qs.Commons
import qs.Services.Location
import qs.Tabs

TestCase {
  id: testCase
  name: "LocationTabWarnings"
  width: 900
  height: 1600
  visible: true
  when: windowShown

  Component {
    id: tabComponent
    LocationTab {
      width: 900
    }
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function control(tab, label) {
    const matches = descendants(tab).filter(item => item.label === label && (item.toggled !== undefined || item.editingFinished !== undefined || item.selected !== undefined));
    compare(matches.length, 1, label);
    return matches[0];
  }

  function reorderControl(tab) {
    const matches = descendants(tab).filter(item => item.itemsReordered !== undefined);
    compare(matches.length, 1);
    return matches[0];
  }

  function init() {
    Settings.data.location.name = "Fixture City";
    Settings.data.location.weatherEnabled = true;
    Settings.data.location.firstDayOfWeek = -1;
    Settings.data.calendar.cards = [
      {
        id: "calendar-header-card",
        enabled: true
      },
      {
        id: "calendar-month-card",
        enabled: true
      },
      {
        id: "timer-card",
        enabled: false
      },
      {
        id: "weather-card",
        enabled: true
      }
    ];
    LocationService.resets = 0;
  }

  function test_locationEdit_data() {
    return [
      {
        tag: "trim",
        input: "  Paris  ",
        saved: "Paris",
        resets: 1
      },
      {
        tag: "unchanged",
        input: " Fixture City ",
        saved: "Fixture City",
        resets: 0
      },
      {
        tag: "empty",
        input: "   ",
        saved: "Fixture Default",
        resets: 1
      }
    ];
  }

  function test_locationEdit(data) {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    const input = control(tab, "settings.location.location.search.label");
    compare(input.text, "Fixture City");
    input.inputItem.forceActiveFocus();
    input.inputItem.text = data.input;
    keyClick(Qt.Key_Return);
    compare(Settings.data.location.name, data.saved);
    compare(LocationService.resets, data.resets);
    input.editingFinished();
    compare(LocationService.resets, data.resets);
    tab.destroy();
    wait(0);
    const reopened = createTemporaryObject(tabComponent, testCase);
    compare(control(reopened, "settings.location.location.search.label").text, data.saved);
  }

  function test_selectionSavesImmediately() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    const combo = control(tab, "settings.location.date-time.first-day-of-week.label");
    compare(combo.currentKey, "-1");
    compare(combo.itemCount(), 4);
    combo.activateCurrentIndex(combo.findIndexByKey("6"));
    compare(Settings.data.location.firstDayOfWeek, 6);
    compare(combo.currentKey, "6");
    combo.activateCurrentIndex(combo.findIndexByKey("1"));
    compare(Settings.data.location.firstDayOfWeek, 1);
    tab.destroy();
    wait(0);
    const reopened = createTemporaryObject(tabComponent, testCase);
    compare(control(reopened, "settings.location.date-time.first-day-of-week.label").currentKey, "1");
  }

  function test_cardToggleReorderSave() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    const cards = reorderControl(tab);
    compare(cards.model.length, 4);
    cards.toggleItem(0);
    compare(Settings.data.calendar.cards[0].enabled, true);
    cards.toggleItem(2);
    compare(Settings.data.calendar.cards[2].enabled, true);
    cards.moveItem(2, 1);
    compare(JSON.stringify(Settings.data.calendar.cards), '[{"id":"calendar-header-card","enabled":true},{"id":"timer-card","enabled":true},{"id":"calendar-month-card","enabled":true},{"id":"weather-card","enabled":true}]');
    tab.destroy();
    wait(0);
    const reopened = createTemporaryObject(tabComponent, testCase);
    compare(reorderControl(reopened).model[1].id, "timer-card");
    compare(reorderControl(reopened).model[1].enabled, true);
  }

  function test_weatherUpdatesCardAndAvailability() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    const weather = control(tab, "settings.location.weather.enabled.label");
    weather.toggled(false);
    compare(Settings.data.location.weatherEnabled, false);
    compare(Settings.data.calendar.cards[3].enabled, false);
    compare(reorderControl(tab).model[3].enabled, false);
    compare(reorderControl(tab).disabledIds.join(","), "weather-card");
    compare(control(tab, "settings.location.weather.fahrenheit.label").enabled, false);
    weather.toggled(true);
    compare(Settings.data.calendar.cards[3].enabled, true);
    compare(reorderControl(tab).disabledIds.length, 0);
    compare(control(tab, "settings.location.weather.fahrenheit.label").enabled, true);
    compare(LocationService.resets, 0);
  }

  function test_missingCardsAndDisabledWeatherSavedOnOpen() {
    Settings.data.location.weatherEnabled = false;
    Settings.data.calendar.cards = [
      {
        id: "timer-card",
        enabled: true
      },
      {
        id: "unknown",
        enabled: true
      }
    ];
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    compare(JSON.stringify(Settings.data.calendar.cards), '[{"id":"timer-card","enabled":true},{"id":"calendar-header-card","enabled":true},{"id":"calendar-month-card","enabled":true},{"id":"weather-card","enabled":false}]');
    compare(reorderControl(tab).model.length, 4);
  }
}
