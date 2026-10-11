"""Bounded real-qmllint coverage for metadata and grouped-taskbar fixtures."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_SCRIPTS = {
    "BarWidgetMetadataHarness.qml": "bar-widget-metadata-runtime.test.py",
    "TaskbarGroupedHarness.qml": "taskbar-grouped-warnings.test.py",
}


class BarFixtureLintTest(unittest.TestCase):
    def stage_repository(self, root):
        directories = ("Commons", "Modules", "Services", "Widgets", "Assets", "Shaders")
        for directory in directories:
            shutil.copytree(ROOT / directory, root / directory)
        tests = root / "Tests"
        (tests / "Qml").mkdir(parents=True)
        for script in (
            *HARNESS_SCRIPTS.values(),
            "media-mini-warnings.test.py",
            "workspace-runtime.test.py",
            "qml_fixture_lint.py",
        ):
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        for harness in HARNESS_SCRIPTS:
            shutil.copy2(ROOT / "Tests/Qml" / harness, tests / "Qml" / harness)
        dependencies = root / "DependencyHarnesses"
        dependencies.mkdir()
        for script, harness in (
            ("media-mini-warnings.test.py", "MediaMiniWarningsHarness.qml"),
            ("workspace-runtime.test.py", "WorkspaceHarness.qml"),
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
        # Dependency harnesses remain readable by staging, but only the two
        # requested harnesses enter static discovery in this bounded test.
        (root / ".ignore").write_text(
            "".join(f"{directory}/\n" for directory in directories)
            + "DependencyHarnesses/\n"
        )
        return runner

    def run_checker(self, runner, root):
        result = subprocess.run(
            [str(runner)],
            cwd=root,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            timeout=90,
        )
        print(result.stdout + result.stderr, end="")
        return result

    def test_two_harnesses_are_checked_once_without_warnings(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-bar-fixture-static-") as temp:
            root = Path(temp)
            result = self.run_checker(self.stage_repository(root), root)
            self.assertEqual(result.returncode, 0, result.stderr)
            files = [
                file
                for line in result.stdout.splitlines()
                if line.startswith('{"files":')
                for file in json.loads(line)["files"]
            ]
            self.assertEqual(len(files), 2, result.stdout)
            self.assertCountEqual(
                [Path(file["filename"]).name for file in files],
                ["shell.qml", "tst_taskbar_grouped.qml"],
            )
            self.assertEqual(
                [
                    warning
                    for file in files
                    for warning in file["warnings"]
                    if warning["type"] in ("warning", "error")
                ],
                [],
            )
            self.assertIn("Checked 2 QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)

    def test_injected_warning_fails_static_checker_for_each_harness(self):
        for name in HARNESS_SCRIPTS:
            with (
                self.subTest(harness=name),
                tempfile.TemporaryDirectory(
                    prefix="noctalia-bar-fixture-warning-"
                ) as temp,
            ):
                root = Path(temp)
                runner = self.stage_repository(root)
                harness = root / "Tests/Qml" / name
                harness.write_text(
                    harness.read_text().replace(
                        "{",
                        "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                        1,
                    )
                )
                for other in HARNESS_SCRIPTS:
                    if other != name:
                        (root / "Tests/Qml" / other).unlink()
                result = self.run_checker(runner, root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("missingFixtureValue", result.stdout)
                self.assertIn('"id":"missing-property"', result.stdout)
                self.assertNotIn("ok qmlStaticCheck", result.stdout)


if __name__ == "__main__":
    unittest.main()
