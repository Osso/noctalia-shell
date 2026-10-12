pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Panels.Process
import qs.Services.System

Item {
    id: scene
    width: 1000
    height: 1200

    Component {
        id: panelComponent
        ProcessPanel {
            width: 500
            height: 1100
        }
    }

    TestCase {
        id: testCase
        name: "ProcessPanelWarnings"
        when: windowShown
        property var panel

        function descendants(owner, predicate) {
            const pending = [owner];
            const seen = [];
            const found = [];
            while (pending.length) {
                const current = pending.pop();
                if (!current || seen.includes(current))
                    continue;
                seen.push(current);
                if (predicate(current))
                    found.push(current);
                for (const list of [current.children, current.resources]) {
                    if (list) {
                        for (const child of list)
                            pending.push(child);
                    }
                }
            }
            return found;
        }

        function repeater(owner) {
            const matches = descendants(owner.contentItem, child => child.itemAt !== undefined && child.model !== undefined);
            compare(matches.length, 1);
            return matches[0];
        }

        function texts(owner) {
            return descendants(owner, child => child.text !== undefined && child.pointSize !== undefined);
        }

        function clickHeader(label) {
            const labels = texts(panel.contentItem).filter(child => child.text === label);
            const header = labels.find(child => child.parent.children.some(sibling => sibling.cursorShape !== undefined));
            verify(header !== undefined);
            mouseClick(header.parent, header.parent.width / 2, header.parent.height / 2);
        }

        function assertRows(expected) {
            const rows = repeater(panel);
            tryCompare(rows, "count", expected.length);
            for (let i = 0; i < expected.length; i++) {
                const row = rows.itemAt(i);
                compare(row.processPid, expected[i].pid);
                const labels = texts(row);
                verify(labels.some(label => label.text === expected[i].displayName));
                verify(labels.some(label => label.text === expected[i].cpu.toFixed(1) + "%"));
                verify(labels.some(label => label.text === (expected[i].memoryKB / 1024).toFixed(1) + " MB"));
                verify(labels.some(label => label.text === expected[i].pid.toString()));
                tryVerify(() => row.width > 0, 1000, "row layout did not assign width");
                compare(row.height, 32);
                if (i > 0)
                    verify(row.y >= rows.itemAt(i - 1).y + rows.itemAt(i - 1).height);
            }
        }

        function init() {
            ProcessService.requests = [];
            Quickshell.requests = [];
            SystemStatService.polling = [];
            ProcessService.refCount = 0;
            ProcessService.sortBy = "cpu";
            ProcessService.sortDescending = true;
            ProcessService.filter = "";
            ProcessService.source = [
                {
                    pid: 901,
                    command: "firefox",
                    displayName: "Firefox",
                    fullCommand: "firefox --private-window",
                    cpu: 60.5,
                    memoryKB: 1024
                },
                {
                    pid: 902,
                    command: "worker",
                    displayName: "Worker",
                    fullCommand: "worker --jobs 2",
                    cpu: 30.0,
                    memoryKB: 8192
                },
                {
                    pid: 903,
                    command: "idle",
                    displayName: "Idle",
                    fullCommand: "idle --wait",
                    cpu: 10.0,
                    memoryKB: 4096
                },
                {
                    pid: 904,
                    command: "boundary",
                    displayName: "Boundary",
                    fullCommand: "boundary",
                    cpu: 50.0,
                    memoryKB: 2048
                },
                {
                    pid: 905,
                    command: "low-boundary",
                    displayName: "Low boundary",
                    fullCommand: "low-boundary",
                    cpu: 20.0,
                    memoryKB: 3072
                }
            ];
            ProcessService.publish();
            panel = panelComponent.createObject(scene);
            verify(panel !== null);
            panel.open();
            tryVerify(() => panel.contentItem !== null);
            wait(0);
        }

        function cleanup() {
            if (panel.isPanelOpen)
                panel.close();
            panel.destroy();
            wait(0);
            compare(ProcessService.refCount, 0);
            compare(SystemStatService.polling, ["begin:cpu", "begin:memory", "end:cpu", "end:memory"]);
        }

        function test_sort_filter_direction_and_colors() {
            assertRows([ProcessService.source[0], ProcessService.source[3], ProcessService.source[1], ProcessService.source[4], ProcessService.source[2]]);
            const expectedColors = [NColor.mError, NColor.mTertiary, NColor.mTertiary, NColor.mOnSurfaceVariant, NColor.mOnSurfaceVariant];
            for (let i = 0; i < expectedColors.length; i++) {
                const row = repeater(panel).itemAt(i);
                compare(row.processCpuColor, expectedColors[i]);
                compare(texts(row).find(label => label.text === row.processCpu.toFixed(1) + "%").color, expectedColors[i]);
            }
            clickHeader("process.header-memory");
            compare(ProcessService.sortBy, "memory");
            assertRows([ProcessService.source[1], ProcessService.source[2], ProcessService.source[4], ProcessService.source[3], ProcessService.source[0]]);
            const direction = descendants(panel.contentItem, child => child.tooltipText === "process.sort-descending")[0];
            direction.clicked();
            verify(!ProcessService.sortDescending);
            assertRows([ProcessService.source[0], ProcessService.source[3], ProcessService.source[4], ProcessService.source[2], ProcessService.source[1]]);
            clickHeader("CPU");
            assertRows([ProcessService.source[2], ProcessService.source[4], ProcessService.source[1], ProcessService.source[3], ProcessService.source[0]]);
            ProcessService.setFilter("boundary");
            assertRows([ProcessService.source[4], ProcessService.source[3]]);
            ProcessService.setFilter("absent");
            assertRows([]);
            ProcessService.setFilter("");
            assertRows([ProcessService.source[2], ProcessService.source[4], ProcessService.source[1], ProcessService.source[3], ProcessService.source[0]]);
            compare(ProcessService.requests, []);
        }

        function test_selected_row_context_actions_record_only() {
            const menu = descendants(panel.contentItem, child => child.processData !== undefined)[0];
            verify(menu !== undefined);
            const row = repeater(panel).itemAt(2);
            mouseClick(row, row.width / 2, row.height / 2, Qt.RightButton);
            tryCompare(menu, "visible", true);
            compare(menu.processData.pid, 902);
            menu.itemAt(0).triggered();
            menu.itemAt(1).triggered();
            menu.itemAt(3).triggered();
            menu.itemAt(4).triggered();
            compare(ProcessService.requests, [
                {
                    action: "kill",
                    pid: 902
                },
                {
                    action: "force-kill",
                    pid: 902
                }
            ]);
            compare(Quickshell.requests, [["wl-copy", "902"], ["wl-copy", "worker --jobs 2"]]);
            menu.close();
            const anotherRow = repeater(panel).itemAt(0);
            mouseClick(anotherRow, anotherRow.width / 2, anotherRow.height / 2, Qt.RightButton);
            tryCompare(menu, "visible", true);
            compare(menu.processData.pid, 901);
            menu.itemAt(0).triggered();
            compare(ProcessService.requests[2], {
                action: "kill",
                pid: 901
            });
            menu.close();
        }

        function test_large_model_and_replacement() {
            const rows = [];
            for (let i = 0; i < 25; i++)
                rows.push({
                    pid: 1000 + i,
                    command: "job-" + i,
                    displayName: "Job " + i,
                    fullCommand: "job-" + i,
                    cpu: i,
                    memoryKB: (25 - i) * 1024
                });
            ProcessService.source = rows;
            ProcessService.publish();
            assertRows(rows.slice().reverse());
            compare(repeater(panel).itemAt(24).processPid, 1000);
            clickHeader("process.header-memory");
            assertRows(rows);
            ProcessService.setFilter("job-2");
            assertRows([rows[2], rows[20], rows[21], rows[22], rows[23], rows[24]]);
        }

        function test_owner_context_and_loader_recreation() {
            const other = panelComponent.createObject(scene, {
                x: 500
            });
            verify(other !== null);
            other.open();
            tryVerify(() => other.contentItem !== null);
            compare(ProcessService.refCount, 2);
            const close = descendants(other.contentItem, child => child.tooltipText === "tooltips.close")[0];
            close.clicked();
            compare(other.closeCount, 1);
            compare(panel.closeCount, 0);
            verify(panel.contentItem !== null);
            tryCompare(other, "contentItem", null);
            other.open();
            tryVerify(() => other.contentItem !== null);
            compare(repeater(other).count, 5);
            other.close();
            other.destroy();
            wait(0);
            compare(ProcessService.refCount, 1);
            SystemStatService.polling = ["begin:cpu", "begin:memory"];
            const ownClose = descendants(panel.contentItem, child => child.tooltipText === "tooltips.close")[0];
            ownClose.clicked();
            compare(panel.closeCount, 1);
            tryCompare(panel, "contentItem", null);
        }
    }
}
