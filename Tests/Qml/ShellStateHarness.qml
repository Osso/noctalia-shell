import QtQuick
import QtTest
import Quickshell.Io
import qs.Commons
import qs.Services.Power
import qs.Services.System
import qs.Services.UI

TestCase {
  id: testCase
  name: "ShellState"

  SignalSpy {
    id: displaySpy
    target: ShellState
    signalName: "displayStateChanged"
  }
  SignalSpy {
    id: notificationsSpy
    target: ShellState
    signalName: "notificationsStateChanged"
  }
  SignalSpy {
    id: changelogSpy
    target: ShellState
    signalName: "changelogStateChanged"
  }
  SignalSpy {
    id: schemesSpy
    target: ShellState
    signalName: "colorSchemesListChanged"
  }

  function test_stateAndServiceToggles() {
    compare(ShellState.stateFile, "");
    Settings.directoriesCreated = true;
    compare(ShellState.stateFile, "/fixture/shell-state.json");
    FixtureIo.file.loaded();
    verify(ShellState.isLoaded);

    compare(ShellState.getDisplay(), {});
    compare(ShellState.getNotificationsState(), {
      lastSeenTs: 0
    });
    compare(ShellState.getChangelogState(), {
      lastSeenVersion: ""
    });
    compare(ShellState.getColorSchemesList(), {
      schemes: [],
      timestamp: 0
    });

    ShellState.setDisplay({
      "DP-1": {
        scale: 1.25
      },
      "HDMI-A-1": {
        scale: 2
      }
    });
    ShellState.setNotificationsState({
      lastSeenTs: 123
    });
    ShellState.setChangelogState({
      lastSeenVersion: "fixture-1"
    });
    ShellState.setColorSchemesList({
      schemes: ["dark", "light"],
      timestamp: 456
    });
    compare(displaySpy.count, 1);
    compare(notificationsSpy.count, 1);
    compare(changelogSpy.count, 1);
    compare(schemesSpy.count, 1);
    verify(ShellState.saveQueued);
    tryCompare(FixtureIo.process, "running", true, 2000);
    compare(FixtureIo.writes, 0);
    FixtureIo.process.finish(0);
    compare(FixtureIo.writes, 1);
    verify(ShellState.saveInProgress);
    FixtureIo.file.saved();
    verify(!ShellState.saveInProgress);

    let snapshot = ShellState.buildStateSnapshot();
    compare(snapshot.settings.screen, "DP-1");
    compare(snapshot.state.doNotDisturb, false);
    compare(snapshot.state.noctaliaPerformanceMode, false);
    compare(snapshot.state.barVisible, true);
    compare(snapshot.state.wallpapers, {
      "DP-1": "first.png"
    });
    compare(snapshot.state.display, ShellState.getDisplay());
    compare(snapshot.state.notificationsState, {
      lastSeenTs: 123
    });
    compare(snapshot.state.changelogState, {
      lastSeenVersion: "fixture-1"
    });
    compare(snapshot.state.colorSchemesList, {
      schemes: ["dark", "light"],
      timestamp: 456
    });

    Settings.data = {
      screen: "HDMI-A-1"
    };
    NotificationService.doNotDisturb = true;
    PowerProfileService.noctaliaPerformanceMode = true;
    BarService.isVisible = false;
    WallpaperService.currentWallpapers = {
      "HDMI-A-1": "second.png"
    };
    ShellState.setDisplay({
      "HDMI-A-1": {
        scale: 1.5
      }
    });
    snapshot = ShellState.buildStateSnapshot();
    compare(snapshot.settings.screen, "HDMI-A-1");
    compare(snapshot.state.doNotDisturb, true);
    compare(snapshot.state.noctaliaPerformanceMode, true);
    compare(snapshot.state.barVisible, false);
    compare(snapshot.state.wallpapers, {
      "HDMI-A-1": "second.png"
    });
    compare(snapshot.state.display, {
      "HDMI-A-1": {
        scale: 1.5
      }
    });
    compare(displaySpy.count, 2);
    compare(Logger.errors, []);
  }
}
