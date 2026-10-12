import QtQuick
import QtTest
import qs.Modules.Panels.Changelog
import qs.Services.Noctalia

Item {
  id: scene

  width: 820
  height: 620

  Component {
    id: panelComponent

    ChangelogPanel {
      width: 820
      height: 620
    }
  }

  TestCase {
    id: tests
    property var panel

    function descendants(parent, predicate) {
      let found = [];
      for (const child of parent.children) {
        if (predicate(child))
          found.push(child);

        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function find(predicate) {
      const matches = descendants(panel.contentItem, predicate);
      compare(matches.length, 1);
      return matches[0];
    }

    function init() {
      UpdateService.changelogCurrentVersion = "4.2";
      UpdateService.previousVersion = "4.1";
      UpdateService.fetchError = "";
      UpdateService.feedbackUrl = "";
      UpdateService.seen = [];
      UpdateService.links = [];
      UpdateService.releaseHighlights = [
        {
          "entries": ["# Highlights", "## Fixes", "Plain entry", ""]
        }
      ];
      panel = panelComponent.createObject(scene);
      verify(panel !== null);
      compare(panel.contentItem, null);
      panel.open();
      tryVerify(() => {
        return panel.contentItem !== null;
      });
      wait(50);
    }

    function cleanup() {
      panel.destroy();
      panel = null;
      wait(0);
      UpdateService.releaseHighlights = [];
      wait(0);
    }

    function test_render_versions_and_heading_rows() {
      compare(find(child => {
        return child.text === "4.1";
      }).visible, true);
      compare(find(child => {
        return child.text === "4.2";
      }).visible, true);
      const heading = find(child => {
        return child.text === "Highlights";
      });
      compare(heading.headingLevel, 1);
      compare(heading.pointSize, 20);
      compare(find(child => {
        return child.text === "Fixes";
      }).headingLevel, 2);
      compare(find(child => {
        return child.text === "Plain entry";
      }).headingLevel, 0);
      verify(find(child => {
        return child.text === "\u00A0";
      }).visible);
      compare(find(child => {
        return child.text === "changelog.panel.empty";
      }).visible, false);
      UpdateService.previousVersion = "";
      tryCompare(panel, "hasPreviousVersion", false);
      verify(find(child => {
        return child.text === "changelog.panel.version.new-user";
      }).visible);
      UpdateService.fetchError = "offline fixture";
      verify(find(child => {
        return child.text === "offline fixture";
      }).visible);
      UpdateService.releaseHighlights = [];
      tryVerify(() => {
        return find(child => {
          return child.text === "changelog.panel.empty";
        }).visible;
      });
    }

    function test_release_date_long_locale_format() {
      compare(panel.formatReleaseDate("2026-01-15T12:00:00"), "Thursday, 15 January 2026");
      compare(panel.formatReleaseDate(""), "");
      compare(panel.formatReleaseDate("not-a-date"), "not-a-date");
    }

    function test_two_instance_content_ownership() {
      const other = panelComponent.createObject(scene);
      verify(other !== null);
      try {
        other.open();
        tryVerify(() => other.contentItem !== null);
        verify(other.contentItem !== panel.contentItem);
        const closeButtons = descendants(other.contentItem, child => child.tooltipText === "tooltips.close");
        compare(closeButtons.length, 1);
        closeButtons[0].clicked();
        tryCompare(other, "contentItem", null);
        verify(panel.isPanelOpen);
        verify(panel.contentItem !== null);
        compare(find(child => child.text === "Highlights").headingLevel, 1);
        other.open();
        tryVerify(() => other.contentItem !== null);
        find(child => child.text === "changelog.panel.buttons.dismiss").clicked();
        tryCompare(panel, "contentItem", null);
        verify(other.isPanelOpen);
        verify(other.contentItem !== null);
      } finally {
        other.destroy();
        wait(0);
      }
    }

    function test_scroll_long_content_and_render() {
      const entries = ["# Long release"];
      for (let index = 0; index < 80; index++)
        entries.push("Entry " + index + " concrete release note");
      UpdateService.releaseHighlights = [
        {
          "entries": entries
        }
      ];
      const scroll = find(child => {
        return child.horizontalPolicy !== undefined;
      });
      tryVerify(() => {
        return scroll.contentItem.contentHeight > scroll.contentItem.height;
      });
      const flickable = scroll.contentItem;
      flickable.contentY = flickable.contentHeight - flickable.height;
      verify(flickable.contentY > 0);
      const last = find(child => {
        return child.text === "Entry 79 concrete release note";
      });
      verify(last.visible);
      verify(last.height > 0);
      const image = grabImage(panel.contentItem);
      compare(image.width, 820);
      compare(image.height, 620);
    }

    function test_close_routes_reopen_and_links_are_inert() {
      find(child => {
        return child.text === "changelog.panel.buttons.discord";
      }).clicked();
      UpdateService.feedbackUrl = "fixture-only";
      const feedback = find(child => {
        return child.text === "changelog.panel.buttons.feedback";
      });
      verify(feedback.visible);
      feedback.clicked();
      compare(UpdateService.links, ["discord", "feedback"]);
      find(child => {
        return child.text === "changelog.panel.buttons.dismiss";
      }).clicked();
      tryCompare(panel, "contentItem", null);
      compare(UpdateService.seen, ["4.2"]);
      panel.open();
      tryVerify(() => {
        return panel.contentItem !== null;
      });
      find(child => {
        return child.tooltipText === "tooltips.close";
      }).clicked();
      tryCompare(panel, "contentItem", null);
      compare(UpdateService.seen, ["4.2", "4.2"]);
      UpdateService.changelogCurrentVersion = "";
      panel.open();
      tryVerify(() => {
        return panel.contentItem !== null;
      });
      panel.close();
      compare(UpdateService.seen, ["4.2", "4.2"]);
    }

    name: "ChangelogPanelWarnings"
    when: windowShown
  }
}
