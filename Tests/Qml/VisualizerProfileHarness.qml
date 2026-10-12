pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets
import qs.Modules.Cards
import qs.Services.Media
import qs.Services.System
import qs.Services.UI

Item {
    id: scene

    property var screen: fixtureScreen

    width: 800
    height: 600

    ShellScreen {
        id: fixtureScreen

        name: "fixture"
    }

    ShellScreen {
        id: secondScreen

        name: "second-owner"
    }

    Component {
        id: shadowOwnerFactory

        Item {
            property ShellScreen screen: secondScreen

            width: 800
            height: 600
        }
    }

    Component {
        id: visualizerFactory

        AudioVisualizer {}
    }

    Component {
        id: profileFactory

        ProfileCard {
            screen: scene.screen
        }
    }

    TestCase {
        property var widget

        function init() {
            Settings.data.general.avatarImage = "";
            Settings.data.bar.position = "top";
            Settings.data.audio.visualizerType = "linear";
            Settings.dataChanged();
            MediaService.isPlaying = true;
            HostService.displayName = "Fixture User";
            PanelService.events = [];
        }

        function test_visualizer_state_sizing_frames() {
            widget = createTemporaryObject(visualizerFactory, scene, {
                "screen": fixtureScreen,
                "widgetId": "AudioVisualizer",
                "widgetSettings": {
                    "width": 120,
                    "hideWhenIdle": true,
                    "colorName": "primary"
                }
            });
            verify(widget !== null);
            const loader = widget.children.find(child => {
                return child.sourceComponent !== undefined;
            });
            for (const type of ["linear", "mirrored", "wave"]) {
                Settings.data.audio.visualizerType = type;
                Settings.dataChanged();
                tryCompare(loader, "status", Loader.Ready);
                compare(loader.item.fillColor, NColor.mPrimary);
                CavaService.values = [0.8, 0, 0.4, 1];
                compare(loader.item.values, [0.8, 0, 0.4, 1]);
                Settings.data.bar.position = "left";
                Settings.dataChanged();
                tryCompare(loader.item, "vertical", true);
                tryCompare(widget, "implicitWidth", 40);
                tryCompare(widget, "implicitHeight", 120);
                Settings.data.bar.position = "top";
                Settings.dataChanged();
                tryCompare(loader.item, "vertical", false);
                tryCompare(widget, "implicitWidth", 120);
                tryCompare(widget, "implicitHeight", 40);
            }
            MediaService.isPlaying = false;
            compare(widget.visible, false);
            compare(loader.active, false);
            tryCompare(widget, "implicitWidth", 0);
            tryCompare(widget, "implicitHeight", 0);
            compare(loader.item, null);
            widget.widgetSettings = {
                "width": 160,
                "hideWhenIdle": false,
                "colorName": "error"
            };
            tryCompare(loader, "status", Loader.Ready);
            compare(loader.item.fillColor, NColor.mError);
            tryCompare(widget, "implicitWidth", 160);
            Settings.data.audio.visualizerType = "none";
            Settings.dataChanged();
            compare(widget.visible, false);
            tryCompare(widget, "implicitWidth", 0);
        }

        function test_visualizer_instance_ownership_and_disposal() {
            const first = createTemporaryObject(visualizerFactory, scene, {
                "screen": fixtureScreen,
                "widgetId": "AudioVisualizer",
                "widgetSettings": {
                    "width": 100,
                    "hideWhenIdle": false,
                    "colorName": "primary"
                }
            });
            const second = createTemporaryObject(visualizerFactory, scene, {
                "screen": fixtureScreen,
                "widgetId": "AudioVisualizer",
                "widgetSettings": {
                    "width": 180,
                    "hideWhenIdle": false,
                    "colorName": "error"
                }
            });
            const firstLoader = first.children.find(child => {
                return child.sourceComponent !== undefined;
            });
            const secondLoader = second.children.find(child => {
                return child.sourceComponent !== undefined;
            });
            for (const type of ["linear", "mirrored", "wave"]) {
                Settings.data.audio.visualizerType = type;
                Settings.dataChanged();
                tryCompare(firstLoader, "status", Loader.Ready);
                tryCompare(secondLoader, "status", Loader.Ready);
                compare(firstLoader.item.fillColor, NColor.mPrimary);
                compare(secondLoader.item.fillColor, NColor.mError);
                tryCompare(first, "implicitWidth", 100);
                tryCompare(second, "implicitWidth", 180);
            }
            first.destroy();
            wait(20);
            second.widgetSettings = {
                "width": 200,
                "hideWhenIdle": false,
                "colorName": "onSurface"
            };
            compare(secondLoader.item.fillColor, NColor.mOnSurface);
            tryCompare(second, "implicitWidth", 200);
        }

        function test_visualizer_interaction_routes() {
            widget = createTemporaryObject(visualizerFactory, scene, {
                "screen": fixtureScreen,
                "widgetId": "AudioVisualizer",
                "section": "left",
                "sectionWidgetIndex": 0,
                "widgetSettings": {
                    "width": 120,
                    "hideWhenIdle": false,
                    "colorName": "primary"
                }
            });
            tryCompare(widget, "implicitWidth", 120);
            mouseClick(widget, 60, 20, Qt.LeftButton);
            compare(Settings.data.audio.visualizerType, "mirrored");
            Settings.dataChanged();
            mouseClick(widget, 60, 20, Qt.RightButton);
            compare(PanelService.lastScreen, fixtureScreen);
            const menu = PanelService.lastMenu;
            verify(menu !== null);
            menu.triggered("cycle-visualizer");
            compare(Settings.data.audio.visualizerType, "wave");
            menu.triggered("widget-settings");
            compare(BarService.settingsArgs, [fixtureScreen, "left", 0, "AudioVisualizer", widget.widgetSettings]);
        }

        function test_profile_layout_uptime_and_actions() {
            widget = createTemporaryObject(profileFactory, scene, {
                "width": 560,
                "height": 90
            });
            verify(widget !== null);
            wait(30);
            const row = widget.children[0];
            const avatar = row.children[0];
            compare(avatar.width, 50);
            compare(avatar.height, 50);
            compare(avatar.radius, 12);
            compare(avatar.showFallback, true);
            const labels = row.children[1];
            compare(labels.children[0].text, "Fixture User");
            HostService.displayName = "Another User";
            compare(labels.children[0].text, "Another User");
            const process = widget.resources.find(resource => {
                return resource.command !== undefined;
            });
            verify(process !== undefined);
            process.stdout.streamFinished();
            compare(widget.uptimeText, "900.5 seconds");
            compare(labels.children[1].text, "Uptime: 900.5 seconds");
            compare(process.running, false);
            widget.updateSystemInfo();
            compare(process.running, true);
            const actions = row.children[2].children.filter(child => {
                return child.icon !== undefined;
            });
            compare(actions.length, 3);
            for (const action of actions) {
                verify(action.width > 0 && action.height > 0);
                verify(action.x >= 0);
            }
            mouseClick(actions[0], 20, 20);
            compare(PanelService.events, ["settingsPanel", "open"]);
            compare(PanelService.panel.requestedTab, 0);
            compare(PanelService.lastScreen, fixtureScreen);
            PanelService.events = [];
            mouseClick(actions[1], 20, 20);
            compare(PanelService.events, ["sessionMenuPanel", "open", "controlCenterPanel", "close"]);
            PanelService.events = [];
            mouseClick(actions[2], 20, 20);
            compare(PanelService.events, ["controlCenterPanel", "close"]);
            widget.width = 650;
            wait(30);
            verify(row.width > 600);
            verify(labels.width > 0);

            const shadowOwner = createTemporaryObject(shadowOwnerFactory, scene);
            verify(shadowOwner !== null);
            const captured = createTemporaryObject(profileFactory, shadowOwner, {
                "width": 560,
                "height": 90
            });
            const second = createTemporaryObject(profileFactory, scene, {
                "screen": secondScreen,
                "width": 560,
                "height": 90,
                "y": 120
            });
            verify(captured !== null);
            verify(second !== null);
            compare(shadowOwner.screen, secondScreen);
            compare(captured.screen, fixtureScreen);
            compare(second.screen, secondScreen);
            wait(30);
            const capturedSettings = captured.children[0].children[2].children.find(child => child.icon === "settings");
            const secondSettings = second.children[0].children[2].children.find(child => child.icon === "settings");
            mouseClick(capturedSettings, 20, 20);
            compare(PanelService.lastScreen, fixtureScreen);
            mouseClick(secondSettings, 20, 20);
            compare(PanelService.lastScreen, secondScreen);
            captured.destroy();
            wait(20);
            mouseClick(secondSettings, 20, 20);
            compare(PanelService.lastScreen, secondScreen);
            const recreated = createTemporaryObject(profileFactory, shadowOwner, {
                "width": 560,
                "height": 90
            });
            verify(recreated !== null);
            compare(recreated.screen, fixtureScreen);
            wait(30);
            const recreatedSettings = recreated.children[0].children[2].children.find(child => child.icon === "settings");
            mouseClick(recreatedSettings, 20, 20);
            compare(PanelService.lastScreen, fixtureScreen);
        }

        name: "VisualizerProfile"
        when: windowShown
    }
}
