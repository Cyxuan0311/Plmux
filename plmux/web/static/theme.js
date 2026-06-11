import { hexToRgba, darken } from "./utils.js";

export function buildXtermTheme(t, bg) {
  var m = t.mode || {};
  var s = t.status || {};
  var c = t.cmdline || {};
  var accentBg = m.normal_bg || "#a6e22e";
  var paneBg = s.pane_bg || "#75715e";
  return {
    background: bg || "#1d2021",
    foreground: c.body_fg || "#ebdbb2",
    cursor: c.body_fg || "#ebdbb2",
    cursorAccent: bg || "#1d2021",
    selectionBackground: hexToRgba(accentBg, 0.3),
    selectionForeground: "#ffffff",
    black: darken(paneBg, 60),
    red: "#cc241d",
    green: "#98971a",
    yellow: "#d79921",
    blue: "#458588",
    magenta: "#b16286",
    cyan: "#689d6a",
    white: "#a89984",
    brightBlack: "#928374",
    brightRed: accentBg,
    brightGreen: accentBg,
    brightYellow: m.prefix_bg || "#fabd2f",
    brightBlue: s.win_bg || "#66d9ef",
    brightMagenta: "#d3869b",
    brightCyan: "#8ec07c",
    brightWhite: c.body_fg || "#ebdbb2",
  };
}

export function applyTheme(t, state, paneManager, overlayManager) {
  if (!t) return;
  state.currentTheme = t;
  var r = document.documentElement.style;
  var m = t.mode || {};
  var s = t.status || {};
  var p = t.pane || {};
  var c = t.cmdline || {};

  r.setProperty("--mode-normal-fg", m.normal_fg || "#000");
  r.setProperty("--mode-normal-bg", m.normal_bg || "#a6e22e");
  r.setProperty("--mode-prefix-fg", m.prefix_fg || "#000");
  r.setProperty("--mode-prefix-bg", m.prefix_bg || "#fabd2f");
  r.setProperty("--mode-cmdline-fg", m.cmdline_fg || "#000");
  r.setProperty("--mode-cmdline-bg", m.cmdline_bg || "#83a598");
  r.setProperty("--win-fg", s.win_fg || "#fff");
  r.setProperty("--win-bg", s.win_bg || "#66d9ef");
  r.setProperty("--pane-fg", s.pane_fg || "#bdae93");
  r.setProperty("--pane-bg", s.pane_bg || "#75715e");
  r.setProperty("--clock-fg", s.clock_fg || "#000");
  r.setProperty("--clock-bg", s.clock_bg || "#85c751");
  r.setProperty("--host-fg", s.host_fg || "#000");
  r.setProperty("--host-bg", s.host_bg || "#85c751");
  r.setProperty("--cmd-fg", s.cmd_fg || "#fff");
  r.setProperty("--cmd-bg", s.cmd_bg || "#75715e");
  r.setProperty("--border-active", p.active_border || "#85c751");
  r.setProperty("--border-inactive", p.inactive_border || "#505050");
  r.setProperty("--cl-indicator-fg", c.indicator_fg || "#fabd2f");
  r.setProperty("--cl-indicator-bg", c.indicator_bg || "#2d2d2d");
  r.setProperty("--cl-body-fg", c.body_fg || "#83a598");
  r.setProperty("--cl-body-bg", c.body_bg || "#2d2d2d");
  r.setProperty("--cl-bg", c.background || "#2d2d2d");

  var termBg = "#1d2021";
  if (c.background) {
    var bgParts = c.background.replace("#", "");
    if (bgParts.length === 6) {
      var br = parseInt(bgParts.substring(0, 2), 16);
      var darker = Math.max(0, br - 30).toString(16).padStart(2, "0");
      termBg = "#" + darker + bgParts.substring(2);
    }
  }
  r.setProperty("--term-bg", termBg);
  state.termBg = termBg;
  state.overlayBg = (t.status && t.status.background) || termBg;
  document.body.style.background = termBg;

  var xtheme = buildXtermTheme(t, termBg);
  for (var idx in paneManager.terms) {
    if (paneManager.terms[idx]) paneManager.terms[idx].options.theme = xtheme;
  }
  if (overlayManager && overlayManager.getTerm) {
    var overlayTerm = overlayManager.getTerm();
    if (overlayTerm) overlayTerm.options.theme = xtheme;
  }

  document.title = "plmux web \u2014 " + (t.name || "default");
}
