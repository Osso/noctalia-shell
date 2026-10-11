import QtQuick
import QtTest
import qs.Commons
import qs.Services.Media
import qs.Widgets.AudioSpectrum

Item {
  id: scene
  width: 400
  height: 200

  NMirroredSpectrum {
    id: mirrored
    width: 120
    height: 100
    values: CavaService.values
  }
  NLinearSpectrum {
    id: linear
    width: 120
    height: 100
    values: CavaService.values
  }
  NWaveSpectrum {
    id: wave
    x: 150
    width: 120
    height: 100
    fillColor: "red"
    values: CavaService.values
  }

  TestCase {
    name: "ProductionAudioSpectrum"
    when: windowShown

    function init() {
      CavaService.values = [];
      mirrored.vertical = false;
      linear.vertical = false;
      wave.vertical = false;
      mirrored.showMinimumSignal = false;
      linear.showMinimumSignal = false;
      wave.showMinimumSignal = false;
      wave.visible = true;
      Settings.data = {
        audio: {
          visualizerType: "high"
        },
        general: {
          animationDisabled: true
        }
      };
      wait(50);
    }

    function bars(spectrum) {
      // Repeater inserts its real visual delegates as children of the spectrum.
      return Array.from(spectrum.children).filter(child => child.toString().startsWith("QQuickRectangle"));
    }

    function compareGeometry(bar, x, y, width, height) {
      fuzzyCompare(bar.x, x, 0.001);
      fuzzyCompare(bar.y, y, 0.001);
      fuzzyCompare(bar.width, width, 0.001);
      fuzzyCompare(bar.height, height, 0.001);
    }

    function test_horizontal_frame_amplitudes() {
      // Concrete normalized Cava frame: 0;25;100; -> [0, .25, 1].
      CavaService.values = [0, 0.25, 1];
      tryCompare(mirrored, "totalBars", 6);
      compare(linear.totalBars, 6);
      const mirrorBars = bars(mirrored);
      const lineBars = bars(linear);
      compare(mirrorBars.length, 6);
      compare(lineBars.length, 6);
      const amplitudes = [1, 0.25, 0, 0, 0.25, 1];
      for (let i = 0; i < amplitudes.length; i++) {
        const amplitude = amplitudes[i];
        fuzzyCompare(mirrorBars[i].rawAmp, amplitude, 0.001);
        fuzzyCompare(lineBars[i].rawAmp, amplitude, 0.001);
        compareGeometry(mirrorBars[i], i * 20 + 5, 50 - amplitude * 50, 16, amplitude * 100);
        compareGeometry(lineBars[i], i * 20 + 5, 100 - amplitude * 100, 10, amplitude * 100);
      }
    }

    function test_vertical_minimum_and_reduced_animation() {
      mirrored.vertical = true;
      linear.vertical = true;
      mirrored.showMinimumSignal = true;
      linear.showMinimumSignal = true;
      mirrored.minimumSignalValue = 0.1;
      linear.minimumSignalValue = 0.1;
      Settings.data = {
        audio: {
          visualizerType: "low"
        },
        general: {
          animationDisabled: true
        }
      };
      CavaService.values = [0, 0.5];
      tryCompare(mirrored, "totalBars", 4);
      compare(mirrored.highQuality, false);
      compare(linear.highQuality, false);
      const mirrorBars = bars(mirrored);
      const lineBars = bars(linear);
      const amplitudes = [0.5, 0.1, 0.1, 0.5];
      for (let i = 0; i < amplitudes.length; i++) {
        const amplitude = amplitudes[i];
        compareGeometry(mirrorBars[i], 60 - amplitude * 60, i * 25 + 6.25, amplitude * 120, 20);
        compareGeometry(lineBars[i], 120 - amplitude * 120, i * 25 + 6.25, amplitude * 120, 12.5);
        compare(mirrorBars[i].antialiasing, false);
        compare(lineBars[i].smooth, false);
      }
      CavaService.values = [1, 0.25];
      wait(0);
      compareGeometry(mirrorBars[0], 45, 6.25, 30, 20);
      compareGeometry(lineBars[0], 90, 6.25, 30, 12.5);
    }

    function test_clear_reassign_and_resize() {
      CavaService.values = [0.2, 0.8];
      tryCompare(mirrored, "totalBars", 4);
      CavaService.values = [];
      tryCompare(mirrored, "totalBars", 0);
      compare(bars(mirrored).length, 0);
      compare(bars(linear).length, 0);
      CavaService.values = [0.5];
      tryCompare(mirrored, "totalBars", 2);
      compare(bars(mirrored).length, 2);
      compare(bars(linear).length, 2);
      mirrored.width = 240;
      linear.height = 80;
      wait(0);
      compareGeometry(bars(mirrored)[0], 30, 25, 96, 50);
      compareGeometry(bars(linear)[0], 15, 40, 30, 40);
      mirrored.width = 120;
      linear.height = 100;
    }

    function assertWavePixel(x, y, filled) {
      tryVerify(function () {
        const image = grabImage(wave);
        const isFilled = image.red(x, y) > 128 && image.green(x, y) < 128;
        return isFilled === filled;
      }, 2000, "wave pixel " + x + "," + y + " filled=" + filled);
    }

    function test_wave_frame_geometry_clear_and_reassign() {
      CavaService.values = [0, 0.5, 1];
      tryCompare(wave, "renderingActive", true);
      assertWavePixel(2, 10, true);
      assertWavePixel(60, 10, false);
      assertWavePixel(30, 40, true);
      assertWavePixel(30, 10, false);
      wave.vertical = true;
      assertWavePixel(10, 2, true);
      assertWavePixel(10, 50, false);
      assertWavePixel(50, 25, true);
      CavaService.values = [];
      tryCompare(wave, "renderingActive", false);
      assertWavePixel(50, 25, false);
      CavaService.values = [0, 1];
      tryCompare(wave, "renderingActive", true);
      assertWavePixel(10, 2, true);
    }

    function test_wave_minimum_signal_and_visibility() {
      wave.showMinimumSignal = true;
      wave.minimumSignalValue = 0.2;
      CavaService.values = [0, 0];
      assertWavePixel(60, 45, true);
      assertWavePixel(60, 30, false);
      wave.visible = false;
      tryCompare(wave, "renderingActive", false);
      wave.visible = true;
      CavaService.values = [0.25, 0.5];
      assertWavePixel(60, 45, true);
      assertWavePixel(60, 10, false);
    }
  }
}
