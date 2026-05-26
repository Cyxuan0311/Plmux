import { hexToRgba, darken } from "./utils.js";

export function createTerminal(theme, termBg) {
  var xtheme = buildXtermTheme(theme, termBg);
  var t = new Terminal({
    theme: xtheme,
    fontFamily: "'JetBrainsMono NFM', 'Symbols Nerd Font', monospace",
    fontSize: 15,
    lineHeight: 1.25,
    cursorBlink: true,
    cursorStyle: "block",
    scrollback: 5000,
    allowProposedApi: true,
    convertEol: false,
  });
  var fit = new FitAddon.FitAddon();
  var links = new WebLinksAddon.WebLinksAddon();
  t.loadAddon(fit);
  t.loadAddon(links);
  return { term: t, fit: fit };
}

function buildXtermTheme(t, bg) {
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
