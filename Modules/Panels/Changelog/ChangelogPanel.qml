pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.Noctalia
import qs.Services.UI
import qs.Widgets

SmartPanel {
  id: root

  readonly property string currentVersion: UpdateService.changelogCurrentVersion || UpdateService.currentVersion
  readonly property string previousVersion: UpdateService.previousVersion
  readonly property bool hasPreviousVersion: previousVersion && previousVersion.length > 0
  readonly property var releaseHighlights: UpdateService.releaseHighlights || []
  readonly property string subtitleText: hasPreviousVersion ? I18n.tr("changelog.panel.subtitle.updated", {
    "previousVersion": previousVersion
  }) : I18n.tr("changelog.panel.subtitle.fresh")

  function headingLevel(text) {
    if (!text)
      return 0;

    const trimmed = text.trim();
    if (trimmed.length === 0)
      return 0;

    const match = trimmed.match(/^(#+)\s+/);
    if (!match)
      return 0;

    return Math.min(match[1].length, 2);
  }

  function formatReleaseDate(dateString) {
    if (!dateString || dateString.length === 0)
      return "";

    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime()))
        return dateString;

      return date.toLocaleDateString(Qt.locale());
    } catch (error) {
      return dateString;
    }
  }

  preferredWidth: Math.round(820 * Style.uiScaleRatio)
  preferredHeight: Math.round(620 * Style.uiScaleRatio)
  panelAnchorHorizontalCenter: true
  panelAnchorVerticalCenter: true
  onClosed: {
    if (UpdateService && UpdateService.changelogCurrentVersion)
      UpdateService.markChangelogSeen(UpdateService.changelogCurrentVersion);
  }

  panelContent: Rectangle {
    color: NColor.mSurfaceVariant
    radius: Style.radiusM
    border.color: NColor.mOutline
    border.width: Style.borderS

    ColumnLayout {
      anchors.fill: parent
      anchors.margins: Style.marginL
      spacing: Style.marginM

      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        NIcon {
          icon: "sparkles"
          color: NColor.mPrimary
          pointSize: Style.fontSizeXXL
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.marginXS

          NText {
            text: I18n.tr("changelog.panel.title", {
              "version": root.currentVersion || UpdateService.currentVersion
            })
            pointSize: Style.fontSizeXL
            font.weight: Style.fontWeightBold
            color: NColor.mPrimary
            wrapMode: Text.WordWrap
          }

          NText {
            text: root.subtitleText
            color: NColor.mOnSurface
            opacity: Style.opacityMedium
            wrapMode: Text.WordWrap
          }
        }

        Item {
          Layout.fillWidth: true
        }

        NIconButton {
          icon: "close"
          tooltipText: I18n.tr("tooltips.close")
          onClicked: root.close()
          Layout.alignment: Qt.AlignTop | Qt.AlignRight
          Layout.preferredHeight: Style.baseWidgetSize
          Layout.preferredWidth: Style.baseWidgetSize
        }
      }

      Rectangle {
        clip: true
        Layout.fillWidth: true
        color: Qt.alpha(NColor.mPrimary, 0.08)
        radius: Style.radiusS
        border.color: NColor.mPrimary
        border.width: Style.borderS

        RowLayout {
          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginS

          NText {
            text: root.hasPreviousVersion ? root.previousVersion : I18n.tr("changelog.panel.version.new-user")
            font.weight: Style.fontWeightSemiBold
            color: NColor.mPrimary
          }

          NIcon {
            icon: "arrow-right"
            color: NColor.mPrimary
          }

          NText {
            text: root.currentVersion || UpdateService.currentVersion
            font.weight: Style.fontWeightSemiBold
            color: NColor.mPrimary
          }
        }
      }

      NDivider {
        Layout.fillWidth: true
      }

      NScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        horizontalPolicy: ScrollBar.AlwaysOff
        verticalPolicy: ScrollBar.AsNeeded
        padding: 0

        ColumnLayout {
          width: parent.width
          spacing: Style.marginM

          NText {
            visible: UpdateService.fetchError !== ""
            text: UpdateService.fetchError
            color: NColor.mError
            wrapMode: Text.WordWrap
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.marginS

            Repeater {
              model: root.releaseHighlights

              delegate: ColumnLayout {
                id: releaseSection

                required property var entries

                width: parent.width
                spacing: Style.marginXS

                Repeater {
                  model: releaseSection.entries

                  delegate: NText {
                    required property string modelData
                    readonly property int headingLevel: root.headingLevel(modelData)

                    text: {
                      if (modelData.length === 0)
                        return "\u00A0";

                      if (headingLevel > 0)
                        return modelData.replace(/^#+\s+/, "");

                      return modelData;
                    }
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                    textFormat: Text.PlainText
                    color: headingLevel > 0 ? NColor.mPrimary : NColor.mOnSurface
                    font.weight: headingLevel > 0 ? Style.fontWeightBold : Style.fontWeightMedium
                    pointSize: headingLevel === 1 ? Style.fontSizeXXL : headingLevel === 2 ? Style.fontSizeXL : Style.fontSizeM
                    Layout.fillWidth: true
                  }
                }
              }
            }
          }

          NText {
            visible: root.releaseHighlights.length === 0
            text: I18n.tr("changelog.panel.empty")
            color: NColor.mOnSurfaceVariant
            wrapMode: Text.WordWrap
          }
        }
      }

      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginS

        NButton {
          Layout.fillWidth: true
          icon: "brand-discord"
          text: I18n.tr("changelog.panel.buttons.discord")
          outlined: true
          onClicked: UpdateService.openDiscord()
        }

        NButton {
          Layout.fillWidth: true
          visible: UpdateService.feedbackUrl !== ""
          icon: "forms"
          text: I18n.tr("changelog.panel.buttons.feedback")
          outlined: true
          onClicked: UpdateService.openFeedbackForm()
        }

        NButton {
          Layout.fillWidth: true
          icon: "check"
          text: I18n.tr("changelog.panel.buttons.dismiss")
          onClicked: root.close()
        }
      }
    }
  }
}
