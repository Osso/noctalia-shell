import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Widgets

ColumnLayout {
  id: root
  spacing: Style.marginM

  // Properties to receive data from parent
  property var widgetData: null
  property var widgetMetadata: null

  // Local state
  property bool valueShowCapsLock: widgetData.showCapsLock !== undefined ? widgetData.showCapsLock : widgetMetadata.showCapsLock
  property bool valueShowNumLock: widgetData.showNumLock !== undefined ? widgetData.showNumLock : widgetMetadata.showNumLock
  property bool valueShowScrollLock: widgetData.showScrollLock !== undefined ? widgetData.showScrollLock : widgetMetadata.showScrollLock

  property string capsIcon: widgetData.capsLockIcon !== undefined ? widgetData.capsLockIcon : widgetMetadata.capsLockIcon
  property string numIcon: widgetData.numLockIcon !== undefined ? widgetData.numLockIcon : widgetMetadata.numLockIcon
  property string scrollIcon: widgetData.scrollLockIcon !== undefined ? widgetData.scrollLockIcon : widgetMetadata.scrollLockIcon

  function saveSettings() {
    var settings = Object.assign({}, widgetData || {});
    settings.showCapsLock = valueShowCapsLock;
    settings.showNumLock = valueShowNumLock;
    settings.showScrollLock = valueShowScrollLock;
    settings.capsLockIcon = capsIcon;
    settings.numLockIcon = numIcon;
    settings.scrollLockIcon = scrollIcon;
    return settings;
  }

  RowLayout {
    spacing: Style.marginM

    NToggle {
      label: I18n.tr("bar.widget-settings.lock-keys.show-caps-lock.label")
      description: I18n.tr("bar.widget-settings.lock-keys.show-caps-lock.description")
      checked: root.valueShowCapsLock
      onToggled: checked => root.valueShowCapsLock = checked
    }

    NIcon {
      Layout.alignment: Qt.AlignVCenter
      icon: root.capsIcon
      pointSize: Style.fontSizeXL
      visible: root.capsIcon !== ""
    }

    NButton {
      text: I18n.tr("bar.widget-settings.lock-keys.browse")
      onClicked: capsPicker.open()
      enabled: root.valueShowCapsLock
    }
  }

  NIconPicker {
    id: capsPicker
    initialIcon: root.capsIcon
    query: "letter-c"
    onIconSelected: function (iconName) {
      root.capsIcon = iconName;
    }
  }

  RowLayout {
    spacing: Style.marginM

    NToggle {
      label: I18n.tr("bar.widget-settings.lock-keys.show-num-lock.label")
      description: I18n.tr("bar.widget-settings.lock-keys.show-num-lock.description")
      checked: root.valueShowNumLock
      onToggled: checked => root.valueShowNumLock = checked
    }

    NIcon {
      Layout.alignment: Qt.AlignVCenter
      icon: root.numIcon
      pointSize: Style.fontSizeXL
      visible: root.numIcon !== ""
    }

    NButton {
      text: I18n.tr("bar.widget-settings.lock-keys.browse")
      onClicked: numPicker.open()
      enabled: root.valueShowNumLock
    }
  }

  NIconPicker {
    id: numPicker
    initialIcon: root.numIcon
    query: "letter-n"
    onIconSelected: function (iconName) {
      root.numIcon = iconName;
    }
  }

  RowLayout {
    spacing: Style.marginM

    NToggle {
      label: I18n.tr("bar.widget-settings.lock-keys.show-scroll-lock.label")
      description: I18n.tr("bar.widget-settings.lock-keys.show-scroll-lock.description")
      checked: root.valueShowScrollLock
      onToggled: checked => root.valueShowScrollLock = checked
    }

    NIcon {
      Layout.alignment: Qt.AlignVCenter
      icon: root.scrollIcon
      pointSize: Style.fontSizeXL
      visible: root.scrollIcon !== ""
    }

    NButton {
      text: I18n.tr("bar.widget-settings.lock-keys.browse")
      onClicked: scrollPicker.open()
      enabled: root.valueShowScrollLock
    }
  }

  NIconPicker {
    id: scrollPicker
    initialIcon: root.scrollIcon
    query: "letter-s"
    onIconSelected: function (iconName) {
      root.scrollIcon = iconName;
    }
  }
}
