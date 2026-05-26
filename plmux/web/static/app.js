import { initInputHandlers, updateSendFunction } from "./input.js";
import { initConnection, connect, send, sendRaw } from "./connection.js";
import { createPaneManager } from "./panes.js";
import { initOverlay } from "./overlay.js";
import { handleMessage } from "./messages.js";
import { reposition, scheduleFit } from "./layout.js";

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
  terms: {},
  send: send,
  sendRaw: sendRaw,
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

  var resizeObserver = new ResizeObserver(function() {
    scheduleFit(paneManager);
    reposition(state, paneManager);
  });
  resizeObserver.observe(paneManager.termArea);

  window.addEventListener("resize", function() {
    scheduleFit(paneManager);
    reposition(state, paneManager);
  });

  paneManager.ensure(0);

  document.fonts.ready.then(function() {
    if (state.connected) {
      paneManager.fitAll();
    }
  });

  connect();
});
