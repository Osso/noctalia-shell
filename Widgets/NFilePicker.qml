import Qt.labs.folderlistmodel
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import "../Helpers/FuzzySort.js" as FuzzySort
import qs.Commons
import qs.Widgets

Popup {
  id: root

  // Properties
  property string title: I18n.tr("widgets.file-picker.title")
  property string initialPath: Quickshell.env("HOME") || "/home"
  property string selectionMode: "files" // "files" or "folders"
  property var nameFilters: ["*"]
  property bool showDirs: true
  property bool showHiddenFiles: false

  property var selectedPaths: []
  property string currentPath: initialPath
  property bool shouldResetSelection: false
  readonly property alias currentSelection: filePickerPanel.currentSelection
  readonly property alias gridItemSize: gridView.itemSize

  // Signals
  signal accepted(var paths)
  signal cancelled

  function openFilePicker() {
    if (!root.currentPath)
      root.currentPath = root.initialPath;
    shouldResetSelection = true;
    open();
  }

  function getFileIcon(fileName) {
    const ext = fileName.split('.').pop().toLowerCase();
    const iconMap = {
      "txt": 'filepicker-file-text',
      "md": 'filepicker-file-text',
      "log": 'filepicker-file-text',
      "jpg": 'filepicker-photo',
      "jpeg": 'filepicker-photo',
      "png": 'filepicker-photo',
      "gif": 'filepicker-photo',
      "bmp": 'filepicker-photo',
      "svg": 'filepicker-photo',
      "mp4": 'filepicker-video',
      "avi": 'filepicker-video',
      "mkv": 'filepicker-video',
      "mov": 'filepicker-video',
      "mp3": 'filepicker-music',
      "wav": 'filepicker-music',
      "flac": 'filepicker-music',
      "ogg": 'filepicker-music',
      "zip": 'filepicker-archive',
      "tar": 'filepicker-archive',
      "gz": 'filepicker-archive',
      "rar": 'filepicker-archive',
      "7z": 'filepicker-archive',
      "pdf": 'filepicker-text',
      "doc": 'filepicker-text',
      "docx": 'filepicker-text',
      "xls": 'filepicker-table',
      "xlsx": 'filepicker-table',
      "ppt": 'filepicker-presentation',
      "pptx": 'filepicker-presentation',
      "html": 'filepicker-code',
      "htm": 'filepicker-code',
      "css": 'filepicker-code',
      "js": 'filepicker-code',
      "json": 'filepicker-code',
      "xml": 'filepicker-code',
      "exe": 'filepicker-settings',
      "app": 'filepicker-settings',
      "deb": 'filepicker-settings',
      "rpm": 'filepicker-settings'
    };
    return iconMap[ext] || 'filepicker-file';
  }

  function formatFileSize(bytes) {
    if (bytes === 0)
      return "0 B";
    const k = 1024, sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function confirmSelection() {
    if (filePickerPanel.currentSelection.length === 0)
      return;
    root.selectedPaths = filePickerPanel.currentSelection;
    root.accepted(filePickerPanel.currentSelection);
    root.close();
  }

  function navigateToPath(path) {
    folderModel.folder = "file://" + path;
    root.currentPath = path;
  }

  function setSearchBarVisible(visible) {
    filePickerPanel.showSearchBar = visible;
    if (visible) {
      Qt.callLater(() => searchInput.forceActiveFocus());
      return;
    }
    filePickerPanel.searchText = "";
    filePickerPanel.filterText = "";
    root.updateFilteredModel();
  }

  function handleFileEntryActivated(filePath, fileIsDir, doubleClick) {
    if (fileIsDir) {
      if (doubleClick) {
        root.navigateToPath(filePath);
      } else if (root.selectionMode === "folders") {
        filePickerPanel.currentSelection = [filePath];
      }
      return;
    }

    if (root.selectionMode !== "files") {
      return;
    }

    filePickerPanel.currentSelection = [filePath];
    if (doubleClick) {
      root.confirmSelection();
    }
  }

  function updateFilteredModel() {
    filteredModel.clear();
    const searchText = filePickerPanel.filterText.toLowerCase();

    for (var i = 0; i < folderModel.count; i++) {
      const fileName = folderModel.get(i, "fileName");
      const filePath = folderModel.get(i, "filePath");
      const fileIsDir = folderModel.get(i, "fileIsDir");
      const fileSize = folderModel.get(i, "fileSize");

      // Skip hidden items if showHiddenFiles is false
      // This additional check ensures hidden files are properly filtered
      if (!root.showHiddenFiles && fileName.startsWith(".")) {
        continue;
      }

      // In folder mode, hide files
      if (root.selectionMode === "folders" && !fileIsDir)
        continue;
      if (searchText === "" || fileName.toLowerCase().includes(searchText)) {
        filteredModel.append({
          "picker": root,
          "fileName": fileName,
          "filePath": filePath,
          "fileIsDir": fileIsDir,
          "fileSize": fileSize
        });
      }
    }
  }

  width: 900
  height: 700
  modal: true
  closePolicy: Popup.CloseOnEscape
  anchors.centerIn: Overlay.overlay

  background: Rectangle {
    color: NColor.mSurfaceVariant
    radius: Style.radiusL
    border.color: NColor.mOutline
    border.width: Style.borderS
  }

  Rectangle {
    id: filePickerPanel
    anchors.fill: parent
    anchors.margins: Style.marginL
    color: NColor.transparent

    property string filterText: ""
    property list<string> currentSelection: []
    property bool viewMode: true // true = grid, false = list
    property string searchText: ""
    property bool showSearchBar: false

    focus: true

    Keys.onPressed: event => {
      if (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_F) {
        root.setSearchBarVisible(!filePickerPanel.showSearchBar);
        event.accepted = true;
      } else if (event.key === Qt.Key_Escape && filePickerPanel.showSearchBar) {
        root.setSearchBarVisible(false);
        event.accepted = true;
      }
    }

    ColumnLayout {
      anchors.fill: parent
      spacing: Style.marginM

      // Header
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        NIcon {
          icon: "filepicker-folder"
          color: NColor.mPrimary
          pointSize: Style.fontSizeXXL
        }
        NText {
          text: root.title
          pointSize: Style.fontSizeXL
          font.weight: Style.fontWeightBold
          color: NColor.mPrimary
          Layout.fillWidth: true
        }

        // "Select Current" button only visible in folder selection mode
        NButton {
          text: I18n.tr("widgets.file-picker.select-current")
          icon: "filepicker-folder-current"
          visible: root.selectionMode === "folders"
          onClicked: {
            filePickerPanel.currentSelection = [root.currentPath];
            root.confirmSelection();
          }
        }

        NIconButton {
          icon: "filepicker-refresh"
          tooltipText: I18n.tr("tooltips.refresh")
          onClicked: {
            // Force a proper refresh by resetting the folder
            const currentFolder = folderModel.folder;
            folderModel.folder = "";
            folderModel.folder = currentFolder;
            Qt.callLater(root.updateFilteredModel);
          }
        }
        NIconButton {
          icon: "filepicker-close"
          tooltipText: I18n.tr("tooltips.close")
          onClicked: {
            root.cancelled();
            root.close();
          }
        }
      }

      NDivider {
        Layout.fillWidth: true
      }

      // Navigation toolbar
      Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 45
        color: NColor.mSurfaceVariant
        radius: Style.radiusS
        border.color: NColor.mOutline
        border.width: Style.borderS

        RowLayout {
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          anchors.leftMargin: Style.marginS
          anchors.rightMargin: Style.marginS
          spacing: Style.marginS

          NIconButton {
            icon: "filepicker-arrow-up"
            tooltipText: I18n.tr("tooltips.up")
            baseSize: Style.baseWidgetSize * 0.8
            enabled: folderModel.folder.toString() !== "file:///"
            onClicked: {
              const parentPath = folderModel.parentFolder.toString().replace("file://", "");
              root.navigateToPath(parentPath);
            }
          }

          NIconButton {
            icon: "filepicker-home"
            tooltipText: I18n.tr("tooltips.home")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: {
              const homePath = Quickshell.env("HOME") || "/home";
              folderModel.folder = "file://" + homePath;
              root.currentPath = homePath;
            }
          }

          NIconButton {
            icon: filePickerPanel.showSearchBar ? "filepicker-x" : "filepicker-search"
            tooltipText: filePickerPanel.showSearchBar ? I18n.tr("tooltips.search-close") : I18n.tr("tooltips.search")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: {
              root.setSearchBarVisible(!filePickerPanel.showSearchBar);
            }
          }

          NTextInput {
            id: locationInput
            text: root.currentPath
            placeholderText: "Enter path..."
            Layout.fillWidth: true

            visible: !filePickerPanel.showSearchBar
            enabled: !filePickerPanel.showSearchBar

            onEditingFinished: {
              const newPath = text.trim();
              if (newPath !== "" && newPath !== root.currentPath) {
                folderModel.folder = "file://" + newPath;
                root.currentPath = newPath;
              } else {
                text = root.currentPath;
              }
            }
            Connections {
              target: root
              function onCurrentPathChanged() {
                if (!locationInput.activeFocus)
                  locationInput.text = root.currentPath;
              }
            }
          }

          // Search bar
          NTextInput {
            id: searchInput
            inputIconName: "search"
            placeholderText: I18n.tr("placeholders.search")
            Layout.fillWidth: true

            visible: filePickerPanel.showSearchBar
            enabled: filePickerPanel.showSearchBar

            text: filePickerPanel.searchText
            onTextChanged: {
              filePickerPanel.searchText = text;
              filePickerPanel.filterText = text;
              root.updateFilteredModel();
            }
            Keys.onEscapePressed: {
              root.setSearchBarVisible(false);
            }
          }

          NIconButton {
            icon: filePickerPanel.viewMode ? "filepicker-list" : "filepicker-layout-grid"
            tooltipText: filePickerPanel.viewMode ? I18n.tr("tooltips.list-view") : I18n.tr("tooltips.grid-view")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: filePickerPanel.viewMode = !filePickerPanel.viewMode
          }
          NIconButton {
            icon: root.showHiddenFiles ? "filepicker-eye-off" : "filepicker-eye"
            tooltipText: root.showHiddenFiles ? I18n.tr("tooltips.hidden-files-hide") : I18n.tr("tooltips.hidden-files-show")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: {
              root.showHiddenFiles = !root.showHiddenFiles;
              // Force model refresh by resetting the folder
              const currentFolder = folderModel.folder;
              folderModel.folder = "";
              folderModel.folder = currentFolder;
              Qt.callLater(root.updateFilteredModel);
            }
          }
        }
      }

      // File list area
      Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: NColor.mSurface
        radius: Style.radiusM
        border.color: NColor.mOutline
        border.width: Style.borderS

        FolderListModel {
          id: folderModel
          folder: "file://" + root.currentPath
          // Use wildcard filters including hidden files when showHiddenFiles is true
          nameFilters: root.showHiddenFiles ? ["*", ".*"] : root.nameFilters
          showDirs: root.showDirs
          showHidden: true // Always true, we'll filter in updateFilteredModel
          showDotAndDotDot: false
          sortField: FolderListModel.Name
          sortReversed: false

          onFolderChanged: {
            root.currentPath = folder.toString().replace("file://", "");
            filePickerPanel.currentSelection = [];
            Qt.callLater(root.updateFilteredModel);
          }

          onStatusChanged: {
            if (status === FolderListModel.Ready) {
              root.updateFilteredModel();
            }
          }
        }

        // Update nameFilters when showHiddenFiles changes
        Connections {
          target: root
          function onShowHiddenFilesChanged() {
            folderModel.nameFilters = root.showHiddenFiles ? ["*", ".*"] : root.nameFilters;
          }
        }

        ListModel {
          id: filteredModel
        }

        // Grid view
        GridView {
          id: gridView
          visible: filePickerPanel.viewMode
          anchors.fill: parent
          anchors.margins: Style.marginM
          model: filteredModel
          clip: true
          reuseItems: true

          property int columns: Math.max(1, Math.floor(width / (120)))
          property int itemSize: Math.floor((width - leftMargin - rightMargin - (columns * Style.marginS)) / columns)

          cellWidth: Math.floor((width - leftMargin - rightMargin) / columns)
          cellHeight: Math.floor(itemSize * 0.8) + Style.marginXS + Style.fontSizeS + Style.marginM

          leftMargin: Style.marginS
          rightMargin: Style.marginS
          topMargin: Style.marginS
          bottomMargin: Style.marginS

          ScrollBar.vertical: PickerScrollBar {}

          delegate: Rectangle {
            id: gridItem
            required property NFilePicker picker
            required property string fileName
            required property string filePath
            required property bool fileIsDir
            required property int fileSize

            width: gridItem.picker.gridItemSize
            height: GridView.view.cellHeight
            color: NColor.transparent
            radius: Style.radiusM

            property bool isSelected: gridItem.picker.currentSelection.includes(gridItem.filePath)

            Rectangle {
              anchors.fill: parent
              color: NColor.transparent
              radius: parent.radius
              border.color: gridItem.isSelected ? NColor.mSecondary : NColor.mSurface
              border.width: Style.borderL
              Behavior on color {
                ColorAnimation {
                  duration: Style.animationFast
                }
              }
            }

            Rectangle {
              anchors.fill: parent
              color: (mouseArea.containsMouse && !gridItem.isSelected) ? NColor.mHover : NColor.transparent
              radius: parent.radius
              border.color: (mouseArea.containsMouse && !gridItem.isSelected) ? NColor.mHover : NColor.transparent
              border.width: Style.borderS
              Behavior on color {
                ColorAnimation {
                  duration: Style.animationFast
                }
              }
              Behavior on border.color {
                ColorAnimation {
                  duration: Style.animationFast
                }
              }
            }

            ColumnLayout {
              anchors.fill: parent
              anchors.margins: Style.marginS
              spacing: Style.marginXS

              Rectangle {
                id: iconContainer
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(gridItem.picker.gridItemSize * 0.67)
                color: NColor.transparent

                property bool isImage: {
                  if (gridItem.fileIsDir)
                    return false;
                  const ext = gridItem.fileName.split('.').pop().toLowerCase();
                  return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico'].includes(ext);
                }

                Image {
                  id: thumbnail
                  anchors.fill: parent
                  anchors.margins: Style.marginXS
                  source: iconContainer.isImage ? "file://" + gridItem.filePath : ""
                  fillMode: Image.PreserveAspectFit
                  visible: iconContainer.isImage && status === Image.Ready
                  smooth: false
                  cache: true
                  asynchronous: true
                  sourceSize.width: 120
                  sourceSize.height: 120
                  onStatusChanged: {
                    if (status === Image.Error)
                      visible = false;
                  }

                  Rectangle {
                    anchors.fill: parent
                    color: NColor.mSurfaceVariant
                    radius: Style.radiusS
                    visible: thumbnail.status === Image.Loading
                    NIcon {
                      icon: "filepicker-photo"
                      pointSize: Style.fontSizeL
                      color: NColor.mOnSurfaceVariant
                      anchors.centerIn: parent
                    }
                  }
                }

                NIcon {
                  icon: gridItem.fileIsDir ? "filepicker-folder" : gridItem.picker.getFileIcon(gridItem.fileName)
                  pointSize: Style.fontSizeXXL * 2
                  color: {
                    if (gridItem.isSelected)
                      return NColor.mSecondary;
                    else if (mouseArea.containsMouse)
                      return NColor.mOnHover;
                    else
                      return gridItem.fileIsDir ? NColor.mPrimary : NColor.mOnSurfaceVariant;
                  }
                  anchors.centerIn: parent
                  visible: !iconContainer.isImage || thumbnail.status !== Image.Ready
                }

                Rectangle {
                  anchors.top: parent.top
                  anchors.right: parent.right
                  anchors.margins: Style.marginS
                  width: 24
                  height: 24
                  radius: Math.min(Style.radiusL, width / 2)
                  color: NColor.mSecondary
                  border.color: NColor.mOutline
                  border.width: Style.borderS
                  visible: gridItem.isSelected
                  NIcon {
                    icon: "filepicker-check"
                    pointSize: Style.fontSizeS
                    color: NColor.mOnSecondary
                    anchors.centerIn: parent
                  }
                }
              }

              NText {
                text: gridItem.fileName
                color: {
                  if (gridItem.isSelected)
                    return NColor.mSecondary;
                  else if (mouseArea.containsMouse)
                    return NColor.mOnHover;
                  else
                    return NColor.mOnSurfaceVariant;
                }
                pointSize: Style.fontSizeS
                font.weight: gridItem.isSelected ? Style.fontWeightBold : Style.fontWeightRegular
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WrapAnywhere
                elide: Text.ElideRight
                maximumLineCount: 2
              }
            }

            MouseArea {
              id: mouseArea
              anchors.fill: parent
              hoverEnabled: true
              acceptedButtons: Qt.LeftButton | Qt.RightButton

              onClicked: mouse => {
                if (mouse.button === Qt.LeftButton) {
                  gridItem.picker.handleFileEntryActivated(gridItem.filePath, gridItem.fileIsDir, false);
                }
              }

              onDoubleClicked: mouse => {
                if (mouse.button === Qt.LeftButton) {
                  gridItem.picker.handleFileEntryActivated(gridItem.filePath, gridItem.fileIsDir, true);
                }
              }
            }
          }
        }

        // List view
        NListView {
          id: listView
          visible: !filePickerPanel.viewMode
          anchors.fill: parent
          anchors.margins: Style.marginS
          model: filteredModel

          delegate: Rectangle {
            id: listItem
            required property NFilePicker picker
            required property string fileName
            required property string filePath
            required property bool fileIsDir
            required property int fileSize

            width: ListView.view.width
            height: 40
            color: {
              if (listItem.picker.currentSelection.includes(listItem.filePath))
                return NColor.mSecondary;
              if (listMouseArea.containsMouse)
                return NColor.mHover;
              return NColor.transparent;
            }
            radius: Style.radiusS
            Behavior on color {
              ColorAnimation {
                duration: Style.animationFast
              }
            }

            RowLayout {
              anchors.fill: parent
              anchors.leftMargin: Style.marginM
              anchors.rightMargin: Style.marginM
              spacing: Style.marginM

              NIcon {
                icon: listItem.fileIsDir ? "filepicker-folder" : listItem.picker.getFileIcon(listItem.fileName)
                pointSize: Style.fontSizeL
                color: listItem.fileIsDir ? (listItem.picker.currentSelection.includes(listItem.filePath) ? NColor.mOnSecondary : NColor.mPrimary) : NColor.mOnSurfaceVariant
              }

              NText {
                text: listItem.fileName
                color: listItem.picker.currentSelection.includes(listItem.filePath) ? NColor.mOnSecondary : NColor.mOnSurface
                pointSize: Style.fontSizeM
                font.weight: listItem.picker.currentSelection.includes(listItem.filePath) ? Style.fontWeightBold : Style.fontWeightRegular
                Layout.fillWidth: true
                elide: Text.ElideRight
              }

              NText {
                text: listItem.fileIsDir ? "" : listItem.picker.formatFileSize(listItem.fileSize)
                color: listItem.picker.currentSelection.includes(listItem.filePath) ? NColor.mOnSecondary : NColor.mOnSurfaceVariant
                pointSize: Style.fontSizeS
                visible: !listItem.fileIsDir
                Layout.preferredWidth: implicitWidth
              }
            }

            MouseArea {
              // Keep grid/list IDs distinct until Qt 6.11 qmllint respects delegate scopes.
              id: listMouseArea
              anchors.fill: parent
              hoverEnabled: true
              acceptedButtons: Qt.LeftButton | Qt.RightButton

              onClicked: mouse => {
                if (mouse.button === Qt.LeftButton) {
                  listItem.picker.handleFileEntryActivated(listItem.filePath, listItem.fileIsDir, false);
                }
              }

              onDoubleClicked: mouse => {
                if (mouse.button === Qt.LeftButton) {
                  listItem.picker.handleFileEntryActivated(listItem.filePath, listItem.fileIsDir, true);
                }
              }
            }
          }
        }
      }

      // Footer
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.marginM

        NText {
          text: {
            if (filePickerPanel.searchText.length > 0) {
              return "Searching for: \"" + filePickerPanel.searchText + "\" (" + filteredModel.count + " matches)";
            } else if (filePickerPanel.currentSelection.length > 0) {
              const selectedName = filePickerPanel.currentSelection[0].split('/').pop();
              return "Selected: " + selectedName;
            } else {
              return filteredModel.count + " items";
            }
          }
          color: filePickerPanel.searchText.length > 0 ? NColor.mPrimary : NColor.mOnSurfaceVariant
          pointSize: Style.fontSizeS
          Layout.fillWidth: true
        }

        NButton {
          text: I18n.tr("widgets.file-picker.cancel")
          outlined: true
          onClicked: {
            root.cancelled();
            root.close();
          }
        }

        NButton {
          text: root.selectionMode === "folders" ? I18n.tr("widgets.file-picker.select-folder") : I18n.tr("widgets.file-picker.select-file")
          icon: "filepicker-check"
          enabled: filePickerPanel.currentSelection.length > 0
          onClicked: root.confirmSelection()
        }
      }
    }

    Connections {
      target: root
      function onShouldResetSelectionChanged() {
        if (root.shouldResetSelection) {
          filePickerPanel.currentSelection = [];
          root.shouldResetSelection = false;
        }
      }
    }

    Component.onCompleted: {
      if (!root.currentPath)
        root.currentPath = root.initialPath;
      folderModel.folder = "file://" + root.currentPath;
    }
  }

  // Common scroll bar component
  component PickerScrollBar: ScrollBar {
    id: pickerScrollBar
    policy: ScrollBar.AsNeeded
    contentItem: Rectangle {
      implicitWidth: 6
      implicitHeight: 100
      radius: Style.radiusM
      color: Qt.alpha(NColor.mHover, 0.8)
      opacity: pickerScrollBar.policy === ScrollBar.AlwaysOn || pickerScrollBar.active ? 1.0 : 0.0
      Behavior on opacity {
        NumberAnimation {
          duration: Style.animationFast
        }
      }
      Behavior on color {
        ColorAnimation {
          duration: Style.animationFast
        }
      }
    }
    background: Rectangle {
      implicitWidth: 6
      implicitHeight: 100
      color: NColor.transparent
      opacity: pickerScrollBar.policy === ScrollBar.AlwaysOn || pickerScrollBar.active ? 0.3 : 0.0
      radius: (Style.radiusM) / 2
      Behavior on opacity {
        NumberAnimation {
          duration: Style.animationFast
        }
      }
    }
  }
}
