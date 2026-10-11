#!/usr/bin/python3
"""Private command provider; never invokes nmcli, shells, or any network API."""

import json
import os
from pathlib import Path
import sys
import time


def respond(arguments, mode, directory):
    if Path(sys.argv[0]).name == "bash":
        return 0, "deleted fixture profile\n", ""
    if arguments == ["radio", "wifi"]:
        return 0, "enabled\n", ""
    if arguments == ["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]:
        connected_file = directory / "connected-ssid"
        ssid = connected_file.read_text() if connected_file.exists() else "Home"
        return 0, f"eth0:ethernet:connected:Wired\nwlan0:wifi:connected:{ssid}\n", ""
    if arguments == ["networking", "connectivity", "check"]:
        return 0, "full\n", ""
    if arguments == ["-t", "-f", "NAME", "connection", "show"]:
        if mode == "profile-error":
            return 10, "partial profiles\n", "profile fixture denied\n"
        return 0, "Saved\nGuest\n", ""
    if arguments == [
        "-t",
        "-f",
        "SSID,SECURITY,SIGNAL,IN-USE",
        "device",
        "wifi",
        "list",
        "--rescan",
        "yes",
    ]:
        if mode == "scan-error":
            return 10, "partial scan\n", "scan fixture denied\n"
        (directory / "connected-ssid").write_text("Guest")
        return 0, "Guest:WPA2:76:*\nSaved:WPA2:50:\n", ""
    if arguments in (
        ["connection", "up", "id", "Saved"],
        ["device", "wifi", "connect", "New", "password", "fixture-secret"],
    ):
        ssid = "Saved" if arguments[0] == "connection" else "New"
        (directory / "connected-ssid").write_text(ssid)
        return 0, "localized success\n", ""
    if arguments == ["device", "wifi", "connect", "Denied"]:
        return 10, "stdout diagnostic\n", "permission denied\nsecond line\n"
    return 99, "", "unexpected fixture request: " + repr(arguments) + "\n"


def main():
    directory = Path(os.environ["NETWORK_FIXTURE_DIR"])
    arguments = sys.argv[1:]
    with (directory / "requests.jsonl").open("a") as output:
        output.write(json.dumps(arguments) + "\n")
    # Make busy state observable before real stream/exit delivery.
    time.sleep(0.08)
    code, output, error = respond(
        arguments, os.environ["NETWORK_FIXTURE_MODE"], directory
    )
    sys.stdout.write(output)
    sys.stderr.write(error)
    sys.exit(code)


if __name__ == "__main__":
    main()
