#!/usr/bin/env python3
"""Changelog qmllint stream boundary: mocked output and native masked children."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "changelog_runner", ROOT / "Tests/changelog-panel-warnings.test.py"
)
OWNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OWNER)

# Exact machine document and trailing stderr notice from the saved final run.
SAVED_JSON = '{"files":[{"filename":"/tmp/noctalia-verify-qml-final-msuvzslb/tmp/noctalia-changelog-q8zcvs38/tst_history.qml","success":true,"warnings":[]}],"revision":6}'
LOCALE_NOTICE = (
    'Detected locale "C" with character encoding "ANSI_X3.4-1968", which is not UTF-8.\n'
    'Qt depends on a UTF-8 locale, and has switched to "C.UTF-8" instead.\n'
    "If this causes problems, reconfigure your locale. See the locale(1) manual\n"
    "for more information.\n"
)


def document(kind=None, success=True):
    warnings = (
        [] if kind is None else [{"type": kind, "message": "concrete diagnostic"}]
    )
    return json.dumps(
        {
            "files": [
                {
                    "filename": "tst_history.qml",
                    "success": success,
                    "warnings": warnings,
                }
            ],
            "revision": 6,
        }
    )


class MockedStreams(unittest.TestCase):
    def invoke(self, stdout, stderr, code=0, injected=False):
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory(prefix="noctalia-changelog-streams-") as tmp:
            directory = Path(tmp)

            def stage(staged):
                (staged / "tst_history.qml").write_text(
                    "import QtQuick\nItem { id: tests }\n"
                )

            def completed(command, **kwargs):
                trace = command[command.index("-o") + 1]
                Path(trace).write_text("")
                return subprocess.CompletedProcess(command, code, stdout, stderr)

            with (
                patch.object(OWNER, "stage_runtime", stage),
                patch.object(subprocess, "run", completed),
                redirect_stdout(self.stdout),
                redirect_stderr(self.stderr),
            ):
                return OWNER.lint_harness(directory, injected)

    def test_saved_final_log_valid_json_and_locale_stderr(self):
        self.assertEqual(self.invoke(SAVED_JSON, LOCALE_NOTICE), 0)
        self.assertIn(SAVED_JSON, self.stdout.getvalue())
        self.assertEqual(self.stderr.getvalue(), LOCALE_NOTICE)
        self.assertNotIn(LOCALE_NOTICE, self.stdout.getvalue())

    def test_semantic_warning_is_rejected_even_with_zero_exit(self):
        self.assertNotEqual(self.invoke(document("warning"), "semantic notice\n"), 0)
        self.assertEqual(self.stderr.getvalue(), "semantic notice\n")

    def test_syntax_error_is_rejected_even_with_zero_exit(self):
        self.assertNotEqual(self.invoke(document("error", False), "syntax error\n"), 0)
        self.assertEqual(self.stderr.getvalue(), "syntax error\n")

    def test_unsuccessful_file_is_rejected_without_diagnostics(self):
        self.assertNotEqual(self.invoke(document(success=False), ""), 0)

    def test_malformed_json_fails_closed_and_preserves_stderr(self):
        for stdout in (
            '{"files":',
            SAVED_JSON + "trailing garbage",
            "notice\n" + SAVED_JSON,
        ):
            with self.subTest(stdout=stdout), self.assertRaises(json.JSONDecodeError):
                self.invoke(stdout, "parser notice\n")
            self.assertEqual(self.stderr.getvalue(), "parser notice\n")

    def test_nonzero_exit_is_preserved_with_clean_json(self):
        self.assertEqual(self.invoke(SAVED_JSON, "fatal tool error\n", 7), 7)
        self.assertEqual(self.stderr.getvalue(), "fatal tool error\n")

    def test_injected_warning_requires_genuine_diagnostic(self):
        self.assertNotEqual(self.invoke(document("warning"), "", 1, True), 0)
        with self.assertRaisesRegex(AssertionError, "injected diagnostic not detected"):
            self.invoke(SAVED_JSON, "", 1, True)

    def test_child_settings_access_remains_rejected(self):
        def completed(command, **kwargs):
            Path(command[command.index("-o") + 1]).write_text('openat("settings.json")')
            return subprocess.CompletedProcess(command, 0, SAVED_JSON, "")

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(subprocess, "run", completed),
        ):
            with self.assertRaisesRegex(AssertionError, "SETTINGS_AUDIT_DENIED"):
                OWNER.run_isolated(Path(tmp), ["qmllint"], "settings-negative")


class NativeStreams(unittest.TestCase):
    def test_native_clean_warning_and_syntax_under_both_locales(self):
        isolated = OWNER.run_isolated
        for locale in ("C", "C.UTF-8"):
            for name, source, rejected in (
                ("clean", "import QtQuick\nItem {}\n", False),
                (
                    "warning",
                    "import QtQuick\nItem { property int value: missingProbe }\n",
                    True,
                ),
                ("syntax", "import QtQuick\nItem { property int value: }\n", True),
            ):
                with (
                    self.subTest(locale=locale, case=name),
                    tempfile.TemporaryDirectory(
                        prefix="noctalia-changelog-native-streams-"
                    ) as tmp,
                ):
                    stdout, stderr = io.StringIO(), io.StringIO()

                    def stage(staged):
                        (staged / "tst_history.qml").write_text(source)

                    reports = []

                    def run(staged, command, label):
                        result = isolated(
                            staged,
                            ["/usr/bin/env", f"LC_ALL={locale}", *command],
                            label,
                        )
                        reports.append(json.loads(result.stdout))
                        return result

                    with (
                        patch.object(OWNER, "stage_runtime", stage),
                        patch.object(OWNER, "run_isolated", run),
                        redirect_stdout(stdout),
                        redirect_stderr(stderr),
                    ):
                        code = OWNER.lint_harness(Path(tmp))
                    self.assertEqual(code != 0, rejected)
                    entry = reports[0]["files"][0]
                    self.assertEqual(entry["success"], not rejected)
                    if name == "warning":
                        self.assertIn(
                            "warning", [item["type"] for item in entry["warnings"]]
                        )
                    if name == "syntax":
                        self.assertTrue(entry["warnings"])
                    self.assertIn(
                        "zero settings attempts; host home/config not mounted",
                        stdout.getvalue(),
                    )
                    if locale == "C":
                        self.assertEqual(stderr.getvalue(), LOCALE_NOTICE)
                    else:
                        self.assertEqual(stderr.getvalue(), "")

    def test_native_malformed_json_and_nonzero_exit_preserve_error_stream(self):
        isolated = OWNER.run_isolated
        for machine, exit_code in (
            (SAVED_JSON + "trailing garbage", 0),
            (SAVED_JSON, 7),
        ):
            with (
                self.subTest(exit_code=exit_code),
                tempfile.TemporaryDirectory(
                    prefix="noctalia-changelog-native-errors-"
                ) as tmp,
            ):
                stdout, stderr = io.StringIO(), io.StringIO()

                def stage(staged):
                    (staged / "tst_history.qml").write_text("import QtQuick\nItem {}\n")

                def run(staged, command, label):
                    emitter = (
                        "import sys; "
                        f"sys.stdout.write({machine!r}); "
                        "sys.stdout.flush(); "
                        "sys.stderr.write('native tool error\\n'); "
                        f"sys.exit({exit_code})"
                    )
                    return isolated(staged, ["/usr/bin/python3", "-c", emitter], label)

                with (
                    patch.object(OWNER, "stage_runtime", stage),
                    patch.object(OWNER, "run_isolated", run),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    if exit_code:
                        self.assertEqual(OWNER.lint_harness(Path(tmp)), exit_code)
                    else:
                        with self.assertRaises(json.JSONDecodeError):
                            OWNER.lint_harness(Path(tmp))
                self.assertEqual(stderr.getvalue(), "native tool error\n")
                self.assertIn(machine, stdout.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("mocked", "native", "all"), default="all", nargs="?"
    )
    args = parser.parse_args()
    suite = unittest.TestSuite()
    for case in (MockedStreams, NativeStreams):
        if args.mode == "all" or args.mode == (
            "mocked" if case is MockedStreams else "native"
        ):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
