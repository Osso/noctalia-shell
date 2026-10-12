#!/usr/bin/env python3
"""Bounded LockContext lint and sandboxed PAM-event/state characterization.

Only production LockContext executes. PAM transport and lock consumer are fake;
no Quickshell executable, session-lock protocol, desktop socket or real settings.
Native PAM/conversation ordering and compositor security are not proven here.
"""

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/LockScreen/LockContext.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("LOCK_CONTEXT_LINT_COUNTS", dict(counts), "TOTAL", sum(counts.values()))
    assert result.returncode == 0, result.returncode
    assert not counts, dict(counts)


PAM = """import QtQuick
import qs.Fixture
QtObject {
  id: transport
  property bool active: false
  property string config: ""
  property string configDirectory: ""
  property string user: ""
  property string message: ""
  property bool messageIsError: false
  property bool responseRequired: false
  property bool responseVisible: false
  property var starts: []
  property var responses: []
  signal pamMessage()
  signal completed(int result)
  signal error(int error)
  function start() {
    starts = starts.concat([{user: user, config: config}]);
    return true;
  }
  function respond(response) { responses = responses.concat([response]); }
  function abort() { active = false; }
  Component.onCompleted: FakeLockService.pam = transport
}
"""


HARNESS = """import QtQuick
import QtTest
import Quickshell.Services.Pam
import qs.Fixture
import qs.Modules.LockScreen

Item {
  id: scene
  property LockContext context: null
  property var signals: []
  Component { id: factory; LockContext {} }
  Connections {
    target: scene.context
    function onUnlocked() {
      scene.signals.push({kind: "unlocked", progress: scene.context.unlockInProgress,
                          failure: scene.context.showFailure, error: scene.context.errorMessage});
      FakeLockService.locked = false;
    }
    function onFailed() {
      scene.signals.push({kind: "failed", progress: scene.context.unlockInProgress,
                          failure: scene.context.showFailure, error: scene.context.errorMessage});
    }
  }
  TestCase {
    name: "LockContextEvents"
    when: true
    function init() {
      scene.signals = [];
      FakeLockService.locked = true;
      scene.context = factory.createObject(scene);
      verify(scene.context !== null);
      verify(FakeLockService.pam !== null);
    }
    function cleanup() {
      scene.context.destroy();
      scene.context = null;
      FakeLockService.pam = null;
    }
    function test_unavailable_fails_closed() {
      scene.context.pamAvailable = false;
      scene.context.tryUnlock();
      compare(scene.context.errorMessage, "PAM not available");
      verify(scene.context.showFailure);
      verify(!scene.context.unlockInProgress);
      compare(FakeLockService.pam.starts.length, 0);
      compare(scene.signals.length, 0);
      verify(FakeLockService.locked);
    }
    function test_start_clears_failure_and_routes_user() {
      scene.context.errorMessage = "old failure";
      scene.context.showFailure = true;
      scene.context.currentText = "fixture-secret";
      scene.context.tryUnlock();
      verify(scene.context.unlockInProgress);
      verify(!scene.context.showFailure);
      compare(scene.context.errorMessage, "");
      compare(FakeLockService.pam.starts, [{user: "fixture-user", config: "login"}]);
      compare(FakeLockService.pam.responses.length, 0);
      verify(FakeLockService.locked);
    }
    function test_edit_clears_failure_only_when_nonempty() {
      scene.context.errorMessage = "old failure";
      scene.context.showFailure = true;
      scene.context.currentText = "";
      verify(scene.context.showFailure);
      scene.context.currentText = "new-secret";
      verify(!scene.context.showFailure);
      compare(scene.context.errorMessage, "");
      verify(FakeLockService.locked);
    }
    function test_messages_route_error_and_info_without_unlocking() {
      const pam = FakeLockService.pam;
      pam.message = "Password expired";
      pam.messageIsError = true;
      pam.pamMessage();
      compare(scene.context.errorMessage, "Password expired");
      compare(scene.context.infoMessage, "");
      verify(!scene.context.showFailure);
      pam.message = "Enter password";
      pam.messageIsError = false;
      pam.pamMessage();
      compare(scene.context.infoMessage, "Enter password");
      compare(scene.context.errorMessage, "Password expired");
      compare(pam.responses.length, 0);
      compare(scene.signals.length, 0);
      verify(FakeLockService.locked);
    }
    function test_required_change_gated_by_progress() {
      const pam = FakeLockService.pam;
      scene.context.currentText = "fixture-secret";
      pam.responseRequired = true;
      compare(pam.responses.length, 0);
      pam.responseRequired = false;
      scene.context.tryUnlock();
      pam.responseRequired = true;
      compare(pam.responses, ["fixture-secret"]);
      verify(FakeLockService.locked);
    }
    function test_message_response_preserves_existing_idle_boundary() {
      const pam = FakeLockService.pam;
      scene.context.currentText = "message-secret";
      pam.responseRequired = true;
      compare(pam.responses.length, 0);
      pam.message = "Password:";
      pam.pamMessage();
      // Existing pamMessage path has no unlockInProgress gate; do not change it.
      compare(pam.responses, ["message-secret"]);
      verify(!scene.context.unlockInProgress);
      verify(FakeLockService.locked);
    }
    function test_success_signal_precedes_progress_reset() {
      scene.context.tryUnlock();
      FakeLockService.pam.completed(PamResult.Success);
      compare(scene.signals, [{kind: "unlocked", progress: true, failure: false, error: ""}]);
      verify(!scene.context.unlockInProgress);
      verify(!FakeLockService.locked);
    }
    function test_unsuccessful_completion_data() {
      return [{tag: "failed", result: PamResult.Failed},
              {tag: "error", result: PamResult.Error},
              {tag: "max-tries", result: PamResult.MaxTries}];
    }
    function test_unsuccessful_completion(data) {
      scene.context.tryUnlock();
      FakeLockService.pam.completed(data.result);
      compare(scene.context.errorMessage, "translated:lock-screen.authentication-failed");
      verify(scene.context.showFailure);
      compare(scene.signals, [{kind: "failed", progress: true, failure: true,
                              error: "translated:lock-screen.authentication-failed"}]);
      verify(!scene.context.unlockInProgress);
      verify(FakeLockService.locked);
    }
    function test_transport_error_data() {
      return [{tag: "message", message: "PAM fixture unavailable", expected: "PAM fixture unavailable"},
              {tag: "empty", message: "", expected: "Authentication error"}];
    }
    function test_transport_error(data) {
      scene.context.tryUnlock();
      FakeLockService.pam.message = data.message;
      FakeLockService.pam.error(0);
      compare(scene.context.errorMessage, data.expected);
      verify(scene.context.showFailure);
      compare(scene.signals, [{kind: "failed", progress: false, failure: true, error: data.expected}]);
      verify(!scene.context.unlockInProgress);
      verify(FakeLockService.locked);
    }
  }
}
"""


