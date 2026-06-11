import { createTerminal } from "./terminal.js";
import { send } from "./connection.js";
import { attachTerminalInputHandlers } from "./input.js";

var _term = null;
var _fit = null;
var _state = null;
var _lastSentCols = 0;
var _lastSentRows = 0;

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
      _sendOverlayDims();
    }
  });
}

function _sendOverlayDims() {
  if (!_term || !_state) return;
  _lastSentCols = _term.cols;
  _lastSentRows = _term.rows;
  send({ type: "overlay_resize", cols: _term.cols, rows: _term.rows });
}

function _getCellDims() {
  if (_term) {
    var dims = _term._core._renderService.dimensions;
    if (dims && dims.css && dims.css.cell && dims.css.cell.width && dims.css.cell.height) {
      return { w: dims.css.cell.width, h: dims.css.cell.height };
    }
  }
  if (_state && _state.terms) {
    for (var key in _state.terms) {
      var t = _state.terms[key];
      if (t) {
        var td = t._core._renderService.dimensions;
        if (td && td.css && td.css.cell && td.css.cell.width && td.css.cell.height) {
          return { w: td.css.cell.width, h: td.css.cell.height };
        }
      }
    }
  }
  var fontSize = 15;
  var lineHeight = 1.25;
  return { w: fontSize * 0.6, h: fontSize * lineHeight };
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

  var cd = _getCellDims();
  var charWidth = cd.w;
  var charHeight = cd.h;

  var borderPx = 4;
  var paddingPx = 8;
  var extra = borderPx + paddingPx;
  var targetCols = Math.min(80, Math.max(40, Math.floor((vw * 0.85 - extra) / charWidth)));
  var targetRows = Math.min(26, Math.max(12, Math.floor((vh * 0.85 - extra) / charHeight)));

  var actualWidth = Math.ceil(charWidth * targetCols + extra);
  var actualHeight = Math.ceil(charHeight * targetRows + extra);

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
  overlayPanel.style.background = _state.overlayBg;

  if (!_term) {
    var result = createTerminal(_state.currentTheme || {}, _state.termBg || "#1d2021", { padding: 4 });
    _term = result.term;
    _fit = result.fit;
    _term.open(overlayPanel);
    _term.loadAddon(_fit);

    attachTerminalInputHandlers(_term);
  }

  requestAnimationFrame(function() {
    if (_lastSentCols === 0 || _term.cols !== _lastSentCols || _term.rows !== _lastSentRows) {
      _sizeOverlayPanel();
      _sendOverlayDims();
    }
    _term.write(content);
    _term.focus();
  });
}

export function hide() {
  var overlayContainer = document.getElementById("overlay-container");
  overlayContainer.classList.add("hidden");
  _state.overlayVisible = false;
  _state.overlayKind = "";
  var overlayPanel = document.getElementById("overlay-panel");
  if (overlayPanel) overlayPanel.style.background = "";
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
