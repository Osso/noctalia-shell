import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.Commons
import qs.Services.Noctalia
import qs.Services.System
import qs.Services.UI
import qs.Tabs

TestCase {
  id: testCase
  name: "AboutTabWarnings"
  visible: true
  width: 800
  height: 2000
  when: windowShown

  Component {
    id: tabComponent
    AboutTab {
      width: 800
    }
  }

  function descendants(item) {
    let children = [item];
    for (const child of item.children || [])
      children = children.concat(descendants(child));
    return children;
  }

  function texts(tab) {
    return descendants(tab).filter(item => item.visible && typeof item.text === "string").map(item => item.text);
  }

  function textItem(tab, text) {
    const matches = descendants(tab).filter(item => item.text === text);
    verify(matches.length > 0, "Rendered text: " + text);
    return matches[0];
  }

  function updateButton(tab) {
    return descendants(tab).find(item => item.text === "settings.about.noctalia.download-latest" && item.clicked !== undefined);
  }

  function linkArea(tab, text) {
    let owner = textItem(tab, text).parent;
    while (owner && owner !== tab) {
      const area = Array.from(owner.children).find(item => item.hoverEnabled !== undefined && item.clicked !== undefined);
      if (area)
        return area;
      owner = owner.parent;
    }
    fail("No navigation area for " + text);
  }

  function contributors(count) {
    return Array.from({
                        length: count
                      }, (_, index) => ({
                        login: "author" + index,
                        contributions: index + 10,
                        avatar_url: index === 0 ? Qt.resolvedUrl("avatar.svg").toString() : "",
                        html_url: index === 21 ? "" : "https://example.invalid/author" + index
                      }));
  }

    function init() {
    GitHubService.latestVersion = "v3.5.0";
    UpdateService.currentVersion = "v3.4.0";
    GitHubService.contributors = contributors(22);
    GitHubService.cachedCircularAvatars = {
    author0: Qt.resolvedUrl("avatar.svg").toString()
  };
    HostService.isNixOS = false;
    ToastService.notices = [];
    Quickshell.launches = [];
    Quickshell.processes = [];
    Quickshell.shellDir = "/fixture/noctalia-shell";
    Quickshell.packageOutput = "noctalia-shell-git 3.4.0.r112.g3f00bec8-1";
    Quickshell.packageExit = 0;
    Quickshell.gitOutput = "abc1234";
    Quickshell.gitExit = 0;
    Quickshell.processDelay = 20;
  }

    function test_dividerContributorGeometry_data() {
    return [
    {
    tag: "narrow",
    width: 600,
    scale: 1
  },
    {
    tag: "wide",
    width: 800,
    scale: 1
  },
    {
    tag: "narrow-scaled",
    width: 600,
    scale: 1.5
  },
    {
    tag: "wide-scaled",
    width: 800,
    scale: 1.5
  }
    ];
  }

    function contributorGeometry(tab) {
    const divider = Array.from(tab.children).find(item => item.vertical === false);
    const header = Array.from(tab.children).find(item => item.label === "settings.about.contributors.section.label");
    const cards = linkArea(tab, "author0").parent.parent;
    const links = linkArea(tab, "author20").parent.parent;
    return [divider, header, cards, links].map(item => [item.x, item.y, item.width, item.height]);
  }

    function test_dividerContributorGeometry(data) {
    Style.uiScaleRatio = data.scale;
    Style.baseWidgetSize = 32 * data.scale;
    try {
    const tab = createTemporaryObject(tabComponent, testCase, {
    width: data.width
  });
    verify(tab !== null);
    wait(50);
    const divider = Array.from(tab.children).find(item => item.vertical === false);
    verify(divider !== undefined);
    compare(divider.Layout.topMargin, 0, "Undefined margin retains Qt default zero");
    const before = contributorGeometry(tab);
    console.log("ABOUT_GEOMETRY", data.tag, JSON.stringify(before));
    divider.Layout.topMargin = 0;
    wait(50);
    compare(JSON.stringify(contributorGeometry(tab)), JSON.stringify(before), "Default zero preserves divider and contributor geometry");
  } finally {
    Style.uiScaleRatio = 1;
    Style.baseWidgetSize = 32;
  }
  }

    function test_versionsAndTitles_data() {
    return [
    {
    tag: "newer-minor",
    latest: "v3.5.0",
    current: "v3.4.0",
    update: true
  },
    {
    tag: "newer-major",
    latest: "v4.0.0",
    current: "v3.9.9",
    update: true
  },
    {
    tag: "equal",
    latest: "v3.4.0",
    current: "v3.4.0",
    update: false
  },
    {
    tag: "older",
    latest: "v3.3.9",
    current: "v3.4.0",
    update: false
  },
    {
    tag: "unknown",
    latest: "Unknown",
    current: "v3.4.0",
    update: false
  }
    ];
  }

    function test_versionsAndTitles(data) {
    GitHubService.latestVersion = data.latest;
    UpdateService.currentVersion = data.current;
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(50);
    verify(texts(tab).includes(data.latest));
    verify(texts(tab).includes(data.current));
    verify(texts(tab).includes("settings.about.noctalia.section.label"));
    verify(texts(tab).includes("settings.about.contributors.section.label"));
    verify(texts(tab).includes("settings.about.contributors.section.description_plural:22"));
    compare(updateButton(tab).visible, data.update);
    GitHubService.latestVersion = "v9.0.0";
    tryCompare(updateButton(tab), "visible", true);
    verify(texts(tab).includes("v9.0.0"));
    UpdateService.currentVersion = "v10.0.0";
    tryCompare(updateButton(tab), "visible", false);
    verify(texts(tab).includes("v10.0.0"));
    compare(Quickshell.processes.length, 0);
  }

    function test_navigation() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(50);
    updateButton(tab).clicked();
    linkArea(tab, "settings.about.support").clicked(null);
    linkArea(tab, "author0").clicked(null);
    linkArea(tab, "author19").clicked(null);
    linkArea(tab, "author20").clicked(null);
    linkArea(tab, "author21").clicked(null);
    compare(JSON.stringify(Quickshell.launches), JSON.stringify([["xdg-open", "https://github.com/Ly-sec/Noctalia/releases/latest"], ["xdg-open", "https://ko-fi.com/lysec"], ["xdg-open", "https://example.invalid/author0"], ["xdg-open", "https://example.invalid/author19"], ["xdg-open", "https://example.invalid/author20"]]));
    compare(ToastService.notices.length, 1);
    compare(ToastService.notices[0].title, "settings.about.support");
    compare(ToastService.notices[0].body, "toast.kofi.opened");
  }

    function test_contributorRolesAndUpdates() {
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(50);
    for (let index = 0; index < 22; index++)
    verify(texts(tab).includes("author" + index));
    verify(texts(tab).includes("10 commits"));
    verify(texts(tab).includes("29 commits"));
    verify(!texts(tab).includes("30 commits"));
    const images = descendants(tab).filter(item => item.source !== undefined && item.status !== undefined && item.visible);
    compare(images.length, 1);
    tryCompare(images[0], "status", Image.Ready);
    compare(images[0].source.toString(), Qt.resolvedUrl("avatar.svg").toString());
    compare(images[0].opacity, 1);
    const changed = contributors(21).reverse();
    changed[0].login = "renamed";
    changed[0].html_url = "https://example.invalid/renamed";
    GitHubService.contributors = changed;
    wait(50);
    verify(texts(tab).includes("renamed"));
    verify(!texts(tab).includes("author21"));
    verify(texts(tab).includes("30 commits"));
    linkArea(tab, "renamed").clicked(null);
    linkArea(tab, "author0").clicked(null);
    compare(Quickshell.launches[0][1], "https://example.invalid/renamed");
    compare(Quickshell.launches[1][1], "https://example.invalid/author0");
    GitHubService.contributors = [
    {
    login: "",
    contributions: 0,
    avatar_url: "",
    html_url: ""
  }
    ];
    wait(50);
    verify(texts(tab).includes("Unknown"));
    verify(texts(tab).includes("0 commits"));
    verify(texts(tab).includes("settings.about.contributors.section.description:1"));
    GitHubService.contributors = [];
    wait(50);
    verify(!texts(tab).includes("Unknown"));
    verify(texts(tab).includes("settings.about.contributors.section.description_plural:0"));
  }

    function test_gitCommit_data() {
    return [
    {
    tag: "arch-package",
    nix: false,
    packageExit: 0,
    packageOutput: "noctalia-shell-git 3.4.0.r112.g3f00bec8-1",
    commit: "3f00bec",
    queries: 1
  },
    {
    tag: "git-after-package-failure",
    nix: false,
    packageExit: 1,
    packageOutput: "",
    commit: "abc1234",
    queries: 2
  },
    {
    tag: "nix-store",
    nix: true,
    packageExit: 0,
    packageOutput: "",
    commit: "225e6d3",
    queries: 0
  }
    ];
  }

    function test_gitCommit(data) {
    UpdateService.currentVersion = "v3.4.0-git";
    HostService.isNixOS = data.nix;
    Quickshell.shellDir = "/nix/store/fixture-noctalia-shell-2025-11-30_225e6d31234/share/noctalia-shell";
    Quickshell.packageExit = data.packageExit;
    Quickshell.packageOutput = data.packageOutput;
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    tryCompare(tab, "commitInfo", data.commit);
    verify(texts(tab).includes(data.commit));
    verify(texts(tab).includes("settings.about.noctalia.git-commit"));
    compare(Quickshell.processes.length, data.queries);
    if (data.queries === 2)
    compare(JSON.stringify(Quickshell.processes[1]), JSON.stringify(["git", "rev-parse", "--short", "HEAD"]));
  }

    function test_disposeDuringCommitFetch() {
    UpdateService.currentVersion = "v3.4.0-git";
    Quickshell.packageExit = 1;
    Quickshell.processDelay = 700;
    const tab = tabComponent.createObject(testCase);
    verify(tab !== null);
    compare(Quickshell.processes.length, 1);
    tab.destroy();
    wait(800);
    compare(Quickshell.processes.length, 1, "No fallback fetch after disposal");
    compare(Quickshell.launches.length, 0);
    GitHubService.contributors = contributors(1);
    GitHubService.latestVersion = "v5.0.0";
    UpdateService.currentVersion = "v3.4.0";
    const reopened = createTemporaryObject(tabComponent, testCase);
    verify(reopened !== null);
    wait(50);
    verify(texts(reopened).includes("author0"));
    verify(texts(reopened).includes("v5.0.0"));
    compare(reopened.commitInfo, "");
  }
  }
