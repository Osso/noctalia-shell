import QtQuick
import QtQuick.Controls
import QtTest
import qs.Widgets

Item {
  id: scene
  width: 900
  height: 700

  Component {
    id: comboFactory
    NComboBox {}
  }
  Component {
    id: searchFactory
    NSearchableComboBox {}
  }
  Component {
    id: reorderFactory
    NReorderCheckboxes {}
  }
  Component {
    id: modelFactory
    ListModel {}
  }

  TestCase {
    id: tests
    name: "SharedUiWidgets"
    when: windowShown
    SignalSpy {
      id: selection
      signalName: "selected"
    }
    SignalSpy {
      id: toggled
      signalName: "itemToggled"
    }
    SignalSpy {
      id: reordered
      signalName: "itemsReordered"
    }
    SignalSpy {
      id: dragStarted
      signalName: "dragPotentialStarted"
    }
    SignalSpy {
      id: dragEnded
      signalName: "dragPotentialEnded"
    }

    function create(factory, props) {
      const widget = createTemporaryObject(factory, scene, props || {});
      verify(widget !== null);
      wait(30);
      return widget;
    }

    function control(widget) {
      for (let i = 0; i < widget.children.length; i++) {
        if (widget.children[i] instanceof ComboBox)
          return widget.children[i];
      }
      fail("missing production ComboBox");
    }

    function descendants(item, predicate) {
      let found = [];
      if (predicate(item))
        found.push(item);
      if (item.children) {
        for (let i = 0; i < item.children.length; i++)
          found = found.concat(descendants(item.children[i], predicate));
      }
      return found;
    }

    function sourceModel(badges) {
      const model = create(modelFactory);
      model.append({
        key: "alpha",
        name: "Alpha",
        badgeLocations: badges ? "LC" : ""
      });
      model.append({
        key: "beta",
        name: "Beta",
        badgeLocations: ""
      });
      model.append({
        key: "gamma",
        name: "Gamma",
        badgeLocations: ""
      });
      return model;
    }

    function open(combo) {
      combo.popup.open();
      tryCompare(combo.popup, "opened", true);
      wait(30);
    }

    function test_combo_model_keyboard_popup() {
      const model = sourceModel(false);
      const widget = create(comboFactory, {
        width: 600,
        label: "Options",
        model: model,
        currentKey: "alpha",
        placeholder: "Choose"
      });
      const combo = control(widget);
      selection.target = widget;
      selection.clear();
      compare(combo.count, 3);
      compare(combo.currentIndex, 0);
      compare(combo.contentItem.text, "Alpha");
      combo.forceActiveFocus();
      verify(combo.activeFocus);
      verify(combo.background.border.color !== combo.background.color);
      keyClick(Qt.Key_Down);
      compare(selection.count, 1);
      compare(selection.signalArguments[0][0], "beta");
      compare(combo.contentItem.text, "Beta");
      open(combo);
      const list = combo.popup.contentItem;
      tryCompare(list, "count", 3);
      list.forceLayout();
      const item = list.itemAtIndex(2);
      verify(item !== null);
      mouseClick(item, item.width / 2, item.height / 2);
      tryCompare(combo.popup, "visible", false);
      compare(selection.signalArguments[selection.count - 1][0], "gamma");
      open(combo);
      tryCompare(list, "count", 3);
      combo.popup.close();
      tryCompare(list, "count", 0);
      model.clear();
      tryCompare(combo, "count", 0);
      widget.currentKey = "missing";
      compare(combo.currentIndex, -1);
      compare(combo.contentItem.text, "Choose");
      const before = selection.count;
      widget.activateCurrentIndex(-1);
      widget.activateCurrentIndex(99);
      compare(selection.count, before);
      widget.model = [
        {
          key: "delta",
          name: "Delta"
        }
      ];
      widget.currentKey = "delta";
      tryCompare(combo, "count", 1);
      compare(combo.contentItem.text, "Delta");
      widget.model = null;
      tryCompare(combo, "count", 0);
      compare(widget.itemCount(), 0);
      compare(widget.getItem(0), null);
      widget.model = {
        length: 4
      };
      compare(widget.itemCount(), 0);
      widget.model = [];
      open(combo);
      compare(list.count, 0);
      combo.popup.close();
    }

    function test_combo_click_during_real_flick() {
      const model = create(modelFactory);
      for (let i = 0; i < 40; i++)
        model.append({
          key: "item-" + i,
          name: "Option " + i
        });
      const widget = create(comboFactory, {
        width: 600,
        label: "Many options",
        model: model
      });
      const combo = control(widget);
      selection.target = widget;
      selection.clear();
      open(combo);
      const list = combo.popup.contentItem;
      list.forceLayout();
      const item = list.itemAtIndex(0);
      verify(item !== null);
      list.flick(0, -800);
      verify(list.flicking || list.moving);
      // Deliver the delegate click at the moving-list boundary, before cancelFlick.
      item.clicked();
      compare(item.pendingClick, true);
      compare(selection.count, 0);
      tryCompare(selection, "count", 1);
      compare(selection.signalArguments[0][0], "item-0");
      tryCompare(combo.popup, "visible", false);
      wait(100);
      compare(selection.count, 1);
    }

    function test_search_filter_keyboard_close_reopen_badges() {
      const model = sourceModel(true);
      const widget = create(searchFactory, {
        width: 600,
        label: "Search options",
        model: model,
        currentKey: "alpha",
        placeholder: "Choose"
      });
      const combo = control(widget);
      selection.target = widget;
      selection.clear();
      compare(widget.filteredModel.count, 3);
      open(combo);
      const inputs = descendants(combo.popup.contentItem, item => item instanceof TextInput);
      compare(inputs.length, 1);
      const input = inputs[0];
      tryCompare(input, "activeFocus", true);
      keyClick(Qt.Key_B, Qt.ShiftModifier);
      keyClick(Qt.Key_E);
      keyClick(Qt.Key_T);
      keyClick(Qt.Key_A);
      tryCompare(widget.filteredModel, "count", 1);
      compare(widget.filteredModel.get(0).key, "beta");
      combo.forceActiveFocus();
      keyClick(Qt.Key_Down);
      keyClick(Qt.Key_Return);
      tryCompare(combo.popup, "visible", false);
      verify(selection.count > 0);
      compare(selection.signalArguments[selection.count - 1][0], "beta");
      widget.searchText = "";
      widget.currentKey = "alpha";
      open(combo);
      const texts = descendants(combo.popup.contentItem, item => item instanceof Text);
      verify(texts.some(item => item.text === "L"));
      verify(texts.some(item => item.text === "C"));
      const delegates = descendants(combo.popup.contentItem, item => item instanceof ItemDelegate);
      const gamma = delegates.filter(item => item.name === "Gamma")[0];
      verify(gamma !== undefined);
      mouseClick(gamma, gamma.width / 2, gamma.height / 2);
      tryCompare(combo.popup, "visible", false);
      compare(selection.signalArguments[selection.count - 1][0], "gamma");
      widget.searchText = "zzzz-no-match";
      compare(widget.filteredModel.count, 0);
      const before = selection.count;
      widget.activateCurrentSelection();
      compare(selection.count, before);
      widget.searchText = "";
      model.clear();
      open(combo);
      compare(widget.filteredModel.count, 0);
      combo.popup.close();
      widget.model = sourceModel(false);
      open(combo);
      compare(widget.filteredModel.count, 3);
      combo.popup.close();
      const withoutBadges = create(modelFactory);
      withoutBadges.append({
        key: "delta",
        name: "Delta"
      });
      widget.model = withoutBadges;
      open(combo);
      compare(widget.filteredModel.count, 1);
      const delta = descendants(combo.popup.contentItem, item => item instanceof ItemDelegate)[0];
      verify(delta !== undefined);
      mouseClick(delta, delta.width / 2, delta.height / 2);
      tryCompare(combo.popup, "visible", false);
      compare(selection.signalArguments[selection.count - 1][0], "delta");
      widget.model = null;
      compare(widget.filteredModel.count, 0);
      compare(widget.filteredKeyAt(-1), "");
      compare(widget.filteredKeyAt(99), "");
    }

    function test_reorder_drag_visual_positions_clear_reassign() {
      const entries = [
        {
          id: "a",
          text: "Alpha",
          enabled: true,
          required: false
        },
        {
          id: "b",
          text: "Beta",
          enabled: true,
          required: false
        },
        {
          id: "c",
          text: "Gamma",
          enabled: false,
          required: false
        }
      ];
      const widget = create(reorderFactory, {
        width: 500,
        model: entries
      });
      const list = widget.children[0];
      reordered.target = widget;
      reordered.clear();
      list.forceLayout();
      const first = list.itemAtIndex(0);
      const second = list.itemAtIndex(1);
      const third = list.itemAtIndex(2);
      const stride = first.height + widget.spacing;
      const restingZ = first.z;
      const handle = descendants(first, item => item instanceof MouseArea)[0];
      mousePress(handle, handle.width / 2, handle.height / 2);
      mouseMove(handle, handle.width / 2, handle.height / 2 + 2 * stride, 50);
      compare(first.dragging, true);
      compare(first.dragTargetIndex, 2);
      tryCompare(first, "y", 2 * stride);
      tryCompare(second, "y", 0);
      tryCompare(third, "y", stride);
      compare(first.z, 999);
      compare(widget.model.map(item => item.id).join(","), "a,b,c");
      compare(reordered.count, 0);

      // Destroy the grabbed delegate before release, then populate a fresh list.
      widget.model = [];
      tryCompare(list, "count", 0);
      wait(30);
      mouseRelease(scene, 750, 600, Qt.LeftButton);
      widget.model = entries.slice();
      tryCompare(list, "count", 3);
      list.forceLayout();
      for (let i = 0; i < 3; i++) {
        const restored = list.itemAtIndex(i);
        verify(restored !== null);
        tryCompare(restored, "y", i * stride);
        compare(restored.dragging, false);
        compare(restored.z, restingZ);
      }
      const last = list.itemAtIndex(2);
      const lastHandle = descendants(last, item => item instanceof MouseArea)[0];
      mousePress(lastHandle, lastHandle.width / 2, lastHandle.height / 2);
      mouseMove(lastHandle, lastHandle.width / 2, lastHandle.height / 2 - 2 * stride, 50);
      tryCompare(list.itemAtIndex(0), "y", stride);
      tryCompare(list.itemAtIndex(1), "y", 2 * stride);
      mouseRelease(lastHandle, lastHandle.width / 2, lastHandle.height / 2, Qt.LeftButton);
      tryCompare(reordered, "count", 1);
      compare(reordered.signalArguments[0][0], 2);
      compare(reordered.signalArguments[0][1], 0);
      compare(widget.model.map(item => item.id).join(","), "c,a,b");
      list.forceLayout();
      for (let i = 0; i < 3; i++)
        tryCompare(list.itemAtIndex(i), "y", i * stride);
    }

    function test_reorder_toggle_drag_clear_reassign_guards() {
      const original = [
        {
          id: "a",
          text: "Alpha",
          enabled: true,
          required: false
        },
        {
          id: "b",
          text: "Beta",
          enabled: true,
          required: true
        },
        {
          id: "c",
          text: "Gamma",
          enabled: false,
          required: false
        }
      ];
      const widget = create(reorderFactory, {
        width: 500,
        model: original,
        disabledIds: ["c"]
      });
      const list = widget.children[0];
      toggled.target = widget;
      toggled.clear();
      reordered.target = widget;
      reordered.clear();
      dragStarted.target = widget;
      dragStarted.clear();
      dragEnded.target = widget;
      dragEnded.clear();
      list.forceLayout();
      compare(list.count, 3);
      const first = list.itemAtIndex(0);
      const required = list.itemAtIndex(1);
      const disabled = list.itemAtIndex(2);
      verify(first && required && disabled);
      const areas = descendants(first, item => item instanceof MouseArea);
      compare(areas.length, 2);
      mouseClick(areas[1], areas[1].width / 2, areas[1].height / 2);
      compare(toggled.count, 1);
      compare(toggled.signalArguments[0][0], 0);
      compare(toggled.signalArguments[0][1], false);
      compare(original[0].enabled, true);
      const requiredAreas = descendants(required, item => item instanceof MouseArea);
      compare(requiredAreas[1].enabled, false);
      const disabledAreas = descendants(disabled, item => item instanceof MouseArea);
      compare(disabledAreas[0].enabled, false);
      compare(disabledAreas[1].enabled, false);
      widget.toggleItem(1);
      widget.toggleItem(-1);
      widget.toggleItem(99);
      compare(toggled.count, 1);
      list.forceLayout();
      const handle = descendants(list.itemAtIndex(0), item => item instanceof MouseArea)[0];
      mousePress(handle, handle.width / 2, handle.height / 2);
      compare(dragStarted.count, 1);
      mouseMove(handle, handle.width / 2, handle.height / 2 + 2 * (list.itemAtIndex(0).height + widget.spacing), 50);
      mouseRelease(handle, handle.width / 2, handle.height / 2, Qt.LeftButton);
      tryCompare(reordered, "count", 1);
      compare(reordered.signalArguments[0][0], 0);
      compare(reordered.signalArguments[0][1], 2);
      compare(dragEnded.count, 1);
      compare(widget.model.map(item => item.id).join(","), "b,c,a");
      compare(original.map(item => item.id).join(","), "a,b,c");
      widget.moveItem(-1, 0);
      widget.moveItem(0, 99);
      widget.moveItem(1, 1);
      compare(reordered.count, 1);
      widget.model = [];
      tryCompare(list, "count", 0);
      widget.model = [
        {
          id: "d",
          text: "Delta",
          enabled: true,
          required: false
        }
      ];
      tryCompare(list, "count", 1);
      list.forceLayout();
      compare(list.itemAtIndex(0).text, "Delta");
      compare(list.itemAtIndex(0).itemEnabled, true);
    }
  }
}
