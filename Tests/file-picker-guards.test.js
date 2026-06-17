#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Widgets/NFilePicker.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createFolderModel(rows) {
  return {
    count: rows.length,
    get(index, key) {
      return rows[index][key];
    },
  };
}

function createFilteredModel() {
  return {
    rows: [{ fileName: "stale" }],
    clear() {
      this.rows = [];
    },
    append(row) {
      this.rows.push(row);
    },
  };
}

function testFilePickerIconMappingUsesKnownExtensionsAndFallback() {
  assert.match(source, /function getFileIcon\(fileName: string\)/, "getFileIcon must type file-name input");
  const getFileIcon = qmlFunction("getFileIcon", "fileName");

  assert.equal(getFileIcon({}, "README.MD"), "filepicker-file-text");
  assert.equal(getFileIcon({}, "photo.jpeg"), "filepicker-photo");
  assert.equal(getFileIcon({}, "movie.mkv"), "filepicker-video");
  assert.equal(getFileIcon({}, "song.flac"), "filepicker-music");
  assert.equal(getFileIcon({}, "archive.7z"), "filepicker-archive");
  assert.equal(getFileIcon({}, "report.pdf"), "filepicker-text");
  assert.equal(getFileIcon({}, "sheet.xlsx"), "filepicker-table");
  assert.equal(getFileIcon({}, "slides.pptx"), "filepicker-presentation");
  assert.equal(getFileIcon({}, "component.qml"), "filepicker-file");
}

function testFilePickerFormatsFileSizes() {
  assert.match(source, /function formatFileSize\(bytes: real\)/, "formatFileSize must type byte-size input");
  const formatFileSize = qmlFunction("formatFileSize", "bytes");

  assert.equal(formatFileSize({}, 0), "0 B");
  assert.equal(formatFileSize({}, 512), "512 B");
  assert.equal(formatFileSize({}, 1536), "1.5 KB");
  assert.equal(formatFileSize({}, 5 * 1024 * 1024), "5 MB");
  assert.equal(formatFileSize({}, 3.5 * 1024 * 1024 * 1024), "3.5 GB");
}

function testFilePickerOpenInitializesPathAndSelectionReset() {
  const openFilePicker = qmlFunction("openFilePicker");
  let openCalls = 0;
  const ctx = {
    root: {
      currentPath: "",
      initialPath: "/home/osso",
    },
    shouldResetSelection: false,
    open() {
      openCalls += 1;
    },
  };

  openFilePicker(ctx);

  assert.equal(ctx.root.currentPath, "/home/osso");
  assert.equal(ctx.shouldResetSelection, true);
  assert.equal(openCalls, 1);

  ctx.root.currentPath = "/tmp";
  ctx.shouldResetSelection = false;
  openFilePicker(ctx);

  assert.equal(ctx.root.currentPath, "/tmp");
  assert.equal(ctx.shouldResetSelection, true);
  assert.equal(openCalls, 2);
}

function testFilePickerConfirmSelectionGuardsEmptySelection() {
  const confirmSelection = qmlFunction("confirmSelection");
  const acceptedSelections = [];
  let closeCalls = 0;
  const ctx = {
    filePickerPanel: {
      currentSelection: [],
    },
    root: {
      selectedPaths: ["existing"],
      accepted(paths) {
        acceptedSelections.push(paths);
      },
      close() {
        closeCalls += 1;
      },
    },
  };

  confirmSelection(ctx);

  assert.deepEqual(ctx.root.selectedPaths, ["existing"]);
  assert.deepEqual(acceptedSelections, []);
  assert.equal(closeCalls, 0);

  ctx.filePickerPanel.currentSelection = ["/home/osso/file.txt"];
  confirmSelection(ctx);

  assert.deepEqual(ctx.root.selectedPaths, ["/home/osso/file.txt"]);
  assert.deepEqual(acceptedSelections, [["/home/osso/file.txt"]]);
  assert.equal(closeCalls, 1);
}

function testFilePickerFilteredModelHidesHiddenFilesAndMatchesSearch() {
  const updateFilteredModel = qmlFunction("updateFilteredModel");
  const filteredModel = createFilteredModel();
  const ctx = {
    filteredModel,
    filePickerPanel: {
      filterText: "pro",
    },
    folderModel: createFolderModel([
      { fileName: "Project", filePath: "/home/osso/Project", fileIsDir: true, fileSize: 0 },
      { fileName: ".profile", filePath: "/home/osso/.profile", fileIsDir: false, fileSize: 42 },
      { fileName: "notes.txt", filePath: "/home/osso/notes.txt", fileIsDir: false, fileSize: 12 },
      { fileName: "proposal.pdf", filePath: "/home/osso/proposal.pdf", fileIsDir: false, fileSize: 100 },
    ]),
    root: {
      showHiddenFiles: false,
      selectionMode: "files",
    },
  };

  updateFilteredModel(ctx);

  assert.deepEqual(filteredModel.rows, [
    { fileName: "Project", filePath: "/home/osso/Project", fileIsDir: true, fileSize: 0 },
    { fileName: "proposal.pdf", filePath: "/home/osso/proposal.pdf", fileIsDir: false, fileSize: 100 },
  ]);
}

function testFilePickerFilteredModelSupportsFolderModeAndHiddenFiles() {
  const updateFilteredModel = qmlFunction("updateFilteredModel");
  const filteredModel = createFilteredModel();
  const ctx = {
    filteredModel,
    filePickerPanel: {
      filterText: "",
    },
    folderModel: createFolderModel([
      { fileName: ".config", filePath: "/home/osso/.config", fileIsDir: true, fileSize: 0 },
      { fileName: "Downloads", filePath: "/home/osso/Downloads", fileIsDir: true, fileSize: 0 },
      { fileName: "file.txt", filePath: "/home/osso/file.txt", fileIsDir: false, fileSize: 20 },
    ]),
    root: {
      showHiddenFiles: true,
      selectionMode: "folders",
    },
  };

  updateFilteredModel(ctx);

  assert.deepEqual(filteredModel.rows, [
    { fileName: ".config", filePath: "/home/osso/.config", fileIsDir: true, fileSize: 0 },
    { fileName: "Downloads", filePath: "/home/osso/Downloads", fileIsDir: true, fileSize: 0 },
  ]);
}

const tests = [
  testFilePickerIconMappingUsesKnownExtensionsAndFallback,
  testFilePickerFormatsFileSizes,
  testFilePickerOpenInitializesPathAndSelectionReset,
  testFilePickerConfirmSelectionGuardsEmptySelection,
  testFilePickerFilteredModelHidesHiddenFilesAndMatchesSearch,
  testFilePickerFilteredModelSupportsFolderModeAndHiddenFiles,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
