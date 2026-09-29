import Quickshell
import Quickshell.Io

IpcHandler {
  target: "shell"

  function reload(): void {
    Qt.callLater(() => Quickshell.reload(false));
  }
}
