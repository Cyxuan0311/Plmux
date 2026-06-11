import { createTerminal } from "./terminal.js";
import { attachTerminalInputHandlers } from "./input.js";
import { send } from "./connection.js";

var _borderStyle = {
  box_style: "square",
  show_title: true,
  title_position: "left",
  active_indicator: "color",
};

var _dragState = null;

export function applyPaneBorderStyle(style) {
  if (!style) return;
  Object.assign(_borderStyle, style);
  _refreshAllBorders();
}

function _refreshAllBorders() {
  var containers = document.querySelectorAll(".pane-container");
  containers.forEach(function(c) {
    var border = c.querySelector(".pane-border");
    var title = c.querySelector(".pane-title");
    var marker = c.querySelector(".pane-marker");
    if (border) {
      border.className = "pane-border box-" + (_borderStyle.box_style || "square");
      if (_borderStyle.active_indicator === "bold") {
        border.classList.add("indicator-bold");
      }
    }
    if (title) {
      title.className = "pane-title pos-" + (_borderStyle.title_position || "left");
      title.style.display = _borderStyle.show_title ? "" : "none";
    }
    if (marker) {
      marker.className = "pane-marker";
      if (_borderStyle.active_indicator === "marker") {
        marker.classList.add("indicator-marker");
      }
    }
    if (_borderStyle.show_title) {
      c.classList.add("has-title");
    } else {
      c.classList.remove("has-title");
    }
  });
}

function _findBorderAt(termArea, clientX, clientY) {
  var containers = termArea.querySelectorAll(".pane-container");
  var areaRect = termArea.getBoundingClientRect();
  var mx = clientX - areaRect.left;
  var my = clientY - areaRect.top;
  var tolerance = 5;
  var allRects = [];

  containers.forEach(function(c) {
    var idx = parseInt(c.id.replace("pane-", ""));
    var r = c.getBoundingClientRect();
    allRects.push({
      idx: idx,
      x: r.left - areaRect.left,
      y: r.top - areaRect.top,
      w: r.width,
      h: r.height,
    });
  });

  for (var i = 0; i < allRects.length; i++) {
    for (var j = i + 1; j < allRects.length; j++) {
      var a = allRects[i];
      var b = allRects[j];

      if (Math.abs((a.x + a.w) - b.x) < tolerance && a.y < b.y + b.h && b.y < a.y + a.h) {
        var borderX = a.x + a.w;
        if (Math.abs(mx - borderX) < tolerance) {
          return { dir: "row", idxA: a.idx, idxB: b.idx, pos: borderX };
        }
      }

      if (Math.abs((b.x + b.w) - a.x) < tolerance && a.y < b.y + b.h && b.y < a.y + a.h) {
        var borderX2 = b.x + b.w;
        if (Math.abs(mx - borderX2) < tolerance) {
          return { dir: "row", idxA: b.idx, idxB: a.idx, pos: borderX2 };
        }
      }

      if (Math.abs((a.y + a.h) - b.y) < tolerance && a.x < b.x + b.w && b.x < a.x + a.w) {
        var borderY = a.y + a.h;
        if (Math.abs(my - borderY) < tolerance) {
          return { dir: "col", idxA: a.idx, idxB: b.idx, pos: borderY };
        }
      }

      if (Math.abs((b.y + b.h) - a.y) < tolerance && a.x < b.x + b.w && b.x < a.x + a.w) {
        var borderY2 = b.y + b.h;
        if (Math.abs(my - borderY2) < tolerance) {
          return { dir: "col", idxA: b.idx, idxB: a.idx, pos: borderY2 };
        }
      }
    }
  }
  return null;
}

var _resizeOverlay = null;

function _createResizeOverlay(termArea) {
  var el = document.createElement("div");
  el.id = "resize-overlay";
  el.style.cssText = "position:absolute;z-index:20;pointer-events:none;display:none;transition:none;";
  termArea.appendChild(el);
  return el;
}

function _showResizeOverlay(dir, pos, areaRect) {
  if (!_resizeOverlay) return;
  var el = _resizeOverlay;
  el.style.display = "block";
  if (dir === "row") {
    el.style.left = (pos - 1) + "px";
    el.style.width = "3px";
    el.style.top = "0";
    el.style.height = "100%";
    el.style.backgroundColor = "var(--border-active)";
  } else {
    el.style.top = (pos - 1) + "px";
    el.style.height = "3px";
    el.style.left = "0";
    el.style.width = "100%";
    el.style.backgroundColor = "var(--border-active)";
  }
}

