import { getWebSocketUrl } from "./utils.js";

var _ws = null;
var _state = null;
var _onMessage = null;
var _reconnectTimer = null;
var _reconnectAttempts = 0;
var _snapshotIgnoreUntil = 0;
var MAX_RECONNECT_DELAY = 16000;

export function setSnapshotIgnoreUntil(ts) {
  _snapshotIgnoreUntil = ts;
}

export function initConnection(state, onMessage) {
  _state = state;
  _onMessage = onMessage;
}

export function connect() {
  var url = getWebSocketUrl();
  var ws = new WebSocket(url);
  _ws = ws;
  _state.ws = ws;

  var connStatus = document.getElementById("conn-status");

  function _setConnected(val) {
    _state.connected = val;
    document.body.classList.toggle("ws-connected", val);
  }

  function _getTermSize() {
    if (_state.fitAllCallback) {
      _state.fitAllCallback();
    }
    var cols = 80, rows = 24;
    var area = document.getElementById("terminal-area");
    if (area) {
      var r = area.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        var cellW = 9.5, cellH = 19;
        if (_state && _state.terms) {
          for (var k in _state.terms) {
            var t = _state.terms[k];
            if (t) {
              var d = t._core._renderService.dimensions;
              if (d && d.css && d.css.cell && d.css.cell.width && d.css.cell.height) {
                cellW = d.css.cell.width;
                cellH = d.css.cell.height;
                break;
              }
            }
          }
        }
        cols = Math.max(40, Math.floor(r.width / cellW));
        rows = Math.max(12, Math.floor(r.height / cellH));
      }
    }
    return { cols: cols, rows: rows };
  }

  ws.onopen = function() {
    _reconnectAttempts = 0;
    connStatus.textContent = "Connected";
    document.getElementById("connect-overlay").classList.add("hidden");
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer);
      _reconnectTimer = null;
    }
    setTimeout(function() { _setConnected(true); }, 250);
    var size = _getTermSize();
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    var cellW = 9.5;
    var cellH = 19;
    if (_state && _state.terms) {
      for (var k in _state.terms) {
        var t = _state.terms[k];
        if (t) {
          var d = t._core._renderService.dimensions;
          if (d && d.css && d.css.cell && d.css.cell.width && d.css.cell.height) {
            cellW = d.css.cell.width;
            cellH = d.css.cell.height;
            break;
          }
        }
      }
    }
    var ocols = Math.min(80, Math.max(40, Math.floor((vw * 0.85 - 12) / cellW)));
    var orows = Math.min(26, Math.max(12, Math.floor((vh * 0.85 - 12) / cellH)));
    send({ type: "ready", cols: size.cols, rows: size.rows, overlay_cols: ocols, overlay_rows: orows });
  };

  ws.onclose = function() {
    _setConnected(false);
    connStatus.textContent = "Disconnected";
    document.getElementById("connect-overlay").classList.remove("hidden");
    scheduleReconnect();
  };

  ws.onerror = function() {
    _setConnected(false);
    connStatus.textContent = "Connection error";
  };

  ws.onmessage = function(ev) {
    try {
      if (typeof ev.data === "string") {
        var msg = JSON.parse(ev.data);
        if (_onMessage) _onMessage(msg);
      } else if (ev.data instanceof ArrayBuffer) {
        var bytes = new Uint8Array(ev.data);
        var text = new TextDecoder().decode(bytes);
        if (Date.now() < _snapshotIgnoreUntil) return;
        if (_state.currentFocus in _state.terms) {
          _state.terms[_state.currentFocus].write(text);
        }
      }
    } catch(e) { console.error("msg error", e); }
  };
}

export function send(obj) {
  if (_ws && _ws.readyState === 1) {
    _ws.send(JSON.stringify(obj));
  }
}

export function sendRaw(data) {
  if (_ws && _ws.readyState === 1) {
    _ws.send(data);
  }
}

function _recalcContainerSize() {
  var area = document.getElementById("terminal-area");
  if (!area) return;
  var areaRect = area.getBoundingClientRect();
  if (areaRect.width <= 0 || areaRect.height <= 0) return;
  var containers = area.querySelectorAll(".pane-container");
  containers.forEach(function(c) {
    if (!c.style.left && !c.style.top) {
      c.style.left = "0";
      c.style.top = "0";
      c.style.width = areaRect.width + "px";
      c.style.height = areaRect.height + "px";
    }
  });
}

function scheduleReconnect() {
  if (_reconnectTimer) return;
  var attempt = _reconnectAttempts + 1;
  var delay = Math.min(1000 * Math.pow(2, _reconnectAttempts), MAX_RECONNECT_DELAY);
  _reconnectAttempts++;
  var connStatus = document.getElementById("conn-status");
  connStatus.textContent = "Reconnecting in " + (delay / 1000) + "s (attempt " + attempt + ")";
  _reconnectTimer = setTimeout(function() {
    _reconnectTimer = null;
    connStatus.textContent = "Connecting...";
    _recalcContainerSize();
    connect();
  }, delay);
}

export function getReconnectDelay() {
  var delays = [1, 2, 4, 8, 16];
  return delays[Math.min(_reconnectAttempts - 1, delays.length - 1)];
}
