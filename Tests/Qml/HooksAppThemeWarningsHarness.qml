import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.Control
import qs.Services.Theming
import qs.Services.UI

TestCase {
    id: testCase

    readonly property string activeScreenName: testCase.Screen.name

    function initTestCase() {
        HooksService.init();
        AppThemeService.init();
    }

    function init() {
        Settings.data.colorSchemes.darkMode = false;
        Settings.data.colorSchemes.useWallpaperColors = false;
        Settings.data.colorSchemes.predefinedScheme = "fixture-day";
        Settings.data.hooks = {
            "enabled": true,
            "wallpaperChange": "wall $1 $2 $1",
            "darkModeChange": "dark $1"
        };
        WallpaperService.currentWallpaper = "/fixture/a.png";
        ColorSchemeService.pending = null;
        Quickshell.rejectCommand = false;
        Recorder.events = [];
        Logger.errors = [];
    }

    function test_darkModeSignalsKeepHookAndDeferredTemplateOrder() {
        Settings.data.colorSchemes.darkMode = true;
        compare(Recorder.events, [["hook", ["sh", "-c", "dark true"]], ["applyScheme", "fixture-day"]]);
        ColorSchemeService.deliver();
        compare(Recorder.events[2], ["schemeTemplates",
            {
                "name": "fixture-day",
                "primary": "#123456"
            },
            "dark"]);
        Recorder.events = [];
        Settings.data.colorSchemes.darkMode = false;
        compare(Recorder.events, [["hook", ["sh", "-c", "dark false"]], ["applyScheme", "fixture-day"]]);
        ColorSchemeService.deliver();
        compare(Recorder.events[2], ["schemeTemplates",
            {
                "name": "fixture-day",
                "primary": "#123456"
            },
            "light"]);
        compare(Logger.errors, []);
    }

    function test_wallpaperSignalsFilterScreenAndUseCurrentState() {
        Settings.data.colorSchemes.useWallpaperColors = true;
        WallpaperService.wallpaperChanged("TEST-B", "/fixture/b.png");
        compare(Recorder.events, [["hook", ["sh", "-c", "wall /fixture/b.png TEST-B /fixture/b.png"]]]);
        Recorder.events = [];
        WallpaperService.wallpaperChanged(testCase.activeScreenName, "/fixture/a.png");
        compare(Recorder.events, [["hook", ["sh", "-c", "wall /fixture/a.png " + testCase.activeScreenName + " /fixture/a.png"]], ["readWallpaper", testCase.activeScreenName], ["wallpaperTemplates", "/fixture/a.png", "light"]]);
        Recorder.events = [];
        Settings.data.colorSchemes.darkMode = true;
        compare(Recorder.events, [["hook", ["sh", "-c", "dark true"]], ["readWallpaper", testCase.activeScreenName], ["wallpaperTemplates", "/fixture/a.png", "dark"]]);
        compare(Logger.errors, []);
    }

    function test_disabledMissingAndBlankHooksDoNotDispatch() {
        const hooks = [null,
            {
                "enabled": false,
                "wallpaperChange": "bad",
                "darkModeChange": "bad"
            },
            {
                "enabled": true,
                "wallpaperChange": "",
                "darkModeChange": ""
            }
        ];
        for (const config of hooks) {
            Settings.data.hooks = config;
            HooksService.executeWallpaperHook("/fixture/a.png", testCase.activeScreenName);
            HooksService.executeDarkModeHook(true);
            WallpaperService.wallpaperChanged(testCase.activeScreenName, "/fixture/a.png");
        }
        compare(Recorder.events, []);
        compare(Logger.errors, []);
    }

    function test_missingWallpaperDoesNotApplyTemplates() {
        Settings.data.colorSchemes.useWallpaperColors = true;
        WallpaperService.currentWallpaper = "";
        WallpaperService.wallpaperChanged(testCase.activeScreenName, "/fixture/missing.png");
        compare(Recorder.events, [["hook", ["sh", "-c", "wall /fixture/missing.png " + testCase.activeScreenName + " /fixture/missing.png"]], ["readWallpaper", testCase.activeScreenName]]);
        compare(Logger.errors, [["AppThemeService", "No wallpaper found"]]);
    }

    function test_commandFailureDoesNotBlockTemplateApplication() {
        Quickshell.rejectCommand = true;
        Settings.data.colorSchemes.darkMode = true;
        compare(Recorder.events, [["applyScheme", "fixture-day"]]);
        compare(Logger.errors.length, 1);
        compare(Logger.errors[0][0], "HooksService");
        verify(Logger.errors[0][1].includes("fixture spawn rejected"));
        ColorSchemeService.deliver();
        compare(Recorder.events[1], ["schemeTemplates",
            {
                "name": "fixture-day",
                "primary": "#123456"
            },
            "dark"]);
    }

    name: "HooksAppThemeOwners"
}
