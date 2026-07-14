import QtQuick
import QtTest

TestCase {
  id: testCase
  name: "PanelServiceLifecycle"
  when: windowShown

  readonly property string initialPanelKey: "launcherPanel-eDP-1"
  readonly property string changedPanelKey: "launcherPanel-unknown"
  property var registeredPanels: ({})
  property bool panelDestroyed: false

  function registerPanel(panelKey, panel) {
    registeredPanels[panelKey] = panel;
  }

  function unregisterPanel(panelKey, panel) {
    if (registeredPanels[panelKey] === panel) {
      delete registeredPanels[panelKey];
    }
  }

  Component {
    id: panelFactory

    Item {
      id: panel
      property string registrationKey: ""

      Component.onCompleted: {
        registrationKey = objectName;
        testCase.registerPanel(registrationKey, panel);
      }

      Component.onDestruction: {
        testCase.panelDestroyed = true;
        testCase.unregisterPanel(registrationKey, panel);
      }
    }
  }

  function init() {
    registeredPanels = ({});
    panelDestroyed = false;
  }

  function test_captured_key_removes_panel_after_object_name_changes() {
    const panel = panelFactory.createObject(testCase, {
                                             "objectName": initialPanelKey
                                           });
    compare(registeredPanels[initialPanelKey], panel);

    panel.objectName = changedPanelKey;
    panel.destroy();

    tryVerify(() => panelDestroyed);
    verify(registeredPanels[initialPanelKey] === undefined);
    verify(registeredPanels[changedPanelKey] === undefined);
  }
}