function _hideResizeOverlay() {
  if (_resizeOverlay) {
    _resizeOverlay.style.display = "none";
  }
}

function _installMouseHandlers(termArea, state, paneManager) {
  _resizeOverlay = _createResizeOverlay(termArea);

  // Capture phase: intercept mousedown near borders before xterm.js
  termArea.addEventListener("mousedown", function(e) {
    if (e.button !== 0) return;

    var borderInfo = _findBorderAt(termArea, e.clientX, e.clientY);
    if (borderInfo) {
      e.preventDefault();
      e.stopPropagation();
      var areaRect = termArea.getBoundingClientRect();
      _dragState = {
        dir: borderInfo.dir,
        idxA: borderInfo.idxA,
        idxB: borderInfo.idxB,
        startX: e.clientX,
        startY: e.clientY,
        areaRect: areaRect,
        pos: borderInfo.pos,
      };
      document.body.style.cursor = borderInfo.dir === "row" ? "col-resize" : "row-resize";
      termArea.style.cursor = borderInfo.dir === "row" ? "col-resize" : "row-resize";
      _showResizeOverlay(borderInfo.dir, borderInfo.pos, areaRect);
      return;
    }
  }, true);

  // Bubble phase: focus handling for normal clicks
  termArea.addEventListener("mousedown", function(e) {
    if (e.button !== 0) return;

    var container = e.target.closest(".pane-container");
    if (!container) return;

    var idx = parseInt(container.id.replace("pane-", ""));
    if (isNaN(idx)) return;

    if (idx !== state.currentFocus) {
      paneManager.focus(idx);
      send({ type: "focus", idx: idx });
    }
  });

  // Capture phase: update cursor on hover near borders
  termArea.addEventListener("mousemove", function(e) {
    if (_dragState) {
      e.preventDefault();
      return;
    }
    var borderInfo = _findBorderAt(termArea, e.clientX, e.clientY);
    if (borderInfo) {
      termArea.style.cursor = borderInfo.dir === "row" ? "col-resize" : "row-resize";
    } else {
      termArea.style.cursor = "";
    }
  }, true);

  termArea.addEventListener("mouseleave", function() {
    if (!_dragState) {
      termArea.style.cursor = "";
    }
  });

  document.addEventListener("mousemove", function(e) {
    if (!_dragState) return;
    e.preventDefault();
    var areaW = _dragState.areaRect.width;
    var areaH = _dragState.areaRect.height;
    if (_dragState.dir === "row" && areaW > 0) {
      var dx = e.clientX - _dragState.startX;
      _showResizeOverlay(_dragState.dir, _dragState.pos + dx, _dragState.areaRect);
    } else if (_dragState.dir === "col" && areaH > 0) {
      var dy = e.clientY - _dragState.startY;
      _showResizeOverlay(_dragState.dir, _dragState.pos + dy, _dragState.areaRect);
    }
  });

  document.addEventListener("mouseup", function(e) {
    if (!_dragState) return;
    e.preventDefault();

    var dx = e.clientX - _dragState.startX;
    var dy = e.clientY - _dragState.startY;
    var areaW = _dragState.areaRect.width;
    var areaH = _dragState.areaRect.height;

    send({ type: "focus", idx: _dragState.idxA });

    if (_dragState.dir === "row" && areaW > 0) {
      var ratio = dx / areaW;
      if (Math.abs(ratio) > 0.005) {
        var direction = ratio > 0 ? "right" : "left";
        var steps = Math.max(1, Math.round(Math.abs(ratio) * 20));
        for (var i = 0; i < steps; i++) {
          send({ type: "resize_pane", direction: direction });
        }
      }
    } else if (_dragState.dir === "col" && areaH > 0) {
      var ratio2 = dy / areaH;
      if (Math.abs(ratio2) > 0.005) {
        var direction2 = ratio2 > 0 ? "down" : "up";
        var steps2 = Math.max(1, Math.round(Math.abs(ratio2) * 20));
        for (var j = 0; j < steps2; j++) {
          send({ type: "resize_pane", direction: direction2 });
        }
      }
    }

    _hideResizeOverlay();
    _dragState = null;
    document.body.style.cursor = "";
    termArea.style.cursor = "";
  });
}

