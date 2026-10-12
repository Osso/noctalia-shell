import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Services.Compositor
import qs.Services.Keyboard

TestCase {
    id: suite

    property MangoService backend: null
    property int scaleSignals: 0

    function init() {
        FixtureIo.processes = [];
        ToplevelManager.toplevels.values = [];
        Quickshell.commands = [];
        CompositorService.displayScales = {};
        CompositorService.scaleUpdates = 0;
        suite.scaleSignals = 0;
        suite.backend = suite.createTemporaryObject(mangoComponent, suite);
        suite.verify(suite.backend !== null);
    }

    function cleanup() {
        suite.backend.initialized = false;
        suite.compare(Quickshell.commands.length, 0, "No detached compositor commands");
        suite.backend = null;
    }

    function process(args) {
        const key = JSON.stringify(["mmsg"].concat(args));
        return FixtureIo.processes.find(value => {
            return JSON.stringify(value.command) === key;
        });
    }

    function readLines(process, lines) {
        for (const line of lines) {
            process.stdout.read(line);
        }
    }

    function test_stream_window_tags() {
        const first = {
            "title": "Editor",
            "appId": "editor",
            "activated": true,
            "outputs": [
                {
                    "name": "DP-1"
                }
            ],
            "fullscreen": false,
            "maximized": false
        };
        const second = {
            "title": "Browser",
            "appId": "browser",
            "activated": false,
            "outputs": [
                {
                    "name": "HDMI-A-1"
                }
            ],
            "fullscreen": false,
            "maximized": true
        };
        ToplevelManager.toplevels.values = [first, second];
        const initial = suite.process(["-g", "-t"]);
        suite.readLines(initial, ["DP-1 title Editor", "DP-1 appid editor", "DP-1 selmon 1", "DP-1 layout []=", "DP-1 kb_layout English (US)", "DP-1 tag 1 1 2 1", "DP-1 tag 2 2 3 0"]);
        suite.compare(suite.backend.workspaces.count, 0, "Wait for initial process exit");
        initial.exited(0);
        suite.compare(suite.backend.workspaces.count, 2);
        suite.compare(suite.backend.workspaces.get(1).isUrgent, true);
        suite.compare(suite.backend.windows.length, 1, "Unknown window stays hidden");
        suite.compare(suite.backend.windows[0].workspaceId, 1);
        suite.compare(suite.backend.focusedWindowIndex, 0);
        suite.compare(suite.backend.currentLayoutSymbol, "[]=");
        suite.compare(KeyboardLayoutService.currentLayout, "English (US)");
        first.activated = false;
        second.activated = true;
        const stream = suite.process(["-w"]);
        suite.readLines(stream, ["HDMI-A-1 title Browser", "HDMI-A-1 appid browser", "HDMI-A-1 selmon 1"]);
        suite.compare(suite.backend.windows.length, 1, "Incomplete frame stays buffered");
        stream.stdout.read("HDMI-A-1 tags 101 100 001");
        suite.compare(suite.backend.workspaces.count, 5);
        suite.compare(suite.backend.workspaces.get(2).id, 101);
        suite.compare(suite.backend.workspaces.get(2).isUrgent, true);
        suite.compare(suite.backend.workspaces.get(3).isOccupied, false);
        suite.compare(suite.backend.workspaces.get(4).id, 103);
        suite.compare(suite.backend.workspaces.get(4).isActive, true);
        suite.compare(suite.backend.windows.length, 2);
        suite.compare(suite.backend.windows[0].workspaceId, 1, "Remember unfocused tag");
        suite.compare(suite.backend.windows[1].workspaceId, 103, "Output index plus tag");
        suite.compare(suite.backend.windows[1].output, "HDMI-A-1");
        suite.compare(suite.backend.focusedWindowIndex, 1);
        suite.readLines(stream, ["HDMI-A-1 title Browser", "HDMI-A-1 appid browser", "HDMI-A-1 tag 2 1 4 1", "HDMI-A-1 tags 101 010 001"]);
        suite.compare(suite.backend.workspaces.count, 5, "Detailed/binary tags not duplicated");
        suite.compare(suite.backend.windows[1].workspaceId, 102);
        suite.compare(suite.backend.workspaces.get(3).isActive, true);
        suite.compare(suite.backend.workspaces.get(3).isOccupied, true);
        suite.compare(suite.backend.windows[0].workspaceId, 1);
    }

    function test_scales() {
        const query = suite.process(["-g", "-A"]);
        suite.backend.queryDisplayScales();
        suite.verify(query.running);
        suite.readLines(query, ["DP-1 scale_factor 1.25", "HDMI-A-1 scale_factor 2", "ignored line"]);
        suite.compare(CompositorService.scaleUpdates, 0, "Wait for scale query exit");
        query.exited(0);
        suite.compare(CompositorService.scaleUpdates, 1);
        suite.compare(suite.scaleSignals, 1);
        suite.compare(JSON.stringify(CompositorService.displayScales), JSON.stringify({
            "DP-1": {
                "name": "DP-1",
                "scale": 1.25,
                "width": 0,
                "height": 0,
                "x": 0,
                "y": 0
            },
            "HDMI-A-1": {
                "name": "HDMI-A-1",
                "scale": 2,
                "width": 0,
                "height": 0,
                "x": 0,
                "y": 0
            }
        }));
        suite.backend.queryDisplayScales();
        suite.readLines(query, ["DP-1 scale_factor 1.5"]);
        query.exited(0);
        suite.compare(CompositorService.displayScales["DP-1"].scale, 1.5);
        suite.compare(CompositorService.displayScales["HDMI-A-1"].scale, 2);
        suite.compare(suite.scaleSignals, 2);
        suite.compare(CompositorService.scaleUpdates, 2);
    }

    name: "MangoService"
    when: suite.windowShown

    Component {
        id: mangoComponent

        MangoService {}
    }

    Connections {
        function onDisplayScalesChanged() {
            suite.scaleSignals++;
        }

        target: suite.backend
    }
}
