import { createTerminal } from "./terminal.js";
import { attachTerminalInputHandlers } from "./input.js";

var _term = null;
var _fit = null;
var _state = null;

export function initOverlay(state) {
  _state = state;
}

export function show(kind, content) {
  var overlayContainer = document.getElementById("overlay-container");
  var overlayPanel = document.getElementById("overlay-panel");

  if (!content) {
    hide();
    return;
  }

  if (!_term) {
    var result = createTerminal(_state.currentTheme || {}, _state.termBg || "#1d2021");
    _term = result.term;
    _fit = result.fit;
    _term.open(overlayPanel);
    _term.loadAddon(_fit);

    attachTerminalInputHandlers(_term);
  }

  _state.overlayVisible = true;
  _state.overlayKind = kind;
  overlayContainer.classList.remove("hidden");
  _term.clear();
  _term.write(content);

  try { _fit.fit(); } catch(e) {}
  _term.focus();
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