export function createPaneManager(state) {
  var manager = {
    terms: {},
    fits: {},
    termArea: null,
    _mouseInstalled: false,

    init: function() {
      this.termArea = document.getElementById("terminal-area");
    },

    _ensureMouseHandlers: function() {
      if (this._mouseInstalled) return;
      this._mouseInstalled = true;
      _installMouseHandlers(this.termArea, state, this);
    },

    ensure: function(idx) {
      if (this.terms[idx]) return this.terms[idx];
      this._ensureMouseHandlers();

      var result = createTerminal(state.currentTheme || {}, state.termBg || "#1d2021");
      this.terms[idx] = result.term;
      this.fits[idx] = result.fit;

      var container = document.createElement("div");
      container.className = "pane-container";
      container.id = "pane-" + idx;

      var border = document.createElement("div");
      border.className = "pane-border box-" + (_borderStyle.box_style || "square");
      if (_borderStyle.active_indicator === "bold") {
        border.classList.add("indicator-bold");
      }

      var title = document.createElement("div");
      title.className = "pane-title pos-" + (_borderStyle.title_position || "left");
      title.style.display = _borderStyle.show_title ? "" : "none";

      var marker = document.createElement("div");
      marker.className = "pane-marker";
      if (_borderStyle.active_indicator === "marker") {
        marker.classList.add("indicator-marker");
      }
      marker.textContent = "\u25B6";

      if (_borderStyle.show_title) {
        container.classList.add("has-title");
      }

      container.appendChild(border);
      container.appendChild(title);
      container.appendChild(marker);

      this.termArea.insertBefore(container, document.getElementById("overlay-container"));

      result.term.open(container);
      result.term.loadAddon(result.fit);

      attachTerminalInputHandlers(result.term);

      return result.term;
    },

    remove: function(idx) {
      if (this.terms[idx]) {
        this.terms[idx].dispose();
        delete this.terms[idx];
        delete this.fits[idx];
      }
      var el = document.getElementById("pane-" + idx);
      if (el) el.remove();
    },

    removeAll: function() {
      for (var idx in this.terms) {
        this.terms[idx].dispose();
      }
      this.terms = {};
      this.fits = {};
      var containers = this.termArea.querySelectorAll(".pane-container");
      containers.forEach(function(el) { el.remove(); });
    },

    focus: function(idx) {
      state.currentFocus = idx;
      var self = this;
      var containers = this.termArea.querySelectorAll(".pane-container");
      containers.forEach(function(c) {
        var cIdx = parseInt(c.id.replace("pane-", ""));
        if (cIdx === idx) {
          c.classList.add("focused");
          if (self.terms[idx]) {
            self.terms[idx].focus();
          }
        } else {
          c.classList.remove("focused");
        }
      });
    },

    setPaneTitle: function(idx, titleText) {
      var container = document.getElementById("pane-" + idx);
      if (!container) return;
      var titleEl = container.querySelector(".pane-title");
      if (titleEl) {
        titleEl.textContent = titleText || "";
      }
    },

    fitAll: function() {
      try {
        for (var idx in this.fits) {
          try { this.fits[idx].fit(); } catch(e) {}
        }
        var totalCols = 80, totalRows = 24;
        if (this.termArea) {
          var r = this.termArea.getBoundingClientRect();
          if (r.width > 0 && r.height > 0) {
            var cellW = 9.5, cellH = 19;
            for (var k in this.terms) {
              var t = this.terms[k];
              if (t) {
                var d = t._core._renderService.dimensions;
                if (d && d.css && d.css.cell && d.css.cell.width && d.css.cell.height) {
                  cellW = d.css.cell.width;
                  cellH = d.css.cell.height;
                  break;
                }
              }
            }
            totalCols = Math.max(40, Math.floor(r.width / cellW));
            totalRows = Math.max(12, Math.floor(r.height / cellH));
          }
        }
        if (totalCols !== state.lastCols || totalRows !== state.lastRows) {
          state.lastCols = totalCols;
          state.lastRows = totalRows;
          state.send({ type: "resize", cols: totalCols, rows: totalRows });
        }
      } catch(e) {}
    }
  };

  return manager;
}
