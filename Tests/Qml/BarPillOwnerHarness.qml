import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras

Item {
    id: scene
    width: 800
    height: 600

    ShellScreen {
        id: firstScreen
        name: "first"
    }
    ShellScreen {
        id: secondScreen
        name: "second"
    }
    Component {
        id: factory
        BarPill {}
    }

    TestCase {
        name: "BarPillOwners"
        when: windowShown

        function descendants(item) {
            let result = [];
            for (const child of item.children)
                result = result.concat([child], descendants(child));
            return result;
        }

        function loaded(widget) {
            return widget.children[0].item;
        }

        function findLabel(widget, text) {
            return descendants(loaded(widget)).filter(child => child.text === text)[0];
        }

        function test_orientation_layout_and_owner_reactivity() {
            Settings.data.bar.position = "top";
            Settings.dataChanged();
            const first = createTemporaryObject(factory, scene, {
                screen: firstScreen,
                text: "17",
                suffix: "%",
                icon: "battery",
                forceOpen: true
            });
            const second = createTemporaryObject(factory, scene, {
                screen: secondScreen,
                text: "82",
                suffix: "W",
                icon: "volume",
                forceOpen: true,
                x: 300
            });
            verify(first !== null);
            verify(second !== null);
            for (const position of ["top", "left", "bottom", "right", "top"]) {
                Settings.data.bar.position = position;
                Settings.dataChanged();
                wait(180);
                const vertical = position === "left" || position === "right";
                compare(first.isVerticalBar, vertical);
                compare(second.isVerticalBar, vertical);
                compare(loaded(first).screen, firstScreen);
                compare(loaded(second).screen, secondScreen);
                verify(findLabel(first, "17%") !== undefined);
                verify(findLabel(second, "82W") !== undefined);
                compare(first.width, loaded(first).width);
                compare(first.height, loaded(first).height);
                compare(second.width, loaded(second).width);
                compare(second.height, loaded(second).height);
                compare(vertical ? first.width : first.height, 40);
                verify((vertical ? first.height : first.width) > 40);
                first.text = "123456";
                first.suffix = "ms";
                first.customTextIconColor = "#abcdef";
                first.density = "compact";
                wait(180);
                const changed = findLabel(first, "123456ms");
                verify(changed !== undefined);
                compare(changed.color, Qt.color("#abcdef"));
                verify(findLabel(second, "82W") !== undefined);
                compare(second.text, "82");
                compare(second.density, "");
                first.screen = secondScreen;
                compare(loaded(first).screen, secondScreen);
                first.screen = firstScreen;
                first.text = "17";
                first.suffix = "%";
            }
            first.forceOpen = false;
            first.hide();
            wait(180);
            compare(first.width, 40);
            compare(first.height, 40);
            verify(findLabel(second, "82W").visible);
            first.show();
            wait(180);
            verify(findLabel(first, "17%").visible);
            first.hide();
            wait(180);
            first.showDelayed();
            wait(30);
            compare(loaded(first).showPill, false);
            tryCompare(loaded(first), "showPill", true, 500);
        }
    }
}
