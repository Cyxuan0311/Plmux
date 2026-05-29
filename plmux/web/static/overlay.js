import { createTerminal } from "./terminal.js";
import { attachTerminalInputHandlers } from "./input.js";

var _term = null;
var _fit = null;
var _state = null;

export function initOverlay(state) {
  _state = state;

  var overlayContainer = document.getElementById("overlay-container");
  if (overlayContainer) {
    overlayContainer.addEventListener("mousedown", function(e) {
      if (e.target === overlayContainer) {
        e.preventDefault();
        hide();
      }
    });
  }

  window.addEventListener("resize", function() {
    if (_state && _state.overlayVisible && _term) {
      _sizeOverlayPanel();
    }
  });
}

function _sizeOverlayPanel() {
  if (!_term || !_fit) return;
  var overlayPanel = document.getElementById("overlay-panel");
  if (!overlayPanel) return;

  var vw = window.innerWidth;
  var vh = window.innerHeight;

  overlayPanel.style.width = Math.min(Math.floor(vw * 0.85), 1100) + "px";
  overlayPanel.style.height = Math.min(Math.floor(vh * 0.85), 600) + "px";

  try { _fit.fit(); } catch(e) {}

  var dims = _term._core._renderService.dimensions;
  if (!dims || !dims.css || !dims.css.cell) return;
  var charWidth = dims.css.cell.width;
  var charHeight = dims.css.cell.height;
  if (!charWidth || !charHeight) return;

  var targetCols = Math.min(80, Math.floor((vw * 0.85 - 24) / charWidth));
  var targetRows = Math.min(26, Math.floor((vh * 0.85 - 24) / charHeight));
  targetCols = Math.max(targetCols, 40);
  targetRows = Math.max(targetRows, 12);

  var actualWidth = Math.ceil(charWidth * targetCols) + 24;
  var actualHeight = Math.ceil(charHeight * targetRows) + 24;

  actualWidth = Math.min(actualWidth, Math.floor(vw * 0.92));
  actualHeight = Math.min(actualHeight, Math.floor(vh * 0.92));

  overlayPanel.style.width = actualWidth + "px";
  overlayPanel.style.height = actualHeight + "px";

  try { _fit.fit(); } catch(e) {}
}

export function show(kind, content) {
  var overlayContainer = document.getElementById("overlay-container");
  var overlayPanel = document.getElementById("overlay-panel");

  if (!content) {
    hide();
    return;
  }

  _state.overlayVisible = true;
  _state.overlayKind = kind;
  overlayContainer.classList.remove("hidden");

  if (!_term) {
    var result = createTerminal(_state.currentTheme || {}, _state.termBg || "#1d2021");
    _term = result.term;
    _fit = result.fit;
    _term.open(overlayPanel);
    _term.loadAddon(_fit);

    attachTerminalInputHandlers(_term);
  }

  requestAnimationFrame(function() {
    _sizeOverlayPanel();

    requestAnimationFrame(function() {
      _term.reset();
      _term.write(content);
      _term.focus();
    });
  });
}

export function hide() {
  var overlayContainer = document.getElementById("overlay-container");
  overlayContainer.classList.add("hidden");
  _state.overlayVisible = false;
  _state.overlayKind = "";
  if (_term) {
    _term.clear();
  }
  if (_state.terms && _state.currentFocus in _state.terms) {
    _state.terms[_state.currentFocus].focus();
  }
}

export function getTerm() {
  return _term;
}
