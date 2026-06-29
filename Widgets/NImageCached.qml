pragma ComponentBehavior

import QtQuick
import Quickshell
import Quickshell.Io
import "../Helpers/sha256.js" as Checksum
import qs.Commons

Image {
  id: root

  property string imagePath: ""
  property string imageHash: ""
  property string cacheFolder: Settings.cacheDirImages
  property int maxCacheDimension: 384
  readonly property string cachePath: imageHash ? `${cacheFolder}${imageHash}@${maxCacheDimension}x${maxCacheDimension}.png` : ""

  asynchronous: true
  fillMode: Image.PreserveAspectCrop
  sourceSize.width: root.shouldLoadImage() ? maxCacheDimension : 0
  sourceSize.height: root.shouldLoadImage() ? maxCacheDimension : 0
  smooth: true

  function shouldLoadImage() {
    if (!visible) {
      return false;
    }
    return imagePath !== "" && width > 0 && height > 0;
  }

  function shouldCacheCurrentImage() {
    if (!visible || !Window.window || !Window.window.visible) {
      return false;
    }
    const originalIsReady = source === imagePath && status === Image.Ready;
    const cacheTargetExists = imageHash !== "" && cachePath !== "";
    return originalIsReady && cacheTargetExists;
  }

  function refreshImageSource() {
    if (!shouldLoadImage()) {
      source = "";
      return;
    }
    if (imageHash && cachePath) {
      source = cachePath;
    } else {
      source = imagePath;
    }
  }

  onImagePathChanged: {
    if (imagePath) {
      imageHash = Checksum.sha256(imagePath);
      // Logger.i("NImageCached", imagePath, imageHash)
    } else {
      imageHash = "";
    }
    refreshImageSource();
  }
  onCachePathChanged: refreshImageSource()
  onVisibleChanged: refreshImageSource()
  onWidthChanged: refreshImageSource()
  onHeightChanged: refreshImageSource()
  Component.onCompleted: refreshImageSource()

  onStatusChanged: {
    if (source === cachePath && status === Image.Error && shouldLoadImage()) {
      // Cached image was not available, show the original
      source = imagePath;
    } else if (shouldCacheCurrentImage()) {
      // Original image is shown and fully loaded, time to cache it
      const grabPath = cachePath;
      grabToImage(res => {
                    return res.saveToFile(grabPath);
                  });
    }
  }
}
