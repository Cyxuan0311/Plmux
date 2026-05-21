export function isMac() {
  if (navigator.userAgentData && navigator.userAgentData.platform) {
    return navigator.userAgentData.platform === "macOS";
  }
  return navigator.platform.toUpperCase().includes("MAC");
}

export function isHttps() {
  return document.location.protocol === "https:";
}

export function getWebSocketUrl() {
  var proto = isHttps() ? "wss:" : "ws:";
  return proto + "//" + location.host + "/ws";
}

export function hexToRgba(hex, alpha) {
  if (!hex || !hex.startsWith("#") || hex.length < 7) return "rgba(128,128,128," + alpha + ")";
  var r = parseInt(hex.substring(1, 3), 16);
  var g = parseInt(hex.substring(3, 5), 16);
  var b = parseInt(hex.substring(5, 7), 16);
  return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
}

export function darken(hex, amount) {
  if (!hex || !hex.startsWith("#") || hex.length < 7) return "#1d2021";
  var r = Math.max(0, parseInt(hex.substring(1, 3), 16) - amount);
  var g = Math.max(0, parseInt(hex.substring(3, 5), 16) - amount);
  var b = Math.max(0, parseInt(hex.substring(5, 7), 16) - amount);
  return "#" + r.toString(16).padStart(2, "0") + g.toString(16).padStart(2, "0") + b.toString(16).padStart(2, "0");
}

export function debounce(fn, ms) {
  var timer = null;
  return function() {
    var args = arguments;
    var self = this;
    if (timer) clearTimeout(timer);
    timer = setTimeout(function() { fn.apply(self, args); }, ms);
  };
}
