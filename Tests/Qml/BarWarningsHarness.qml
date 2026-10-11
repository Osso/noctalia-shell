import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Modules.Bar

Item {
    id: scene

    width: 800
    height: 600

    ShellScreen {
        id: screenA

        name: "fixture-A"
    }

    ShellScreen {
        id: screenB

        name: "fixture-B"
    }

    Component {
        id: factory

        Bar {
        }

    }

    TestCase {
        id: tests

        property var bars: []

        function makeBar(screen) {
            const widget = factory.createObject(scene, {
                "screen": screen
            });
            verify(widget !== null);
            bars = bars.concat([widget]);
            return widget;
        }

        function destroyBars() {
            for (const bar of bars) bar.destroy()
            bars = [];
            wait(10);
            compare(Object.keys(BarService.widgets).length, 0);
        }

        function init() {
            Settings.data.bar.position = "top";
            Settings.data.bar.monitors = [];
            Settings.data.bar.floating = false;
            Settings.data.bar.outerCorners = false;
            Settings.dataChanged();
            BarService.readyScreens = [];
            PanelService.available = true;
            PanelService.requestedScreens = [];
            PanelService.toggles = [];
        }

        function cleanup() {
            destroyBars();
        }

        function test_initial_screen_selection_and_teardown() {
            const pending = makeBar(null);
            wait(10);
            compare(pending.barRegion, null);
            compare(pending.barItem, null);
            compare(Object.keys(BarService.widgets).length, 0);
            compare(BarService.readyScreens.length, 0);
            Settings.data.bar.monitors = ["fixture-A"];
            Settings.dataChanged();
            const excluded = makeBar(screenB);
            wait(10);
            compare(excluded.barRegion, null);
            compare(BarService.readyScreens[0], "fixture-B");
            pending.screen = screenA;
            wait(10);
            verify(pending.visible);
            compare(pending.barItem, pending.barRegion);
            compare(Object.keys(BarService.widgets).length, 7);
            compare(BarService.readyScreens.join(","), "fixture-B,fixture-A");
            Settings.data.bar.monitors = ["fixture-B"];
            Settings.dataChanged();
            wait(10);
            compare(pending.barRegion, null);
            verify(excluded.barRegion !== null);
            for (const record of Object.values(BarService.widgets)) compare(record.screen, "fixture-B")
            destroyBars();
        }

        function test_sections_and_input_region_data() {
            return ["top", "bottom", "left", "right"].map((position) => {
                return ({
                    "tag": position,
                    "position": position
                });
            });
        }

        function sectionLoaders(bar, section) {
            return Object.values(BarService.widgets).filter((record) => {
                return record.screen === bar.screen.name && record.section === section;
            }).sort((a, b) => {
                return a.index - b.index;
            }).map((record) => {
                return record.item.parent.parent;
            });
        }

        function checkSection(bar, section, vertical) {
            const entries = Settings.data.bar.widgets[section];
            const records = Object.values(BarService.widgets).filter((record) => {
                return record.screen === bar.screen.name && record.section === section;
            }).sort((a, b) => {
                return a.index - b.index;
            });
            compare(records.length, entries.length);
            const loaders = sectionLoaders(bar, section);
            let previousEnd = -1;
            for (let index = 0; index < entries.length; index++) {
                const record = records[index];
                const loader = loaders[index];
                compare(record.widget, entries[index].id);
                compare(record.index, index);
                compare(record.item.widgetId, entries[index].id);
                compare(record.item.sectionWidgetIndex, index);
                compare(record.count, entries.length);
                compare(record.assignedScreen, bar.screen);
                const shown = record.widget !== "hidden";
                compare(record.initialVisible, shown);
                compare(record.item.visible, shown);
                compare(record.initialWidth, record.widget.endsWith("B") ? 30 : 20);
                compare(loader.visible, shown);
                compare(loader.implicitWidth, shown ? record.item.implicitWidth : 0);
                compare(loader.implicitHeight, shown ? record.item.implicitHeight : 0);
                if (!shown)
                    continue;

                compare(loader.width, record.item.implicitWidth);
                compare(loader.height, record.item.implicitHeight);
                const start = vertical ? loader.y : loader.x;
                if (previousEnd >= 0)
                    compare(start - previousEnd, Style.marginS);

                previousEnd = start + (vertical ? loader.height : loader.width);
            }
            const layout = loaders[0].parent;
            const visibleLoaders = loaders.filter((loader) => {
                return loader.visible;
            });
            const extent = visibleLoaders.reduce((sum, loader) => {
                return sum + (vertical ? loader.height : loader.width);
            }, 0) + Style.marginS * (visibleLoaders.length - 1);
            compare(vertical ? layout.height : layout.width, extent);
            if (section === "left")
                compare(vertical ? layout.y : layout.x, vertical ? Style.marginM : Style.marginS);

            if (section === "center")
                compare(vertical ? layout.y : layout.x, ((vertical ? bar.barRegion.height : bar.barRegion.width) - extent) / 2);

            if (section === "right")
                compare(vertical ? layout.y : layout.x, (vertical ? bar.barRegion.height : bar.barRegion.width) - extent - (vertical ? Style.marginM : Style.marginS));

        }

        function test_sections_and_input_region(row) {
            Settings.data.bar.position = row.position;
            Settings.dataChanged();
            const first = makeBar(screenA);
            const second = makeBar(screenB);
            wait(20);
            compare(Object.keys(BarService.widgets).length, 14);
            compare(BarService.readyScreens.join(","), "fixture-A,fixture-B");
            const vertical = row.position === "left" || row.position === "right";
            for (const bar of [first, second]) {
                // Fixture screens share one offscreen window; route input to one at a time.
                first.visible = bar === first;
                second.visible = bar === second;
                compare(bar.width, 800);
                compare(bar.height, 600);
                verify(bar.visible);
                compare(bar.barRegion, bar.barItem);
                compare(bar.barRegion.width, vertical ? 40 : 800);
                compare(bar.barRegion.height, vertical ? 600 : 40);
                compare(bar.barRegion.x, row.position === "right" ? 760 : 0);
                compare(bar.barRegion.y, row.position === "bottom" ? 560 : 0);
                for (const section of ["left", "center", "right"]) checkSection(bar, section, vertical)
                mouseClick(bar.barRegion, vertical ? 20 : 400, vertical ? 300 : 20, Qt.RightButton);
            }
            compare(PanelService.requestedScreens.join(","), "fixture-A,fixture-B");
            compare(PanelService.toggles.length, 2);
            console.log("BAR_GEOMETRY", row.position, JSON.stringify([first.barRegion.x, first.barRegion.y, first.barRegion.width, first.barRegion.height]));
            destroyBars();
        }

        function test_corner_states_and_orientation_replacement() {
            const bar = makeBar(screenA);
            for (const position of ["top", "bottom", "left", "right"]) {
                Settings.data.bar.position = position;
                Settings.data.bar.outerCorners = true;
                Settings.dataChanged();
                wait(10);
                compare(Object.keys(BarService.widgets).length, 7);
                const expected = {
                    "top": [-1, -1, 2, 2],
                    "bottom": [2, 2, -1, -1],
                    "left": [-1, 1, -1, 1],
                    "right": [1, -1, 1, -1]
                }[position];
                const region = bar.barRegion;
                const names = ["topLeftCornerState", "topRightCornerState", "bottomLeftCornerState", "bottomRightCornerState"];
                for (let index = 0; index < names.length; index++) compare(region[names[index]], expected[index])
                Settings.data.bar.floating = true;
                Settings.dataChanged();
                for (const name of names) compare(region[name], 0)
                Settings.data.bar.floating = false;
                Settings.data.bar.outerCorners = false;
                Settings.dataChanged();
                for (const name of names) compare(region[name], -1)
            }
            destroyBars();
        }

        function test_control_center_modes() {
            const bar = makeBar(screenA);
            Settings.data.controlCenter.position = "close_to_bar_button";
            bar.toggleControlCenterPanel();
            compare(PanelService.toggles[0], "ControlCenter");
            Settings.data.controlCenter.position = "center";
            bar.toggleControlCenterPanel();
            compare(PanelService.toggles[1], "default");
            PanelService.available = false;
            bar.toggleControlCenterPanel();
            compare(PanelService.toggles.length, 2);
        }

        name: "ProductionBar"
        when: windowShown
    }

}
