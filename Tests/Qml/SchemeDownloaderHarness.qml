import QtQuick
import Quickshell
import qs.Commons
import qs.Downloader
import qs.Services.Theming
import qs.Services.UI

ShellRoot {
    id: harness

    property int phase: 0
    property int ticks: 0
    property int recursiveCompletions: 0
    property var recursiveFiles: []
    readonly property var scheme: ({
            "name": "aurora",
            "path": "aurora",
            "url": "synthetic:aurora"
        })

    function require(condition, message) {
        if (!condition)
            throw new Error(message);
    }

    function testCacheAndColors() {
        ShellState.cache = {
            "schemes": [scheme],
            "timestamp": Time.timestamp
        };
        downloader.loadSchemesFromCache();
        require(downloader.hasInitialData && downloader.availableSchemes[0].name === "aurora", "fresh cache");
        require(Transport.requests.length === 0, "hidden downloader fetched colors");
        downloader.fetchSchemeColors(scheme);
        Transport.respond(0, 200, {
            "dark": {
                "mPrimary": "#123456"
            },
            "light": {
                "mPrimary": "#abcdef"
            }
        });
        require(downloader.cacheVersion === 1, "color cache version");
        require(downloader.getSchemeColor("aurora", "mPrimary") === "#123456", "dark variant");
        Settings.data.colorSchemes.darkMode = false;
        require(downloader.getSchemeColor("aurora", "mPrimary") === "#abcdef", "light variant");
        require(downloader.getSchemeColor("missing", "mPrimary").toString() === NColor.mPrimary.toString(), "uncached color");
        downloader.fetchSchemeColors(scheme);
        require(Transport.requests.length === 1, "cached colors fetched twice");
        Transport.reset();
        downloader.fetchAvailableSchemesFromAPI();
        require(downloader.fetching, "fetch state");
        downloader.fetchAvailableSchemesFromAPI();
        require(Transport.requests.length === 1, "concurrent fetch");
        Transport.respond(0, 200, [
            {
                "type": "file",
                "name": "README"
            },
            {
                "type": "dir",
                "name": "aurora",
                "path": "aurora",
                "url": "synthetic:aurora"
            }
        ]);
        require(!downloader.fetching && downloader.availableSchemes.length === 1, "directory filtering");
        require(ShellState.cache.schemes[0].name === "aurora", "saved metadata");
        downloader.lastApiFetchTime = 0;
        downloader.fetchAvailableSchemesFromAPI();
        Transport.respond(1, 403, {});
        require(downloader.downloadError.includes("rate-limit") && downloader.availableSchemes.length === 1, "rate-limit cache");
        downloader.lastApiFetchTime = 0;
        downloader.fetchAvailableSchemesFromAPI();
        Transport.respond(2, 200, "{");
        require(!downloader.fetching && downloader.downloadError.includes("parse-failed"), "malformed metadata");
    }

    function testRecursiveClosure() {
        Transport.reset();
        recursiveFiles = [];
        recursiveCompletions = 0;
        downloader.getAllFilesRecursive(scheme, [
            {
                "type": "dir",
                "path": "aurora/one",
                "url": "synthetic:one"
            },
            {
                "type": "dir",
                "path": "aurora/two",
                "url": "synthetic:two"
            }
        ], recursiveFiles, function () {
            harness.recursiveCompletions++;
        });
        require(Transport.requests.length === 2, "two directory requests pending");
        const firstFile = {
            "path": "aurora/one/a",
            "url": "file:a",
            "name": "a"
        };
        const secondFile = {
            "path": "aurora/two/b",
            "url": "file:b",
            "name": "b"
        };
        // Finish the last-created request first, while its sibling is still pending.
        Transport.respond(1, 200, [
            {
                "type": "file",
                "path": secondFile.path,
                "name": secondFile.name,
                "download_url": secondFile.url
            }
        ]);
        require(JSON.stringify(recursiveFiles) === JSON.stringify([secondFile]), "second directory file exactly once");
        require(recursiveCompletions === 0, "completion before pending sibling response");
        Transport.respond(0, 200, [
            {
                "type": "file",
                "path": firstFile.path,
                "name": firstFile.name,
                "download_url": firstFile.url
            }
        ]);
        require(JSON.stringify(recursiveFiles) === JSON.stringify([secondFile, firstFile]), "both directory files exactly once, without duplicated response");
        require(recursiveCompletions === 1, "one completion after both directory responses");
        console.log("SCHEME_DOWNLOADER_REVERSE_DIRECTORY_PASS");
        Transport.reset();
        recursiveCompletions = 0;
        recursiveFiles = [];
        downloader.getAllFilesRecursive(scheme, [
            {
                "type": "file",
                "path": "aurora/aurora.json",
                "name": "aurora.json",
                "download_url": Qt.resolvedUrl("fixtures/scheme.json").toString()
            },
            {
                "type": "dir",
                "path": "aurora/nested",
                "url": "synthetic:nested"
            }
        ], recursiveFiles, function () {
            harness.recursiveCompletions++;
        });
        Transport.respond(0, 200, [
            {
                "type": "file",
                "path": "aurora/nested/terminal.txt",
                "name": "terminal.txt",
                "download_url": Qt.resolvedUrl("fixtures/terminal.txt").toString()
            }
        ]);
        require(recursiveCompletions === 1 && recursiveFiles.length === 2, "single-directory completion");
    }

    function testTreeResolution() {
        Transport.reset();
        downloader.cachedBranch = "";
        downloader.cachedBranchSha = "";
        downloader.downloadScheme(scheme);
        require(downloader.downloading && downloader.downloadingScheme === "aurora", "download state");
        Transport.respond(0, 200, {
            "default_branch": "synthetic"
        });
        require(Transport.requests[1].url.endsWith("/heads/synthetic"), "default branch closure");
        Transport.respond(1, 200, {
            "object": {
                "sha": "fixture-sha"
            }
        });
        require(downloader.cachedBranchSha === "fixture-sha", "SHA cache");
        Transport.respond(2, 200, {
            "tree": [
                {
                    "type": "blob",
                    "path": "elsewhere/ignored.json"
                },
                {
                    "type": "tree",
                    "path": "aurora/nested"
                }
            ]
        });
        require(!downloader.downloading && downloader.downloadError.includes("no-files"), "tree filtering");
        downloader.getSchemeFilesDirect(scheme);
        Transport.respond(3, 200, {});
        require(downloader.downloadError.includes("invalid-response"), "invalid direct response");
        downloader.getSchemeTreeWithSha(scheme, "synthetic", "fixture-sha");
        Transport.respond(4, 200, "{");
        require(downloader.downloadError.includes("parse-failed"), "malformed tree");
    }

    function startFileDownload() {
        downloader.downloading = true;
        downloader.downloadingScheme = "aurora";
        downloader.downloadSchemeFiles("aurora", recursiveFiles);
        require(downloader.downloading, "process must finish asynchronously");
    }

    function testInstalledPaths() {
        ColorSchemeService.schemes = ["/builtin/preinstalled/preinstalled.json", ColorSchemeService.downloadedSchemesDirectory + "/aurora/aurora.json"];
        require(downloader.isSchemeInstalled("aurora") && downloader.isSchemeDownloaded("aurora"), "downloaded path");
        require(downloader.isSchemeInstalled("preinstalled") && !downloader.isSchemeDownloaded("preinstalled"), "preinstalled path");
        require(!downloader.isSchemeInstalled("missing"), "unknown path");
    }

    SchemeDownloader {
        id: downloader

        visible: false
    }

    Timer {
        interval: 20
        running: true
        repeat: true
        onTriggered: {
            try {
                harness.ticks++;
                harness.require(harness.ticks < 500, "process timeout");
                if (harness.phase === 0) {
                    harness.testCacheAndColors();
                    harness.testRecursiveClosure();
                    harness.testTreeResolution();
                    harness.startFileDownload();
                    harness.phase = 1;
                } else if (harness.phase === 1 && !downloader.downloading) {
                    harness.require(ToastService.notices === 1 && ColorSchemeService.reloads === 1, "successful process callback");
                    harness.require(downloader.pendingApplyScheme === "aurora", "pending application");
                    ColorSchemeService.scanning = true;
                    ColorSchemeService.scanning = false;
                    harness.phase = 2;
                } else if (harness.phase === 2 && ColorSchemeService.applied === "aurora") {
                    harness.require(downloader.pendingApplyScheme === "", "pending cleared");
                    harness.testInstalledPaths();
                    downloader.downloading = true;
                    downloader.downloadSchemeFiles("broken", [
                        {
                            "path": "broken/a",
                            "url": "https://forbidden.invalid/a"
                        }
                    ]);
                    harness.phase = 3;
                } else if (harness.phase === 3 && !downloader.downloading) {
                    harness.require(ToastService.errors === 1 && downloader.downloadError.includes("Exit code: 9"), "failed process details");
                    harness.require(downloader.lastStderrOutput === "", "stderr cleared");
                    Settings.data.colorSchemes.predefinedScheme = "delete-me";
                    downloader.deleteScheme("delete-me");
                    harness.phase = 4;
                } else if (harness.phase === 4 && ColorSchemeService.reloads === 2) {
                    harness.require(Settings.data.colorSchemes.predefinedScheme === "Noctalia (default)", "active deletion reset");
                    harness.require(ColorSchemeService.applied === "Noctalia (default)" && ToastService.notices === 2, "delete callbacks");
                    harness.require(!downloader.visible, "popup became visible");
                    console.log("SCHEME_DOWNLOADER_PASS");
                    Qt.quit();
                }
            } catch (error) {
                console.error("SCHEME_DOWNLOADER_FAIL: " + error.message);
                Qt.exit(1);
            }
        }
    }
}
