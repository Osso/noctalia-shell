import QtQuick
import qs.Commons

// Rounded group container using the variant surface color.
// To be used in side panels and settings panes to group fields or buttons.
Rectangle {
  id: root

  color: NColor.mSurfaceVariant
  radius: Style.radiusM
  border.color: NColor.mOutline
  border.width: Style.borderS
}