def stage_runtime(directory, mutation):
    helpers = helper("about-tab-warnings.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    write(directory, "Quickshell", {"Scope": "import QtQuick\nItem {}"})
    write(
        directory,
        "qs.Fixture",
        {
            "FakeLockService": singleton(
                "property QtObject pam: null\nproperty bool locked: true"
            )
        },
    )
    write(
        directory,
        "Quickshell.Services.Pam",
        {
            "PamContext": PAM,
            "PamResult": singleton("enum Result { Success, Failed, Error, MaxTries }"),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Logger": singleton("function i(...args) {}"),
            "I18n": singleton('function tr(key) { return "translated:" + key; }'),
            "Settings": singleton(
                'Component.onCompleted: { throw new Error("SETTINGS_ACCESS_DENIED"); }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "HostService": singleton('property string username: "fixture-user"'),
        },
    )
    source = (ROOT / TARGET).read_text()
    if mutation == "message-owner":
        source = re.sub(
            r"(?:root\.)?errorMessage = message;", "root.infoMessage = message;", source
        )
    elif mutation == "completion":
        source = source.replace("root.unlocked();", "root.failed();")
    elif mutation == "response":
        source = source.replace("respond(root.currentText);", 'respond("");')
    write(directory, "qs.Modules.LockScreen", {"LockContext": source})
    (directory / "tst_lock_context.qml").write_text(HARNESS)


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
    audit = directory / "file-access.log"
    # Only installed libraries and this isolated fixture are mounted. Real home,
    # repo, /run (desktop sockets), /etc/pam.d and network are inaccessible.
    sandbox = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/tmp/home",
        "--dir",
        "/tmp/config",
        "--dir",
        "/tmp/cache",
        "--dir",
        "/tmp/runtime",
        "--ro-bind",
        str(directory),
        "/fixture",
        "--chdir",
        "/fixture",
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin",
        "--setenv",
        "HOME",
        "/tmp/home",
        "--setenv",
        "XDG_CONFIG_HOME",
        "/tmp/config",
        "--setenv",
        "XDG_CACHE_HOME",
        "/tmp/cache",
        "--setenv",
        "XDG_RUNTIME_DIR",
        "/tmp/runtime",
        "--setenv",
        "QT_QPA_PLATFORM",
        "offscreen",
        "--setenv",
        "QT_QUICK_BACKEND",
        "software",
        "/usr/lib/qt6/bin/qmltestrunner",
        "-input",
        "/fixture/tst_lock_context.qml",
        "-import",
        "/fixture",
    ]
    result = subprocess.run(
        ["strace", "-f", "-qq", "-e", "trace=%file", "-o", str(audit), *sandbox],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    accesses = audit.read_text()
    forbidden = [
        line
        for line in accesses.splitlines()
        if re.search(
            r'"(?:/home/osso|/syncthing|/run/user)(?:/|\")|noctalia/settings\.json|/etc/pam\.d|libquickshell',
            line,
        )
    ]
    assert not forbidden, forbidden
    assert "SETTINGS_ACCESS_DENIED" not in output, output
    print(
        "LOCK_CONTEXT_AUDIT_DENY_PASS real settings/desktop/PAM inaccessible; forbidden attempts 0"
    )
    # Existing implicit error-parameter injection is outside owner-only scope.
    warnings = [line for line in output.splitlines() if "QWARN" in line]
    assert len(warnings) == 1 and 'Parameter "error" is not declared' in warnings[0], (
        warnings
    )
    print(
        "LOCK_CONTEXT_RUNTIME_RESIDUAL 1 existing onError parameter-injection deprecation"
    )
    assert not re.search(r"QFATAL|ReferenceError|TypeError|Fontconfig error", output), (
        output
    )
    assert result.returncode == 0, result.returncode
    assert "0 failed" in output, output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument(
        "--mutation", choices=("message-owner", "completion", "response")
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-lock-context-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint":
            lint(directory)
        else:
            runtime(directory, args.mutation)
