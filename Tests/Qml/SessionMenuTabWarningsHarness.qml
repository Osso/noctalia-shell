import QtQuick
import QtTest
import qs.Commons
import qs.Tabs

TestCase {
    id: testCase
    name: "SessionMenuTabWarnings"
    width: 1800
    height: 1400
    visible: true
    when: windowShown

    Component {
        id: tabFactory
        SessionMenuTab {
            width: 800
        }
    }

    function descendants(item) {
        let items = [item];
        for (const child of item.children || [])
            items = items.concat(descendants(child));
        return items;
    }

    function control(tab, label) {
        const matches = descendants(tab).filter(item => item.label === label && (item.toggled !== undefined || item.selected !== undefined));
        compare(matches.length, 1, label);
        return matches[0];
    }

    function entryList(tab) {
        const matches = descendants(tab).filter(item => item.itemAtIndex !== undefined);
        compare(matches.length, 1);
        compare(matches[0].count, 6);
        return matches[0];
    }

    function newTab(x) {
        const tab = createTemporaryObject(tabFactory, testCase, {
            x: x || 0
        });
        verify(tab !== null);
        wait(30);
        verify(tab.implicitHeight > 0);
        compare(tab.entriesModel.length, 6);
        // Startup mutates an array without notifying ListView (pre-existing, out of scope).
        // Exercise the production edit/save boundary to publish a fresh model for UI tests.
        tab.updateEntry(0, {});
        wait(30);
        const view = entryList(tab);
        for (let i = 0; i < 6; i++) {
            verify(view.itemAtIndex(i) !== null);
            verify(view.itemAtIndex(i).width > 0);
            verify(view.itemAtIndex(i).height > 0);
        }
        return tab;
    }

    function init() {
        Settings.data.sessionMenu = {
            position: "center",
            showHeader: true,
            enableCountdown: true,
            countdownDuration: 5000,
            powerOptions: [
                {
                    action: "logout",
                    enabled: false,
                    countdownEnabled: false
                },
                {
                    action: "lock",
                    enabled: true
                }
            ]
        };
        Settings.dataChanged();
    }

    function test_optionsAndSaveDefaults() {
        const tab = newTab();
        compare(tab.entriesModel.map(entry => entry.id), ["logout", "lock", "suspend", "hibernate", "reboot", "shutdown"]);
        compare(Settings.data.sessionMenu.powerOptions, [
            {
                action: "logout",
                enabled: false,
                countdownEnabled: false
            },
            {
                action: "lock",
                enabled: true,
                countdownEnabled: true
            },
            {
                action: "suspend",
                enabled: true,
                countdownEnabled: true
            },
            {
                action: "hibernate",
                enabled: true,
                countdownEnabled: true
            },
            {
                action: "reboot",
                enabled: true,
                countdownEnabled: true
            },
            {
                action: "shutdown",
                enabled: true,
                countdownEnabled: true
            }
        ]);
        const view = entryList(tab);
        compare(view.itemAtIndex(0).text, "session-menu.logout");
        compare(view.itemAtIndex(0).entryEnabled, false);
        compare(view.itemAtIndex(0).countdownEnabled, false);
        compare(view.itemAtIndex(1).countdownEnabled, true);
    }

    function test_selectionAndCountdownSettings() {
        const tab = newTab();
        const position = control(tab, "settings.session-menu.position.label");
        compare(position.itemCount(), 7);
        position.activateCurrentIndex(position.findIndexByKey("bottom_right"));
        compare(Settings.data.sessionMenu.position, "bottom_right");
        control(tab, "settings.session-menu.show-header.label").toggled(false);
        compare(Settings.data.sessionMenu.showHeader, false);
        const countdown = control(tab, "settings.session-menu.enable-countdown.label");
        const slider = descendants(tab).filter(item => item.stepSize === 1000 && item.text !== undefined && item.moved !== undefined)[0];
        verify(slider !== undefined);
        compare(slider.value, 5000);
        slider.moved(12000);
        compare(Settings.data.sessionMenu.countdownDuration, 12000);
        countdown.toggled(false);
        compare(Settings.data.sessionMenu.enableCountdown, false);
        Settings.dataChanged();
        compare(slider.parent.visible, false);
        countdown.toggled(true);
        Settings.dataChanged();
        compare(slider.parent.visible, true);
        tab.destroy();
        wait(0);
        const reopened = newTab();
        compare(control(reopened, "settings.session-menu.position.label").currentKey, "bottom_right");
        compare(control(reopened, "settings.session-menu.show-header.label").checked, false);
    }

    function test_delegateEditRoutesToOwningInstance() {
        const first = newTab();
        const second = newTab(900);
        const firstView = entryList(first);
        const secondView = entryList(second);
        const entry = secondView.itemAtIndex(0);
        const checkbox = descendants(entry).filter(item => item.clicked !== undefined && item.containsMouse !== undefined && item.preventStealing !== undefined && item.pressed !== undefined && item.cursorShape === Qt.PointingHandCursor)[0];
        verify(checkbox !== undefined);
        mouseClick(checkbox, checkbox.width / 2, checkbox.height / 2);
        wait(0);
        compare(second.entriesModel[0].enabled, true);
        compare(first.entriesModel[0].enabled, false);
        compare(firstView.itemAtIndex(0).entryEnabled, false);
        compare(Settings.data.sessionMenu.powerOptions[0].enabled, true);
        const countdownToggle = descendants(secondView.itemAtIndex(1)).filter(item => item.toggled !== undefined)[0];
        countdownToggle.toggled(false);
        wait(0);
        compare(second.entriesModel[1].countdownEnabled, false);
        compare(first.entriesModel[1].countdownEnabled, true);
        compare(Settings.data.sessionMenu.powerOptions[1].countdownEnabled, false);
        second.destroy();
        wait(0);
        const reopened = newTab(900);
        compare(entryList(reopened).itemAtIndex(0).entryEnabled, true);
        compare(entryList(reopened).itemAtIndex(1).countdownEnabled, false);
    }

    function test_dragUsesOwningViewAndPersistsOrder() {
        const first = newTab();
        const second = newTab(900);
        const view = entryList(second);
        const entry = view.itemAtIndex(0);
        const handle = descendants(entry).filter(item => item.cursorShape === Qt.SizeVerCursor)[0];
        verify(handle !== undefined);
        mousePress(handle, handle.width / 2, handle.height / 2);
        compare(entry.dragging, true);
        compare(entry.dragStartIndex, 0);
        mouseMove(handle, handle.width / 2, handle.height / 2 + 2 * (entry.height + Style.marginS), 20);
        verify(entry.dragTargetIndex > 0);
        verify(entry.dragTargetIndex < view.count);
        const destination = entry.dragTargetIndex;
        mouseRelease(handle, handle.width / 2, handle.height / 2);
        wait(30);
        compare(second.entriesModel[destination].id, "logout");
        compare(first.entriesModel[0].id, "logout");
        compare(Settings.data.sessionMenu.powerOptions.map(option => option.action), second.entriesModel.map(option => option.id));
        const moved = view.itemAtIndex(destination);
        compare(moved.dragging, false);
        compare(moved.dragStartIndex, -1);
        compare(moved.y, destination * (moved.height + Style.marginS));
        second.destroy();
        wait(0);
        const reopened = newTab(900);
        compare(reopened.entriesModel[destination].id, "logout");
    }
}
