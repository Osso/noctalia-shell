import QtQuick
import QtTest
import qs.Modules.Panels.Settings.ControlCenter.WidgetSettings

Item {
    id: scene
    width: 1000
    height: 1000

    Component {
        id: factory
        CustomButtonSettings {}
    }

    TestCase {
        name: "CustomButtonControlSettings"
        when: windowShown
        property var editor
        property var stored
        property var metadata: ({
                icon: "terminal",
                onClicked: "fixture-left",
                onRightClicked: "fixture-right",
                onMiddleClicked: "fixture-middle",
                generalTooltipText: "Fixture tooltip",
                enableOnStateLogic: true,
                stateChecksJson: '[{"command":"fixture-status","icon":"star"},{"command":"fixture-second","icon":"moon"}]'
            })
        readonly property string prefix: "settings.control-center.shortcuts.custom-button."

        function descendants(item) {
            let result = [];
            for (const child of item.children || [])
                result = result.concat([child], descendants(child));
            return result;
        }

        function input(key) {
            const matches = descendants(editor).filter(item => item.label === prefix + key + ".label" && item.inputItem !== undefined);
            compare(matches.length, 1, key);
            return matches[0];
        }

        function stateInputs() {
            return descendants(editor).filter(item => item.placeholderText === prefix + "state-checks.command" && item.inputItem !== undefined);
        }

        function button(text, scope) {
            const matches = descendants(scope || editor).filter(item => item.text === text && item.clicked !== undefined);
            compare(matches.length, 1, text);
            return matches[0];
        }

        function picker(scope) {
            const matches = (scope || editor).data.filter(item => item.iconSelected !== undefined);
            compare(matches.length, 1);
            return matches[0];
        }

        function reopen(data) {
            editor.destroy();
            wait(1);
            editor = createTemporaryObject(factory, scene, {
                widgetData: data,
                widgetMetadata: metadata
            });
            verify(editor !== null);
            wait(10);
        }

        function init() {
            stored = {
                id: "CustomButton",
                icon: "star",
                onClicked: "",
                enableOnStateLogic: true
            };
            editor = createTemporaryObject(factory, scene, {
                widgetData: stored,
                widgetMetadata: metadata
            });
            verify(editor !== null);
            wait(10);
        }

        function test_commands_apply_reopen_cancel() {
            const before = JSON.stringify(stored);
            compare(input("on-clicked").text, "");
            compare(input("on-right-clicked").text, "fixture-right");
            for (const key of ["on-clicked", "on-right-clicked", "on-middle-clicked", "general-tooltip-text"])
                input(key).inputItem.text = "fixture-" + key + " --never-execute";
            const saved = editor.saveSettings();
            compare(saved.onClicked, "fixture-on-clicked --never-execute");
            compare(saved.onRightClicked, "fixture-on-right-clicked --never-execute");
            compare(saved.onMiddleClicked, "fixture-on-middle-clicked --never-execute");
            compare(saved.generalTooltipText, "fixture-general-tooltip-text --never-execute");
            compare(JSON.stringify(stored), before);
            reopen(stored);
            compare(input("on-clicked").text, "");
            reopen(saved);
            compare(input("on-clicked").text, saved.onClicked);
        }

        function test_state_roles_edit_icons_add_remove() {
            const fields = stateInputs();
            compare(fields.length, 2);
            compare(fields[0].text, "fixture-status");
            const delegate = fields[0].parent.parent;
            const preview = descendants(delegate).find(item => item.pointSize !== undefined && item.icon !== undefined);
            verify(preview !== undefined);
            compare(preview.icon, "star");
            fields[0].inputItem.text = "fixture-changed --never-execute";
            fields[0].inputItem.editingFinished();
            const iconPicker = picker(delegate);
            compare(iconPicker.initialIcon, "star");
            iconPicker.selectedIcon = "sun";
            button("widgets.icon-picker.apply", iconPicker.contentItem).clicked();
            let checks = JSON.parse(editor.saveSettings().stateChecksJson);
            compare(checks[0], {
                command: "fixture-changed --never-execute",
                icon: "sun"
            });
            compare(preview.icon, "sun");
            button(prefix + "state-checks.add").clicked();
            compare(stateInputs().length, 3);
            const remove = descendants(delegate).find(item => item.tooltipText === prefix + "state-checks.remove");
            verify(remove.width > 0);
            remove.clicked();
            compare(stateInputs().length, 2);
            const remaining = stateInputs()[0];
            remaining.inputItem.text = "fixture-shifted";
            remaining.inputItem.editingFinished();
            checks = JSON.parse(editor.saveSettings().stateChecksJson);
            compare(checks, [
                {
                    command: "fixture-shifted",
                    icon: "moon"
                },
                {
                    command: "",
                    icon: ""
                }
            ]);
            const saved = editor.saveSettings();
            reopen(saved);
            compare(stateInputs()[0].text, "fixture-shifted");
            reopen(stored);
            compare(stateInputs()[0].text, "fixture-status");
        }

        function test_primary_icon_and_toggle() {
            const iconPicker = picker();
            compare(iconPicker.initialIcon, "star");
            iconPicker.selectedIcon = "moon";
            button("widgets.icon-picker.apply", iconPicker.contentItem).clicked();
            compare(editor.saveSettings().icon, "moon");
            iconPicker.selectedIcon = "sun";
            button("widgets.icon-picker.cancel", iconPicker.contentItem).clicked();
            compare(editor.saveSettings().icon, "moon");
            const toggle = descendants(editor).find(item => item.label === prefix + "enable-on-state-logic.label" && item.toggled !== undefined);
            toggle.toggled(false);
            compare(editor.saveSettings().enableOnStateLogic, false);
            compare(stateInputs()[0].visible, false);
            toggle.toggled(true);
            compare(stateInputs()[0].visible, true);
        }

        function test_state_list_parsing() {
            reopen({
                id: "CustomButton",
                stateChecksJson: "[]"
            });
            compare(stateInputs().length, 0);
            reopen({
                id: "CustomButton",
                stateChecksJson: "{}"
            });
            compare(JSON.parse(editor.saveSettings().stateChecksJson), []);
            reopen({
                id: "CustomButton",
                stateChecksJson: "broken"
            });
            compare(stateInputs().length, 0);
            ignoreWarning("⚠️ Invalid stateChecks entry at index 0: null");
            reopen({
                id: "CustomButton",
                stateChecksJson: '[null,{"command":"fixture-only"}]'
            });
            compare(JSON.parse(editor.saveSettings().stateChecksJson), [
                {
                    command: "fixture-only",
                    icon: ""
                }
            ]);
        }
    }
}
