import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Services.System
import qs.Services.Theming
import qs.Widgets

ColumnLayout {
  id: root
  spacing: Style.marginM

  function extractSchemeName(path) {
    var basename = path.split('/').pop();
    return basename.replace('.json', '');
  }

  // Cache for scheme colors (mirrors ColorSchemeTab approach)
  property var schemeColorsCache: ({})
  property int cacheVersion: 0

  function getSchemeColor(schemeName, key) {
    try {
      const mode = Settings.data.colorSchemes.darkMode ? "dark" : "light";
      const data = schemeColorsCache[schemeName];
      if (data && data[mode] && data[mode][key])
        return data[mode][key];
    } catch (e) {}
    return NColor.mSurfaceVariant;
  }

  // Match ColorSchemeTab helpers
  function schemeLoaded(schemeName, jsonData) {
    var value = jsonData || {};
    schemeColorsCache[schemeName] = value;
    cacheVersion++;
    Logger.i("SetupAppearanceStep", `Loaded scheme ${schemeName}`);
  }

  Connections {
    target: ColorSchemeService
    function onSchemesChanged() {
      Logger.i("SetupAppearanceStep", `Color schemes changed: ${ColorSchemeService.schemes.length}`);
      root.schemeColorsCache = {};
      root.cacheVersion++;
    }
  }

  // Beautiful header with icon
  RowLayout {
    Layout.fillWidth: true
    Layout.bottomMargin: Style.marginL
    spacing: Style.marginM

    Rectangle {
      Layout.preferredWidth: 40
      Layout.preferredHeight: 40
      radius: Style.radiusL
      color: NColor.mSurfaceVariant
      opacity: 0.6

      NIcon {
        icon: "palette"
        pointSize: Style.fontSizeL
        color: NColor.mPrimary
        anchors.centerIn: parent
      }
    }

    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.marginXS

      NText {
        text: I18n.tr("setup.appearance.header")
        pointSize: Style.fontSizeXL
        font.weight: Style.fontWeightBold
        color: NColor.mPrimary
      }

      NText {
        text: I18n.tr("setup.appearance.subheader")
        pointSize: Style.fontSizeM
        color: NColor.mOnSurfaceVariant
      }
    }
  }

  ScrollView {
    Layout.fillWidth: true
    Layout.fillHeight: true
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    ColumnLayout {
      width: parent.width
      spacing: Style.marginM

      // Dark Mode Toggle
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        Rectangle {
          Layout.preferredWidth: 28
          Layout.preferredHeight: 28
          radius: Style.radiusM
          color: NColor.mSurface

          NIcon {
            icon: "moon"
            pointSize: Style.fontSizeL
            color: NColor.mPrimary
            anchors.centerIn: parent
          }
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: 2

          NText {
            text: I18n.tr("settings.color-scheme.dark-mode.switch.label")
            pointSize: Style.fontSizeL
            font.weight: Style.fontWeightBold
            color: NColor.mOnSurface
          }

          NText {
            text: I18n.tr("settings.color-scheme.dark-mode.switch.description")
            pointSize: Style.fontSizeS
            color: NColor.mOnSurfaceVariant
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
          }
        }

        NToggle {
          checked: Settings.data.colorSchemes.darkMode
          onToggled: checked => Settings.data.colorSchemes.darkMode = checked
        }
      }

      // Divider
      Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: NColor.mOutline
        opacity: 0.2
        Layout.topMargin: Style.marginS
        Layout.bottomMargin: Style.marginS
      }

      // Wallpaper Colors Toggle
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        Rectangle {
          Layout.preferredWidth: 28
          Layout.preferredHeight: 28
          radius: Style.radiusM
          color: NColor.mSurface

          NIcon {
            icon: ProgramCheckerService.matugenAvailable ? "color-picker" : "alert-triangle"
            pointSize: Style.fontSizeL
            color: NColor.mPrimary
            anchors.centerIn: parent
          }
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: 2

          NText {
            text: I18n.tr("settings.color-scheme.color-source.use-wallpaper-colors.label")
            pointSize: Style.fontSizeL
            font.weight: Style.fontWeightBold
            color: NColor.mOnSurface
          }

          NText {
            text: I18n.tr("settings.color-scheme.color-source.use-wallpaper-colors.description")
            pointSize: Style.fontSizeS
            color: NColor.mOnSurfaceVariant
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
          }
        }

        NToggle {
          enabled: ProgramCheckerService.matugenAvailable
          checked: Settings.data.colorSchemes.useWallpaperColors && ProgramCheckerService.matugenAvailable
          onToggled: checked => {
            if (!ProgramCheckerService.matugenAvailable)
              return;
            if (checked) {
              Settings.data.colorSchemes.useWallpaperColors = true;
              AppThemeService.generate();
            } else {
              Settings.data.colorSchemes.useWallpaperColors = false;
              if (Settings.data.colorSchemes.predefinedScheme) {
                ColorSchemeService.applyScheme(Settings.data.colorSchemes.predefinedScheme);
              }
            }
          }
        }
      }

      // Matugen scheme type (visible when wallpaper colors enabled and matugen available)
      ColumnLayout {
        Layout.fillWidth: true
        spacing: Style.marginM
        visible: Settings.data.colorSchemes.useWallpaperColors && ProgramCheckerService.matugenAvailable

        RowLayout {
          Layout.fillWidth: true
          spacing: Style.marginS

          Rectangle {
            Layout.preferredWidth: 28
            Layout.preferredHeight: 28
            radius: Style.radiusM
            color: NColor.mSurface

            NIcon {
              icon: "wand"
              pointSize: Style.fontSizeL
              color: NColor.mPrimary
              anchors.centerIn: parent
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            NText {
              text: I18n.tr("settings.color-scheme.color-source.matugen-scheme-type.label")
              pointSize: Style.fontSizeL
              font.weight: Style.fontWeightBold
              color: NColor.mOnSurface
            }

            NText {
              text: I18n.tr("settings.color-scheme.color-source.use-wallpaper-colors.description")
              pointSize: Style.fontSizeS
              color: NColor.mOnSurfaceVariant
            }
          }
        }

        // Matugen scheme options styled like bar position buttons
        GridLayout {
          Layout.fillWidth: true
          columns: 2
          rowSpacing: Style.marginS
          columnSpacing: Style.marginS

          Repeater {
            model: [
              {
                "key": "scheme-content",
                "name": "Content"
              },
              {
                "key": "scheme-expressive",
                "name": "Expressive"
              },
              {
                "key": "scheme-fidelity",
                "name": "Fidelity"
              },
              {
                "key": "scheme-fruit-salad",
                "name": "Fruit Salad"
              },
              {
                "key": "scheme-monochrome",
                "name": "Monochrome"
              },
              {
                "key": "scheme-neutral",
                "name": "Neutral"
              },
              {
                "key": "scheme-rainbow",
                "name": "Rainbow"
              },
              {
                "key": "scheme-tonal-spot",
                "name": "Tonal Spot"
              }
            ]
            delegate: Rectangle {
              id: matugenOption
              required property string key
              required property string name

              Layout.fillWidth: true
              Layout.preferredHeight: 48
              radius: Style.radiusM
              border.width: Style.borderS

              property bool isActive: Settings.data.colorSchemes.matugenSchemeType === key

              color: (hoverHandler.hovered || isActive) ? NColor.mPrimary : NColor.mSurfaceVariant
              border.color: (hoverHandler.hovered || isActive) ? NColor.mPrimary : NColor.mOutline
              opacity: (hoverHandler.hovered || isActive) ? 1.0 : 0.8

              NText {
                text: matugenOption.name
                pointSize: Style.fontSizeM
                font.weight: (hoverHandler.hovered || parent.isActive) ? Style.fontWeightBold : Style.fontWeightMedium
                color: (hoverHandler.hovered || parent.isActive) ? NColor.mOnPrimary : NColor.mOnSurface
                anchors.centerIn: parent
              }

              HoverHandler {
                id: hoverHandler
              }
              MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                  Settings.data.colorSchemes.matugenSchemeType = matugenOption.key;
                  AppThemeService.generate();
                }
              }

              Behavior on color {
                ColorAnimation {
                  duration: Style.animationFast
                }
              }
              Behavior on border.color {
                ColorAnimation {
                  duration: Style.animationFast
                }
              }
              Behavior on opacity {
                NumberAnimation {
                  duration: Style.animationFast
                }
              }
            }
          }
        }
      }

      // Divider
      Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: NColor.mOutline
        opacity: 0.2
        Layout.topMargin: Style.marginS
        Layout.bottomMargin: Style.marginS
        visible: !Settings.data.colorSchemes.useWallpaperColors
      }

      // Predefined schemes section (visible when wallpaper colors disabled)
      ColumnLayout {
        Layout.fillWidth: true
        spacing: Style.marginM
        visible: !Settings.data.colorSchemes.useWallpaperColors

        RowLayout {
          Layout.fillWidth: true
          spacing: Style.marginS

          Rectangle {
            Layout.preferredWidth: 28
            Layout.preferredHeight: 28
            radius: Style.radiusM
            color: NColor.mSurface

            NIcon {
              icon: "palette"
              pointSize: Style.fontSizeL
              color: NColor.mPrimary
              anchors.centerIn: parent
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            NText {
              text: I18n.tr("settings.color-scheme.predefined.section.label")
              pointSize: Style.fontSizeL
              font.weight: Style.fontWeightBold
              color: NColor.mOnSurface
            }

            NText {
              text: I18n.tr("settings.color-scheme.predefined.section.description")
              pointSize: Style.fontSizeS
              color: NColor.mOnSurfaceVariant
            }
          }
        }

        // Predefined schemes Grid (matches ColorSchemeTab)
        GridLayout {
          id: schemesGrid
          columns: Math.max(2, Math.floor((parent.width - Style.marginM * 2) / 180))
          rowSpacing: Style.marginM
          columnSpacing: Style.marginM
          Layout.fillWidth: true

          Repeater {
            model: ColorSchemeService.schemes.map(path => ({
              schemePath: path,
              appearanceOwner: root
            }))

            delegate: Rectangle {
              id: schemeItem

              required property string schemePath
              required property var appearanceOwner
              property string schemeName: schemeItem.appearanceOwner.extractSchemeName(schemeItem.schemePath)

              Layout.fillWidth: true
              Layout.alignment: Qt.AlignHCenter
              height: 50
              radius: Style.radiusS
              color: schemeItem.appearanceOwner.cacheVersion >= 0 ? schemeItem.appearanceOwner.getSchemeColor(schemeName, "mSurface") : schemeItem.appearanceOwner.getSchemeColor(schemeName, "mSurface")
              border.width: Style.borderL
              border.color: itemMouseArea.containsMouse ? NColor.mHover : (Settings.data.colorSchemes.predefinedScheme === schemeName ? NColor.mSecondary : NColor.mOutline)

              RowLayout {
                anchors.fill: parent
                anchors.margins: Style.marginL
                spacing: Style.marginXS

                NText {
                  text: schemeItem.schemeName
                  pointSize: Style.fontSizeS
                  font.weight: Style.fontWeightMedium
                  color: NColor.mOnSurface
                  Layout.fillWidth: true
                  elide: Text.ElideRight
                  verticalAlignment: Text.AlignVCenter
                  wrapMode: Text.WordWrap
                  maximumLineCount: 1
                }

                Rectangle {
                  Layout.preferredWidth: 14
                  Layout.preferredHeight: 14
                  radius: width * 0.5
                  color: schemeItem.appearanceOwner.cacheVersion >= 0 ? (function () {
                    var mode = Settings.data.colorSchemes.darkMode ? "dark" : "light";
                    var cached = schemeItem.appearanceOwner.schemeColorsCache[schemeItem.schemeName];
                    return (cached && cached[mode] && cached[mode].mPrimary) || schemeItem.appearanceOwner.getSchemeColor(schemeItem.schemeName, "mPrimary");
                  })() : NColor.mPrimary
                }
                Rectangle {
                  Layout.preferredWidth: 14
                  Layout.preferredHeight: 14
                  radius: width * 0.5
                  color: schemeItem.appearanceOwner.cacheVersion >= 0 ? (function () {
                    var mode = Settings.data.colorSchemes.darkMode ? "dark" : "light";
                    var cached = schemeItem.appearanceOwner.schemeColorsCache[schemeItem.schemeName];
                    return (cached && cached[mode] && cached[mode].mSecondary) || schemeItem.appearanceOwner.getSchemeColor(schemeItem.schemeName, "mSecondary");
                  })() : NColor.mSecondary
                }
                Rectangle {
                  Layout.preferredWidth: 14
                  Layout.preferredHeight: 14
                  radius: width * 0.5
                  color: schemeItem.appearanceOwner.cacheVersion >= 0 ? (function () {
                    var mode = Settings.data.colorSchemes.darkMode ? "dark" : "light";
                    var cached = schemeItem.appearanceOwner.schemeColorsCache[schemeItem.schemeName];
                    return (cached && cached[mode] && cached[mode].mTertiary) || schemeItem.appearanceOwner.getSchemeColor(schemeItem.schemeName, "mTertiary");
                  })() : NColor.mTertiary
                }
                Rectangle {
                  Layout.preferredWidth: 14
                  Layout.preferredHeight: 14
                  radius: width * 0.5
                  color: schemeItem.appearanceOwner.cacheVersion >= 0 ? (function () {
                    var mode = Settings.data.colorSchemes.darkMode ? "dark" : "light";
                    var cached = schemeItem.appearanceOwner.schemeColorsCache[schemeItem.schemeName];
                    return (cached && cached[mode] && cached[mode].mError) || schemeItem.appearanceOwner.getSchemeColor(schemeItem.schemeName, "mError");
                  })() : NColor.mError
                }
              }

              MouseArea {
                id: itemMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                  Settings.data.colorSchemes.useWallpaperColors = false;
                  Settings.data.colorSchemes.predefinedScheme = schemeItem.schemeName;
                  ColorSchemeService.applyScheme(Settings.data.colorSchemes.predefinedScheme);
                }
              }
            }
          }
        }
      }

      // Bottom spacer
      Item {
        Layout.fillWidth: true
        Layout.preferredHeight: Style.marginL
      }
    }
  }

  // Hidden loader to populate schemeColorsCache from files
  Item {
    visible: false
    Repeater {
      model: ColorSchemeService.schemes.map(path => ({
        schemePath: path,
        appearanceOwner: root
      }))
      delegate: Item {
        id: schemeLoader
        required property string schemePath
        required property var appearanceOwner

        FileView {
          id: schemeFile
          path: schemeLoader.schemePath
          blockLoading: false
          onLoaded: {
            const schemeName = schemeLoader.appearanceOwner.extractSchemeName(schemeFile.path);
            try {
              const jsonData = JSON.parse(schemeFile.text());
              schemeLoader.appearanceOwner.schemeLoaded(schemeName, jsonData);
            } catch (e) {
              schemeLoader.appearanceOwner.schemeLoaded(schemeName, null);
            }
          }
        }
      }
    }
  }
}
