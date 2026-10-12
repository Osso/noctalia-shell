import QtQuick
import qs.Commons
import qs.TestScreens
import qs.Services.System
import qs.Services.UI

Item {
  id: probe

  required property var shell
  required property Loader fullLoader
  required property var errorVariants
  property int step: 0
  property TestScreen first: TestScreen {
    name: "FAKE-A"
  }
  property TestScreen second: TestScreen {
    name: "FAKE-B"
  }

  function check(condition, message) {
    if (!condition)
      throw new Error("SHELL_ROOT_ASSERT: " + message);
  }

  function checkErrors(screens) {
    const instances = probe.errorVariants.instances;
    probe.check(instances.length === screens.length, "error surface count");
    for (const screen of screens) {
      const matching = instances.filter(instance => instance.targetScreen === screen);
      probe.check(matching.length === 1, "exact error screen identity " + screen.name);
      probe.check(matching[0].message === Settings.errorMessage, "error message binding");
      probe.check(matching[0].settingsPath === Settings.settingsFile, "error path binding");
    }
  }

  Timer {
    id: advance
    interval: 80
    repeat: true
    running: true
    onTriggered: {
      try {
        switch (probe.step++) {
        case 0:
          probe.check(probe.fullLoader.item === null, "cold loader gated");
          probe.checkErrors([]);
          Settings.bootstrapState = Settings.Error;
          TestScreens.screens = [probe.first];
          break;
        case 1:
          probe.checkErrors([probe.first]);
          TestScreens.screens = [probe.first, probe.second];
          Settings.errorMessage = "second diagnostic";
          Settings.settingsFile = "/fixture/changed-settings";
          break;
        case 2:
          probe.checkErrors([probe.first, probe.second]);
          probe.errorVariants.instances[0].retryRequested();
          probe.check(Settings.retries === 1, "retry routed to fake Settings");
          TestScreens.screens = [probe.second];
          break;
        case 3:
          probe.checkErrors([probe.second]);
          Settings.bootstrapState = 0;
          I18n.translationsLoaded();
          probe.check(probe.shell.i18nLoaded, "translation signal updates root");
          ShellState.isLoaded = true;
          probe.check(probe.shell.shellStateLoaded, "shell-state signal updates root");
          break;
        case 4:
          probe.checkErrors([]);
          probe.check(probe.fullLoader.item === null, "Settings readiness still gates loader");
          Settings.ready = true;
          break;
        case 5:
          probe.check(probe.fullLoader.item !== null, "full shell loaded");
          probe.check(PanelService.initializations === 1, "services initialized once");
          Settings.ready = false;
          break;
        case 6:
          probe.check(probe.fullLoader.item === null, "loader unloaded");
          Settings.ready = true;
          Settings.shouldOpenSetupWizard = true;
          HostService.isReady = true;
          break;
        case 7:
          probe.check(probe.fullLoader.item !== null, "loader recreated");
          probe.check(PanelService.initializations === 2, "services initialized again");
          // Host readiness and loader completion must reach the root timer.
          advance.interval = 1200;
          break;
        case 8:
          probe.check(PanelService.opens === 1, "root timer opens setup on attached screen");
          probe.check(PanelService.openedScreen === probe.second, "setup exact screen identity");
          TestScreens.screens = [probe.second, probe.first];
          probe.shell.showSetupWizard();
          probe.check(PanelService.opens === 2, "screen attach preserves setup routing");
          probe.check(PanelService.openedScreen === probe.second, "setup uses first attached screen");
          advance.running = false;
          console.log("SHELL_ROOT_RESOLUTION_READY 9 lifecycle cases");
          break;
        }
      } catch (error) {
        advance.running = false;
        console.error(error.message);
        Qt.quit();
      }
    }
  }
}
