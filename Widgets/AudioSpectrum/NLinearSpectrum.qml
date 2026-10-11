pragma ComponentBehavior: Bound

import QtQuick
import qs.Commons

Item {
  id: root
  property color fillColor: NColor.mPrimary
  property color strokeColor: NColor.mOnSurface
  property int strokeWidth: 0
  property var values: []
  property bool vertical: false

  // Minimum signal properties
  property bool showMinimumSignal: false
  property real minimumSignalValue: 0.05 // Default to 5% of height

  // Pre compute horizontal mirroring
  readonly property int valuesCount: (values && Array.isArray(values)) ? values.length : 0
  readonly property int totalBars: valuesCount * 2
  readonly property real barSlotSize: totalBars > 0 ? (vertical ? height : width) / totalBars : 0
  readonly property bool highQuality: (Settings.data.audio.visualizerType === "low") ? false : true

  Repeater {
    model: root.totalBars

    Rectangle {
      id: bar
      required property int index
      readonly property NLinearSpectrum spectrum: root
      // The first half of bars are a mirror image (reversed values array).
      // The second half of bars are in normal order.
      property int valueIndex: bar.index < bar.spectrum.valuesCount ? bar.spectrum.valuesCount - 1 - bar.index // Mirrored half
      : bar.index - bar.spectrum.valuesCount // Normal half

      property real rawAmp: (bar.spectrum.values && bar.spectrum.values[bar.valueIndex] !== undefined) ? bar.spectrum.values[bar.valueIndex] : 0
      property real amp: (bar.spectrum.showMinimumSignal && bar.rawAmp === 0) ? bar.spectrum.minimumSignalValue : bar.rawAmp

      color: bar.spectrum.fillColor
      border.color: bar.spectrum.strokeColor
      border.width: bar.spectrum.strokeWidth
      antialiasing: bar.spectrum.highQuality
      smooth: bar.spectrum.highQuality

      // Only update when value actually changes - reduces GPU load
      width: bar.spectrum.vertical ? bar.spectrum.width * bar.amp : bar.spectrum.barSlotSize * 0.5
      height: bar.spectrum.vertical ? bar.spectrum.barSlotSize * 0.5 : bar.spectrum.height * bar.amp
      x: bar.spectrum.vertical ? bar.spectrum.width - bar.width : bar.index * bar.spectrum.barSlotSize + (bar.spectrum.barSlotSize * 0.25)
      y: bar.spectrum.vertical ? bar.index * bar.spectrum.barSlotSize + (bar.spectrum.barSlotSize * 0.25) : bar.spectrum.height - bar.height

      // Disable updates when invisible to save GPU
      visible: bar.spectrum.visible
    }
  }
}
