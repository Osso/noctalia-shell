/*
* Noctalia – made by https://github.com/noctalia-dev
* Licensed under the MIT License.
* Forks and modifications are allowed under the MIT License,
* but proper credit must be given to the original author.
*/

// Qt & Quickshell Core
import QtQuick
import Quickshell
import Quickshell.Services.SystemTray

// Commons & Services
import qs.Commons

// Modules
import qs.Modules.Background
import qs.Modules.Bar
import qs.Modules.Dock
import qs.Modules.LockScreen
import qs.Modules.MainScreen
import qs.Modules.Notification
import qs.Modules.OSD
import qs.Modules.Startup
import qs.Modules.Toast
import qs.Services.Control
import qs.Services.Hardware
import qs.Services.Location
import qs.Services.Networking
import qs.Services.Noctalia
import qs.Services.Power
import qs.Services.System
import qs.Services.Theming
import qs.Services.UI

ShellRoot {
  id: shellRoot

  property bool i18nLoaded: false
  property bool shellStateLoaded: false

  Component.onCompleted: {
    Logger.i("Shell", "---------------------------");
    Logger.i("Shell", "Noctalia Hello!");
  }

  Connections {
    target: Quickshell
    function onReloadCompleted() {
      Quickshell.inhibitReloadPopup();
    }
    function onReloadFailed() {
      if (!Settings || !Settings.isDebug) {
        Quickshell.inhibitReloadPopup();
      }
    }
  }

  Connections {
    target: I18n ? I18n : null
    function onTranslationsLoaded() {
      i18nLoaded = true;
    }
  }

  Connections {
    target: ShellState ? ShellState : null
    function onIsLoadedChanged() {
      if (ShellState.isLoaded) {
        shellStateLoaded = true;
      }
    }
  }

  Variants {
    model: Settings.bootstrapState === Settings.Error ? Quickshell.screens : []

    delegate: SettingsLoadError {
      required property ShellScreen modelData
      targetScreen: modelData
      message: Settings.errorMessage
      settingsPath: Settings.settingsFile
      onRetryRequested: Settings.retryBootstrap()
    }
  }

  Loader {
    active: i18nLoaded && Settings.ready && shellStateLoaded

    sourceComponent: Item {
      Component.onCompleted: {
        Logger.i("Shell", "---------------------------");
        WallpaperService.init();
        AppThemeService.init();
        ColorSchemeService.init();
        LocationService.init();
        NightLightService.apply();
        DarkModeService.init();
        HooksService.init();
        BluetoothService.init();
        IdleInhibitorService.init();
        PowerProfileService.init();
        HostService.init();
        FontService.init();
        GitHubService.init();
        UpdateService.init();
        UpdateService.showLatestChangelog();

        checkSetupWizard();
      }

      Overview {}
      Background {}
      AllScreens {}
      Dock {}
      Notification {}
      ToastOverlay {}
      OSD {}

      LockScreen {}

      // IPCService is treated as a service but it's actually an Item that needs to exists in the shell.
      IPCService {}
    }
  }

  // ---------------------------------------------
  // Setup Wizard
  // ---------------------------------------------
  Connections {
    target: HostService
    function onIsReadyChanged() {
      shellRoot.checkSetupWizard();
    }
    function onOsInfoLoadFailedChanged() {
      shellRoot.checkSetupWizard();
    }
  }

  Timer {
    id: setupWizardTimer
    running: false
    interval: 1000
    onTriggered: {
      showSetupWizard();
    }
  }

  function checkSetupWizard() {
    // Only open the setup wizard for new users
    if (!Settings.shouldOpenSetupWizard) {
      return;
    }

    // Host state changes call this function again when metadata becomes ready.
    if (!HostService.isReady) {
      return;
    }

    // No setup wizard on NixOS
    if (HostService.isNixOS) {
      return;
    }

    setupWizardTimer.start();
  }

  function showSetupWizard() {
    if (!Settings.shouldOpenSetupWizard || !HostService.isReady || HostService.isNixOS) {
      return;
    }

    // Open Setup Wizard as a panel in the same windowing system as Settings/ControlCenter
    if (Quickshell.screens.length > 0) {
      var targetScreen = Quickshell.screens[0];
      var setupPanel = PanelService.getPanel("setupWizardPanel", targetScreen);
      if (setupPanel) {
        setupPanel.open();
      } else {
        // If not yet loaded, ensure it loads and try again shortly
        setupWizardTimer.restart();
      }
    }
  }
}
