import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Services.Compositor
import qs.Services.Media
import qs.Services.UI

ShellRoot {
    id: harness

    property var active: null
    property var media: null

    function require(condition, message) {
        if (!condition) {
            console.error("BAR_WIDGET_METADATA_FAIL", message);
            Qt.exit(1);
            throw new Error(message);
        }
    }

    function constructWidget(key, index) {
        const loader = loaderComponent.createObject(offscreen.contentItem, {
            "widgetId": key,
            "widgetScreen": Quickshell.screens[0],
            "widgetProps": {
                "widgetId": key,
                "section": "left",
                "sectionWidgetIndex": index
            }
        });
        require(loader !== null, key + " production Loader created");
        const item = loader.children[0].item;
        require(item.widgetId === key && item.sectionWidgetIndex === index, key + " onLoaded assigned instance settings");
        return item;
    }

    function setWidgets(activeSettings, mediaSettings, position) {
        Settings.data = Object.assign({
        }, Settings.data, {
            "bar": Object.assign({
            }, Settings.data.bar, {
                "position": position,
                "widgets": {
                    "left": [activeSettings, mediaSettings],
                    "center": [],
                    "right": []
                }
            })
        });
    }

    Component {
        id: loaderComponent

        BarWidgetLoader {
        }

    }

    Window {
        id: offscreen

        visible: true // Runner removes desktop connections and forces offscreen.
        width: 480
        height: 120
    }

    Timer {
        property int step: 0

        interval: 100
        running: true
        repeat: true
        onTriggered: {
            running = false;
            switch (step) {
            case 0:
                harness.active = harness.constructWidget("ActiveWindow", 0);
                harness.media = harness.constructWidget("MediaMini", 1);
                harness.require(BarWidgetRegistry.snapshots.length === 2, "both Loader instances completed");
                harness.require(BarWidgetRegistry.widgetMetadata.ActiveWindow.maxWidth === 145 && BarWidgetRegistry.widgetMetadata.MediaMini.maxWidth === 145, "registry constants ready");
                for (const snapshot of BarWidgetRegistry.snapshots) {
                    harness.require(snapshot.widgetId === "", "instance ID still empty during construction");
                    harness.require(snapshot.metadataReady, snapshot.key + " metadata ready before instance ID");
                    harness.require(snapshot.width === 0 && snapshot.height === 0 && !snapshot.visible, snapshot.key + " hidden empty dimensions");
                    harness.require(snapshot.maxWidth === 145 && !snapshot.fixed, snapshot.key + " default width settings");
                }
                MediaService.currentPlayer = {
                };
                harness.setWidgets({
                    "id": "ActiveWindow",
                    "hideMode": "visible",
                    "maxWidth": 210,
                    "useFixedWidth": true,
                    "showIcon": false
                }, {
                    "id": "MediaMini",
                    "hideMode": "visible",
                    "maxWidth": 190,
                    "useFixedWidth": true
                }, "top");
                break;
            case 1:
                harness.require(active.visible && active.implicitWidth === 210 && active.implicitHeight === 32 && !active.showIcon, "late ActiveWindow settings and fixed dimensions");
                harness.require(media.visible && media.implicitWidth === 190 && media.implicitHeight === 32, "late MediaMini settings and fixed dimensions");
                active.widgetId = "different-instance-id";
                media.widgetId = "different-instance-id";
                harness.require(active.maxWidth === 210 && media.maxWidth === 190, "instance ID change preserves per-section user settings");
                CompositorService.focusedWindow = {
                    "title": "Concrete long focused window title",
                    "appId": "fixture"
                };
                MediaService.currentPlayer = {
                };
                MediaService.trackTitle = "Concrete long playing track title";
                harness.setWidgets({
                    "id": "ActiveWindow",
                    "hideMode": "visible",
                    "maxWidth": 90,
                    "useFixedWidth": false
                }, {
                    "id": "MediaMini",
                    "hideMode": "visible",
                    "maxWidth": 85,
                    "useFixedWidth": false
                }, "top");
                break;
            case 2:
                harness.require(active.implicitWidth === 90, "ActiveWindow long title capped at 90");
                harness.require(media.implicitWidth === 85, "MediaMini long title capped at 85");
                harness.setWidgets({
                    "id": "ActiveWindow",
                    "hideMode": "visible"
                }, {
                    "id": "MediaMini",
                    "hideMode": "visible"
                }, "left");
                active.scaling = 0.8;
                media.scaling = 0.8;
                break;
            case 3:
                harness.require(active.implicitWidth === 22 && active.implicitHeight === 22, "ActiveWindow vertical scaling");
                harness.require(media.implicitWidth === 22 && media.implicitHeight === 22, "MediaMini vertical scaling");
                CompositorService.focusedWindow = null;
                MediaService.currentPlayer = null;
                harness.setWidgets({
                    "id": "ActiveWindow",
                    "hideMode": "hidden"
                }, {
                    "id": "MediaMini",
                    "hideMode": "hidden"
                }, "top");
                break;
            case 4:
                harness.require(!active.visible && active.implicitWidth === 0 && active.implicitHeight === 0, "ActiveWindow late hidden setting");
                harness.require(!media.visible && media.implicitWidth === 0 && media.implicitHeight === 0, "MediaMini late hidden setting");
                console.log("BAR_WIDGET_METADATA_PASS");
                Qt.quit();
                break;
            }
            step++;
            running = step < 5;
        }
    }

}
