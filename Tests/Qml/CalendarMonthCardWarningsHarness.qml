import QtQuick
import QtTest
import Quickshell
import qs.Cards
import qs.Commons
import qs.Services.Location
import qs.Services.System
import qs.Services.UI

TestCase {
    id: testCase

    property var card

    function descendants(item, predicate) {
        let matches = [];
        for (const child of item.children) {
            if (predicate(child))
                matches.push(child);

            matches = matches.concat(descendants(child, predicate));
        }
        return matches;
    }

    function isEventDot(item) {
        return item.width === 4 && item.height === 4 && item.color !== undefined;
    }

    function dayCell(day) {
        const matches = descendants(card, (item) => {
            return item.day === day && item.currentMonth === true;
        });
        compare(matches.length, 1);
        return matches[0];
    }

    function navigation(icon) {
        const matches = descendants(card, (item) => {
            return item.icon === icon;
        });
        compare(matches.length, 1);
        return matches[0];
    }

    function init() {
        Settings.data.location.firstDayOfWeek = 1;
        Settings.data.location.showCalendarEvents = true;
        Settings.data.location.showWeekNumberInCalendar = true;
        Settings.data.location.use12hourFormat = false;
        I18n.locale = Qt.locale("en_US");
        CalendarService.events = [];
        CalendarService.loads = [];
        Quickshell.launches = [];
        TooltipService.hide();
        ProgramCheckerService.gnomeCalendarAvailable = true;
        card = createTemporaryObject(cardComponent, testCase);
        verify(card !== null);
        wait(30);
    }

    function cleanup() {
        card = null;
    }

    function test_navigation_year_boundary_reset() {
        compare(card.calendarMonth, 0);
        compare(card.calendarYear, 2026);
        mouseClick(navigation("chevron-left"));
        compare(card.calendarMonth, 11);
        compare(card.calendarYear, 2025);
        mouseClick(navigation("chevron-right"));
        compare(card.calendarMonth, 0);
        compare(card.calendarYear, 2026);
        card.calendarMonth = 6;
        mouseClick(navigation("calendar"));
        compare(card.calendarMonth, 0);
        compare(CalendarService.loads.length, 3);
        verify(CalendarService.loads[0].ahead >= 30);
        verify(CalendarService.loads[0].behind >= 30);
    }

    function test_date_selection_program_gate() {
        mouseClick(dayCell(15));
        compare(Quickshell.launches.length, 1);
        compare(Quickshell.launches[0].join("|"), "gnome-calendar|--date|01/15/26");
        ProgramCheckerService.gnomeCalendarAvailable = false;
        mouseClick(dayCell(16));
        compare(Quickshell.launches.length, 1);
        Settings.data.location.showCalendarEvents = false;
        ProgramCheckerService.gnomeCalendarAvailable = true;
        mouseClick(dayCell(17));
        compare(Quickshell.launches.length, 1);
    }

    function test_weekday_locale_geometry() {
        const header = descendants(card, (item) => {
            return item.text === "MO";
        });
        compare(header.length, 1);
        const first = dayCell(1);
        const second = dayCell(2);
        verify(first.width > 0);
        compare(first.width, second.width);
        const firstPoint = first.mapToItem(card, 0, 0);
        const secondPoint = second.mapToItem(card, 0, 0);
        verify(secondPoint.x > firstPoint.x);
        compare(firstPoint.y, secondPoint.y);
        Settings.data.location.firstDayOfWeek = -1;
        I18n.locale = Qt.locale("fr_FR");
        tryCompare(card, "firstDayOfWeek", 1);
        tryVerify(() => {
            return descendants(card, (item) => {
                return item.text === "LU";
            }).length === 1;
        });
        I18n.locale = Qt.locale("en_US");
        tryCompare(card, "firstDayOfWeek", 0);
        tryVerify(() => {
            return descendants(card, (item) => {
                return item.text === "SU";
            }).length === 1;
        });
        const widthWithWeekNumbers = dayCell(1).width;
        Settings.data.location.showWeekNumberInCalendar = false;
        wait(30);
        verify(dayCell(1).width > widthWithWeekNumbers);
    }

    function test_two_instance_delegate_ownership() {
        const secondCard = createTemporaryObject(cardComponent, testCase, {
            "calendarMonth": 1,
            "x": 500
        });
        verify(secondCard !== null);
        const start = new Date(2026, 0, 15, 10).getTime() / 1000;
        CalendarService.events = [{
            "start": start,
            "end": start + 3600,
            "summary": "January only"
        }];
        wait(30);
        compare(descendants(dayCell(15), isEventDot).length, 1);
        compare(descendants(secondCard, isEventDot).length, 0);
        secondCard.calendarMonth = 0;
        wait(30);
        compare(descendants(secondCard, isEventDot).length, 1);
        card.calendarMonth = 1;
        wait(30);
        compare(descendants(secondCard, isEventDot).length, 1);
        compare(descendants(dayCell(15), isEventDot).length, 0);
    }

    function test_events_dots_tooltip_locale_and_recreation() {
        const start = new Date(2026, 0, 15, 10, 0).getTime() / 1000;
        CalendarService.events = [{
            "start": start,
            "end": start + 3600,
            "summary": "Fixture meeting"
        }, {
            "start": start - 86400,
            "end": start + 86400,
            "summary": "Fixture span"
        }];
        wait(30);
        const cell = dayCell(15);
        const dots = descendants(cell, isEventDot);
        compare(dots.length, 2);
        compare(dots[0].color, NColor.mPrimary);
        compare(dots[1].color, NColor.mTertiary);
        mouseMove(cell, cell.width / 2, cell.height / 2);
        tryVerify(() => {
            return TooltipService.message.indexOf("10:00-11:00 Fixture meeting") >= 0;
        });
        mouseMove(testCase, 479, 599);
        tryCompare(TooltipService, "message", "");
        Settings.data.location.use12hourFormat = true;
        mouseMove(cell, cell.width / 2, cell.height / 2);
        tryVerify(() => {
            return TooltipService.message.indexOf("10:00 AM-11:00 AM Fixture meeting") >= 0;
        });
        card.calendarMonth = 1;
        wait(30);
        compare(descendants(dayCell(15), isEventDot).length, 0);
        card.calendarMonth = 0;
        wait(30);
        compare(descendants(dayCell(15), isEventDot).length, 2);
    }

    name: "CalendarMonthCardWarnings"
    width: 480
    height: 600
    when: windowShown
    visible: true

    Component {
        id: cardComponent

        CalendarMonthCard {
            id: cardOwner

            width: 448
            height: cardOwner.implicitHeight
        }

    }

}
