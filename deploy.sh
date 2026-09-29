#!/usr/bin/env python3
"""Reload this checkout in its running Quickshell instance without restarting it."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

SHELL = Path(__file__).resolve().parent / "shell.qml"
LOAD = "Configuration Loaded"
FAILURE = "Failed to load configuration"
WAIT_SECONDS = 10


def quickshell(*args):
    result = subprocess.run(
        ["quickshell", *args], capture_output=True, text=True, timeout=2
    )
    if result.returncode:
        raise RuntimeError(
            f"quickshell {' '.join(args)}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def active_instance():
    instances = json.loads(quickshell("list", "--all", "--json"))
    matches = [item for item in instances if item.get("config_path") == str(SHELL)]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one active instance for {SHELL}, found {len(matches)}"
        )
    instance = matches[0]
    if not instance.get("id") or not isinstance(instance.get("pid"), int):
        raise RuntimeError("active instance is missing an id or pid")
    return instance


def instance_log(pid):
    return quickshell("log", "--pid", str(pid), "--no-color")


def main():
    instance = active_instance()
    pid = instance["pid"]
    baseline = instance_log(pid)
    os.utime(SHELL, None)
    deadline = time.monotonic() + WAIT_SECONDS

    while time.monotonic() < deadline:
        current = active_instance()
        if current["id"] != instance["id"] or current["pid"] != pid:
            raise RuntimeError("active Quickshell instance changed during reload")
        log = instance_log(pid)
        if not log.startswith(baseline):
            raise RuntimeError(
                "instance log changed unexpectedly; cannot establish new load"
            )
        new_lines = log[len(baseline) :]
        if FAILURE.lower() in new_lines.lower():
            raise RuntimeError(new_lines.strip())
        if LOAD in new_lines:
            quickshell("ipc", "--pid", str(pid), "show")
            current = active_instance()
            if current["id"] != instance["id"] or current["pid"] != pid:
                raise RuntimeError("active Quickshell instance changed after IPC check")
            print(f"{LOAD} on instance {instance['id']} (PID {pid}); IPC responsive")
            return
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for new {LOAD} on PID {pid}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Deployment failed: {error}", file=sys.stderr)
        sys.exit(1)
