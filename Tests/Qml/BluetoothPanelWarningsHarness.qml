import QtQuick
import QtTest
import Quickshell.Bluetooth
import qs.Commons
import qs.Services.Networking
import qs.Modules.Panels.Bluetooth

TestCase {
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
    verify(first.content !== null && second.content !== null);
  }

  function cleanup() {
    first.close();
    second.close();
  }

  function column(panel) {
    return panel.content.children[0];
  }
  function header(panel) {
    return column(panel).children[0].children[0];
  }
  function toggle(panel) {
    return header(panel).children[2];
  }
  function refresh(panel) {
    return header(panel).children[3];
  }
  function closeButton(panel) {
    return header(panel).children[4];
  }
  function disabledBox(panel) {
    return column(panel).children[1];
  }
  function scroll(panel) {
    return column(panel).children[2];
  }
  function lists(panel) {
    return scroll(panel).contentItem.contentItem.children[0];
  }

  function test_absent_disabled_enabled_and_action_routing() {
    verify(disabledBox(first).visible);
    verify(!scroll(first).visible);
    verify(!toggle(first).checked);
    verify(!refresh(first).enabled);
    toggle(first).toggled(true);
    compare(BluetoothService.requests, [true]);
    BluetoothService.adapter = adapter;
    verify(disabledBox(first).visible);
    adapter.enabled = true;
    verify(!disabledBox(first).visible);
    verify(scroll(first).visible);
    verify(toggle(first).checked);
    verify(refresh(first).enabled);
    compare(refresh(first).icon, "refresh");
    refresh(first).clicked();
    verify(adapter.discovering);
    compare(refresh(first).icon, "stop");
    refresh(first).clicked();
    verify(!adapter.discovering);
    BluetoothService.adapter = replacement;
    refresh(second).clicked();
    verify(replacement.discovering);
    verify(!adapter.discovering);
    toggle(second).toggled(false);
    compare(BluetoothService.requests, [true, false]);
    BluetoothService.adapter = null;
    refresh(first).clicked();
    verify(!adapter.discovering);
  }

  function assertCategory(list, devices) {
    compare(list.model, devices);
    compare(list.visible, devices.length > 0);
  }

  function test_device_categories_follow_model_replacement() {
    BluetoothService.adapter = adapter;
    adapter.enabled = true;
    Bluetooth.devices.values = [phone, trusted, blocked, headphones, keyboard, speaker, null];
    const categories = lists(first).children;
    assertCategory(categories[0], [headphones]);
    assertCategory(categories[1], [keyboard, trusted]);
    assertCategory(categories[2], [speaker, phone]);
    Bluetooth.devices.values = [trusted, phone];
    assertCategory(categories[0], []);
    assertCategory(categories[1], [trusted]);
    assertCategory(categories[2], [phone]);
    BluetoothService.adapter = null;
    for (let i = 0; i < 3; ++i)
      assertCategory(categories[i], []);
    BluetoothService.adapter = replacement;
    assertCategory(categories[2], [phone]);
    Bluetooth.devices.values = [];
    for (let i = 0; i < 3; ++i)
      assertCategory(categories[i], []);
  }

  function test_scanning_empty_signal_and_blocked_devices() {
    BluetoothService.adapter = adapter;
    adapter.enabled = true;
    const scanning = lists(first).children[3];
    verify(!scanning.visible);
    adapter.discovering = true;
    verify(scanning.visible);
    Bluetooth.devices.values = [headphones, blocked];
    verify(scanning.visible);
    Bluetooth.devices.values = [phone];
    verify(!scanning.visible);
    phone.signalStrength = 0;
    verify(scanning.visible);
    adapter.discovering = false;
    verify(!scanning.visible);
    adapter.discovering = true;
    BluetoothService.adapter = null;
    verify(!scanning.visible);
  }

  function test_content_height_and_close_keep_each_owner_after_reload() {
    compare(first.content.contentPreferredHeight, 280);
    compare(second.content.contentPreferredHeight, 180);
    first.preferredHeight = 220;
    compare(first.content.contentPreferredHeight, 220);
    compare(second.content.contentPreferredHeight, 180);
    BluetoothService.adapter = adapter;
    adapter.enabled = true;
    Bluetooth.devices.values = [phone];
    compare(first.content.contentPreferredHeight, Math.min(first.preferredHeight, first.content.calculatedHeight));
    compare(second.content.contentPreferredHeight, Math.min(second.preferredHeight, second.content.calculatedHeight));
    const firstCloses = first.closes;
    const secondCloses = second.closes;
    closeButton(first).clicked();
    verify(!first.isPanelOpen);
    verify(first.content === null);
    verify(second.isPanelOpen);
    compare(first.closes, firstCloses + 1);
    compare(second.closes, secondCloses);
    first.open();
    verify(first.content !== null);
    first.preferredHeight = 120;
    compare(first.content.contentPreferredHeight, Math.min(120, first.content.calculatedHeight));
    closeButton(second).clicked();
    verify(first.isPanelOpen);
    verify(!second.isPanelOpen);
    compare(second.closes, secondCloses + 1);
    closeButton(first).clicked();
    compare(first.closes, firstCloses + 2);
  }
}
