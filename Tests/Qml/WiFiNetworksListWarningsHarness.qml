import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.Networking
import qs.Modules.Panels.WiFi

ShellRoot {
  id: harness

  property int scenario: 0
  property int phase: 0
  property var snapshots: []
  property var signals: []
  readonly property var networks: [
    {
      ssid: "Home",
      signal: 90,
      connected: true,
      security: "WPA2",
      existing: true,
      cached: true
    },
    {
      ssid: "Saved",
      signal: 65,
      connected: false,
      security: "WPA2",
      existing: true,
      cached: true
    },
    {
      ssid: "Cafe",
      signal: 40,
      connected: false,
      security: "Open",
      existing: false,
      cached: false
    },
    {
      ssid: "Secure",
      signal: 20,
      connected: false,
      security: "WPA2",
      existing: false,
      cached: false
    }
  ]

  // QT_QPA_PLATFORM=offscreen: polish real layouts without a desktop surface.
  Window {
    width: harness.scenario % 2 === 0 ? 900 : 430
    height: 1000
    visible: true

    RowLayout {
      id: host
      width: parent.width
      height: list.Layout.preferredHeight

      WiFiNetworksList {
        id: list
        label: "Networks"
        model: harness.networks
        onPasswordRequested: ssid => {
          harness.signals.push({
            action: "password",
            ssid: ssid
          });
          list.passwordSsid = ssid;
        }
        onPasswordSubmitted: (ssid, password) => {
          harness.signals.push({
            action: "submit",
            ssid: ssid,
            password: password
          });
          list.passwordSsid = "";
        }
        onPasswordCancelled: {
          harness.signals.push({
            action: "cancel-password"
          });
          list.passwordSsid = "";
        }
        onForgetRequested: ssid => {
          harness.signals.push({
            action: "forget-request",
            ssid: ssid
          });
          list.expandedSsid = ssid;
        }
        onForgetConfirmed: ssid => {
          harness.signals.push({
            action: "forget-confirm",
            ssid: ssid
          });
          list.expandedSsid = "";
        }
        onForgetCancelled: {
          harness.signals.push({
            action: "cancel-forget"
          });
          list.expandedSsid = "";
        }
      }
    }
  }

  function require(condition, message) {
    if (!condition)
      throw new Error(message);
  }

  function descendants(item) {
    let found = [];
    for (const child of item.children || [])
      found = found.concat([child], descendants(child));
    return found;
  }

  function rows() {
    const repeater = descendants(list).find(item => typeof item.itemAt === "function");
    require(repeater.count === 4, "four concrete delegates required");
    return [0, 1, 2, 3].map(index => repeater.itemAt(index));
  }

  function button(row, key) {
    const found = descendants(row).find(item => item.visible && typeof item.clicked === "function" && item.text === I18n.tr(key));
    require(found !== undefined, "missing visible action " + key);
    return found;
  }

  function clickIcon(row, icon) {
    const found = descendants(row).find(item => item.visible && item.icon === icon && typeof item.clicked === "function");
    require(found !== undefined, "missing icon action " + icon);
    found.clicked();
  }

  function closeEnough(actual, expected, label) {
    require(Math.abs(actual - expected) < 0.01, label + ": " + actual + " != " + expected);
  }

  function rounded(value) {
    return Math.round(value * 1000) / 1000;
  }

  function geometry(state) {
    const record = {
      state: state,
      width: list.width,
      height: list.height,
      rows: []
    };
    for (const row of rows()) {
      closeEnough(row.width, list.width - Style.marginM * 2 - Style.marginXS * 2, "layout-owned row width");
      require(row.height > 0 && row.children[0].width > 0, "production list must be laid out");
      const texts = descendants(row).filter(item => item.visible && typeof item.text === "string" && typeof item.clicked !== "function");
      const badges = texts.filter(item => item.parent.color !== undefined && ["connected", "disconnecting", "forgetting", "saved"].some(key => item.text === I18n.tr("wifi.panel." + key)));
      for (const text of badges) {
        closeEnough(text.parent.width, text.implicitWidth + Style.marginS * 2, "badge width");
        closeEnough(text.parent.height, text.implicitHeight + Style.marginXXS * 2, "badge height");
        closeEnough(text.x, (text.parent.width - text.width) / 2, "centered badge x");
        closeEnough(text.y, (text.parent.height - text.height) / 2, "centered badge y");
      }
      record.rows.push({
        ssid: row.networkSsid,
        bounds: [row.x, row.y, row.width, row.height].map(rounded),
        texts: texts.map(item => ({
              text: item.text,
              bounds: [item.x, item.y, item.width, item.height].map(rounded)
            })),
        badges: badges.map(item => ({
              text: item.text,
              size: [item.parent.width, item.parent.height].map(rounded)
            }))
      });
    }
    snapshots.push(record);
  }

  function assertActions() {
    const delegates = rows();
    require(delegates.map(row => row.networkSsid).join(",") === "Home,Saved,Cafe,Secure", "model order/roles changed");
    require(delegates.map(row => row.networkSignal).join(",") === "90,65,40,20", "signal roles changed");
    button(delegates[0], "wifi.panel.disconnect").clicked();
    button(delegates[1], "wifi.panel.connect").clicked();
    button(delegates[2], "wifi.panel.connect").clicked();
    require(JSON.stringify(NetworkService.requests) === JSON.stringify([
      {
        action: "disconnect",
        ssid: "Home"
      },
      {
        action: "connect",
        ssid: "Saved"
      },
      {
        action: "connect",
        ssid: "Cafe"
      }
    ]), "direct actions must use each delegate SSID");
    button(delegates[3], "wifi.panel.password").clicked();
    require(signals[0].ssid === "Secure" && list.passwordSsid === "Secure", "secured network must request password");
  }

  function assertPassword() {
    const row = rows()[3];
    const editor = descendants(row).find(item => typeof item.echoMode !== "undefined");
    require(editor !== undefined && editor.echoMode === TextInput.Password, "protected password input required");
    const submit = button(row, "wifi.panel.connect");
    require(!submit.enabled, "empty password must disable submit");
    editor.text = "s3cret";
    require(submit.enabled, "nonempty password enables submit");
    NetworkService.connecting = true;
    require(!submit.enabled, "overlapping connection disables submit");
    editor.accepted();
    require(editor.text === "s3cret", "busy Enter must not submit");
    NetworkService.connecting = false;
    editor.accepted();
    require(editor.text === "" && list.passwordSsid === "", "Enter clears credentials");
    require(signals[1].ssid === "Secure" && signals[1].password === "s3cret", "password signal role binding");
    list.passwordSsid = "Secure";
    editor.text = "cancel-me";
    clickIcon(row, "close");
    require(editor.text === "" && signals[2].action === "cancel-password", "cancel clears credentials");
    list.passwordSsid = "Secure";
    editor.text = "button-secret";
    submit.clicked();
    require(editor.text === "" && signals[3].password === "button-secret", "button submission clears credentials");
    list.passwordSsid = "Secure";
    editor.text = "hidden-secret";
    list.passwordSsid = "";
    require(editor.text === "", "hiding editor clears credentials");
    clickIcon(rows()[1], "trash");
  }

  function assertDetails(ssid) {
    const row = rows().find(item => item.networkSsid === ssid);
    const details = row.children[0].children.filter(item => item.visible && item.children.length === 1);
    require(details.length === 1, "one expanded detail expected");
    const detail = details[0];
    closeEnough(detail.height, detail.children[0].implicitHeight + Style.marginS * 2, "text-sized detail height");
  }

  function advance() {
    switch (phase) {
    case 0:
      I18n.translated = scenario >= 2;
      snapshots = [];
      signals = [];
      NetworkService.requests = [];
      list.model = [];
      list.model = networks;
      break;
    case 1:
      geometry("connected-disconnected");
      assertActions();
      break;
    case 2:
      geometry("password");
      assertDetails("Secure");
      assertPassword();
      break;
    case 3:
      geometry("forget-confirmation");
      assertDetails("Saved");
      button(rows()[1], "wifi.panel.forget").clicked();
      require(signals[5].action === "forget-confirm" && signals[5].ssid === "Saved", "forget confirmed target");
      clickIcon(rows()[1], "trash");
      clickIcon(rows()[1], "close");
      require(signals[7].action === "cancel-forget" && list.expandedSsid === "", "forget cancellation");
      NetworkService.connectingTo = "Cafe";
      NetworkService.connecting = true;
      break;
    case 4:
      geometry("connecting");
      require(rows()[2].networkBusy, "connecting target busy");
      require(!button(rows()[1], "wifi.panel.connect").enabled, "other connects disabled");
      NetworkService.connectingTo = "";
      NetworkService.connecting = false;
      NetworkService.disconnectingFrom = "Home";
      break;
    case 5:
      geometry("disconnecting");
      require(rows()[0].networkBusy && rows()[0].opacity === 0.6, "disconnect busy opacity");
      NetworkService.disconnectingFrom = "";
      NetworkService.forgettingNetwork = "Saved";
      break;
    case 6:
      geometry("forgetting");
      require(rows()[1].networkBusy && rows()[1].opacity === 0.6, "forget busy opacity");
      NetworkService.forgettingNetwork = "";
      list.model = networks.map(network => Object.assign({}, network, {
          connected: false
        }));
      break;
    case 7:
      geometry("disconnected");
      require(!rows()[0].networkConnected, "model replacement must update delegates");
      button(rows()[0], "wifi.panel.connect").clicked();
      list.model = [networks[3], networks[1], networks[0], networks[2]];
      break;
    case 8:
      require(rows().map(row => row.networkSsid).join(",") === "Secure,Saved,Home,Cafe", "caller sorting order must remain intact");
      console.log("WIFI_SNAPSHOT " + JSON.stringify({
        width: host.width,
        translated: I18n.translated,
        states: snapshots
      }));
      list.model = networks;
      scenario++;
      phase = -1;
      if (scenario === 4) {
        console.log("WIFI_LIST_BEHAVIOR_PASS");
        Qt.quit();
      }
      break;
    }
    phase++;
  }

  Timer {
    interval: 40
    repeat: true
    running: true
    onTriggered: {
      try {
        harness.advance();
      } catch (error) {
        console.error("WIFI_LIST_FAIL scenario=" + harness.scenario + " phase=" + harness.phase + ": " + error.message);
        Qt.exit(1);
      }
    }
  }
}
