import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Panels.Settings
import qs.Services.System
import qs.Services.UI

ShellRoot {
    id: harness

    property SettingsPanel panel: null
    property int phase: 0
    property int visited: 0
    property int saveCount: 0
    readonly property var labels: ["general", "user-interface", "color-scheme", "wallpaper", "bar", "dock", "control-center", "launcher", "notifications", "osd", "lock-screen", "session-menu", "audio", "battery", "display", "network", "location", "screen-recorder", "system-monitor", "hooks", "about"]

    // Offscreen platform only: no DISPLAY/WAYLAND_DISPLAY or desktop connection.
    Window {
        id: window
        visible: true
        width: 1100
        height: 1000
    }

    Component {
        id: panelComponent
        SettingsPanel {
            objectName: "settingsPanel"
        }
    }

    Connections {
        target: Settings
        function onSettingsSaved() {
            harness.saveCount++;
        }
    }

    function check(condition, message) {
        if (!condition) {
            console.error("SETTINGS_PANEL_ASSERT", message);
            Qt.quit();
            throw new Error(message);
        }
    }

    function findItem(item, predicate) {
        if (predicate(item))
            return item;
        for (const child of item.children) {
            const found = harness.findItem(child, predicate);
            if (found)
                return found;
        }
        return null;
    }

    function assertSelectedTab(index) {
        check(panel.currentTabIndex === index, "Tab index mismatch: " + index);
        check(panel.tabsModel[index].label === "settings." + labels[index] + ".title", "Tab order changed at " + index + ": " + panel.tabsModel[index].label);
        check(panel.activeScrollView !== null, "Active scroll view missing");
        check(findItem(panel, item => item.text === I18n.tr(harness.panel.tabsModel[index].label)) !== null, "Selected title missing");
        const expectedName = "fixture-" + (index === 9 ? "Osd" : labels[index].split("-").map(part => part[0].toUpperCase() + part.slice(1)).join(""));
        check(findItem(panel, item => item.objectName === expectedName) !== null, "Tab loader content missing: " + expectedName);
        const list = findItem(panel, item => item.count === 21 && item.currentIndex !== undefined && typeof item.itemAtIndex === "function");
        check(list !== null && list.currentIndex === index, "Sidebar selection desynchronized");
        const entry = list.itemAtIndex(index);
        check(entry !== null && entry.selected, "Sidebar delegate selection missing");
        check(entry.icon === panel.tabsModel[index].icon && entry.label === panel.tabsModel[index].label, "Sidebar model roles lost");
    }

    function assertScroll() {
        const view = panel.activeScrollView;
        check(view.contentHeight > view.height, "Fixture must overflow for scroll assertions");
        const bar = view.ScrollBar.vertical;
        bar.position = 0;
        panel.onPageDownPressed();
        check(bar.position > 0, "Page down did not move active scroll view");
        panel.onPageUpPressed();
        check(Math.abs(bar.position) < 0.00001, "Page up did not restore scroll position");
        panel.onDownPressed();
        check(bar.position > 0, "Down did not move scroll view");
        panel.onUpPressed();
        check(Math.abs(bar.position) < 0.00001, "Up did not restore scroll position");
    }

    Timer {
        interval: 40
        running: true
        repeat: true
        onTriggered: {
            if (harness.phase === 0 && Settings.ready) {
                harness.panel = panelComponent.createObject(window.contentItem);
                harness.check(harness.panel !== null, "Production panel failed to instantiate");
                harness.check(harness.panel.tabsModel.length === 21, "Tab count changed");
                harness.panel.requestedTab = SettingsPanel.Tab.General;
                harness.panel.open();
                harness.phase = 1;
            } else if (harness.phase === 1 && harness.panel.isPanelVisible && harness.panel.sizeAnimationComplete) {
                harness.assertSelectedTab(harness.visited);
                harness.assertScroll();
                harness.visited++;
                if (harness.visited < 21) {
                    harness.panel.onTabPressed();
                } else {
                    harness.panel.onTabPressed();
                    harness.phase = 2;
                }
            } else if (harness.phase === 2) {
                harness.assertSelectedTab(0);
                harness.panel.onBackTabPressed();
                harness.phase = 3;
            } else if (harness.phase === 3) {
                harness.assertSelectedTab(20);
                harness.check(ProgramCheckerService.checks === 1 && PanelService.opens === 1, "Open checks not run exactly once");
                Settings.data.ui.fontDefault = "Panel Dirty Sans";
                harness.check(!Settings.persistedSettingsText.includes("Panel Dirty Sans"), "Dirty change already persisted before close");
                const closeButton = harness.findItem(harness.panel, item => item.icon === "close" && typeof item.clicked === "function");
                harness.check(closeButton !== null, "Close button missing");
                closeButton.clicked();
                harness.phase = 4;
            } else if (harness.phase === 4 && !harness.panel.isPanelOpen && harness.saveCount > 0 && !Settings.saveInProgress) {
                harness.check(!harness.panel.isPanelVisible && PanelService.closes === 1, "Close lifecycle did not finish");
                harness.check(Settings.ready && Settings.persistedSettingsText.includes("Panel Dirty Sans"), "Debounced dirty value lost on close");
                harness.check(harness.panel.activeScrollView === null, "Closed loader left active scroll view alive");
                harness.panel.requestedTab = SettingsPanel.Tab.Audio;
                harness.panel.open();
                harness.phase = 5;
            } else if (harness.phase === 5 && harness.panel.isPanelVisible && harness.panel.sizeAnimationComplete) {
                harness.assertSelectedTab(12);
                harness.check(Settings.data.ui.fontDefault === "Panel Dirty Sans", "Reopen reset persisted value");
                harness.check(ProgramCheckerService.checks === 2 && PanelService.opens === 2, "Reopen skipped checks");
                harness.panel.onEscapePressed();
                harness.phase = 6;
            } else if (harness.phase === 6 && !harness.panel.isPanelOpen) {
                harness.check(PanelService.closes === 2, "Escape close not finalized");
                harness.panel.destroy();
                console.log("SETTINGS_PANEL_BEHAVIOR_PASS", harness.visited, "tabs, wrap, scroll, close, debounce, reopen, escape");
                Qt.quit();
            }
        }
    }

    Timer {
        interval: 15000
        running: true
        onTriggered: {
            console.error("SETTINGS_PANEL_TIMEOUT", harness.phase, Settings.bootstrapState, Settings.errorMessage);
            Qt.quit();
        }
    }
}
