import { initInputHandlers, updateSendFunction } from "./input.js";
import { initConnection, connect, send, sendRaw } from "./connection.js";
import { createPaneManager } from "./panes.js";
import { initOverlay } from "./overlay.js";
import { handleMessage } from "./messages.js";
import { reposition, scheduleFit } from "./layout.js";
import { getAuthMode, getSessionName } from "./utils.js";

var state = {
  currentTheme: null,
  currentMode: "NORMAL",
  currentFocus: 0,
  layoutTree: null,
  layoutPanes: [],
  lastCols: 0,
  lastRows: 0,
  ws: null,
  connected: false,
  overlayVisible: false,
  overlayKind: "",
  termBg: "#1d2021",
  overlayBg: "#1d2021",
  terms: {},
  send: send,
  sendRaw: sendRaw,
  authMode: getAuthMode(),
  sessionName: getSessionName(),
  readonly: getAuthMode() === "ro",
};

document.addEventListener("DOMContentLoaded", function() {
  var paneManager = createPaneManager(state);
  paneManager.init();

  initOverlay(state);
  initConnection(state, function(msg) {
    handleMessage(msg, state, paneManager);
  });

  initInputHandlers(paneManager, null, state);
  updateSendFunction(function(data) {
    if (typeof data === "string") {
      sendRaw(data);
    }
  });

  state.send = send;
  state.sendRaw = sendRaw;

  Object.defineProperty(state, 'terms', {
    get: function() { return paneManager.terms; },
    configurable: true
  });

  state.fitAllCallback = function() {
    paneManager.fitAll();
  };

  function _onResize() {
    if (state.layoutTree) {
      scheduleFit(paneManager);
      reposition(state, paneManager);
    } else {
      var c = document.getElementById("pane-0");
      if (c && paneManager.termArea) {
        var r = paneManager.termArea.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          c.style.left = "0";
          c.style.top = "0";
          c.style.width = r.width + "px";
          c.style.height = r.height + "px";
          if (paneManager.fits[0]) {
            try { paneManager.fits[0].fit(); } catch(e) {}
          }
        }
      }
    }
  }

  var resizeObserver = new ResizeObserver(_onResize);
  resizeObserver.observe(paneManager.termArea);

  window.addEventListener("resize", _onResize);

  paneManager.ensure(0);

  var initContainer = document.getElementById("pane-0");
  if (initContainer && paneManager.termArea) {
    var areaRect = paneManager.termArea.getBoundingClientRect();
    if (areaRect.width > 0 && areaRect.height > 0) {
      initContainer.style.left = "0";
      initContainer.style.top = "0";
      initContainer.style.width = areaRect.width + "px";
      initContainer.style.height = areaRect.height + "px";
      var ft = paneManager.fits[0];
      if (ft) { try { ft.fit(); } catch(e) {} }
    }
  }

  connect();
});
