import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Cards
import qs.Modules.Panels.Clock
import qs.Modules.Panels.ControlCenter
import qs.Services.Location
import qs.Services.UI

Item {
    id: scene

    width: 1000
    height: 1000

    ShellScreen {
        id: firstScreen

        name: "first"
    }

    ShellScreen {
        id: secondScreen

        name: "second"
    }

    Component {
        id: shortcutHost

        ControlCenterPanel {
            id: root

            width: 480
            height: 80

            ShortcutsCard {
                anchors.fill: parent
            }

        }

    }

    Component {
        id: actionWidget

        Rectangle {
            id: action

            property ShellScreen screen
            property string widgetId
            property string section
            property int sectionWidgetIndex
            property int sectionWidgetsCount
            property var widgetSettings

            signal activated(string caption, string monitor)

            implicitWidth: 80
            implicitHeight: 32

            Text {
                anchors.centerIn: parent
                text: action.widgetSettings ? action.widgetSettings.caption : ""
            }

            MouseArea {
                anchors.fill: parent
                onClicked: action.activated(action.widgetSettings.caption, action.screen.name)
            }

        }

    }

    Component {
        id: clockComponent

        ClockPanel {
            width: preferredWidth
            height: 850
        }

    }

    SignalSpy {
        id: actionSpy

        signalName: "activated"
    }

    TestCase {
        id: testCase

        property var host
        property var otherHost
        property var panel

        function descendants(item, predicate) {
            let matches = [];
            for (const child of item.children) {
                if (predicate(child))
                    matches.push(child);

                matches = matches.concat(descendants(child, predicate));
            }
            return matches;
        }

        function configure(cards, weather, left, right) {
            Settings.data = {
                "controlCenter": {
                    "shortcuts": {
                        "left": left,
                        "right": right
                    }
                },
                "calendar": {
                    "cards": cards
                },
                "location": {
                    "weatherEnabled": weather,
                    "analogClockInCalendar": false,
                    "firstDayOfWeek": 1,
                    "showWeekNumberInCalendar": true,
                    "showCalendarEvents": false,
                    "use12hourFormat": false
                },
                "ui": {
                    "fontFixed": "monospace"
                }
            };
        }

        function init() {
            Time.now = new Date(2026, 0, 15, 12, 34);
            Quickshell.launches = [];
            CalendarService.pollingRefs = 0;
            ControlCenterWidgetRegistry.widgets = {
                "Action": actionWidget
            };
            configure([{
                "id": "calendar-header-card",
                "enabled": true
            }, {
                "id": "calendar-month-card",
                "enabled": true
            }, {
                "id": "timer-card",
                "enabled": true
            }, {
                "id": "weather-card",
                "enabled": true
            }, {
                "id": "unknown",
                "enabled": true
            }, {
                "id": "timer-card",
                "enabled": false
            }], false, [{
                "id": "Action",
                "caption": "Left"
            }], [{
                "id": "Action",
                "caption": "Right"
            }]);
            host = createTemporaryObject(shortcutHost, scene, {
                "screen": firstScreen
            });
            otherHost = createTemporaryObject(shortcutHost, scene, {
                "screen": secondScreen,
                "shortcutsHeight": 64,
                "y": 100
            });
            panel = createTemporaryObject(clockComponent, scene, {
                "x": 500
            });
            verify(host !== null && otherHost !== null && panel !== null);
            wait(40);
        }

        function cleanup() {
            actionSpy.target = null;
            compare(Quickshell.launches.length, 0);
        }

        function test_shortcut_render_owner_action_and_empty_sections() {
            const actions = descendants(host, (child) => {
                return child.activated !== undefined;
            });
            const others = descendants(otherHost, (child) => {
                return child.activated !== undefined;
            });
            compare(actions.length, 2);
            compare(others.length, 2);
            compare(actions[0].widgetSettings.caption, "Left");
            compare(actions[1].widgetSettings.caption, "Right");
            compare(actions[0].screen, firstScreen);
            compare(others[1].screen, secondScreen);
            compare(actions[0].section, "quickSettings");
            compare(actions[0].sectionWidgetIndex, 0);
            compare(actions[0].sectionWidgetsCount, 1);
            const boxes = descendants(host, (child) => {
                return child.border !== undefined && child.activated === undefined;
            });
            compare(boxes.length, 2);
            compare(boxes[0].Layout.preferredHeight, 52);
            otherHost.shortcutsHeight = 73;
            const otherBoxes = descendants(otherHost, (child) => {
                return child.border !== undefined && child.activated === undefined;
            });
            compare(otherBoxes[1].Layout.preferredHeight, 73);
            compare(boxes[0].Layout.preferredHeight, 52);
            verify(actions[0].width > 0 && actions[0].height > 0);
            actionSpy.target = actions[1];
            actionSpy.clear();
            mouseClick(actions[1], actions[1].width / 2, actions[1].height / 2);
            compare(actionSpy.count, 1);
            compare(actionSpy.signalArguments[0][0], "Right");
            compare(actionSpy.signalArguments[0][1], "first");
            configure([], false, [], [{
                "id": "Action",
                "caption": "Changed"
            }, {
                "id": "Action",
                "caption": "Second"
            }]);
            tryCompare(boxes[0], "visible", false);
            const updated = descendants(host, (child) => {
                return child.activated !== undefined;
            });
            compare(updated.length, 2);
            compare(updated[1].sectionWidgetIndex, 1);
            compare(updated[1].sectionWidgetsCount, 2);
        }

        function test_clock_display_month_selection_and_card_routing() {
            const rows = descendants(panel.contentItem, (child) => {
                return child.itemAt !== undefined && child.count === 6;
            })[0];
            verify(rows !== undefined);
            verify(rows.itemAt(0).item !== null);
            verify(rows.itemAt(1).item !== null);
            verify(rows.itemAt(2).item !== null);
            compare(rows.itemAt(3).active, false);
            compare(rows.itemAt(4).item, null);
            compare(rows.itemAt(5).active, false);
            const header = rows.itemAt(0).item;
            compare(header.currentYear, 2026);
            compare(header.currentMonth, 0);
            compare(descendants(header, (child) => {
                return child.text === "12:34";
            }).length, 1);
            Time.now = new Date(2027, 1, 8, 9, 5);
            tryCompare(header, "currentYear", 2027);
            compare(header.currentMonth, 1);
            compare(descendants(header, (child) => {
                return child.text === "09:05";
            }).length, 1);
            const month = rows.itemAt(1).item;
            const previous = descendants(month, (child) => {
                return child.icon === "chevron-left";
            })[0];
            mouseClick(previous, 16, 16);
            compare(month.calendarMonth, 0);
            compare(month.calendarYear, 2027);
            const today = descendants(month, (child) => {
                return child.icon === "calendar";
            })[0];
            mouseClick(today, 16, 16);
            compare(month.calendarMonth, 1);
            compare(month.calendarYear, 2027);
            compare(panel.preferredWidth, 460);
            panel.opened();
            compare(CalendarService.pollingRefs, 1);
            panel.closed();
            compare(CalendarService.pollingRefs, 0);
            configure([{
                "id": "weather-card",
                "enabled": true
            }, {
                "id": "calendar-header-card",
                "enabled": true
            }], true, [], []);
            wait(40);
            const reordered = descendants(panel.contentItem, (child) => {
                return child.itemAt !== undefined && child.count === 2;
            })[0];
            verify(reordered.itemAt(0).item !== null);
            compare(reordered.itemAt(0).item.forecastDays, 5);
            compare(reordered.itemAt(0).item.showLocation, false);
            compare(reordered.itemAt(1).item.currentYear, 2027);
            Settings.data = Object.assign({
            }, Settings.data, {
                "location": Object.assign({
                }, Settings.data.location, {
                    "showWeekNumberInCalendar": false
                })
            });
            compare(panel.preferredWidth, 440);
            Style.uiScaleRatio = 1.5;
            compare(panel.preferredWidth, 660);
            Style.uiScaleRatio = 1;
        }

        name: "ShortcutsClockWarnings"
        when: windowShown
    }

}
