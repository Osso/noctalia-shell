"""Bounded real-qmllint routing for downloader, clipboard and active-window fixtures."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_SCRIPTS = {
    "SchemeDownloaderHarness.qml": "scheme-downloader-runtime.test.py",
    "ClipboardPreviewWarningsHarness.qml": "clipboard-preview-warnings.test.py",
    "ActiveWindowWarningsHarness.qml": "active-window-warnings.test.py",
}
DEPENDENCIES = (
    "Commons",
    "Modules",
    "Services",
    "Widgets",
    "Assets",
    "Shaders",
    "Helpers",
)


class RuntimeFixtureRoutingTest(unittest.TestCase):
    def stage_repository(self, root):
        for directory in DEPENDENCIES:
            shutil.copytree(ROOT / directory, root / directory)
        tests = root / "Tests"
        (tests / "Qml").mkdir(parents=True)
        for script in (
            *HARNESS_SCRIPTS.values(),
            "media-mini-warnings.test.py",
            "bar-widget-metadata-runtime.test.py",
            "file-picker-warnings.test.py",
            "qml_fixture_lint.py",
        ):
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        for harness in HARNESS_SCRIPTS:
            shutil.copy2(ROOT / "Tests/Qml" / harness, tests / "Qml" / harness)
        dependencies = root / "DependencyHarnesses"
        dependencies.mkdir()
        for script, harness in (
            ("scheme-downloader-runtime.test.py", "SchemeDownloaderTransport.qml"),
            ("media-mini-warnings.test.py", "MediaMiniWarningsHarness.qml"),
            ("bar-widget-metadata-runtime.test.py", "BarWidgetMetadataHarness.qml"),
        ):
            shutil.copy2(ROOT / "Tests/Qml" / harness, dependencies / harness)
            copied_script = tests / script
            copied_script.write_text(
                copied_script.read_text().replace(
                    f"Tests/Qml/{harness}", f"DependencyHarnesses/{harness}"
                )
            )
        runner = root / "Bin/dev/qml-static-check.sh"
        runner.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "Bin/dev/qml-static-check.sh", runner)
        (runner.parent / "qml-static-exclusions.txt").write_text("")
        # Dependencies remain readable by runtime staging, but discovery is bounded.
        (root / ".ignore").write_text(
            "".join(f"{directory}/\n" for directory in DEPENDENCIES)
            + "DependencyHarnesses/\n"
        )
        return runner

    def run_checker(self, runner, root):
        result = subprocess.run(
            [str(runner)], cwd=root, capture_output=True, text=True, timeout=90
        )
        print(result.stdout + result.stderr, end="")
        files = [
            file
            for line in result.stdout.splitlines()
            if line.startswith('{"files":')
            for file in json.loads(line)["files"]
        ]
        return result, files

    def test_three_harnesses_are_clean_and_each_counted_once(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-runtime-static-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            result, files = self.run_checker(runner, root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertCountEqual(
                [Path(file["filename"]).name for file in files],
                ["shell.qml", "tst_clipboard_preview.qml", "shell.qml"],
            )
            for file in files:
                self.assertTrue(file["success"], file)
                self.assertEqual(
                    [w for w in file["warnings"] if w["type"] in ("warning", "error")],
                    [],
                )
            self.assertIn("Checked 3 QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)

    def test_genuine_warning_fails_checker_for_each_harness(self):
        for name in HARNESS_SCRIPTS:
            with (
                self.subTest(harness=name),
                tempfile.TemporaryDirectory(prefix="noctalia-runtime-warning-") as temp,
            ):
                root = Path(temp)
                runner = self.stage_repository(root)
                for other in HARNESS_SCRIPTS:
                    if other != name:
                        (root / "Tests/Qml" / other).unlink()
                harness = root / "Tests/Qml" / name
                harness.write_text(
                    harness.read_text().replace(
                        "{",
                        "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                        1,
                    )
                )
                result, files = self.run_checker(runner, root)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(files), 1, result.stdout)
                self.assertTrue(
                    any(
                        w["id"] == "missing-property"
                        and "missingFixtureValue" in w["message"]
                        for w in files[0]["warnings"]
                    ),
                    files[0],
                )
                self.assertNotIn("ok qmlStaticCheck", result.stdout)
                self.assertNotIn("Checked 1 QML files", result.stdout)

    def test_same_basenames_outside_exact_paths_keep_default_diagnostics(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-runtime-default-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            for name in HARNESS_SCRIPTS:
                (root / "Tests/Qml" / name).unlink()
                source = root / "Other" / name
                source.parent.mkdir(exist_ok=True)
                source.write_text(
                    "import QtQuick\nQtObject { property int broken: missingDefaultValue }\n"
                )
            result, files = self.run_checker(runner, root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(files, [])
            self.assertEqual(result.stderr.count("[unqualified]"), 3, result.stderr)
            self.assertIn("missingDefaultValue", result.stderr)
            self.assertIn("Checked 3 QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
