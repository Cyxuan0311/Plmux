import { applyLayout, reposition } from "./layout.js";
import { show as showOverlay, hide as hideOverlay, getTerm as getOverlayTerm } from "./overlay.js";
import { applyTheme } from "./theme.js";
import { updateMode, updateStatus, updateCmdline, applyStatusBarStyle } from "./statusbar.js";
import { applyPaneBorderStyle } from "./panes.js";
import { setSnapshotIgnoreUntil } from "./connection.js";

var OVERLAY_MODES = ["HELP", "THEME_LIST", "SESSION_LIST", "PLUGIN_LIST", "LAYOUT_LIST", "COPY", "STATUSBAR_STYLE", "PANE_BORDER_STYLE"];

var _snapshotIgnoreUntil = 0;

export function handleMessage(msg, state, paneManager) {
  switch(msg.type) {
    case "output":
      if (Date.now() < _snapshotIgnoreUntil) break;
      if (state.currentFocus in paneManager.terms) {
        paneManager.terms[state.currentFocus].write(msg.data || "");
      }
      break;
    case "pane_output":
      if (Date.now() < _snapshotIgnoreUntil) break;
      var pidx = msg.idx;
      if (pidx in paneManager.terms) {
        paneManager.terms[pidx].write(msg.data || "");
      }
      break;
    case "pane_snapshot":
      var sidx = msg.idx;
      var term = paneManager.ensure(sidx);
      term.reset();
      if (msg.data) {
        term.write(msg.data);
      }
      if (msg.cursor) {
        var cy = msg.cursor[0];
        var cx = msg.cursor[1];
        term.write("\x1b[" + (cy + 1) + ";" + (cx + 1) + "H");
      }
      _snapshotIgnoreUntil = Date.now() + 300;
      setSnapshotIgnoreUntil(_snapshotIgnoreUntil);
      break;
    case "snapshot":
      if (state.currentFocus in paneManager.terms) {
        paneManager.terms[state.currentFocus].write(msg.data || "");
      }
      break;
    case "layout":
      applyLayout(msg, state, paneManager);
      break;
    case "mode":
      handleModeChange(msg.mode, msg.prev_mode, state, paneManager);
      break;
    case "overlay":
      showOverlay(msg.kind, msg.content);
      break;
    case "overlay_close":
      hideOverlay();
      break;
    case "theme":
      applyTheme(msg, state, paneManager, { getTerm: getOverlayTerm });
      break;
    case "status":
      updateStatus(msg, state);
      break;
    case "cmdline":
      updateCmdline(msg);
      break;
    case "statusbar_style":
      applyStatusBarStyle(msg.style || msg);
      break;
    case "pane_border_style":
      applyPaneBorderStyle(msg.style || msg);
      break;
    case "bell":
      if (state.currentFocus in paneManager.terms) {
        paneManager.terms[state.currentFocus].write("\x07");
      }
      break;
    case "title":
      document.title = msg.title || "plmux web";
      break;
  }
}

function handleModeChange(newMode, prevMode, state, paneManager) {
  state.currentMode = newMode;
  updateMode(newMode);

  if (OVERLAY_MODES.indexOf(newMode) === -1 && newMode !== "COPY") {
    hideOverlay();
  }

  if (newMode === "CMDLINE") {
    updateCmdline({ active: true, buffer: "" });
  } else if (newMode === "NORMAL") {
    updateCmdline({ active: false });
  }
}
