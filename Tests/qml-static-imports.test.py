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
            self.assertNotIn("not declared as singleton", result.stderr)
            self.assertNotIn('Member "spacing" not found', result.stderr)
            before = len(re.findall(r"^Warning:", baseline_diagnostics, re.MULTILINE))
            after = len(re.findall(r"^Warning:", result.stderr, re.MULTILINE))
            self.assertGreater(before, after, result.stderr)
            self.assertGreater(after, 0, "Real diagnostics must remain visible")
            self.assertEqual(list(scratch.iterdir()), [], "Lint tree leaked")
            print(f"fixture warnings: {before} -> {after} (delta {after - before})")
            print(result.stderr, end="")


if __name__ == "__main__":
    unittest.main()
