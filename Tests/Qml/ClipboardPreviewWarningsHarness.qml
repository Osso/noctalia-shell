import QtQuick
import QtQuick.Controls
import QtTest
import qs.Services.Keyboard

Item {
  id: harness
  width: 480
  height: 320

  readonly property string imagePath: "@IMAGE_PATH@"
  readonly property string imageData: "data:image/svg+xml;base64," + Qt.btoa('<svg xmlns="http://www.w3.org/2000/svg" width="7" height="5"><rect width="7" height="5" fill="blue"/></svg>')

  Loader {
    id: previewLoader
    anchors.fill: parent
    source: "qs/Modules/Panels/Launcher/ClipboardPreview.qml"
  }

  TestCase {
    name: "ClipboardPreviewLifecycle"
    when: windowShown

    function descendants(item, predicate) {
      if (predicate(item))
        return item;
      for (const child of item.children) {
        const match = descendants(child, predicate);
        if (match)
          return match;
      }
      return null;
    }

    function imageView() {
      return descendants(previewLoader.item, child => child.imagePath !== undefined);
    }

    function textView() {
      return descendants(previewLoader.item, child => child.readOnly !== undefined && child.textFormat !== undefined);
    }

    function select(id, isImage) {
      previewLoader.item.currentItem = {
        clipboardId: id,
        isImage: isImage,
        mime: isImage ? "image/svg+xml" : "text/plain"
      };
    }

    function init() {
      compare(previewLoader.status, Loader.Ready);
      previewLoader.item.currentItem = null;
      ClipboardService.reset();
    }

    function cleanup() {
      previewLoader.item.currentItem = null;
    }

    function test_text_decode_and_path_text() {
      const preview = previewLoader.item;
      select("text", false);
      verify(preview.loadingFullContent);
      verify(!textView().visible);
      ClipboardService.finishText("text", "Alpha <tag> & beta\nsecond line");
      verify(!preview.loadingFullContent);
      verify(preview.fullContent.includes("Alpha &lt;tag&gt; &amp; beta\nsecond line"));
      compare(textView().getText(0, textView().length).replace(/\u2029/g, "\n").trim(), "Alpha <tag> & beta\nsecond line");
      verify(textView().visible);
      verify(!imageView().visible);
      select("path", false);
      compare(preview.fullContent, "");
      ClipboardService.finishText("path", harness.imagePath);
      verify(textView().text.includes(harness.imagePath));
    }

    function test_pending_image_revision_and_cached_reassign() {
      const preview = previewLoader.item;
      select("image", true);
      verify(preview.loadingFullContent);
      compare(ClipboardService.requestedImageId, "image");
      verify(!imageView().visible);
      ClipboardService.publishImage("image", harness.imageData);
      compare(preview._rev, 1);
      tryCompare(preview, "imageDataUrl", harness.imageData);
      verify(!preview.loadingFullContent);
      verify(imageView().visible);
      verify(!textView().visible);
      const source = descendants(imageView(), child => child.sourceSize !== undefined);
      tryCompare(source, "status", Image.Ready);
      verify(source.sourceSize.width > 0);
      // Reassign after replacing the cache: loaded images intentionally stop polling.
      ClipboardService.publishImage("image", harness.imagePath);
      compare(preview._rev, 2);
      select("image", true);
      compare(preview.imageDataUrl, harness.imagePath);
      tryCompare(source, "status", Image.Ready);
      compare(source.source.toString(), harness.imagePath);
    }

    function test_clear_pending_image_and_reassign_text() {
      const preview = previewLoader.item;
      select("pending", true);
      verify(preview.loadingFullContent);
      preview.currentItem = null;
      compare(preview.fullContent, "");
      compare(preview.imageDataUrl, "");
      verify(!preview.isImageContent);
      verify(!preview.loadingFullContent);
      ClipboardService.publishImage("pending", harness.imageData);
      wait(250);
      compare(preview.imageDataUrl, "");
      select("replacement", false);
      ClipboardService.finishText("replacement", "Replacement text");
      verify(textView().visible);
      verify(textView().text.includes("Replacement text"));
      compare(imageView().imagePath, "");
      preview.currentItem = null;
      compare(textView().length, 0);
    }

    function test_loader_destroy_and_reload_cached_image() {
      ClipboardService.publishImage("cached", harness.imagePath);
      select("cached", true);
      compare(previewLoader.item.imageDataUrl, harness.imagePath);
      previewLoader.active = false;
      compare(previewLoader.item, null);
      previewLoader.active = true;
      compare(previewLoader.status, Loader.Ready);
      compare(previewLoader.item.currentItem, null);
      select("cached", true);
      compare(imageView().imagePath, harness.imagePath);
      verify(!previewLoader.item.loadingFullContent);
    }
  }
}
