pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

/*
Noctalia is not strictly a Material Design project, it supports both some predefined
color schemes and dynamic color generation from the wallpaper (using Matugen).

We ultimately decided to use a restricted set of colors that follows the
Material Design 3 naming convention.

NOTE: All color names are prefixed with 'm' (e.g., mPrimary) to prevent QML from
misinterpreting them as signals (e.g., the 'onPrimary' property name).
*/
Singleton {
  id: root

  property alias colorsData: customColorsData

  // --- Key Colors: These are the main accent colors that define your app's style
  readonly property color mPrimary: root.colorsData.mPrimary
  readonly property color mOnPrimary: root.colorsData.mOnPrimary
  readonly property color mSecondary: root.colorsData.mSecondary
  readonly property color mOnSecondary: root.colorsData.mOnSecondary
  readonly property color mTertiary: root.colorsData.mTertiary
  readonly property color mOnTertiary: root.colorsData.mOnTertiary

  // --- Utility Colors: These colors serve specific, universal purposes like indicating errors
  readonly property color mError: root.colorsData.mError
  readonly property color mOnError: root.colorsData.mOnError

  // --- Surface and Variant Colors: These provide additional options for surfaces and their contents, creating visual hierarchy
  readonly property color mSurface: root.colorsData.mSurface
  readonly property color mOnSurface: root.colorsData.mOnSurface

  readonly property color mSurfaceVariant: root.colorsData.mSurfaceVariant
  readonly property color mOnSurfaceVariant: root.colorsData.mOnSurfaceVariant

  readonly property color mOutline: root.colorsData.mOutline
  readonly property color mShadow: root.colorsData.mShadow

  readonly property color mHover: root.colorsData.mHover
  readonly property color mOnHover: root.colorsData.mOnHover

  // --- Absolute Colors
  readonly property color transparent: "transparent"
  readonly property color black: "#000000"
  readonly property color white: "#ffffff"

  // ----------------------------------------------------------------
  // FileView to load custom colors data from colors.json
  FileView {
    id: customColorsFile
    path: Settings.directoriesCreated ? (Settings.configDir + "colors.json") : undefined
    printErrors: false
    watchChanges: true
    onFileChanged: {
      Logger.i("Color", "Reloading colors from disk");
      reload();
    }
    onAdapterUpdated: {
      Logger.i("Color", "Writing colors to disk");
      writeAdapter();
    }

    // Trigger initial load when path changes from empty to actual path
    onPathChanged: {
      if (path !== undefined) {
        reload();
      }
    }
    onLoadFailed: function (error) {
      // Error code 2 = ENOENT (No such file or directory)
      if (error === 2 || error.toString().includes("No such file")) {
        // File doesn't exist, create it with default values
        writeAdapter();
      }
    }
    JsonAdapter {
      id: customColorsData

      // Default colors: Rose Pine
      property color mPrimary: "#c7a1d8"
      property color mOnPrimary: "#1a151f"

      property color mSecondary: "#a984c4"
      property color mOnSecondary: "#f3edf7"

      property color mTertiary: "#e0b7c9"
      property color mOnTertiary: "#20161f"

      property color mError: "#e9899d"
      property color mOnError: "#1e1418"

      property color mSurface: "#1c1822"
      property color mOnSurface: "#e9e4f0"

      property color mSurfaceVariant: "#262130"
      property color mOnSurfaceVariant: "#a79ab0"

      property color mOutline: "#342c42"
      property color mShadow: "#120f18"

      property color mHover: "#e0b7c9"
      property color mOnHover: "#20161f"
    }
  }
}
