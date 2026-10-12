"""Popup-only filesystem-sandbox adapter for the installed PrivateDisplay helper.

The shared helper's systemd/host MIME integration is not used here. Its private
settings, Niri config, socket discovery and validation remain authoritative.
"""

import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

HELPER = Path(
    "/home/osso/AgentConfig/skills/desktop-control/scripts/private_display.py"
)
spec = importlib.util.spec_from_file_location("popup_private_display_helper", HELPER)
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def sandbox(directory, command):
    return [
        "bwrap",
        "--die-with-parent",
        "--unshare-all",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(directory),
        str(directory),
        "--chdir",
        str(directory),
        "--",
        *command,
    ]


def stop_owned(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(timeout=3)
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError("owned private process group survived cleanup")


# Query advertised globals without creating an application or layer surface.
REGISTRY_PROBE = r"""
import ctypes as c
import json
from pathlib import Path
assert not Path('/dev/dri').exists(), 'DRM devices exposed'
assert not Path('/dev/input').exists(), 'input devices exposed'
assert not Path('/home/osso').exists(), 'host home exposed'
assert not Path('/run/user').exists(), 'host runtime exposed'
lib = c.CDLL('libwayland-client.so.0')
lib.wl_display_connect.argtypes = [c.c_char_p]
lib.wl_display_connect.restype = c.c_void_p
lib.wl_display_roundtrip.argtypes = [c.c_void_p]
lib.wl_display_disconnect.argtypes = [c.c_void_p]
lib.wl_proxy_destroy.argtypes = [c.c_void_p]
lib.wl_proxy_marshal_flags.argtypes = [c.c_void_p, c.c_uint, c.c_void_p, c.c_uint, c.c_uint]
lib.wl_proxy_marshal_flags.restype = c.c_void_p
lib.wl_proxy_add_listener.argtypes = [c.c_void_p, c.c_void_p, c.c_void_p]
class Interface(c.Structure):
    _fields_ = [('name', c.c_char_p), ('version', c.c_int), ('method_count', c.c_int),
                ('methods', c.c_void_p), ('event_count', c.c_int), ('events', c.c_void_p)]
interface = Interface.in_dll(lib, 'wl_registry_interface')
display = lib.wl_display_connect(None)
assert display, 'private Wayland connection failed'
registry = lib.wl_proxy_marshal_flags(display, 1, c.byref(interface), 1, 0, c.c_void_p())
assert registry, 'registry creation failed'
globals_seen = []
@c.CFUNCTYPE(None, c.c_void_p, c.c_void_p, c.c_uint, c.c_char_p, c.c_uint)
def added(data, proxy, name, interface, version):
    globals_seen.append(interface.decode())
@c.CFUNCTYPE(None, c.c_void_p, c.c_void_p, c.c_uint)
def removed(data, proxy, name):
    globals_seen.append('REMOVED:' + str(name))
listener = (c.c_void_p * 2)(c.cast(added, c.c_void_p), c.cast(removed, c.c_void_p))
assert lib.wl_proxy_add_listener(registry, listener, None) == 0
assert lib.wl_display_roundtrip(display) >= 0
lib.wl_proxy_destroy(registry)
lib.wl_display_disconnect(display)
print(json.dumps(globals_seen))
assert 'zwlr_layer_shell_v1' in globals_seen, 'private layer-shell not advertised'
"""


class PopupPrivateDisplay(shared.PrivateDisplay):
    """Reuse shared private sockets/config inside namespaces, not the host unit."""

    def __init__(self, out):
        super().__init__(out, app="/usr/bin/true")
        self.process = None
        self.stream = None

    def __enter__(self):
        manifest = Path(shared.PRIVATE_SETTINGS["VK_DRIVER_FILES"])
        assert manifest.is_file(), f"missing CPU Vulkan ICD: {manifest}"
        self.out.mkdir(mode=0o700)
        self.runtime.mkdir(mode=0o700)
        self.settings = dict(shared.PRIVATE_SETTINGS, XDG_RUNTIME_DIR=str(self.runtime))
        for name in ("home", "config", "cache", "data", "state"):
            path = self.out / name
            path.mkdir(mode=0o700)
            key = "HOME" if name == "home" else f"XDG_{name.upper()}_HOME"
            self.settings[key] = str(path)
        self.env = dict(
            self.settings,
            PATH="/usr/bin",
            LANG="C.UTF-8",
            QT_QPA_PLATFORM="wayland",
            QT_QUICK_BACKEND="software",
            QML_DISABLE_DISK_CACHE="1",
            DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/popup-test",
            GALLIUM_DRIVER="llvmpipe",
        )
        config = self.out / "niri.kdl"
        config.write_text(shared.NIRI_CONFIG)
        command = sandbox(
            self.out,
            [
                "strace",
                "-f",
                "-yy",
                "-e",
                "trace=openat,open,connect",
                "-o",
                str(self.out / "devices.trace"),
                "dbus-run-session",
                "--",
                "cage",
                "-d",
                "--",
                "niri",
                "--config",
                str(config),
            ],
        )
        self.stream = (self.out / "display.log").open("w")
        try:
            self.process = subprocess.Popen(
                command,
                cwd=self.out,
                env=self.env,
                stdout=self.stream,
                stderr=self.stream,
                start_new_session=True,
            )
            self.discover_sockets()
            self.verify_backend()
            return dict(self.env)
        except BaseException:
            self.cleanup()
            raise

    def verify_backend(self):
        assert self.process.poll() is None, (self.out / "display.log").read_text()
        result = subprocess.run(
            sandbox(self.out, ["niri", "msg", "--json", "outputs"]),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        (self.out / "outputs.json").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
        outputs = json.loads(result.stdout)
        assert list(outputs) == ["winit"], outputs
        log = (self.out / "display.log").read_text()
        assert "niri::backend::winit" in log, log
        trace = (self.out / "devices.trace").read_text()
        assert re.search(r'"/usr/lib/libgallium[^" ]*".*= [0-9]+', trace), trace
        assert re.search(r'"/usr/lib/libLLVM[^" ]*".*= [0-9]+', trace), trace
        result = subprocess.run(
            sandbox(self.out, ["python3", "-c", REGISTRY_PROBE]),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        (self.out / "registry.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        self.verify_devices()
        print("POPUP_PRIVATE_PREFLIGHT_PASS Winit llvmpipe layer-shell no-hardware")

    def verify_devices(self):
        trace = (self.out / "devices.trace").read_text()
        opened = [
            line
            for line in trace.splitlines()
            if re.search(r'"/dev/(?:dri|input|snd|tty|video|fb)', line)
            and re.search(r"= [0-9]+", line)
        ]
        assert not opened, opened

    def cleanup(self):
        if self.process is not None:
            stop_owned(self.process)
            assert self.process.poll() is not None
            self.verify_devices()
        if self.stream is not None:
            self.stream.close()
        sockets = [
            path
            for path in self.runtime.iterdir()
            if path.is_socket() or path.name.endswith(".lock")
        ]
        for path in sockets:
            path.unlink()
        remaining = [str(path) for path in self.runtime.iterdir() if path.is_socket()]
        assert not remaining, remaining
        (self.out / "cleanup.json").write_text(
            json.dumps(
                {
                    "display_exit": self.process.returncode if self.process else None,
                    "owned_group_remaining": False,
                    "remaining_sockets": remaining,
                }
            )
            + "\n"
        )
