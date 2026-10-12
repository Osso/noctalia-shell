import QtQuick

// Screen-space geometry and per-corner states consumed by background paths.
// -1: square, 0: inner curve, 1: X inversion, 2: Y inversion.
Item {
  property int topLeftCornerState: 0
  property int topRightCornerState: 0
  property int bottomRightCornerState: 0
  property int bottomLeftCornerState: 0
}
