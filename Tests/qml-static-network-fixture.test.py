"""Bounded real-qmllint regression for the isolated network-service harness."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NetworkFixtureLintTest(unittest.TestCase):
    def stage_repository(self, root):
        service = root / "Services/Networking/NetworkService.qml"
        service.parent.mkdir(parents=True)
        shutil.copy2(ROOT / service.relative_to(root), service)
        tests = root / "Tests"
        tests.mkdir()
        for name in ("network-service-warnings.test.py", "qml_fixture_lint.py"):
            shutil.copy2(ROOT / "Tests" / name, tests / name)
        shutil.copytree(ROOT / "Tests/network-service", tests / "network-service")
        runner = root / "Bin/dev/qml-static-check.sh"
        runner.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "Bin/dev/qml-static-check.sh", runner)
        (runner.parent / "qml-static-exclusions.txt").write_text("")
        # Production service remains available to staging, outside discovery.
        (root / ".ignore").write_text("Services/\n")
        return runner

    def run_checker(self, runner, root):
        result = subprocess.run(
            [str(runner)], cwd=root, capture_output=True, text=True, timeout=60
        )
        print(result.stdout + result.stderr, end="")
        files = [
            file
            for line in result.stdout.splitlines()
            if line.startswith('{"files":')
            for file in json.loads(line)["files"]
        ]
        return result, files

    def test_harness_is_lint_clean_and_counted_once(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-network-static-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            result, files = self.run_checker(runner, root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(files), 1, result.stdout)
            self.assertEqual(Path(files[0]["filename"]).name, "shell.qml")
            self.assertTrue(files[0]["success"], files[0])
            self.assertEqual(
                [w for w in files[0]["warnings"] if w["type"] in ("warning", "error")],
                [],
            )
            self.assertIn("Checked 1 QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)

    def test_injected_genuine_warning_fails_checker(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-network-warning-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            harness = root / "Tests/network-service/shell.qml"
            harness.write_text(
                harness.read_text().replace(
                    "id: test",
                    "id: test\n  property int regressionWarning: Qt.application.missingFixtureValue",
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


if __name__ == "__main__":
    unittest.main()
