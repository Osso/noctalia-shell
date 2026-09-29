#!/usr/bin/env python3
"""Isolated deployment behavior with fake CLI failures and a real offscreen shell."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "deploy.sh"
RELOAD = SOURCE.parent / "Services/Control/ShellReload.qml"
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
    elif scenario == "replaced" and state.read_text() == "requested":
        print(json.dumps([other]))
    else:
        print(json.dumps([instance]))
elif sys.argv[1] == "log":
    if "1234" not in sys.argv:
        sys.exit(4)
    lines = ["INFO: Configuration Loaded", "INFO: stale startup message"]
    if state.read_text() == "requested":
        if scenario == "failure":
            lines += ["INFO: Reloading configuration...", "CRITICAL: Failed to load configuration"]
        elif scenario in ("success", "show-failure", "replaced"):
            lines += ["INFO: Reloading configuration...", "INFO: Configuration Loaded"]
    print("\\n".join(lines))
elif sys.argv[1] == "ipc":
    if "1234" not in sys.argv or scenario == "ipc-failure":
        sys.exit(5)
    if "call" in sys.argv:
        if sys.argv[-2:] != ["shell", "reload"]:
            sys.exit(6)
        state.write_text("requested")
    elif scenario == "show-failure":
        sys.exit(5)
    else:
        print("shell")
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
        self.deploy = self.checkout / "deploy.sh"
        shutil.copy2(SOURCE, self.deploy)
        self.bin = root / "bin"
        self.bin.mkdir()
        fake = self.bin / "quickshell"
        fake.write_text(FAKE_QUICKSHELL)
        fake.chmod(0o755)
        self.state = root / "state"
        self.state.write_text("idle")

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
        self.assertEqual(self.state.read_text(), "requested")
        self.assertIn("Configuration Loaded", result.stdout)

    def test_missing_instance_does_not_request_reload(self):
        result = self.deploy_scenario("missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state.read_text(), "idle")

    def test_ambiguous_instance_does_not_request_reload(self):
        result = self.deploy_scenario("ambiguous")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state.read_text(), "idle")

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

    def test_show_failure_exits_nonzero(self):
        result = self.deploy_scenario("show-failure")
        self.assertNotEqual(result.returncode, 0)


class RealReloadTest(unittest.TestCase):
    def test_unchanged_source_reloads_same_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            env = dict(os.environ)
            env.update(
                XDG_CONFIG_HOME=str(root / "config"),
                XDG_CACHE_HOME=str(root / "cache"),
                XDG_DATA_HOME=str(root / "data"),
                XDG_RUNTIME_DIR=str(runtime),
                QT_QPA_PLATFORM="offscreen",
            )
            env.pop("WAYLAND_DISPLAY", None)
            env.pop("DISPLAY", None)
            checkout = root / "checkout"
            control = checkout / "Services/Control"
            control.mkdir(parents=True)
            shell = checkout / "shell.qml"
            shell.write_text(
                "import Quickshell\nimport qs.Services.Control\n"
                "ShellRoot { ShellReload {} }\n"
            )
            component = control / "ShellReload.qml"
            shutil.copy2(RELOAD, component)
            deploy = checkout / "deploy.sh"
            shutil.copy2(SOURCE, deploy)
            digest = hashlib.sha256(shell.read_bytes()).digest()
            source_mtime = shell.stat().st_mtime_ns
            component_digest = hashlib.sha256(component.read_bytes()).digest()
            component_mtime = component.stat().st_mtime_ns
            started = subprocess.Popen(
                ["quickshell", "-p", str(checkout)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 7
                while time.monotonic() < deadline:
                    listing = subprocess.run(
                        ["quickshell", "list", "--all", "--json"],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if listing.returncode == 0 and listing.stdout.lstrip().startswith(
                        "["
                    ):
                        try:
                            instances = json.loads(listing.stdout)
                        except json.JSONDecodeError:
                            self.fail(
                                f"invalid instance list: {listing.stdout!r}; {listing.stderr!r}"
                            )
                        if any(
                            item.get("config_path") == str(shell) for item in instances
                        ):
                            break
                    if started.poll() is not None:
                        output, errors = started.communicate()
                        self.fail(
                            f"offscreen Quickshell exited {started.returncode}: {output.decode()}; {errors.decode()}"
                        )
                    time.sleep(0.1)
                else:
                    self.fail("offscreen Quickshell did not register")
                result = subprocess.run(
                    [str(deploy)],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(started.poll(), None)
                self.assertIn(f"PID {started.pid}", result.stdout)
                self.assertEqual(hashlib.sha256(shell.read_bytes()).digest(), digest)
                self.assertEqual(shell.stat().st_mtime_ns, source_mtime)
                self.assertEqual(
                    hashlib.sha256(component.read_bytes()).digest(), component_digest
                )
                self.assertEqual(component.stat().st_mtime_ns, component_mtime)
            finally:
                if started.poll() is None:
                    os.killpg(started.pid, signal.SIGTERM)
                try:
                    started.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(started.pid, signal.SIGKILL)
                    started.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
