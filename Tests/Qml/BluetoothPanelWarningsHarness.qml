import QtQuick
import QtTest
import Quickshell.Bluetooth
import qs.Services.Networking
import qs.Modules.Panels.Bluetooth

TestCase {
  id: suite
  name: "BluetoothPanel"
  visible: true
  BluetoothAdapter {
    id: adapter
  }
  BluetoothAdapter {
    id: replacement
  }
  BluetoothDevice {
    id: headphones
    name: "Studio Headphones"
    paired: true
    connected: true
  }
  BluetoothDevice {
    id: keyboard
    name: "Desk Keyboard"
    paired: true
  }
  BluetoothDevice {
    id: trusted
    name: "Trusted Mouse"
    trusted: true
  }
  BluetoothDevice {
    id: phone
    name: "Pocket Phone"
  }
  BluetoothDevice {
    id: speaker
    name: "Available Speaker"
  }
  BluetoothDevice {
    id: blocked
    name: "Blocked"
    blocked: true
  }
  BluetoothPanel {
    id: first
    width: 400
    height: 500
  }
  BluetoothPanel {
    id: second
    width: 400
    height: 500
  }

  function init() {
    adapter.enabled = false;
    adapter.discovering = false;
    replacement.enabled = true;
    replacement.discovering = false;
    BluetoothService.adapter = null;
    BluetoothService.requests = [];
    Bluetooth.devices.values = [];
    phone.signalStrength = 80;
    first.preferredHeight = 500;
    second.preferredHeight = 180;
    first.open();
    second.open();
    suite.verify(first.content !== null && second.content !== null);
  }

  function cleanup() {
    first.close();
    second.close();
  }

  function column(panel) {
    return panel.content.children[0];
  }
  function header(panel) {
    return suite.column(panel).children[0].children[0];
  }
  function toggle(panel) {
    return suite.header(panel).children[2];
  }
  function refresh(panel) {
    return suite.header(panel).children[3];
  }
  function closeButton(panel) {
    return suite.header(panel).children[4];
  }
  function disabledBox(panel) {
    return suite.column(panel).children[1];
  }
  function scroll(panel) {
    return suite.column(panel).children[2];
  }
  function lists(panel) {
    return suite.scroll(panel).contentItem.contentItem.children[0];
  }

  function test_absent_disabled_enabled_and_action_routing() {
    suite.verify(suite.disabledBox(first).visible);
    suite.verify(!suite.scroll(first).visible);
    suite.verify(!suite.toggle(first).checked);
    suite.verify(!suite.refresh(first).enabled);
    suite.toggle(first).toggled(true);
    suite.compare(BluetoothService.requests, [true]);
    BluetoothService.adapter = adapter;
    suite.verify(suite.disabledBox(first).visible);
    adapter.enabled = true;
    suite.verify(!suite.disabledBox(first).visible);
    suite.verify(suite.scroll(first).visible);
    suite.verify(suite.toggle(first).checked);
    suite.verify(suite.refresh(first).enabled);
    suite.compare(suite.refresh(first).icon, "refresh");
    suite.refresh(first).clicked();
    suite.verify(adapter.discovering);
    suite.compare(suite.refresh(first).icon, "stop");
    suite.refresh(first).clicked();
    suite.verify(!adapter.discovering);
    BluetoothService.adapter = replacement;
    suite.refresh(second).clicked();
    suite.verify(replacement.discovering);
    suite.verify(!adapter.discovering);
    suite.toggle(second).toggled(false);
    suite.compare(BluetoothService.requests, [true, false]);
    BluetoothService.adapter = null;
    suite.refresh(first).clicked();
    suite.verify(!adapter.discovering);
  }

  function assertCategory(list, devices) {
    suite.compare(list.model, devices);
    suite.compare(list.visible, devices.length > 0);
  }

  function test_device_categories_follow_model_replacement() {
    BluetoothService.adapter = adapter;
    adapter.enabled = true;
    Bluetooth.devices.values = [phone, trusted, blocked, headphones, keyboard, speaker, null];
    const categories = suite.lists(first).children;
    suite.assertCategory(categories[0], [headphones]);
    suite.assertCategory(categories[1], [keyboard, trusted]);
    suite.assertCategory(categories[2], [speaker, phone]);
    Bluetooth.devices.values = [trusted, phone];
    suite.assertCategory(categories[0], []);
    suite.assertCategory(categories[1], [trusted]);
    suite.assertCategory(categories[2], [phone]);
    BluetoothService.adapter = null;
    for (let i = 0; i < 3; ++i)
      suite.assertCategory(categories[i], []);
    BluetoothService.adapter = replacement;
    suite.assertCategory(categories[2], [phone]);
    Bluetooth.devices.values = [];
    for (let i = 0; i < 3; ++i)
      suite.assertCategory(categories[i], []);
  }

  function test_scanning_empty_signal_and_blocked_devices() {
    BluetoothService.adapter = adapter;
    adapter.enabled = true;
    const scanning = suite.lists(first).children[3];
    suite.verify(!scanning.visible);
    adapter.discovering = true;
    suite.verify(scanning.visible);
    Bluetooth.devices.values = [headphones, blocked];
    suite.verify(scanning.visible);
    Bluetooth.devices.values = [phone];
    suite.verify(!scanning.visible);
    phone.signalStrength = 0;
    suite.verify(scanning.visible);
    adapter.discovering = false;
    suite.verify(!scanning.visible);
    adapter.discovering = true;
    BluetoothService.adapter = null;
    suite.verify(!scanning.visible);
  }

  function test_content_height_and_close_keep_each_owner_after_reload() {
    suite.compare(first.content.contentPreferredHeight, 280);
    suite.compare(second.content.contentPreferredHeight, 180);
    first.preferredHeight = 220;
    suite.compare(first.content.contentPreferredHeight, 220);
    suite.compare(second.content.contentPreferredHeight, 180);
    BluetoothService.adapter = adapter;
    adapter.enabled = true;
    Bluetooth.devices.values = [phone];
    suite.compare(first.content.contentPreferredHeight, Math.min(first.preferredHeight, first.content.calculatedHeight));
    suite.compare(second.content.contentPreferredHeight, Math.min(second.preferredHeight, second.content.calculatedHeight));
    const firstCloses = first.closes;
    const secondCloses = second.closes;
    suite.closeButton(first).clicked();
    suite.verify(!first.isPanelOpen);
    suite.verify(first.content === null);
    suite.verify(second.isPanelOpen);
    suite.compare(first.closes, firstCloses + 1);
    suite.compare(second.closes, secondCloses);
    first.open();
    suite.verify(first.content !== null);
    first.preferredHeight = 120;
    suite.compare(first.content.contentPreferredHeight, Math.min(120, first.content.calculatedHeight));
    suite.closeButton(second).clicked();
    suite.verify(first.isPanelOpen);
    suite.verify(!second.isPanelOpen);
    suite.compare(second.closes, secondCloses + 1);
    suite.closeButton(first).clicked();
    suite.compare(first.closes, firstCloses + 2);
  }
}
