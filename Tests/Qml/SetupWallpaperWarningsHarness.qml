import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Panels.SetupWizard
import qs.Services.UI

ShellRoot {
    id: test

    property var owned: []
    property var scanStep
    property var scanner
    property int scanPhase: 0
    property int geometryIndex: 0
    property var geometryStep

    function verify(value) {
        if (!value)
            throw new Error("Verification failed");

    }

    function compare(actual, expected) {
        if (JSON.stringify(actual) !== JSON.stringify(expected))
            throw new Error(JSON.stringify(actual) + " != " + JSON.stringify(expected));

    }

    function tryVerify(predicate) {
        verify(predicate());
    }

    function createTemporaryObject(component, owner, properties) {
        const object = component.createObject(window.contentItem, properties || {
        });
        owned.push(object);
        return object;
    }

    function cleanup() {
        for (const object of owned) object.destroy()
        owned = [];
    }

    function startGeometry() {
        init();
        const data = test_selection_geometry_data()[geometryIndex];
        Style.uiScaleRatio = data.scale;
        geometryStep = createTemporaryObject(stepComponent, test, {
            "width": data.width,
            "height": 760
        });
        geometryStep.refreshWallpapers();
        geometryTimer.start();
    }

    function find(item, predicate) {
        if (predicate(item))
            return item;

        for (const child of item.children || []) {
            const found = find(child, predicate);
            if (found)
                return found;

        }
        return null;
    }

    function findResource(item, predicate) {
        for (const resource of item.resources || []) {
            if (predicate(resource))
                return resource;

        }
        for (const child of item.children || []) {
            const found = findResource(child, predicate);
            if (found)
                return found;

        }
        return null;
    }

    function init() {
        Settings.data.wallpaper.directory = "/fixture/gallery";
        Settings.saves = 0;
        WallpaperService.currentWallpaper = "";
        WallpaperService.files = ["/fixture/forest.png", "/fixture/desert.jpg", "/fixture/ocean.webp"];
        WallpaperService.appliedWallpaper = "";
    }

    function test_selection_geometry_data() {
        return [{
            "tag": "480x1",
            "width": 480,
            "scale": 1
        }, {
            "tag": "1000x1",
            "width": 1000,
            "scale": 1
        }, {
            "tag": "480x1.25",
            "width": 480,
            "scale": 1.25
        }, {
            "tag": "1000x1.25",
            "width": 1000,
            "scale": 1.25
        }];
    }

    function test_selection_geometry(data) {
        const step = geometryStep;
        verify(step !== null);
        compare(step.selectedWallpaper, "/fixture/forest.png");
        const preview = find(step, (child) => {
            return child.imagePath !== undefined;
        });
        verify(preview !== null);
        tryVerify(() => {
            return preview.width > 0 && preview.height >= 180;
        });
        compare(preview.width, data.width);
        compare(preview.imagePath, "file:///fixture/forest.png");
        compare(preview.visible, true);
        compare(preview.borderWidth, 2);
        const thumbnail = find(step, (child) => {
            return String(child.source) === "file:///fixture/desert.jpg";
        });
        verify(thumbnail !== null);
        compare(thumbnail.parent.parent.width, 146);
        compare(thumbnail.parent.parent.height, 106);
        const changes = [];
        step.wallpaperChanged.connect((path) => {
            return changes.push(path);
        });
        input.mouseClick(thumbnail.parent.parent);
        compare(step.selectedWallpaper, "/fixture/desert.jpg");
        compare(changes, ["/fixture/desert.jpg"]);
        compare(preview.imagePath, "file:///fixture/desert.jpg");
        step.selectedWallpaper = "";
        compare(preview.visible, false);
        compare(preview.imagePath, "");
        compare(preview.borderWidth, 1);
        step.selectedDirectory = "";
        step.refreshWallpapers();
        compare(step.filteredWallpapers.length, 0);
    }

    function test_directory_signals() {
        const step = createTemporaryObject(stepComponent, test, {
            "width": 480,
            "height": 760
        });
        const input = find(step, (child) => {
            return typeof child.inputEditingFinished === "function";
        });
        const picker = find(step, (child) => {
            return typeof child.accepted === "function";
        });
        verify(input !== null && picker !== null);
        const changes = [];
        step.directoryChanged.connect((path) => {
            return changes.push(path);
        });
        input.text = "/fixture/typed";
        input.inputEditingFinished();
        compare(step.selectedDirectory, "/fixture/typed");
        compare(Settings.data.wallpaper.directory, "/fixture/typed");
        input.buttonClicked();
        compare(picker.opens, 1);
        picker.accepted([]);
        compare(changes, ["/fixture/typed"]);
        picker.accepted(["/fixture/picked"]);
        compare(changes, ["/fixture/typed", "/fixture/picked"]);
        compare(step.selectedDirectory, "/fixture/picked");
    }

    function test_scanner_exit_collection() {
        init();
        scanStep = createTemporaryObject(stepComponent, test, {
            "width": 480,
            "height": 760
        });
        scanStep.selectedDirectory = "";
        scanStep.selectedWallpaper = "";
        scanner = findResource(scanStep, (child) => {
            return child.command !== undefined;
        });
        verify(scanner !== null);
        // Real Process/StdioCollector lifecycle; fixture output, no filesystem scan.
        scanner.command = ["/usr/bin/python3", "-c", "print(' /fixture/a.png \\n\\n/fixture/b.jpg')"];
        scanner.running = true;
        scannerTimer.start();
    }

    function checkScanner() {
        if (scanner.running)
            return ;

        if (scanPhase === 0) {
            compare(scanStep.wallpapersList, ["/fixture/a.png", "/fixture/b.jpg"]);
            compare(scanStep.filteredWallpapers, ["/fixture/a.png", "/fixture/b.jpg"]);
            compare(scanStep.selectedWallpaper, "/fixture/a.png");
            scanStep.selectedWallpaper = "/fixture/chosen.webp";
            scanner.command = ["/usr/bin/python3", "-c", "print('/fixture/c.png')"];
        } else if (scanPhase === 1) {
            compare(scanStep.selectedWallpaper, "/fixture/chosen.webp");
            scanner.command = ["/usr/bin/python3", "-c", "raise SystemExit(2)"];
        } else {
            compare(scanStep.filteredWallpapers, ["/fixture/c.png"]);
            scannerTimer.stop();
            cleanup();
            console.log("PASS setup wallpaper: 7 cases");
            Qt.quit();
            return ;
        }
        scanPhase++;
        scanner.running = true;
    }

    function test_next_back_preserve_selection() {
        const wizard = createTemporaryObject(wizardComponent, test);
        const content = wizard.panelContent.createObject(window.contentItem, {
            "width": 1000,
            "height": 900
        });
        verify(content !== null);
        wizard.opened();
        wizard.currentStep = 1;
        const step = find(content, (child) => {
            return typeof child.refreshWallpapers === "function";
        });
        verify(step !== null);
        step.refreshWallpapers();
        const thumbnail = find(step, (child) => {
            return String(child.source) === "file:///fixture/ocean.webp";
        });
        verify(thumbnail !== null);
        input.wait(100);
        input.mouseClick(thumbnail.parent.parent);
        compare(wizard.selectedWallpaper, "/fixture/ocean.webp");
        compare(WallpaperService.appliedWallpaper, "/fixture/ocean.webp");
        const next = find(content, (child) => {
            return child.text === "Continue →" && typeof child.clicked === "function";
        });
        const back = find(content, (child) => {
            return child.text === "← Back" && typeof child.clicked === "function";
        });
        next.clicked();
        compare(wizard.currentStep, 2);
        back.clicked();
        compare(wizard.currentStep, 1);
        compare(step.selectedWallpaper, "/fixture/ocean.webp");
        compare(wizard.selectedWallpaper, "/fixture/ocean.webp");
        compare(Settings.saves, 0);
        content.destroy();
    }

    Window {
        id: window

        visible: true
        width: 1000
        height: 900
    }

    Timer {
        interval: 100
        running: true
        onTriggered: {
            test.init();
            test.test_directory_signals();
            test.cleanup();
            test.init();
            test.test_next_back_preserve_selection();
            test.cleanup();
            test.startGeometry();
        }
    }

    Timer {
        id: geometryTimer

        interval: 100
        onTriggered: {
            test.test_selection_geometry(test.test_selection_geometry_data()[test.geometryIndex]);
            test.cleanup();
            test.geometryIndex++;
            if (test.geometryIndex < 4)
                test.startGeometry();
            else
                test.test_scanner_exit_collection();
        }
    }

    Timer {
        id: scannerTimer

        interval: 50
        repeat: true
        onTriggered: test.checkScanner()
    }

    Timer {
        interval: 10000
        running: true
        onTriggered: {
            console.error("Setup wallpaper timeout");
            Qt.quit();
        }
    }

    TestCase {
        id: input

        when: false
    }

    Component {
        id: stepComponent

        SetupWallpaperStep {
        }

    }

    Component {
        id: wizardComponent

        SetupWizard {
        }

    }

}
