import { getWebSocketUrl } from "./utils.js";

var _ws = null;
var _state = null;
var _onMessage = null;
var _reconnectTimer = null;
var _reconnectAttempts = 0;
var MAX_RECONNECT_DELAY = 16000;

export function initConnection(state, onMessage) {
  _state = state;
  _onMessage = onMessage;
}

export function connect() {
  var url = getWebSocketUrl();
  var ws = new WebSocket(url);
  _ws = ws;
  _state.ws = ws;

  ws.onopen = function() {
    _state.connected = true;
    _reconnectAttempts = 0;
    document.getElementById("connect-overlay").classList.add("hidden");
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer);
      _reconnectTimer = null;
    }
    var cols = 80, rows = 24;
    if (_state.currentFocus in _state.terms) {
      var t = _state.terms[_state.currentFocus];
      if (t) { cols = t.cols; rows = t.rows; }
    }
    send({ type: "ready", cols: cols, rows: rows });
  };

  ws.onclose = function() {
    _state.connected = false;
    document.getElementById("connect-overlay").classList.remove("hidden");
    document.getElementById("conn-status").textContent = "Disconnected. Reconnecting...";
    scheduleReconnect();
  };

  ws.onerror = function() {
    _state.connected = false;
  };

  ws.onmessage = function(ev) {
    try {
      if (typeof ev.data === "string") {
        var msg = JSON.parse(ev.data);
        if (_onMessage) _onMessage(msg);
      } else if (ev.data instanceof ArrayBuffer) {
        var bytes = new Uint8Array(ev.data);
        var text = new TextDecoder().decode(bytes);
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

function scheduleReconnect() {
  if (_reconnectTimer) return;
  var delay = Math.min(1000 * Math.pow(2, _reconnectAttempts), MAX_RECONNECT_DELAY);
  _reconnectAttempts++;
  _reconnectTimer = setTimeout(function() {
    _reconnectTimer = null;
    connect();
  }, delay);
}

export function getReconnectDelay() {
  var delays = [1, 2, 4, 8, 16];
  return delays[Math.min(_reconnectAttempts - 1, delays.length - 1)];
}
