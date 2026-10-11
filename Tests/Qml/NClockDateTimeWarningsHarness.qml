import QtQuick
import QtTest
import qs.Commons
import qs.Widgets

TestCase {
  id: suite
  name: "NClockDateTime"
  width: 1000
  height: 1400
  when: windowShown
  visible: true

  Component {
    id: clockComponent
    NClock {}
  }
  Component {
    id: tokensComponent
    NDateTimeTokens {}
  }
  SignalSpy {
    id: tokenSpy
    signalName: "tokenClicked"
  }

  function descendants(item) {
    let result = [item];
    for (const child of item.children || [])
      result = result.concat(descendants(child));
    return result;
  }

  function canvas(clock) {
    return descendants(clock).find(child => typeof child.requestPaint === "function");
  }

  function labels(clock) {
    return descendants(clock).filter(child => child.text !== undefined).map(child => child.text);
  }

  function createClock(style) {
    const clock = createTemporaryObject(clockComponent, suite, {
      "clockStyle": style,
      "width": 120,
      "height": 120,
      "now": new Date(2023, 11, 25, 14, 30, 0),
      "clockColor": "#ffffff",
      "secondHandColor": "#ff0000",
      "progressColor": "#ff0000"
    });
    verify(clock !== null);
    wait(80);
    return clock;
  }

  function init() {
    compare(Time.consumers, 0);
    Time.now = new Date(2023, 11, 25, 14, 30, 0);
    I18n.locale = Qt.locale("en_US");
    Settings.data = Object.assign({}, Settings.data, {
      location: {
        use12hourFormat: false
      }
    });
  }

  function test_analogInjectedDatePaint() {
    const clock = createClock("analog");
    const before = grabImage(canvas(clock));
    compare(before.red(60, 15), 255, "initial second hand points up");
    clock.now = new Date(2023, 11, 25, 14, 30, 15);
    wait(80);
    const after = grabImage(canvas(clock));
    verify(!after.equals(before), "changing supplied date repaints analog hands");
    compare(after.red(100, 60), 255, "15-second hand points right");
    verify(after.green(100, 60) < 64, "red hand with antialiased edge");
  }

  function test_digitalInjectedDateProgress() {
    const clock = createClock("digital");
    compare(labels(clock), ["14", "30"]);
    Time.now = new Date(2023, 11, 25, 14, 30, 1);
    wait(80);
    const before = grabImage(canvas(clock));
    clock.now = new Date(2023, 11, 26, 0, 5, 30, 500);
    wait(80);
    compare(labels(clock), ["00", "05"]);
    const after = grabImage(canvas(clock));
    verify(!after.equals(before), "injected date updates seconds arc without Time signal");
    compare(after.red(117, 60), 255);
    compare(after.green(117, 60), 0);
  }

  function test_clockModeLocaleAndLifecycle() {
    const clock = createClock("digital");
    compare(Time.consumers, 1);
    clock.refreshSecondUpdateRegistration();
    compare(Time.consumers, 1);
    Settings.data = Object.assign({}, Settings.data, {
      location: {
        use12hourFormat: true
      }
    });
    tryVerify(() => labels(clock)[0] === "02");
    I18n.locale = Qt.locale("fr_FR");
    compare(labels(clock), ["02", "30"]);
    clock.hoursFontSize = 18;
    clock.minutesFontSize = 13;
    clock.clockColor = "#00ff00";
    const texts = descendants(clock).filter(child => child.text !== undefined);
    compare(texts[0].pointSize, 18);
    compare(texts[1].pointSize, 13);
    compare(texts[0].color, "#00ff00");
    clock.clockStyle = "analog";
    wait(80);
    verify(canvas(clock) !== undefined);
    clock.clockStyle = "digital";
    wait(80);
    compare(labels(clock), ["02", "30"]);
    compare(Time.consumers, 1);
    clock.visible = false;
    compare(Time.consumers, 0);
    clock.visible = true;
    compare(Time.consumers, 1);
    clock.destroy();
    wait(0);
    compare(Time.consumers, 0);
    const replacement = createClock("analog");
    compare(Time.consumers, 1);
    replacement.destroy();
    wait(0);
    compare(Time.consumers, 0);
  }

  function test_sharedTimeMidnightUpdates() {
    const analog = createTemporaryObject(clockComponent, suite, {
      "width": 120,
      "height": 120
    });
    const digital = createTemporaryObject(clockComponent, suite, {
      "clockStyle": "digital",
      "x": 140,
      "width": 120,
      "height": 120
    });
    verify(analog !== null && digital !== null);
    wait(80);
    compare(Time.consumers, 2);
    compare(labels(digital), ["14", "30"]);
    const before = grabImage(canvas(analog));
    Time.now = new Date(2023, 11, 26, 0, 0, 15);
    wait(80);
    compare(labels(digital), ["00", "00"]);
    verify(!grabImage(canvas(analog)).equals(before), "shared clock signal repaints analog");
    Settings.data = Object.assign({}, Settings.data, {
      location: {
        use12hourFormat: true
      }
    });
    tryVerify(() => labels(digital)[0] === "12");
  }

  function tokenList(tokens) {
    return descendants(tokens).find(child => typeof child.itemAtIndex === "function");
  }

  function test_tokensLocaleClickAndRebuild() {
    const tokens = createTemporaryObject(tokensComponent, suite, {
      "width": 900,
      "height": 1300,
      "sampleDate": new Date(2023, 11, 25, 14, 30, 45)
    });
    verify(tokens !== null);
    tokenSpy.target = tokens;
    tokenSpy.clear();
    const list = tokenList(tokens);
    list.forceLayout();
    wait(80);
    compare(list.count, 27);
    for (let index = 0; index < list.count; index++) {
      const delegate = list.itemAtIndex(index);
      verify(delegate !== null);
      const texts = descendants(delegate).filter(child => child.text !== undefined);
      verify(texts.some(child => child.text === I18n.locale.toString(tokens.sampleDate, delegate.token)), delegate.token);
    }
    const row = list.itemAtIndex(4);
    mouseClick(row, 200, row.height / 2);
    compare(tokenSpy.count, 1);
    compare(tokenSpy.signalArguments[0][0], "yyyy-MM-dd");
    I18n.locale = Qt.locale("fr_FR");
    tokens.sampleDate = new Date(2024, 0, 1, 0, 5, 6);
    wait(80);
    verify(labels(list.itemAtIndex(26)).includes("lundi"));
    list.model = [
      {
        "category": "Day",
        "token": "dddd",
        "description": "Weekday"
      }
    ];
    list.forceLayout();
    wait(80);
    compare(list.count, 1);
    const rebuilt = list.itemAtIndex(0);
    compare(labels(rebuilt), ["Day", "dddd", "Weekday", "lundi"]);
    compare(rebuilt.width, list.width);
    mouseClick(rebuilt, 200, rebuilt.height / 2);
    compare(tokenSpy.count, 2);
    compare(tokenSpy.signalArguments[1][0], "dddd");
    wait(350);
    tokens.destroy();
    wait(0);
    const replacement = createTemporaryObject(tokensComponent, suite, {
      "width": 900,
      "height": 1300
    });
    verify(replacement !== null);
    tokenList(replacement).forceLayout();
    wait(80);
    compare(tokenList(replacement).count, 27);
  }
}
