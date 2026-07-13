import Quickshell.Io
import "../Helpers/SettingsDefaults.js" as SettingsDefaults
import qs.Modules.OSD

JsonAdapter {
  property int settingsVersion: 26

  // bar
  property JsonObject bar: JsonObject {
    property string position: "top" // "top", "bottom", "left", or "right"
    property real backgroundOpacity: 1.0
    property var monitors: [] // holds bar visibility per monitor
    property string density: "default" // "compact", "default", "comfortable"
    property bool showCapsule: true
    property real capsuleOpacity: 1.0

    // Floating bar settings
    property bool floating: false
    property real marginVertical: 0.25
    property real marginHorizontal: 0.25

    // Bar outer corners (inverted/concave corners at bar edges when not floating)
    property bool outerCorners: true

    // Reserves space with compositor
    property bool exclusive: true

    // Widget configuration for modular bar system
    property JsonObject widgets
    widgets: JsonObject {
      property var left: [
        {
          "icon": "rocket",
          "id": "CustomButton",
          "leftClickExec": "qs -c noctalia-shell ipc call launcher toggle"
        },
        {
          "id": "Clock",
          "usePrimaryColor": false
        },
        {
          "id": "SystemMonitor"
        },
        {
          "id": "ActiveWindow"
        },
        {
          "id": "MediaMini"
        }
      ]
      property var center: [
        {
          "id": "Workspace"
        }
      ]
      property var right: [
        {
          "id": "ScreenRecorder"
        },
        {
          "id": "Tray"
        },
        {
          "id": "NotificationHistory"
        },
        {
          "id": "Battery"
        },
        {
          "id": "Volume"
        },
        {
          "id": "Brightness"
        },
        {
          "id": "ControlCenter"
        }
      ]
    }
  }

  // general
  property JsonObject general: JsonObject {
    property string avatarImage: ""
    property real dimmerOpacity: 0.6
    property bool showScreenCorners: false
    property bool forceBlackScreenCorners: false
    property real scaleRatio: 1.0
    property real radiusRatio: 1.0
    property real screenRadiusRatio: 1.0
    property real animationSpeed: 1.0
    property bool animationDisabled: false
    property bool compactLockScreen: false
    property bool lockOnSuspend: true
    property bool showHibernateOnLockScreen: false
    property bool enableShadows: true
    property string shadowDirection: "bottom_right"
    property int shadowOffsetX: 2
    property int shadowOffsetY: 3
    property string language: ""
    property bool allowPanelsOnScreenWithoutBar: true
  }

  // ui
  property JsonObject ui: JsonObject {
    property string fontDefault: ""
    property string fontFixed: ""
    property real fontDefaultScale: 1.0
    property real fontFixedScale: 1.0
    property bool tooltipsEnabled: true
    property real panelBackgroundOpacity: 1.0
    property bool panelsAttachedToBar: true
    property bool settingsPanelAttachToBar: false
  }

  // location
  property JsonObject location: JsonObject {
    property string name: SettingsDefaults.defaultLocation
    property bool weatherEnabled: true
    property bool weatherShowEffects: true
    property bool useFahrenheit: false
    property bool use12hourFormat: false
    property bool showWeekNumberInCalendar: false
    property bool showCalendarEvents: true
    property bool showCalendarWeather: true
    property bool analogClockInCalendar: false
    property int firstDayOfWeek: -1 // -1 = auto (use locale), 0 = Sunday, 1 = Monday, 6 = Saturday
  }

  // calendar
  property JsonObject calendar: JsonObject {
    property var cards: [
      {
        "id": "calendar-header-card",
        "enabled": true
      },
      {
        "id": "calendar-month-card",
        "enabled": true
      },
      {
        "id": "timer-card",
        "enabled": true
      },
      {
        "id": "weather-card",
        "enabled": true
      }
    ]
  }

  // screen recorder
  property JsonObject screenRecorder: JsonObject {
    property string directory: ""
    property int frameRate: 60
    property string audioCodec: "opus"
    property string videoCodec: "h264"
    property string quality: "very_high"
    property string colorRange: "limited"
    property bool showCursor: true
    property string audioSource: "default_output"
    property string videoSource: "eDP-1"
  }

  // wallpaper
  property JsonObject wallpaper: JsonObject {
    property bool enabled: true
    property bool overviewEnabled: false
    property string directory: ""
    property var monitorDirectories: []
    property bool enableMultiMonitorDirectories: false
    property bool recursiveSearch: false
    property bool setWallpaperOnAllMonitors: true
    property string fillMode: "crop"
    property string fillColor: "#000000"
    property bool randomEnabled: false
    property int randomIntervalSec: 300 // 5 min
    property int transitionDuration: 1500 // 1500 ms
    property string transitionType: "none"
    property real transitionEdgeSmoothness: 0.05
    property string panelPosition: "follow_bar"
    property bool hideWallpaperFilenames: false
    // Wallhaven settings
    property bool useWallhaven: false
    property string wallhavenQuery: ""
    property string wallhavenSorting: "relevance"
    property string wallhavenOrder: "desc"
    property string wallhavenCategories: "111" // general,anime,people
    property string wallhavenPurity: "100" // sfw only
    property string wallhavenResolutionMode: "atleast" // "atleast" or "exact"
    property string wallhavenResolutionWidth: ""
    property string wallhavenResolutionHeight: ""
  }

  // applauncher
  property JsonObject appLauncher: JsonObject {
    property bool enableClipboardHistory: false
    property bool enableClipPreview: true
    // Position: center, top_left, top_right, bottom_left, bottom_right, bottom_center, top_center
    property string position: "center"
    property var pinnedExecs: []
    property bool useApp2Unit: false
    property bool sortByMostUsed: true
    property string terminalCommand: "xterm -e"
    property bool customLaunchPrefixEnabled: false
    property string customLaunchPrefix: ""
    // View mode: "list" or "grid"
    property string viewMode: "list"
  }

  // control center
  property JsonObject controlCenter: JsonObject {
    // Position: close_to_bar_button, center, top_left, top_right, bottom_left, bottom_right, bottom_center, top_center
    property string position: "close_to_bar_button"
    property JsonObject shortcuts
    shortcuts: JsonObject {
      property var left: [
        {
          "id": "WiFi"
        },
        {
          "id": "Bluetooth"
        },
        {
          "id": "ScreenRecorder"
        },
        {
          "id": "WallpaperSelector"
        }
      ]
      property var right: [
        {
          "id": "Notifications"
        },
        {
          "id": "PowerProfile"
        },
        {
          "id": "KeepAwake"
        },
        {
          "id": "NightLight"
        }
      ]
    }
    property var cards: [
      {
        "id": "profile-card",
        "enabled": true
      },
      {
        "id": "shortcuts-card",
        "enabled": true
      },
      {
        "id": "audio-card",
        "enabled": true
      },
      {
        "id": "weather-card",
        "enabled": true
      },
      {
        "id": "media-sysmon-card",
        "enabled": true
      }
    ]
  }

  // system monitor
  property JsonObject systemMonitor: JsonObject {
    property int cpuWarningThreshold: 80
    property int cpuCriticalThreshold: 90
    property int tempWarningThreshold: 80
    property int tempCriticalThreshold: 90
    property int memWarningThreshold: 80
    property int memCriticalThreshold: 90
    property int diskWarningThreshold: 80
    property int diskCriticalThreshold: 90
    property int cpuPollingInterval: 10000
    property int tempPollingInterval: 30000
    property int memPollingInterval: 10000
    property int diskPollingInterval: 30000
    property int networkPollingInterval: 10000
    property bool useCustomColors: false
    property string warningColor: ""
    property string criticalColor: ""
  }

  // dock
  property JsonObject dock: JsonObject {
    property bool enabled: true
    property string displayMode: "auto_hide" // "always_visible", "auto_hide", "exclusive"
    property real backgroundOpacity: 1.0
    property real floatingRatio: 1.0
    property real size: 1
    property bool onlySameOutput: true
    property var monitors: [] // holds dock visibility per monitor
    // Desktop entry IDs pinned to the dock (e.g., "org.kde.konsole", "firefox.desktop")
    property var pinnedApps: []
    property bool colorizeIcons: false
  }

  // network
  property JsonObject network: JsonObject {
    property bool wifiEnabled: true
  }

  // session menu
  property JsonObject sessionMenu: JsonObject {
    property bool enableCountdown: true
    property int countdownDuration: 10000
    property string position: "center"
    property bool showHeader: true
    property var powerOptions: [
      {
        "action": "lock",
        "enabled": true
      },
      {
        "action": "suspend",
        "enabled": true
      },
      {
        "action": "hibernate",
        "enabled": true
      },
      {
        "action": "reboot",
        "enabled": true
      },
      {
        "action": "logout",
        "enabled": true
      },
      {
        "action": "shutdown",
        "enabled": true
      }
    ]
  }

  // notifications
  property JsonObject notifications: JsonObject {
    property bool enabled: true
    property var monitors: [] // holds notifications visibility per monitor
    property string location: "top_right"
    property bool overlayLayer: true
    property real backgroundOpacity: 1.0
    property bool respectExpireTimeout: false
    property int lowUrgencyDuration: 3
    property int normalUrgencyDuration: 8
    property int criticalUrgencyDuration: 15
    property bool enableKeyboardLayoutToast: true
  }

  // on-screen display
  property JsonObject osd: JsonObject {
    property bool enabled: true
    property string location: "top_right"
    property int autoHideMs: 2000
    property bool overlayLayer: true
    property real backgroundOpacity: 1.0
    property var enabledTypes: [OSD.Type.Volume, OSD.Type.InputVolume, OSD.Type.Brightness]
    property var monitors: [] // holds osd visibility per monitor
  }

  // audio
  property JsonObject audio: JsonObject {
    property int volumeStep: 5
    property bool volumeOverdrive: false
    property int cavaFrameRate: 30
    property string visualizerType: "linear"
    property string visualizerQuality: "high"
    property var mprisBlacklist: []
    property string preferredPlayer: ""
    property string externalMixer: "pwvucontrol || pavucontrol"
  }

  // brightness
  property JsonObject brightness: JsonObject {
    property int brightnessStep: 5
    property bool enforceMinimum: true
    property bool enableDdcSupport: false
  }

  property JsonObject colorSchemes: JsonObject {
    property bool useWallpaperColors: false
    property string predefinedScheme: "Noctalia (default)"
    property bool darkMode: true
    property string schedulingMode: "off"
    property string manualSunrise: "06:30"
    property string manualSunset: "18:30"
    property string matugenSchemeType: "scheme-fruit-salad"
    property bool generateTemplatesForPredefined: true
  }

  // templates toggles
  property JsonObject templates: JsonObject {
    property bool gtk: false
    property bool qt: false
    property bool kcolorscheme: false
    property bool alacritty: false
    property bool kitty: false
    property bool ghostty: false
    property bool foot: false
    property bool wezterm: false
    property bool fuzzel: false
    property bool discord: false
    property bool pywalfox: false
    property bool vicinae: false
    property bool walker: false
    property bool code: false
    property bool spicetify: false
    property bool telegram: false
    property bool cava: false
    property bool emacs: false
    property bool niri: false
    property bool enableUserTemplates: false
  }

  // night light
  property JsonObject nightLight: JsonObject {
    property bool enabled: false
    property bool forced: false
    property bool autoSchedule: true
    property string nightTemp: "4000"
    property string dayTemp: "6500"
    property string manualSunrise: "06:30"
    property string manualSunset: "18:30"
  }

  property JsonObject changelog: JsonObject {
    property string lastSeenVersion: ""
  }

  // hooks
  property JsonObject hooks: JsonObject {
    property bool enabled: false
    property string wallpaperChange: ""
    property string darkModeChange: ""
  }
}
