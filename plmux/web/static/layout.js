import { applyStatusBarStyle } from "./statusbar.js";
import { applyPaneBorderStyle } from "./panes.js";

export function computeRects(node, x, y, w, h) {
  if (node.leaf !== undefined) {
    return [{ idx: node.leaf, x: x, y: y, w: w, h: h }];
  }
  var dir = node.dir;
  var ratio = node.ratio;
  var rects = [];
  if (dir === "row") {
    var leftW = Math.floor(w * ratio);
    var rightW = w - leftW;
    rects = rects.concat(computeRects(node.a, x, y, leftW, h));
    rects = rects.concat(computeRects(node.b, x + leftW, y, rightW, h));
  } else {
    var topH = Math.floor(h * ratio);
    var bottomH = h - topH;
    rects = rects.concat(computeRects(node.a, x, y, w, topH));
    rects = rects.concat(computeRects(node.b, x, y + topH, w, bottomH));
  }
  return rects;
}

export function applyLayout(msg, state, paneManager) {
  state.layoutTree = msg.tree;
  state.layoutPanes = msg.panes || [];
  state.currentFocus = msg.focus !== undefined ? msg.focus : 0;

  if (msg.status_bar_style) {
    applyStatusBarStyle(msg.status_bar_style);
  }
  if (msg.pane_border_style) {
    applyPaneBorderStyle(msg.pane_border_style);
  }

  var areaRect = paneManager.termArea.getBoundingClientRect();
  var areaW = areaRect.width;
  var areaH = areaRect.height;

  var rects = computeRects(state.layoutTree, 0, 0, areaW, areaH);

  var activeIndices = {};
  rects.forEach(function(r) { activeIndices[r.idx] = true; });

  for (var idx in paneManager.terms) {
    if (!activeIndices[idx]) {
      paneManager.remove(parseInt(idx));
    }
  }

  var paneInfo = {};
  state.layoutPanes.forEach(function(p) { paneInfo[p.idx] = p; });

  rects.forEach(function(r) {
    paneManager.ensure(r.idx);
    var container = document.getElementById("pane-" + r.idx);
    if (!container) return;

    container.style.left = r.x + "px";
    container.style.top = r.y + "px";
    container.style.width = r.w + "px";
    container.style.height = r.h + "px";

    var info = paneInfo[r.idx];
    if (r.idx === state.currentFocus) {
      container.classList.add("focused");
    } else {
      container.classList.remove("focused");
    }

    var titleEl = container.querySelector(".pane-title");
    if (titleEl && info) {
      titleEl.textContent = info.title || ("P" + (r.idx + 1));
    }

    try {
      if (paneManager.fits[r.idx]) paneManager.fits[r.idx].fit();
    } catch(e) {}
  });

  rects.forEach(function(r) {
    var term = paneManager.terms[r.idx];
    var container = document.getElementById("pane-" + r.idx);
    if (!term || !container) return;
    try {
      var cellWidth = term._core._renderService.dimensions.css.cell.width;
      if (cellWidth > 0) {
        var actualWidth = Math.ceil(term.cols * cellWidth);
        var borderW = container.querySelector(".pane-border");
        var borderX = 0;
        if (borderW) {
          var cs = getComputedStyle(borderW);
          borderX = parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
        }
        container.style.width = (actualWidth + borderX) + "px";
      }
    } catch(e) {}
  });

  scheduleFit(paneManager);
}

export function reposition(state, paneManager) {
  if (!state.layoutTree) return;
  var areaRect = paneManager.termArea.getBoundingClientRect();
  var rects = computeRects(state.layoutTree, 0, 0, areaRect.width, areaRect.height);
  rects.forEach(function(r) {
    var container = document.getElementById("pane-" + r.idx);
    if (container) {
      container.style.left = r.x + "px";
      container.style.top = r.y + "px";
      container.style.width = r.w + "px";
      container.style.height = r.h + "px";
    }
  });
  try {
    paneManager.fitAll();
  } catch(e) {}
  rects.forEach(function(r) {
    var term = paneManager.terms[r.idx];
    var container = document.getElementById("pane-" + r.idx);
    if (!term || !container) return;
    try {
      var cellWidth = term._core._renderService.dimensions.css.cell.width;
      if (cellWidth > 0) {
        var actualWidth = Math.ceil(term.cols * cellWidth);
        var borderW = container.querySelector(".pane-border");
        var borderX = 0;
        if (borderW) {
          var cs = getComputedStyle(borderW);
          borderX = parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
        }
        container.style.width = (actualWidth + borderX) + "px";
      }
    } catch(e) {}
  });
}

var _fitTimer = null;

function scheduleFit(paneManager) {
  if (_fitTimer) clearTimeout(_fitTimer);
  _fitTimer = setTimeout(function() {
    paneManager.fitAll();
  }, 50);
}

export { scheduleFit };
