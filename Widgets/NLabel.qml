import QtQuick
import QtQuick.Layouts
import qs.Commons

ColumnLayout {
  id: root

  property string label: ""
  property string description: ""
  property color labelColor: NColor.mOnSurface
  property color descriptionColor: NColor.mOnSurfaceVariant

  spacing: Style.marginXXS
  Layout.fillWidth: true

  NText {
    text: root.label
    pointSize: Style.fontSizeL
    font.weight: Style.fontWeightSemiBold
    color: root.labelColor
    visible: root.label !== ""
    Layout.fillWidth: true
  }

  NText {
    text: root.description
    pointSize: Style.fontSizeS
    color: root.descriptionColor
    wrapMode: Text.WordWrap
    visible: root.description !== ""
    Layout.fillWidth: true
    // allow HTML like <i>...</i> in labels/descriptions
    textFormat: Text.StyledText
  }
}
