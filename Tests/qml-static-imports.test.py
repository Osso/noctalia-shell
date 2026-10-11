#!/usr/bin/env python3
"""Exercise virtual qs imports through the real static-check runner and qmllint."""

from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
QMLLINT = "/usr/lib/qt6/bin/qmllint"


class StaticImportsTest(unittest.TestCase):
    def test_qs_types_and_singletons_resolve_without_hiding_real_warnings(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-static-imports-") as temp:
            root = Path(temp)
            runner = root / "Bin/dev/qml-static-check.sh"
            runner.parent.mkdir(parents=True)
            shutil.copy2(REPO / "Bin/dev/qml-static-check.sh", runner)
            (runner.parent / "qml-static-exclusions.txt").write_text("")
            sources = {
                "Commons/Palette.qml": """pragma Singleton
import QtQuick
QtObject { readonly property int spacing: 8 }
""",
                "Widgets/BaseTile.qml": """import QtQuick
Item { property int count: 3 }
""",
                "Widgets/Nested/Tile.qml": """import qs.Commons
import qs.Widgets
BaseTile { width: Palette.spacing; height: count }
""",
                "Consumer.qml": """import QtQuick
import qs.Commons
import qs.Widgets.Nested
Tile {
    width: Palette.spacing
    property int broken: missingValue
}
""",
            }
            for relative, source in sources.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            baseline_diagnostics = "".join(
                subprocess.run(
                    [QMLLINT, str(root / relative)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stderr
                for relative in sorted(sources)
            )
            scratch = root / "scratch"
            scratch.mkdir()
            result = subprocess.run(
                [str(runner)],
                env=dict(os.environ, TMPDIR=str(scratch)),
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("missingValue", result.stderr)
            self.assertNotIn("Failed to import qs.", result.stderr)
            self.assertNotIn("was not found", result.stderr)
            self.assertNotIn('Member "spacing" not found', result.stderr)
            self.assertNotIn("not declared as singleton", result.stderr)
            before = len(re.findall(r"^Warning:", baseline_diagnostics, re.MULTILINE))
            after = len(re.findall(r"^Warning:", result.stderr, re.MULTILINE))
            self.assertGreater(before, after, result.stderr)
            self.assertGreater(after, 0, "Real diagnostics must remain visible")
            self.assertEqual(list(scratch.iterdir()), [], "Lint tree leaked")
            print(f"fixture warnings: {before} -> {after} (delta {after - before})")
            print(result.stderr, end="")

    def test_relative_javascript_imports_resolve_without_hiding_real_warnings(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-static-js-") as temp:
            root = Path(temp)
            runner = root / "Bin/dev/qml-static-check.sh"
            runner.parent.mkdir(parents=True)
            shutil.copy2(REPO / "Bin/dev/qml-static-check.sh", runner)
            (runner.parent / "qml-static-exclusions.txt").write_text("")
            consumer = root / "Widgets/Consumer.qml"
            consumer.parent.mkdir()
            consumer.write_text(
                "import QtQuick\n"
                'import "Adjacent.js" as Adjacent\n'
                'import "../Helpers/Parent.js" as Parent\n'
                "QtObject {\n"
                "    property int answer: Adjacent.answer() + Parent.answer()\n"
                "    property int broken: missingValue\n"
                "}\n"
            )
            scratch = root / "scratch"
            scratch.mkdir()
            command = [str(runner)]
            environment = dict(os.environ, TMPDIR=str(scratch))
            baseline = subprocess.run(
                command, env=environment, capture_output=True, text=True, timeout=30
            )
            self.assertEqual(baseline.returncode, 0, baseline.stderr)
            before = baseline.stderr.count("[import]")
            self.assertEqual(before, 2, baseline.stderr)
            sources = {
                "Widgets/Adjacent.js": ".pragma library\nfunction answer() { return 8; }\n",
                "Helpers/Parent.js": ".pragma library\nfunction answer() { return 16; }\n",
            }
            for relative, source in sources.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            originals = {
                path: path.read_bytes()
                for path in (consumer, *(root / relative for relative in sources))
            }
            result = subprocess.run(
                command, env=environment, capture_output=True, text=True, timeout=30
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            after = result.stderr.count("[import]")
            print(
                f"JS fixture import warnings: {before} -> {after} (delta {after - before})"
            )
            print(result.stderr, end="")
            self.assertEqual(after, 0, result.stderr)
            warnings = re.findall(r"^Warning:.*$", result.stderr, re.MULTILINE)
            self.assertEqual(len(warnings), 1, result.stderr)
            self.assertIn("[unqualified]", warnings[0])
            self.assertIn("missingValue", result.stderr)
            self.assertEqual(list(scratch.iterdir()), [], "Lint tree leaked")
            for path, original in originals.items():
                self.assertEqual(path.read_bytes(), original, f"Source changed: {path}")

    def test_singleton_imports_are_warning_free_and_refresh_on_next_run(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-static-refresh-") as temp:
            root = Path(temp)
            runner = root / "Bin/dev/qml-static-check.sh"
            runner.parent.mkdir(parents=True)
            shutil.copy2(REPO / "Bin/dev/qml-static-check.sh", runner)
            (runner.parent / "qml-static-exclusions.txt").write_text("")
            palette = root / "Commons/Palette.qml"
            palette.parent.mkdir()
            consumer = root / "Consumer.qml"
            scratch = root / "scratch"
            scratch.mkdir()

            for property_name, value in (("spacing", 8), ("margin", 16)):
                with self.subTest(property_name=property_name):
                    palette.write_text(
                        "pragma Singleton\nimport QtQuick\n"
                        f"QtObject {{ readonly property int {property_name}: {value} }}\n"
                    )
                    consumer.write_text(
                        "import QtQuick\nimport qs.Commons\n"
                        f"Item {{ width: Palette.{property_name} }}\n"
                    )
                    result = subprocess.run(
                        [str(runner)],
                        env=dict(os.environ, TMPDIR=str(scratch)),
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertIn("Checked 2 QML files", result.stdout)
                    self.assertEqual(list(scratch.iterdir()), [], "Lint tree leaked")


if __name__ == "__main__":
    unittest.main()
