import { createTerminal } from "./terminal.js";
import { attachTerminalInputHandlers } from "./input.js";
import { scheduleFit } from "./layout.js";

export function createPaneManager(state) {
  var manager = {
    terms: {},
    fits: {},
    termArea: null,

    init: function() {
      this.termArea = document.getElementById("terminal-area");
    },

    ensure: function(idx) {
      if (this.terms[idx]) return this.terms[idx];
      var result = createTerminal(state.currentTheme || {}, state.termBg || "#1d2021");
      this.terms[idx] = result.term;
      this.fits[idx] = result.fit;

      var container = document.createElement("div");
      container.className = "pane-container";
      container.id = "pane-" + idx;
      container.innerHTML = '<div class="pane-border"></div><div class="pane-title"></div>';
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

    fitAll: function() {
      try {
        for (var idx in this.fits) {
          try { this.fits[idx].fit(); } catch(e) {}
        }
        var focusedTerm = this.terms[state.currentFocus];
        if (focusedTerm && (focusedTerm.cols !== state.lastCols || focusedTerm.rows !== state.lastRows)) {
          state.lastCols = focusedTerm.cols;
          state.lastRows = focusedTerm.rows;
          state.send({ type: "resize", cols: state.lastCols, rows: state.lastRows });
        }
      } catch(e) {}
    }
  };

  return manager;
}
