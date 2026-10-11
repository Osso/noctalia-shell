import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Modules.Panels.Settings.Bar
import qs.Modules.Panels.Settings.Bar.WidgetSettings

TestCase {
    id: suite

    property var metadata: ({
        "usePrimaryColor": true,
        "useCustomFont": false,
        "customFont": "",
        "formatHorizontal": "HH:mm ddd, MMM dd",
        "formatVertical": "HH mm dd MM"
    })
    property var updates: []

    function descendants(item) {
        let items = [item];
        for (const child of item.children || []) items = items.concat(descendants(child))
        return items;
    }

    function createClock(data) {
        const clock = createTemporaryObject(clockComponent, suite, {
            "widgetData": data || {
            },
            "widgetMetadata": suite.metadata
        });
        verify(clock !== null);
        wait(50);
        return clock;
    }

    function inputs(clock) {
        return descendants(clock).filter((item) => {
            return item.inputItem !== undefined && item.placeholderText !== undefined;
        });
    }

    function previewRepeaters(clock) {
        return descendants(clock).filter((item) => {
            return typeof item.itemAt === "function" && typeof item.itemAtIndex !== "function" && item.model !== undefined;
        });
    }

    function previewText(repeater) {
        const lines = [];
        for (let index = 0; index < repeater.count; index++) lines.push(repeater.itemAt(index).text)
        return lines;
    }

    function edit(input, text) {
        input.inputItem.forceActiveFocus();
        input.inputItem.selectAll();
        for (const character of text) keyClick(character)
        compare(input.text, text);
    }

    function init() {
        suite.updates = [];
        Settings.data.bar.widgets.left = [{
            "id": "Clock",
            "formatHorizontal": "HH:mm",
            "formatVertical": "HH mm"
        }];
    }

    function test_formatExamples_data() {
        return [{
            "tag": "24h",
            "horizontal": "HH:mm:ss ddd, MMM dd",
            "vertical": "HH mm dd MM",
            "expectedHorizontal": ["14:30:45 Mon, Dec 25"],
            "expectedVertical": ["14", "30", "25", "12"]
        }, {
            "tag": "12h",
            "horizontal": "hh:mm AP",
            "vertical": "hh mm ap",
            "expectedHorizontal": ["02:30 PM"],
            "expectedVertical": ["02", "30", "pm"]
        }, {
            "tag": "multiline",
            "horizontal": "yyyy-MM-dd\\nHH:mm",
            "vertical": "dddd MMMM d",
            "expectedHorizontal": ["2023-12-25", "14:30"],
            "expectedVertical": ["Monday", "December", "25"]
        }];
    }

    function test_formatExamples(data) {
        const clock = createClock();
        const fields = inputs(clock);
        compare(fields.length, 2);
        edit(fields[0], data.horizontal);
        edit(fields[1], data.vertical);
        const repeaters = previewRepeaters(clock);
        compare(repeaters.length, 2);
        compare(previewText(repeaters[0]), data.expectedHorizontal);
        compare(previewText(repeaters[1]), data.expectedVertical);
        compare(clock.saveSettings().formatHorizontal, data.horizontal);
        compare(clock.saveSettings().formatVertical, data.vertical);
    }

    function test_focusTokenClickAndDragReorder() {
        const clock = createClock({
            "formatHorizontal": "HH mm",
            "formatVertical": "dd MM"
        });
        const fields = inputs(clock);
        const vertical = fields[1].inputItem;
        vertical.forceActiveFocus();
        tryCompare(clock, "focusedInput", fields[1]);
        vertical.cursorPosition = 2;
        const tokens = descendants(clock).find((item) => {
            return item.tokenClicked !== undefined;
        });
        verify(tokens !== undefined);
        const list = descendants(tokens).find((item) => {
            return typeof item.itemAtIndex === "function";
        });
        verify(list !== undefined);
        list.forceLayout();
        const row = list.itemAtIndex(0);
        verify(row !== null);
        mouseClick(row, row.width / 2, row.height / 2);
        compare(fields[1].text, "ddh:mm AP MM ");
        compare(fields[0].text, "HH mm");
        compare(vertical.cursorPosition, 10);
        const horizontal = fields[0].inputItem;
        horizontal.forceActiveFocus();
        tryCompare(clock, "focusedInput", fields[0]);
        const start = horizontal.positionToRectangle(0);
        const end = horizontal.positionToRectangle(2);
        mouseDrag(horizontal, start.x, horizontal.height / 2, end.x - start.x, 0);
        compare(horizontal.selectedText, "HH");
        keyClick(Qt.Key_X, Qt.ControlModifier);
        horizontal.cursorPosition = horizontal.text.length;
        keyClick(Qt.Key_V, Qt.ControlModifier);
        compare(fields[0].text, " mmHH");
        compare(clock.saveSettings().formatHorizontal, "mmHH");
        compare(fields[1].text, "ddh:mm AP MM ");
        edit(fields[0], "hh:mm AP");
        compare(previewText(previewRepeaters(clock)[0]), ["02:30 PM"]);
        edit(fields[0], "HH:mm");
        compare(previewText(previewRepeaters(clock)[0]), ["14:30"]);
    }

    function test_defaultFocusAndSaveIsolation() {
        const source = {
            "id": "Clock",
            "retained": 17,
            "usePrimaryColor": false,
            "useCustomFont": true,
            "customFont": "DejaVu Sans",
            "formatHorizontal": "HH:mm",
            "formatVertical": "dd MM"
        };
        const original = JSON.stringify(source);
        const clock = createClock(source);
        compare(clock.valueUsePrimaryColor, false);
        compare(clock.valueUseCustomFont, true);
        clock.insertToken("AP");
        compare(clock.focusedInput, inputs(clock)[0]);
        edit(inputs(clock)[0], "  hh:mm AP  ");
        edit(inputs(clock)[1], "  yyyy MM dd  ");
        const saved = clock.saveSettings();
        compare(saved.formatHorizontal, "hh:mm AP");
        compare(saved.formatVertical, "yyyy MM dd");
        compare(saved.retained, 17);
        compare(saved.customFont, "DejaVu Sans");
        compare(saved.usePrimaryColor, false);
        compare(JSON.stringify(source), original);
        saved.retained = 18;
        compare(source.retained, 17);
        const preview = previewRepeaters(clock)[0].itemAt(0);
        compare(preview.family, "DejaVu Sans");
        const toggles = descendants(clock).filter((item) => {
            return item.toggled !== undefined && item.baseSize !== undefined;
        });
        toggles[0].toggled(true);
        compare(clock.valueUsePrimaryColor, true);
        compare(preview.color, NColor.mPrimary);
        toggles[1].toggled(false);
        compare(clock.valueUseCustomFont, false);
        compare(preview.family, Settings.data.ui.fontDefault);
    }

    function test_dialogCancelAndApply() {
        const original = JSON.stringify(Settings.data.bar.widgets.left);
        const dialog = createTemporaryObject(dialogComponent, suite, {
            "widgetId": "Clock",
            "widgetIndex": 0,
            "sectionId": "left",
            "widgetData": Settings.data.bar.widgets.left[0]
        });
        verify(dialog !== null);
        dialog.open();
        tryCompare(dialog, "opened", true);
        wait(100);
        const loadedClock = descendants(dialog.contentItem).find((item) => {
            return typeof item.saveSettings === "function";
        });
        verify(loadedClock !== undefined);
        edit(inputs(loadedClock)[0], "hh:mm AP");
        const cancel = descendants(dialog.contentItem).find((item) => {
            return item.text === "bar.widget-settings.dialog.cancel";
        });
        verify(cancel !== undefined);
        mouseClick(cancel, cancel.width / 2, cancel.height / 2);
        tryCompare(dialog, "opened", false);
        compare(suite.updates.length, 0);
        compare(JSON.stringify(Settings.data.bar.widgets.left), original);
        dialog.open();
        tryCompare(dialog, "opened", true);
        wait(100);
        const reopened = descendants(dialog.contentItem).find((item) => {
            return typeof item.saveSettings === "function";
        });
        compare(reopened.valueFormatHorizontal, "HH:mm");
        edit(inputs(reopened)[0], "  hh:mm AP  ");
        edit(inputs(reopened)[1], "hh mm ap");
        const apply = descendants(dialog.contentItem).find((item) => {
            return item.text === "bar.widget-settings.dialog.apply";
        });
        verify(apply !== undefined);
        mouseClick(apply, apply.width / 2, apply.height / 2);
        tryCompare(dialog, "opened", false);
        compare(suite.updates.length, 1);
        compare(suite.updates[0].section, "left");
        compare(suite.updates[0].index, 0);
        compare(suite.updates[0].settings.formatHorizontal, "hh:mm AP");
        compare(suite.updates[0].settings.formatVertical, "hh mm ap");
        compare(JSON.stringify(Settings.data.bar.widgets.left), original);
    }

    name: "ClockSettingsWarnings"
    width: 1100
    height: 1400
    when: windowShown
    visible: true

    Component {
        id: clockComponent

        ClockSettings {
        }

    }

    Component {
        id: dialogComponent

        BarWidgetSettingsDialog {
            onUpdateWidgetSettings: (section, index, settings) => {
                return suite.updates.push({
                    "section": section,
                    "index": index,
                    "settings": settings
                });
            }
        }

    }

}
