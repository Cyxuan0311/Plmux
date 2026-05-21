import { encodeKittyKey, hasModifiersToHandle, encodeSpecialKey, isSpecialKey, isFunctionKey, encodeFunctionKey, encodeCtrlKey } from "./keyboard.js";
import { isMac } from "./utils.js";

var _sendFn = null;
var _stateRef = null;
var _paneManager = null;
var _overlayTerm = null;

export function initInputHandlers(paneManager, overlayTerm, state) {
  _stateRef = state;
  _paneManager = paneManager;
  _overlayTerm = overlayTerm;
  installImeBypass();
  installPasteHandler();
}

export function attachTerminalInputHandlers(term) {
  term.attachCustomKeyEventHandler(function(ev) {
    if (ev.type !== "keydown") return true;
    if (!_sendFn || !_stateRef || !_stateRef.connected) return true;

    if (ev.key === "V" && ev.ctrlKey && ev.shiftKey) {
      return true;
    }
    if (isMac() && ev.key === "v" && ev.metaKey) {
      return true;
    }

    if (hasModifiersToHandle(ev)) {
      ev.preventDefault();
      _send(encodeKittyKey(ev));
      return false;
    }

    if (ev.ctrlKey && !ev.altKey && !ev.metaKey) {
      var key = ev.key.toLowerCase();
      var encoded = encodeCtrlKey(key);
      if (encoded !== null) {
        ev.preventDefault();
        _send(encoded);
        return false;
      }
    }

    if (ev.altKey && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      if (ev.key.length === 1) {
        _send("\x1b" + ev.key.toLowerCase());
      } else if (isSpecialKey(ev.key)) {
        var seq = encodeSpecialKey(ev.key);
        if (seq) {
          var modSeq = seq.replace(/\x1b\[/, "\x1b[1;3");
          _send(modSeq);
        }
      } else {
        _send("\x1b" + ev.key.toLowerCase());
      }
      return false;
    }

    if (ev.ctrlKey && ev.altKey) {
      ev.preventDefault();
      var k = ev.key.toLowerCase();
      if (k.length === 1 && k >= "a" && k <= "z") {
        _send("\x1b" + String.fromCharCode(k.charCodeAt(0) - 32));
      }
      return false;
    }

    if (ev.key === "Escape") {
      ev.preventDefault();
      _send("\x1b");
      return false;
    }

    if (isSpecialKey(ev.key)) {
      ev.preventDefault();
      var specialSeq = encodeSpecialKey(ev.key);
      if (specialSeq) _send(specialSeq);
      return false;
    }

    if (isFunctionKey(ev.key)) {
      ev.preventDefault();
      var fSeq = encodeFunctionKey(ev.key);
      if (fSeq) _send(fSeq);
      return false;
    }

    if (ev.key === "ArrowLeft" && ev.altKey) {
      ev.preventDefault();
      _send("\x1b[1;3D");
      return false;
    }
    if (ev.key === "ArrowRight" && ev.altKey) {
      ev.preventDefault();
      _send("\x1b[1;3C");
      return false;
    }
    if (ev.key === "ArrowUp" && ev.altKey) {
      ev.preventDefault();
      _send("\x1b[1;3A");
      return false;
    }
    if (ev.key === "ArrowDown" && ev.altKey) {
      ev.preventDefault();
      _send("\x1b[1;3B");
      return false;
    }

    return true;
  });

  term.onData(function(data) {
    if (!_sendFn || !_stateRef || !_stateRef.connected) return;
    _send(data);
  });

  term.onBinary(function(data) {
    if (!_sendFn || !_stateRef || !_stateRef.connected) return;
    var buffer = new Uint8Array(data.length);
    for (var i = 0; i < data.length; ++i) {
      buffer[i] = data.charCodeAt(i) & 255;
    }
    _send(buffer);
  });
}

export function updateSendFunction(fn) {
  _sendFn = fn;
  if (window.__plmuxImeBypass) {
    window.__plmuxImeBypass.sendFn = fn;
  }
}

function _send(data) {
  if (_sendFn) _sendFn(data);
}

function installImeBypass() {
  if (typeof window.__plmuxImeBypass !== "undefined") {
    window.__plmuxImeBypass.installed = true;
    return;
  }

  window.__plmuxImeBypass = {
    installed: true,
    sendFn: _send,
    lastKeyWasProcess: false,
  };

  var state = window.__plmuxImeBypass;

  document.addEventListener("keydown", function(ev) {
    state.lastKeyWasProcess = ev.key === "Process";
  }, true);

  var attachToTextarea = function() {
    var ta = document.querySelector(".xterm-helper-textarea");
    if (!ta) {
      setTimeout(attachToTextarea, 100);
      return;
    }
    ta.addEventListener("input", function(ev) {
      if (
        state.lastKeyWasProcess &&
        ev.inputType === "insertText" &&
        !ev.isComposing &&
        ev.data
      ) {
        _send(ev.data);
        ev.target.value = "";
        state.lastKeyWasProcess = false;
      }
    }, true);
  };
  attachToTextarea();
}

function installPasteHandler() {
  document.addEventListener("paste", function(e) {
    if (!_sendFn || !_stateRef || !_stateRef.connected) return;
    var inTerm = false;
    var el = e.target;
    while (el) {
      if (el.classList && (
        el.classList.contains("xterm") ||
        el.classList.contains("pane-container") ||
        el.id === "overlay-panel" ||
        el.id === "terminal-area"
      )) {
        inTerm = true;
        break;
      }
      el = el.parentElement;
    }
    if (!inTerm) return;
    e.preventDefault();
    var text = e.clipboardData.getData("text");
    if (text) _send(text);
  });
}
