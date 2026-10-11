import QtQuick
import QtQuick.Layouts
import Quickshell
import "../Helpers/ColorsConvert.js" as ColorsConvert
import qs.Commons
import qs.Widgets

Item {
    id: root

    property date now: Time.now

    // Style: "analog" or "digital"
    property string clockStyle: "analog"

    // Color properties
    property color backgroundColor: NColor.mPrimary
    property color clockColor: NColor.mOnPrimary

    property color secondHandColor: {
        var defaultColor = NColor.mError;
        var bestContrast = 1.0; // 1.0 is "no contrast"
        var bestColor = defaultColor;
        var candidates = [NColor.mSecondary, NColor.mTertiary, NColor.mError];

        const minContrast = 1.149;

        for (var i = 0; i < candidates.length; i++) {
            var candidate = candidates[i];
            var contrastClock = ColorsConvert.getContrastRatio(candidate.toString(), clockColor.toString());
            if (contrastClock < minContrast) {
                continue;
            }
            var contrastBg = ColorsConvert.getContrastRatio(candidate.toString(), backgroundColor.toString());
            if (contrastBg < minContrast) {
                continue;
            }

            var currentWorstContrast = Math.min(contrastBg, contrastClock);

            if (currentWorstContrast > bestContrast) {
                bestContrast = currentWorstContrast;
                bestColor = candidate;
            }
        }

        return bestColor;
    }

    property color progressColor: root.secondHandColor

    // Font size properties for digital clock
    property real hoursFontSize: Style.fontSizeXS
    property real minutesFontSize: Style.fontSizeXXS
    property bool secondUpdatesRegistered: false

    function refreshSecondUpdateRegistration() {
        if (visible && !secondUpdatesRegistered) {
            Time.beginSecondUpdates();
            secondUpdatesRegistered = true;
        } else if (!visible && secondUpdatesRegistered) {
            Time.endSecondUpdates();
            secondUpdatesRegistered = false;
        }
    }

    Component.onCompleted: refreshSecondUpdateRegistration()
    Component.onDestruction: {
        if (secondUpdatesRegistered) {
            Time.endSecondUpdates();
            secondUpdatesRegistered = false;
        }
    }
    onVisibleChanged: refreshSecondUpdateRegistration()

    height: Math.round((Style.fontSizeXXXL * 1.9) / 2 * Style.uiScaleRatio) * 2
    width: root.height

    Loader {
        id: clockLoader
        anchors.fill: parent

        sourceComponent: root.clockStyle === "analog" ? analogClockComponent : digitalClockComponent

        onLoaded: {
            item.now = Qt.binding(function () {
                return root.now;
            });
            item.backgroundColor = Qt.binding(function () {
                return root.backgroundColor;
            });
            item.clockColor = Qt.binding(function () {
                return root.clockColor;
            });
            if (item.hasOwnProperty("secondHandColor")) {
                item.secondHandColor = Qt.binding(function () {
                    return root.secondHandColor;
                });
            }
            if (item.hasOwnProperty("progressColor")) {
                item.progressColor = Qt.binding(function () {
                    return root.progressColor;
                });
            }
            if (item.hasOwnProperty("hoursFontSize")) {
                item.hoursFontSize = Qt.binding(function () {
                    return root.hoursFontSize;
                });
            }
            if (item.hasOwnProperty("minutesFontSize")) {
                item.minutesFontSize = Qt.binding(function () {
                    return root.minutesFontSize;
                });
            }
        }
    }

    // Analog Clock Component
    component NClockAnalog: Item {
        id: analogClock
        property date now
        property color backgroundColor: NColor.mPrimary
        property color clockColor: NColor.mOnPrimary
        property color secondHandColor: NColor.mError
        anchors.fill: parent

        Canvas {
            id: clockCanvas
            anchors.fill: parent

            Connections {
                target: analogClock
                function onNowChanged() {
                    clockCanvas.requestPaint();
                }
            }

            onPaint: {
                var currentTime = analogClock.now;
                var hours = currentTime.getHours();
                var minutes = currentTime.getMinutes();
                var seconds = currentTime.getSeconds();

                const markAlpha = 0.7;
                var ctx = getContext("2d");
                ctx.reset();
                ctx.translate(width / 2, height / 2);
                var radius = Math.min(width, height) / 2;

                // Hour marks
                ctx.strokeStyle = Qt.alpha(analogClock.clockColor, markAlpha);
                ctx.lineWidth = 2 * Style.uiScaleRatio;
                var scaleFactor = 0.7;

                for (var i = 0; i < 12; i++) {
                    var scaleFactor = 0.8;
                    if (i % 3 === 0) {
                        scaleFactor = 0.65;
                    }
                    ctx.save();
                    ctx.rotate(i * Math.PI / 6);
                    ctx.beginPath();
                    ctx.moveTo(0, -radius * scaleFactor);
                    ctx.lineTo(0, -radius);
                    ctx.stroke();
                    ctx.restore();
                }

                // Hour hand
                ctx.save();
                var hourAngle = (hours % 12 + minutes / 60) * Math.PI / 6;
                ctx.rotate(hourAngle);
                ctx.strokeStyle = analogClock.clockColor;
                ctx.lineWidth = 3 * Style.uiScaleRatio;
                ctx.lineCap = "round";
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(0, -radius * 0.6);
                ctx.stroke();
                ctx.restore();

                // Minute hand
                ctx.save();
                var minuteAngle = (minutes + seconds / 60) * Math.PI / 30;
                ctx.rotate(minuteAngle);
                ctx.strokeStyle = analogClock.clockColor;
                ctx.lineWidth = 2 * Style.uiScaleRatio;
                ctx.lineCap = "round";
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(0, -radius * 0.9);
                ctx.stroke();
                ctx.restore();

                // Second hand
                ctx.save();
                var secondAngle = seconds * Math.PI / 30;
                ctx.rotate(secondAngle);
                ctx.strokeStyle = analogClock.secondHandColor;
                ctx.lineWidth = 1.6 * Style.uiScaleRatio;
                ctx.lineCap = "round";
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(0, -radius);
                ctx.stroke();
                ctx.restore();

                // Center dot
                ctx.beginPath();
                ctx.arc(0, 0, 3 * Style.uiScaleRatio, 0, 2 * Math.PI);
                ctx.fillStyle = analogClock.clockColor;
                ctx.fill();
            }

            Component.onCompleted: requestPaint()
        }
    }

    // Digital Clock Component
    component NClockDigital: Item {
        id: digitalClock
        property date now
        property color backgroundColor: NColor.mPrimary
        property color clockColor: NColor.mOnPrimary
        property color progressColor: NColor.mError
        property real hoursFontSize: Style.fontSizeXS
        property real minutesFontSize: Style.fontSizeXXS

        anchors.fill: parent

        // Digital clock's seconds circular progress
        Canvas {
            id: secondsProgress
            anchors.fill: parent
            property real progress: (digitalClock.now.getSeconds() * 1000 + digitalClock.now.getMilliseconds()) / 60000
            onProgressChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d");
                var centerX = width / 2;
                var centerY = height / 2;
                var radius = Math.min(width, height) / 2 - 3;
                ctx.reset();

                // Background circle
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                ctx.lineWidth = 2.5;
                ctx.strokeStyle = Qt.alpha(digitalClock.clockColor, 0.15);
                ctx.stroke();

                // Progress arc
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + progress * 2 * Math.PI);
                ctx.lineWidth = 2.5;
                ctx.strokeStyle = digitalClock.progressColor;
                ctx.lineCap = "round";
                ctx.stroke();
            }
        }

        // Digital clock
        ColumnLayout {
            anchors.centerIn: parent
            spacing: -Style.marginXXS

            NText {
                text: {
                    var t = Settings.data.location.use12hourFormat ? I18n.locale.toString(digitalClock.now, "hh AP") : I18n.locale.toString(digitalClock.now, "HH");
                    return t.split(" ")[0];
                }

                pointSize: digitalClock.hoursFontSize
                font.weight: Style.fontWeightBold
                color: digitalClock.clockColor
                family: Settings.data.ui.fontFixed
                Layout.alignment: Qt.AlignHCenter
            }

            NText {
                text: Qt.formatTime(digitalClock.now, "mm")
                pointSize: digitalClock.minutesFontSize
                font.weight: Style.fontWeightBold
                color: digitalClock.clockColor
                family: Settings.data.ui.fontFixed
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    Component {
        id: analogClockComponent
        NClockAnalog {}
    }

    Component {
        id: digitalClockComponent
        NClockDigital {}
    }
}
