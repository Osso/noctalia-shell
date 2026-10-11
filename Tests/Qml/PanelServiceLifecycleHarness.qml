import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.UI

ShellRoot {
    id: testRoot

    readonly property string initialPanelKey: "launcherPanel-eDP-1"
    property var screenOwner: null
    property int exitCode: 0

    function fail(message) {
        console.error("FAIL PanelServiceLifecycle:", message);
        exitCode = 1;
    }

    function verify(condition, message) {
        if (!condition)
            fail(message);

    }

    function finishAfterDestruction() {
        verify(PanelService.registeredPanels[initialPanelKey] === undefined, "destroyed panel remained registered under its original screen key");
        if (exitCode === 0)
            console.log("PASS PanelServiceLifecycle");

        Qt.exit(exitCode);
    }

    function runLifecycleTest() {
        verify(PanelService.registeredPanels[initialPanelKey] === screenOwner.panel, "SmartPanel did not register under its initial screen key");
        screenOwner.screenName = "unknown";
        verify(screenOwner.panel.objectName === "launcherPanel-unknown", "test did not reproduce the screen-bound objectName change");
        screenOwner.destroy();
        Qt.callLater(finishAfterDestruction);
    }

    // SmartPanel consumes NColor, whose file path requires completed directory setup.
    Timer {
        interval: 10
        running: true
        repeat: true
        onTriggered: {
            if (!Settings.isLoaded)
                return ;

            stop();
            PanelService.registeredPanels = ({
            });
            screenOwner = screenOwnerFactory.createObject(testRoot);
            Qt.callLater(runLifecycleTest);
        }
    }

    Timer {
        interval: 10000
        running: true
        onTriggered: {
            fail("setup timeout waiting for isolated settings bootstrap");
            Qt.exit(exitCode);
        }
    }

    Component {
        id: screenOwnerFactory

        PanelWindow {
            id: owner

            property string screenName: "eDP-1"
            property alias panel: panel

            visible: false
            implicitWidth: 1
            implicitHeight: 1

            SmartPanel {
                id: panel

                objectName: "launcherPanel-" + owner.screenName
            }

        }

    }

}
