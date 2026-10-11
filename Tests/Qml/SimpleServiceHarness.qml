import QtQuick
import QtTest
import Quickshell.Io
import qs.Commons
import qs.Services.Noctalia
import qs.Services.Networking
import qs.Services.Media
import qs.Services.Location
import qs.Services.System
import qs.Services.UI

TestCase {
  name: "SimpleServiceOwners"

  function test_github_streamsAndMetadataLifetime() {
    compare(GitHubService.latestVersion, "system.unknown-version");
    const metadata = FixtureIo.find("cat /fixture/contributors/metadata.json");
    const live = FixtureIo.liveProcesses;
    metadata.finish(0, "{}", "");
    tryCompare(GitHubService, "metadataLoaded", true);
    tryCompare(FixtureIo, "liveProcesses", live - 1);

    GitHubService.fetchFromGitHub();
    const version = FixtureIo.find("curl -fsSL https://api.github.com/repos/noctalia-dev/noctalia-shell/releases");
    const contributors = FixtureIo.find("curl -fsSL https://api.github.com/repos/noctalia-dev/noctalia-shell/contributors");
    verify(version.running && contributors.running);
    version.finish(0, '{"tag_name":"v9.8.7"}', "");
    compare(GitHubService.latestVersion, "v9.8.7");
    verify(GitHubService.isFetchingData);
    contributors.finish(0, "[]", "");
    // Current service checks running from streamFinished, before exit.
    verify(GitHubService.isFetchingData);
    GitHubService.checkAndSaveData();
    compare(GitHubService.isFetchingData, false);
    tryVerify(() => FixtureIo.writes > 0);

    GitHubService.fetchFromGitHub();
    version.finish(1, "{broken", "HTTP failure");
    contributors.finish(1, '{"message":"rate limited"}', "");
    compare(GitHubService.latestVersion, "v9.8.7");
    compare(GitHubService.contributors.length, 0);
    verify(Logger.messages.some(m => m.includes("Failed to parse version")));
    verify(Logger.messages.some(m => m.includes("Unexpected contributors response shape")));
    GitHubService.checkAndSaveData();
  }

  function test_network_statusScanAndErrorOrdering() {
    compare(NetworkService.activePolling, false);
    FixtureIo.find("nmcli radio wifi").finish(0, "enabled", "");
    FixtureIo.find("nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device").finish(0, "eth0:ethernet:connected:Wired", "");
    compare(NetworkService.ethernetConnected, true);
    NetworkService.beginActivePolling();
    const profile = FixtureIo.find("nmcli -t -f NAME connection show");
    profile.finish(0, "Office\n", "");
    const scan = FixtureIo.find("nmcli -t -f SSID,SECURITY,SIGNAL,IN-USE");
    verify(scan.running);
    scan.finish(0, "Office:WPA2:75:*\n", "");
    compare(NetworkService.scanning, false);
    verify(NetworkService.networks.Office !== undefined);
    NetworkService.scan();
    profile.finish(1, "", "profile denied");
    compare(NetworkService.scanning, false);
    compare(NetworkService.lastError, "profile denied");
    NetworkService.endActivePolling();
    compare(NetworkService.activePolling, false);
  }

  function test_vpn_requestExitAndStartFailure() {
    VPNService.refresh();
    const refresh = FixtureIo.find("nmcli -t -f NAME,UUID,TYPE,DEVICE");
    refresh.finish(0, "Office:vpn-1:wireguard:--\n", "");
    compare(VPNService.refreshing, false);
    VPNService.connect("vpn-1");
    const connect = FixtureIo.find("nmcli connection up uuid vpn-1");
    connect.finish(0, "connected", "");
    compare(VPNService.connecting, false);
    verify(VPNService.connections["vpn-1"].active);
    VPNService.disconnect("vpn-1");
    const disconnect = FixtureIo.find("nmcli connection down uuid vpn-1");
    disconnect.finish(1, "", "permission denied\nmore detail");
    compare(VPNService.lastError, "permission denied");
    verify(VPNService.connections["vpn-1"].active);
    VPNService.connect("vpn-1");
    connect.running = false;
    compare(VPNService.connecting, false);
    compare(VPNService.lastError, "nmcli VPN connect failed to start");
    VPNService.refresh();
    refresh.finish(1, "", "refresh denied");
    compare(VPNService.lastError, "refresh denied");
  }

  function test_cava_configFramesSilenceAndExit() {
    CavaService.shouldRun = true;
    const process = FixtureIo.find("cava -p /dev/stdin");
    verify(process.running);
    verify(process.input.join("").includes("[general]\nbars=32\n"));
    compare(CavaService.values.length, 32);
    process.stdout.read("50;100;");
    compare(CavaService.isIdle, false);
    compare(CavaService.values, [0.5, 1]);
    for (let i = 0; i < 30; i++) process.stdout.read("0;0;");
    compare(CavaService.isIdle, true);
    compare(CavaService.values, Array(32).fill(0));
    process.stderr.text = "fixture error";
    process.stderr.streamFinished();
    verify(Logger.messages.some(m => m.includes("fixture error")));
    process.exited(1, 0);
    CavaService.shouldRun = false;
    compare(CavaService.values, Array(32).fill(0));
  }

  function test_recorder_discoveryPortalFailureAndExit() {
    compare(ScreenRecorderService.isAvailable, false);
    ProgramCheckerService.gpuScreenRecorderAvailable = true;
    ProgramCheckerService.checksCompleted();
    const captures = FixtureIo.find("gpu-screen-recorder --list-capture-options");
    const monitors = FixtureIo.find("gpu-screen-recorder --list-monitors");
    captures.finish(0, "portal\nDP-1\n", "");
    verify(ScreenRecorderService.discoveryInProgress);
    monitors.finish(0, "DP-1 1920x1080\n", "");
    compare(ScreenRecorderService.discoveryInProgress, false);
    ScreenRecorderService.startRecording();
    const portal = FixtureIo.find("sh -c pidof xdg-desktop-portal");
    portal.finish(1, "", "no portals");
    compare(ScreenRecorderService.isPending, false);
    compare(ScreenRecorderService.hasActiveRecording, false);
    ScreenRecorderService.startRecording();
    portal.finish(0, "", "");
    const recorder = FixtureIo.find("sh -c \n    _gpuscreenrecorder_flatpak_installed");
    verify(recorder.running);
    recorder.finish(1, "", "encoder failed");
    compare(ScreenRecorderService.isPending, false);
    compare(ScreenRecorderService.isRecording, false);
    verify(ToastService.messages.some(m => m.includes("encoder failed")));
  }

  function test_nightLight_connectionsCleanupAndDisabledRace() {
    compare(NightLightService.cleanupPending, false);
    Settings.data.nightLight.enabled = true;
    const cleanup = FixtureIo.find("sh -c \npids=");
    verify(cleanup.running);
    compare(NightLightService.cleanupPending, true);
    cleanup.finish(1, "", "enumeration failed");
    compare(NightLightService.cleanupPending, false);
    verify(Logger.messages.some(m => m.includes("enumeration failed")));
    Settings.data.nightLight.nightTemp = 3900;
    cleanup.finish(0, "", "");
    const runner = FixtureIo.find("wlsunset");
    verify(runner.running);
    verify(runner.command.includes("3900"));
    Settings.data.nightLight.dayTemp = 6600;
    compare(NightLightService.cleanupPending, true);
    Settings.data.nightLight.enabled = false;
    cleanup.finish(0, "", "");
    compare(runner.running, false);
  }

  function test_bar_timerRegistryVisualizer() {
    compare(BarService.hasAudioVisualizer, false);
    BarService.registerWidget("DP-1", "left", "AudioVisualizer", 0, {});
    tryCompare(BarService, "hasAudioVisualizer", true);
    BarService.unregisterWidget("DP-1", "left", "AudioVisualizer", 0);
    BarService.registerWidget("DP-1", "left", "MediaMini", 1, {showVisualizer: false});
    tryCompare(BarService, "hasAudioVisualizer", false);
    BarService.registerWidget("DP-1", "right", "MediaMini", 2, {showVisualizer: true});
    tryCompare(BarService, "hasAudioVisualizer", true);
    compare(BarService.getAllWidgetInstances("MediaMini").length, 2);
  }
}
