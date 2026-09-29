#!/usr/bin/env python3
"""Isolated deployment behavior with a fake Quickshell and disposable checkout."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "deploy.sh"
FAKE_QUICKSHELL = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

state = Path(os.environ["FAKE_STATE"])
scenario = os.environ["FAKE_SCENARIO"]
shell = Path(os.environ["FAKE_SHELL"])
instance = {"config_path": str(shell), "id": "original", "pid": 1234,
            "launch_time": "2026-09-29T00:00:00", "shell_id": "shell"}
other = {"config_path": str(shell), "id": "other", "pid": 5678,
         "launch_time": "2026-09-29T00:01:00", "shell_id": "shell"}
if sys.argv[1] == "list":
    if scenario == "missing":
        print("[]")
    elif scenario == "ambiguous":
        print(json.dumps([instance, other]))
    elif scenario == "replaced" and shell.stat().st_mtime_ns != int(state.read_text()):
        print(json.dumps([other]))
    else:
        print(json.dumps([instance]))
elif sys.argv[1] == "log":
    if "1234" not in sys.argv:
        sys.exit(4)
    lines = ["INFO: Configuration Loaded", "INFO: stale startup message"]
    if state.exists() and shell.stat().st_mtime_ns != int(state.read_text()):
        if scenario == "failure":
            lines += ["INFO: Reloading configuration...", "CRITICAL: Failed to load configuration"]
        elif scenario == "success" or scenario == "ipc-failure" or scenario == "replaced":
            lines += ["INFO: Reloading configuration...", "INFO: Configuration Loaded"]
    print("\\n".join(lines))
elif sys.argv[1] == "ipc":
    if scenario == "ipc-failure" or "1234" not in sys.argv:
        sys.exit(5)
    print("launcher")
else:
    sys.exit(6)
"""


class DeploySourceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.checkout = root / "checkout"
        self.checkout.mkdir()
        self.shell = self.checkout / "shell.qml"
        self.shell.write_text("ShellRoot {}\n")
        os.utime(self.shell, ns=(1_000_000_000, 1_000_000_000))
        self.deploy = self.checkout / "deploy.sh"
        shutil.copy2(SOURCE, self.deploy)
        self.bin = root / "bin"
        self.bin.mkdir()
        fake = self.bin / "quickshell"
        fake.write_text(FAKE_QUICKSHELL)
        fake.chmod(0o755)
        self.state = root / "initial-mtime"
        self.state.write_text(str(self.shell.stat().st_mtime_ns))

    def deploy_scenario(self, scenario):
        env = dict(
            os.environ,
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            FAKE_SCENARIO=scenario,
            FAKE_SHELL=str(self.shell),
            FAKE_STATE=str(self.state),
        )
        return subprocess.run(
            [str(self.deploy)], env=env, capture_output=True, text=True, timeout=15
        )

    def test_success_requires_new_load_and_ipc_on_original_instance(self):
        result = self.deploy_scenario("success")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(self.shell.stat().st_mtime_ns, 1_000_000_000)
        self.assertIn("Configuration Loaded", result.stdout)

    def test_missing_instance_does_not_touch_source(self):
        result = self.deploy_scenario("missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.shell.stat().st_mtime_ns, 1_000_000_000)

    def test_ambiguous_instance_does_not_touch_source(self):
        result = self.deploy_scenario("ambiguous")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.shell.stat().st_mtime_ns, 1_000_000_000)

    def test_load_failure_exits_nonzero(self):
        result = self.deploy_scenario("failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed to load configuration", result.stderr)

    def test_no_new_load_times_out(self):
        result = self.deploy_scenario("timeout")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timed out", result.stderr.lower())

    def test_replaced_instance_exits_nonzero(self):
        result = self.deploy_scenario("replaced")
        self.assertNotEqual(result.returncode, 0)

    def test_ipc_failure_exits_nonzero(self):
        result = self.deploy_scenario("ipc-failure")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
