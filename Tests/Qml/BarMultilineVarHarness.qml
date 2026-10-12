import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Services.Power
import qs.Services.Keyboard
import qs.Modules.Bar.Widgets as W

Item {
    id: scene

    width: 800
    height: 600

    ShellScreen {
        id: fixtureScreen

        name: "inert"
    }

    Component {
        id: customFactory

        W.CustomButton {
        }

    }

    Component {
        id: awakeFactory

        W.KeepAwake {
        }

    }

    Component {
        id: keyboardFactory

        W.KeyboardLayout {
        }

    }

    Component {
        id: spacerFactory

        W.Spacer {
        }

    }

    TestCase {
        id: tests

        property var widget

        function init() {
            Settings.data.bar.position = "top";
            Settings.data.bar.widgets.left = [];
            Settings.dataChanged();
            PanelService.events = [];
            PanelService.panel.requestedTab = -1;
            Quickshell.commands = [];
            IdleInhibitorService.isInhibited = false;
            IdleInhibitorService.timeout = null;
            IdleInhibitorService.deltas = [];
            KeyboardLayoutService.currentLayout = "us";
            stateSpy.clear();
        }

        function rows() {
            return [{
                "tag": "CustomButton",
                "factory": customFactory,
                "config": {
                    "icon": "star",
                    "maxTextLength": {
                        "horizontal": 4,
                        "vertical": 2
                    }
                }
            }, {
                "tag": "KeepAwake",
                "factory": awakeFactory,
                "config": {
                    "marker": "awake"
                }
            }, {
                "tag": "KeyboardLayout",
                "factory": keyboardFactory,
                "config": {
                    "displayMode": "forceOpen"
                }
            }, {
                "tag": "Spacer",
                "factory": spacerFactory,
                "config": {
                    "width": 23
                }
            }];
        }

        function make(row) {
            Settings.data.bar.widgets.left = [row.config, {
                "width": 31,
                "icon": "moon",
                "displayMode": "alwaysHide"
            }];
            Settings.dataChanged();
            widget = createTemporaryObject(row.factory, scene, {
                "screen": fixtureScreen,
                "widgetId": row.tag,
                "section": "left",
                "sectionWidgetIndex": 0,
                "x": 200,
                "y": 200
            });
            verify(widget !== null);
            wait(120);
            return widget.children.find((child) => {
                return child.wheel !== undefined && child.show !== undefined;
            });
        }

        function test_settings_lifetime_data() {
            return rows();
        }

        function test_settings_lifetime(row) {
            const pill = make(row);
            compare(widget.widgetSettings, row.config);
            widget.sectionWidgetIndex = 1;
            compare(widget.widgetSettings, Settings.data.bar.widgets.left[1]);
            widget.sectionWidgetIndex = 9;
            compare(widget.widgetSettings, {
            });
            widget.sectionWidgetIndex = 0;
            widget.section = "";
            compare(widget.widgetSettings, {
            });
            widget.section = "left";
            compare(widget.widgetSettings, row.config);
            Settings.data.bar.widgets.left = [{
                "width": 47,
                "icon": "sun",
                "displayMode": "alwaysHide"
            }];
            Settings.dataChanged();
            compare(widget.widgetSettings.width, 47);
            if (row.tag === "CustomButton")
                compare(pill.icon, "sun");

            if (row.tag === "KeyboardLayout")
                verify(pill.forceClose);

            if (row.tag === "Spacer")
                compare(widget.width, 47);

        }

        function test_custom_icon_tooltip_click_commands() {
            const pill = make(rows()[0]);
            compare(pill.icon, "star");
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.LeftButton);
            compare(PanelService.events, ["settingsPanel", "open"]);
            compare(PanelService.panel.requestedTab, 0);
            widget.widgetSettings = {
                "icon": "star",
                "parseJson": true,
                "maxTextLength": {
                    "horizontal": 12,
                    "vertical": 2
                },
                "leftClickExec": "left",
                "rightClickExec": "right",
                "middleClickExec": "middle",
                "wheelMode": "unified",
                "wheelExec": "wheel $delta $delta+2 $delta*3"
            };
            widget.parseDynamicContent('{"text":"Hi","icon":"moon","tooltip":"detail"}');
            compare(pill.icon, "moon");
            compare(pill.text, "Hi");
            verify(pill.tooltipText.includes("Left click: left."));
            verify(pill.tooltipText.endsWith("detail"));
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.LeftButton);
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.RightButton);
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.MiddleButton);
            pill.wheel(120);
            pill.wheel(-120);
            compare(Quickshell.commands, [["sh", "-c", "left"], ["sh", "-c", "right"], ["sh", "-c", "middle"], ["sh", "-c", "wheel 1 3 3"], ["sh", "-c", "wheel -1 1 -3"]]);
            verify(widget.implicitWidth > 0 && widget.implicitHeight > 0);
        }

        function test_custom_scroll_branch_lifetimes() {
            const pill = make(rows()[0]);
            widget.parseDynamicContent("ABCDEFGH");
            const timer = widget.data.find((child) => {
                return child.interval === 300;
            });
            verify(timer !== undefined);
            timer.stop();
            compare(widget._dynamicText, "ABCD");
            for (let tick = 0; tick < 6; tick++) timer.triggered()
            compare(widget._scrollState.phase, 1);
            timer.triggered();
            compare(widget._dynamicText, "BCDE");
            timer.triggered();
            compare(widget._dynamicText, "CDEF");
            timer.triggered();
            timer.triggered();
            compare(widget._dynamicText, "EFGH");
            compare(widget._scrollState.phase, 2);
            timer.triggered();
            compare(widget._dynamicText, "EFGH");
            for (let tick = 0; tick < 5; tick++) timer.triggered()
            verify(!timer.running);
            widget.parseDynamicContent("XY");
            compare(widget._dynamicText, "XY");
            compare(widget._scrollState.offset, 0);
            verify(!widget._scrollState.needsScrolling);
            Settings.data.bar.position = "left";
            Settings.dataChanged();
            widget.parseDynamicContent("12345");
            timer.stop();
            compare(widget.currentMaxTextLength, 2);
            compare(pill.text, "12");
            for (let tick = 0; tick < 10; tick++) timer.triggered()
            compare(widget._dynamicText, "45");
            verify(pill.rotateText);
            widget._scrollState.needsScrolling = false;
            timer.triggered();
            verify(!timer.running);
        }

        function test_awake_state_click_signal() {
            const pill = make(rows()[1]);
            compare(pill.icon, "keep-awake-off");
            compare(pill.text, "");
            verify(pill.forceClose);
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.LeftButton);
            compare(stateSpy.count, 1);
            compare(pill.icon, "keep-awake-on");
            compare(pill.tooltipText, "tooltips.disable-keep-awake");
            IdleInhibitorService.timeout = 600;
            compare(pill.text, "600s");
            verify(pill.forceOpen);
            Settings.data.bar.position = "right";
            Settings.dataChanged();
            wait(120);
            verify(widget.implicitHeight > 0);
            pill.clicked();
            compare(stateSpy.count, 2);
            compare(pill.icon, "keep-awake-off");
        }

        function test_awake_wheel_data() {
            return [{
                "tag": "null-up",
                "timeout": null,
                "delta": 120,
                "expected": 60
            }, {
                "tag": "null-down",
                "timeout": null,
                "delta": -120,
                "expected": -60
            }, {
                "tag": "below-ten",
                "timeout": 599,
                "delta": 120,
                "expected": 60
            }, {
                "tag": "ten-up",
                "timeout": 600,
                "delta": 120,
                "expected": 300
            }, {
                "tag": "ten-down",
                "timeout": 600,
                "delta": -120,
                "expected": -60
            }, {
                "tag": "thirty-up",
                "timeout": 1800,
                "delta": 120,
                "expected": 600
            }, {
                "tag": "thirty-down",
                "timeout": 1800,
                "delta": -120,
                "expected": -300
            }, {
                "tag": "hour-up",
                "timeout": 3600,
                "delta": 120,
                "expected": 1800
            }, {
                "tag": "hour-down",
                "timeout": 3600,
                "delta": -120,
                "expected": -600
            }];
        }

        function test_awake_wheel(row) {
            const pill = make(rows()[1]);
            IdleInhibitorService.timeout = row.timeout;
            pill.wheel(row.delta);
            compare(IdleInhibitorService.deltas, [row.expected]);
            compare(IdleInhibitorService.timeout, (row.timeout || 0) + row.expected);
        }

        function test_keyboard_layout_and_context_signal() {
            const pill = make(rows()[2]);
            compare(pill.icon, "keyboard");
            compare(pill.text, "US");
            verify(pill.forceOpen);
            KeyboardLayoutService.currentLayout = "fr";
            compare(pill.text, "FR");
            compare(pill.tooltipText, "tooltips.keyboard-layout:FR");
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.LeftButton);
            compare(PanelService.events, []);
            mouseClick(pill, pill.width / 2, pill.height / 2, Qt.RightButton);
            compare(PanelService.events, ["menu"]);
            const menu = PanelService.lastMenu;
            compare(menu.lastAnchor, pill);
            compare(menu.lastX, 7);
            compare(menu.lastY, 9);
            menu.triggered("widget-settings");
            compare(PanelService.events, ["menu", "close"]);
            compare(BarService.settingsArgs, [fixtureScreen, "left", 0, "KeyboardLayout", widget.widgetSettings]);
            widget.sectionWidgetIndex = 1;
            verify(pill.forceClose);
            Settings.data.bar.position = "left";
            Settings.dataChanged();
            wait(120);
            compare(pill.text, "FR");
            verify(widget.implicitHeight > 0);
        }

        function test_spacer_layout() {
            make(rows()[3]);
            compare(widget.width, 23);
            compare(widget.height, 40);
            Settings.data.bar.position = "right";
            Settings.dataChanged();
            compare(widget.width, 40);
            compare(widget.height, 23);
            widget.sectionWidgetIndex = 1;
            compare(widget.height, 31);
            widget.sectionWidgetIndex = -1;
            compare(widget.height, widget.widgetMetadata.width);
            Settings.data.bar.position = "bottom";
            Settings.dataChanged();
            compare(widget.width, widget.widgetMetadata.width);
            compare(widget.height, 40);
        }

        name: "BarMultilineVar"
        when: windowShown

        SignalSpy {
            id: stateSpy

            signalName: "isInhibitedChanged"
            target: IdleInhibitorService
        }

    }

}
