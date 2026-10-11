import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets
import qs.Services.Media
import qs.Services.UI

ShellRoot {
  id: harness

  TestCase {
    id: input
    when: false
  }

  Window {
    width: 480
    height: 120
    visible: true // Only an offscreen platform; runner removes desktop connections.

    MediaMini {
      id: widget
      width: implicitWidth
      height: implicitHeight
      widgetMetadata: ({})
      widgetSettings: ({
          hideMode: "visible",
          hideWhenIdle: false,
          showAlbumArt: false,
          showArtistFirst: true,
          showVisualizer: false,
          visualizerType: "linear",
          scrollingMode: "never",
          showProgressRing: false,
          maxWidth: 220,
          useFixedWidth: false
        })
    }
  }

  function require(condition, message) {
    if (!condition) {
      console.error("MEDIA_MINI_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function findItems(item, predicate) {
    let matches = predicate(item) ? [item] : [];
    for (const child of item.children || []) {
      matches = matches.concat(findItems(child, predicate));
    }
    return matches;
  }

  function configure(changes) {
    widget.widgetSettings = Object.assign({}, widget.widgetSettings, changes);
  }

  function title() {
    return findItems(widget, item => item.family !== undefined && item.visible)[0];
  }

  function mouse() {
    return findItems(widget, item => item.acceptedButtons !== undefined)[0];
  }

  function menu() {
    for (const object of widget.data) {
      if (object.triggered !== undefined && object.model !== undefined) {
        return object;
      }
    }
    throw new Error("popup not found");
  }

  function arts() {
    return findItems(widget, item => item.imagePath !== undefined);
  }

  function spectra() {
    return findItems(widget, item => item.values !== undefined && item.fillColor !== undefined);
  }

  Timer {
    interval: 150
    running: true
    repeat: true
    property int step: 0
    property int spectrumIndex: 0
    property int spectrumPhase: 0
    readonly property var spectrumTypes: ["linear", "mirrored", "wave"]

    onTriggered: {
      switch (step) {
      case 0:
        harness.require(harness.title().text === widget.placeholderText, "no-player placeholder");
        harness.require(MediaService.positionConsumers === 1, "visible widget registers position updates");
        harness.require(harness.menu().model.length === 1, "no-player settings menu");
        input.mouseClick(widget, widget.width / 2, widget.height / 2, Qt.LeftButton);
        harness.require(!MediaService.isPlaying, "no-player click does nothing");
        MediaService.currentPlayer = {};
        break;
      case 1:
        harness.require(harness.title().text === "Artist - Title", "artist-first live title");
        harness.require(harness.menu().model[0].action === "play-pause", "player menu transport action");
        harness.require(harness.menu().model[0].icon === "media-play", "paused menu icon");
        input.mouseClick(widget, widget.width / 2, widget.height / 2, Qt.LeftButton);
        harness.require(MediaService.isPlaying, "left click starts playback");
        harness.configure({
          showArtistFirst: false
        });
        break;
      case 2:
        harness.require(harness.title().text === "Title - Artist", "title-first live title");
        harness.require(harness.menu().model[0].icon === "media-pause", "playing menu icon updates");
        harness.menu().triggered("play-pause");
        harness.require(!MediaService.isPlaying, "menu pauses playback");
        MediaService.canPlay = false;
        input.mouseClick(widget, widget.width / 2, widget.height / 2, Qt.LeftButton);
        harness.require(!MediaService.isPlaying, "capability blocks left click");
        input.mouseClick(widget, widget.width / 2, widget.height / 2, Qt.MiddleButton);
        harness.require(MediaService.previousCount === 1, "middle click selects previous track");
        harness.menu().triggered("next");
        harness.require(MediaService.nextCount === 1, "menu selects next track");
        MediaService.trackArtist = "";
        break;
      case 3:
        harness.require(harness.title().text === "Title", "empty artist omits separator");
        MediaService.canPlay = true;
        harness.configure({
          showAlbumArt: true,
          showProgressRing: true
        });
        break;
      case 4:
        harness.require(harness.arts().length === 2, "both orientations have real album-art widgets");
        harness.require(harness.arts()[0].showFallback, "empty art uses fallback");
        harness.require(harness.arts()[0].fallbackIcon === "media-play", "paused art fallback");
        const progress = harness.findItems(widget, item => item.progressRatio !== undefined);
        harness.require(progress.length === 2 && progress.every(item => item.progressRatio === 0.25), "both progress ratios");
        MediaService.isPlaying = true;
        MediaService.trackArtUrl = Qt.resolvedUrl("cover.svg").toString();
        MediaService.currentPosition = 150;
        break;
      case 5:
        harness.require(harness.arts()[0].fallbackIcon === "media-pause", "playing art fallback updates");
        harness.require(!harness.arts()[0].showFallback, "nonempty art replaces fallback");
        const images = harness.findItems(widget, item => item.sourceSize !== undefined && item.status !== undefined);
        harness.require(images.some(image => image.status === Image.Ready && image.source.toString() === MediaService.trackArtUrl), "real thumbnail loads local artwork");
        harness.require(harness.findItems(widget, item => item.progressRatio !== undefined).every(item => item.progressRatio === 1), "progress clamps above duration");
        Settings.data = Object.assign({}, Settings.data, {
          bar: Object.assign({}, Settings.data.bar, {
            position: "left"
          })
        });
        break;
      case 6:
        harness.require(widget.isVerticalBar, "vertical orientation updates");
        harness.require(harness.arts()[1].visible && harness.arts()[1].width > 0, "vertical album art visible with dimensions");
        harness.configure({
          showAlbumArt: false,
          showProgressRing: false
        });
        break;
      case 7:
        const icons = harness.findItems(widget, item => item.icon !== undefined && item.visible);
        harness.require(icons.some(icon => icon.icon === "media-pause"), "vertical playback icon");
        Settings.data = Object.assign({}, Settings.data, {
          bar: Object.assign({}, Settings.data.bar, {
            position: "top"
          })
        });
        harness.configure({
          showVisualizer: true,
          visualizerType: spectrumTypes[spectrumIndex]
        });
        break;
      case 8:
        const loaded = harness.spectra();
        harness.require(loaded.length === 1, "exactly one visualizer loaded: " + spectrumTypes[spectrumIndex]);
        const expectedWidth = widget.width - (widget.isVerticalBar ? 1 : 3) * Style.marginS;
        const expectedHeight = spectrumIndex === 0 ? 20 : widget.height - Style.marginS;
        harness.require(loaded[0].width === expectedWidth && loaded[0].height === expectedHeight, "loaded spectrum follows container dimensions in phase " + spectrumPhase);
        harness.require(loaded[0].values.length === 3 && loaded[0].values[1] === 0.6, "loader receives actual spectrum data");
        if (spectrumIndex === 0) {
          const bars = harness.findItems(loaded[0], item => item.rawAmp !== undefined);
          harness.require(bars.length === 6, "linear mirrored delegate count");
          harness.require(bars.map(bar => bar.rawAmp).join(",") === "0.9,0.6,0.2,0.2,0.6,0.9", "actual injected delegate indices select amplitudes");
        }
        if (spectrumPhase === 0) {
          harness.configure({
            useFixedWidth: true,
            maxWidth: 180
          });
          spectrumPhase++;
          return;
        }
        if (spectrumPhase === 1) {
          Settings.data = Object.assign({}, Settings.data, {
            bar: Object.assign({}, Settings.data.bar, {
              position: "left"
            })
          });
          spectrumPhase++;
          return;
        }
        Settings.data = Object.assign({}, Settings.data, {
          bar: Object.assign({}, Settings.data.bar, {
            position: "top"
          })
        });
        spectrumPhase = 0;
        harness.configure({
          showVisualizer: false
        });
        break;
      case 9:
        harness.require(harness.spectra().length === 0, "visualizer unloads");
        spectrumIndex++;
        if (spectrumIndex < spectrumTypes.length) {
          harness.configure({
            showVisualizer: true,
            visualizerType: spectrumTypes[spectrumIndex]
          });
          step = 7;
        } else {
          input.mouseMove(widget, 400, 80);
          harness.require(!harness.mouse().containsMouse, "cursor leaves widget before always-scroll test");
          MediaService.trackTitle = "A very long concrete track title that exceeds this compact widget width";
          harness.configure({
            scrollingMode: "always",
            maxWidth: 100,
            useFixedWidth: true
          });
        }
        break;
      case 10:
        harness.require(harness.title().text === MediaService.trackTitle, "track change updates visible title");
        harness.require(widget.dynamicWidth === 100, "fixed width honors setting");
        harness.require(harness.findItems(widget, item => item.needsScrolling !== undefined)[0].needsScrolling, "long title overflows");
        interval = 1250;
        break;
      case 11:
        const scrolling = harness.findItems(widget, item => item.needsScrolling !== undefined)[0];
        harness.require(scrolling.isScrolling, "always mode starts after delay");
        harness.require(harness.findItems(widget, item => item.scrollX !== undefined)[0].scrollX < 0, "title position advances");
        MediaService.trackTitle = "Short";
        harness.configure({
          scrollingMode: "never",
          hideMode: "idle"
        });
        MediaService.isPlaying = false;
        interval = 150;
        break;
      case 12:
        harness.require(!widget.visible && widget.implicitWidth === 0, "idle mode hides paused widget");
        harness.require(MediaService.positionConsumers === 0, "hidden widget deregisters position updates");
        MediaService.isPlaying = true;
        break;
      case 13:
        harness.require(widget.visible && widget.implicitWidth > 0, "playing widget reappears");
        harness.require(MediaService.positionConsumers === 1, "visible widget registers again");
        input.mouseMove(widget, widget.width / 2, widget.height / 2);
        harness.require(TooltipService.lastText.indexOf("Short") === 0, "hover uses current title tooltip");
        input.mouseMove(widget, 400, 80);
        harness.require(TooltipService.lastText === "", "exit hides tooltip");
        console.log("MEDIA_MINI_BEHAVIOR_PASS");
        Qt.quit();
        break;
      }
      step++;
    }
  }
}
