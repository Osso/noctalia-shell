import QtQuick
import QtTest
import Quickshell
import qs.Commons

TestCase {
    id: testCase

    property string greeting: I18n.tr("menu.greeting", {
        "name": "Ada"
    })

    function enumerateLanguages(listing, code) {
        I18n.directoryScanner.stdout.text = listing;
        I18n.directoryScanner.exited(code, 0);
    }

    function test_languageListAndTranslationUpdate() {
        verify(I18n.directoryScanner.running);
        compare(I18n.directoryScanner.command, ["ls", "/private-fixture/Assets/Translations/"]);
        enumerateLanguages("it.json\nen.json\nfr.json\nREADME\nx.json\nlongname.json\n", 0);
        compare(I18n.availableLanguages, ["en", "fr", "it"]);
        compare(I18n.langCode, "it");
        compare(languageSpy.count, 1);
        compare(I18n.translationFile.path, "file:///private-fixture/Assets/Translations/it.json");
        compare(I18n.fallbackTranslationFile.path, "file:///private-fixture/Assets/Translations/en.json");
        compare(testCase.greeting, "menu.greeting");
        I18n.fallbackTranslationFile.deliver('{"menu":{"onlyEnglish":"English"}}');
        I18n.translationFile.deliver('{"menu":{"greeting":"Ciao {name}!"}}');
        compare(testCase.greeting, "Ciao Ada!");
        compare(translationsSpy.count, 1);
        compare(I18n.tr("menu.onlyEnglish"), "<i>English</i>");
        compare(I18n.tr("menu.missing"), "## menu.missing ##");
        verify(I18n.hasTranslation("menu.greeting"));
        I18n.translationFile.fileChanged();
        compare(I18n.translationFile.reloadCount, 1);
        I18n.translationFile.deliver('{"menu":{"greeting":"Salve {name}!"}}');
        compare(testCase.greeting, "Salve Ada!");
        compare(translationsSpy.count, 2);
        // Exercise the nested FileView error handlers and scanner failure boundary.
        I18n.translationFile.deliver("invalid json");
        compare(I18n.langCode, "en");
        verify(!I18n.isLoaded);
        I18n.setLanguage("it");
        I18n.translationFile.loadFailed(1);
        compare(I18n.langCode, "en");
        enumerateLanguages("", 1);
        compare(I18n.availableLanguages, ["en"]);
        enumerateLanguages("", 0);
        compare(I18n.availableLanguages, ["en"]);
        compare(Logger.errors.length, 3);
    }

    function test_namedIconsAndThemeUpdate() {
        compare(ThemeIcons.iconFromName("firefox"), "/private-icons/day/firefox.svg");
        compare(ThemeIcons.iconFromName("missing"), "/private-icons/day/application-x-executable.svg");
        compare(ThemeIcons.iconFromName("/private/unsafe.svg"), "/private-icons/day/application-x-executable.svg");
        compare(ThemeIcons.iconFromName("file:///private/unsafe.svg", "firefox"), "/private-icons/day/firefox.svg");
        compare(ThemeIcons.iconFromName("missing", "also-missing"), "");
        Quickshell.iconTheme = "night";
        compare(ThemeIcons.iconFromName("firefox"), "/private-icons/night/firefox.svg");
        compare(ThemeIcons.distroLogoPath(), "");
    }

    name: "I18nThemeIcons"

    SignalSpy {
        id: languageSpy

        target: I18n
        signalName: "languageChanged"
    }

    SignalSpy {
        id: translationsSpy

        target: I18n
        signalName: "translationsLoaded"
    }
}
