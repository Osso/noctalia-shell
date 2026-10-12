import QtQuick
import QtTest
import qs.Modules.Panels.Launcher
import qs.Services.Keyboard
import qs.Commons

Item {
    width: 526
    height: 600

    Component {
        id: launcherComponent
        Launcher {}
    }

    Component {
        id: searchPluginComponent
        Item {
            property var launcher
            property string name: "Fixture"
            property bool handleSearch: true
            property var rows: []
            function getResults(text) {
                return rows.filter(row => row.name.toLowerCase().includes(text.toLowerCase()));
            }
        }
    }

    TestCase {
        id: tests
        name: "LauncherWarnings"
        when: windowShown
        property var launcher
        property var plugin

        function init() {
            Settings.data.appLauncher.viewMode = "list";
            ClipboardService.cache = ({});
            ClipboardService.revision = 0;
            launcher = createTemporaryObject(launcherComponent, tests.parent);
            verify(launcher !== null);
            plugin = createTemporaryObject(searchPluginComponent, tests.parent);
            launcher.registerPlugin(plugin);
            launcher.opened();
            tryCompare(launcher, "resultsReady", true);
        }

        function rows() {
            return [
                {
                    name: "Alpha",
                    clipboardId: "alpha",
                    isImage: true,
                    mime: "image/png"
                },
                {
                    name: "Beta",
                    clipboardId: "beta",
                    isImage: true,
                    mime: "image/png"
                },
                {
                    name: "Gamma",
                    clipboardId: "gamma",
                    isImage: true,
                    mime: "image/png"
                }
            ];
        }

        function view(name) {
            const found = findChild(launcher, name);
            verify(found !== null, name);
            return found;
        }

        function test_async_rebuild_filter_current_selection() {
            plugin.rows = rows();
            launcher.updateResults();
            const list = view("resultsList");
            tryCompare(list, "count", 3);
            launcher.onEndPressed();
            compare(launcher.selectedIndex, 2);
            tryCompare(list, "currentIndex", 2);
            Qt.callLater(() => {
                tests.plugin.rows = [
                    {
                        name: "Delta"
                    },
                    {
                        name: "Beta two"
                    }
                ];
                tests.launcher.updateResults();
            });
            tryCompare(list, "count", 2);
            compare(launcher.results[0].name, "Delta");
            compare(launcher.selectedIndex, 0);
            tryCompare(list, "currentIndex", 0);
            launcher.setSearchText("beta");
            tryCompare(list, "count", 1);
            compare(launcher.results[0].name, "Beta two");
            launcher.setSearchText("absent");
            tryCompare(list, "count", 0);
            launcher.onDownPressed();
            launcher.onEndPressed();
            compare(launcher.selectedIndex, 0);
            launcher.setSearchText("");
            tryCompare(list, "count", 2);
            compare(launcher.selectedIndex, 0);
        }

        function test_keyboard_category_sibling_scopes() {
            const apps = view("ApplicationsPlugin");
            const emoji = view("EmojiPlugin");
            apps.selectedCategory = "games";
            emoji.selectedCategory = "faces";
            const input = view("searchInput");
            input.forceActiveFocus();
            keyClick(Qt.Key_Tab);
            compare(apps.selectedCategory, "all");
            compare(emoji.selectedCategory, "faces");
            launcher.activePlugin = emoji;
            keyClick(Qt.Key_Tab);
            compare(emoji.selectedCategory, "nature");
            compare(apps.selectedCategory, "all");
            keyClick(Qt.Key_Tab);
            compare(emoji.selectedCategory, "recent");
            launcher.activePlugin = plugin;
            plugin.rows = rows();
            launcher.updateResults();
            launcher.activePlugin = plugin;
            keyClick(Qt.Key_Tab);
            compare(launcher.selectedIndex, 1);
            keyClick(Qt.Key_Backtab);
            compare(launcher.selectedIndex, 0);
            launcher.onUpPressed();
            compare(launcher.selectedIndex, 2);
            launcher.onDownPressed();
            compare(launcher.selectedIndex, 0);
        }

        function test_grid_keyboard_deferred_selection() {
            Settings.data.appLauncher.viewMode = "grid";
            // Settings.data is a JS object; assign to notify the production binding.
            Settings.data = JSON.parse(JSON.stringify(Settings.data));
            plugin.rows = rows().concat([
                {
                    name: "Delta"
                },
                {
                    name: "Epsilon"
                },
                {
                    name: "Zeta"
                }
            ]);
            launcher.updateResults();
            const grid = view("resultsGrid");
            tryCompare(grid, "count", 6);
            launcher.gridColumns = 5;
            launcher.selectedIndex = 4;
            launcher.onDownPressed();
            tryCompare(launcher, "selectedIndex", 5);
            launcher.onUpPressed();
            tryCompare(launcher, "selectedIndex", 0);
            const input = view("searchInput");
            input.forceActiveFocus();
            keyClick(Qt.Key_Left);
            compare(launcher.selectedIndex, 5);
            keyClick(Qt.Key_Right);
            compare(launcher.selectedIndex, 0);
        }

        function test_list_revision_without_model_change() {
            plugin.rows = rows();
            launcher.updateResults();
            const list = view("resultsList");
            tryCompare(list, "count", 3);
            tryVerify(() => list.itemAtIndex(0) !== null);
            const image = findChild(list.itemAtIndex(0), "imagePreview");
            verify(image !== null);
            compare(image.imagePath, "");
            launcher.selectedIndex = 1;
            Qt.callLater(() => ClipboardService.publish("alpha", "cache:first"));
            tryCompare(image, "imagePath", "cache:first");
            Qt.callLater(() => ClipboardService.publish("alpha", "cache:second"));
            tryCompare(image, "imagePath", "cache:second");
            compare(list.count, 3);
            compare(launcher.selectedIndex, 1);
            // A model replacement creates new delegates that must use the new ID.
            plugin.rows = [
                {
                    name: "Beta",
                    clipboardId: "beta",
                    isImage: true
                }
            ];
            launcher.updateResults();
            tryCompare(list, "count", 1);
            tryVerify(() => list.itemAtIndex(0) !== null);
            const replacement = findChild(list.itemAtIndex(0), "imagePreview");
            verify(replacement !== null);
            compare(replacement.imagePath, "");
            Qt.callLater(() => ClipboardService.publish("beta", "cache:beta"));
            tryCompare(replacement, "imagePath", "cache:beta");
            compare(launcher.selectedIndex, 0);
        }

        function test_grid_revision_without_model_change() {
            Settings.data.appLauncher.viewMode = "grid";
            Settings.data = JSON.parse(JSON.stringify(Settings.data));
            plugin.rows = rows();
            launcher.updateResults();
            const grid = view("resultsGrid");
            tryCompare(grid, "count", 3);
            tryVerify(() => grid.itemAtIndex(0) !== null);
            const image = findChild(grid.itemAtIndex(0), "imagePreview");
            verify(image !== null);
            compare(image.imagePath, "");
            launcher.selectedIndex = 2;
            Qt.callLater(() => ClipboardService.publish("alpha", "cache:grid-first"));
            tryCompare(image, "imagePath", "cache:grid-first");
            Qt.callLater(() => ClipboardService.publish("alpha", "cache:grid-second"));
            tryCompare(image, "imagePath", "cache:grid-second");
            compare(grid.count, 3);
            compare(launcher.selectedIndex, 2);
        }
    }
}
