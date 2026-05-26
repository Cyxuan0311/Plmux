var MODE_CLASS_MAP = {
  "NORMAL": "mode-normal",
  "PREFIX": "mode-prefix",
  "CMDLINE": "mode-cmdline",
  "COPY": "mode-copy",
  "HELP": "mode-help",
  "THEME_LIST": "mode-theme_list",
  "SESSION_LIST": "mode-session_list",
  "PLUGIN_LIST": "mode-plugin_list",
  "LAYOUT_LIST": "mode-layout_list",
  "STATUSBAR_STYLE": "mode-statusbar_style",
  "PANE_BORDER_STYLE": "mode-pane_border_style",
  "ESC_WAIT": "mode-esc_wait",
};

var SEPARATOR_CHARS = {
  "powerline": ["\uE0B0", "\uE0B2"],
  "powerline_round": ["\uE0B4", "\uE0B6"],
  "powerline_diamond": ["\uE0B8", "\uE0BA"],
  "ascii": ["/", "\\"],
  "unicode": ["\u2503", "\u2503"],
  "unicode_thin": ["\u2502", "\u2502"],
  "dots": ["\u00B7", "\u00B7"],
  "pipes": ["|", "|"],
  "none": [" ", " "],
};

var MODE_DISPLAY = {
  "full": { "NORMAL": "NORMAL", "PREFIX": "PREFIX", "COPY": "COPY", "INSERT": "INSERT" },
  "short": { "NORMAL": "N", "PREFIX": "P", "COPY": "C", "INSERT": "I" },
  "minimal": { "NORMAL": "", "PREFIX": ">", "COPY": "*", "INSERT": "+" },
};

var _sbStyle = {
  separator: "powerline",
  mode_indicator: "full",
  show_command: true,
  show_session: true,
  show_window_index: true,
  show_pane_index: true,
  right_sections: "clock_host",
  spacing: "compact",
};

var _colorVars = {
  mode_bg: "var(--mode-normal-bg)",
  mode_fg: "var(--mode-normal-fg)",
  win_bg: "var(--win-bg)",
  win_fg: "var(--win-fg)",
  pane_bg: "var(--pane-bg)",
  pane_fg: "var(--pane-fg)",
  cmd_bg: "var(--cmd-bg)",
  cmd_fg: "var(--cmd-fg)",
  clock_bg: "var(--clock-bg)",
  clock_fg: "var(--clock-fg)",
  host_bg: "var(--host-bg)",
  host_fg: "var(--host-fg)",
};

export function applyStatusBarStyle(style) {
  if (!style) return;
  Object.assign(_sbStyle, style);
}

function _sepPair() {
  return SEPARATOR_CHARS[_sbStyle.separator] || SEPARATOR_CHARS["powerline"];
}

function _pad() {
  return _sbStyle.spacing === "spaced" ? "  " : " ";
}

function _modeClass(mode) {
  return MODE_CLASS_MAP[mode] || "mode-normal";
}

function _modeDisplay(mode) {
  var indicator = _sbStyle.mode_indicator || "full";
  var map = MODE_DISPLAY[indicator] || MODE_DISPLAY["full"];
  return map[mode] !== undefined ? map[mode] : mode;
}

function _modeBgVar(mode) {
  var map = {
    "NORMAL": "--mode-normal-bg",
    "PREFIX": "--mode-prefix-bg",
    "CMDLINE": "--mode-cmdline-bg",
    "COPY": "--border-active",
    "HELP": "--border-active",
    "THEME_LIST": "--border-active",
    "SESSION_LIST": "--border-active",
    "PLUGIN_LIST": "--border-active",
    "LAYOUT_LIST": "--border-active",
    "STATUSBAR_STYLE": "--border-active",
    "PANE_BORDER_STYLE": "--border-active",
    "ESC_WAIT": "--mode-normal-bg",
  };
  return map[mode] || "--mode-normal-bg";
}

function _makeSeg(text, cls, bgVar) {
  var pad = _pad();
  var spacedCls = _sbStyle.spacing === "spaced" ? " spaced" : "";
  return '<span class="sb-seg ' + cls + spacedCls + '" style="background:var(' + bgVar + ')">' + pad + text + pad + '</span>';
}

function _makeSepLeft(char, fromBgVar, toBgVar) {
  if (!char || char === " ") return "";
  if (_sbStyle.separator.startsWith("powerline")) {
    return '<span class="sb-sep" style="color:var(' + fromBgVar + ');background:var(' + toBgVar + ')">' + char + '</span>';
  }
  return '<span class="sb-sep" style="color:var(' + fromBgVar + ')">' + char + '</span>';
}

function _makeSepRight(char, fromBgVar, toBgVar) {
  if (!char || char === " ") return "";
  if (_sbStyle.separator.startsWith("powerline")) {
    return '<span class="sb-sep" style="color:var(' + fromBgVar + ');background:var(' + toBgVar + ')">' + char + '</span>';
  }
  return '<span class="sb-sep" style="color:var(' + fromBgVar + ')">' + char + '</span>';
}

export function updateMode(mode) {
  state_currentMode = mode;
}

var state_currentMode = "NORMAL";

export function updateStatus(m, state) {
  var modeText = (m.mode || "NORMAL").toUpperCase();
  state.currentMode = modeText;
  state_currentMode = modeText;

  var sep = _sepPair();
  var sepL = sep[0];
  var sepR = sep[1];

  var modeBgVar = _modeBgVar(modeText);
  var modeClass = _modeClass(modeText);

  var leftHtml = "";

  var modeDisp = _modeDisplay(modeText);
  if (modeDisp) {
    leftHtml += _makeSeg(modeDisp, modeClass, modeBgVar);
    leftHtml += _makeSepLeft(sepL, modeBgVar, "--win-bg");
  }

  if (_sbStyle.show_session && m.session) {
    leftHtml += _makeSeg(m.session, "win", "--win-bg");
    leftHtml += _makeSepLeft(sepL, "--win-bg", "--pane-bg");
  }

  if (_sbStyle.show_window_index && m.win) {
    leftHtml += _makeSeg(m.win, "win", "--win-bg");
    leftHtml += _makeSepLeft(sepL, "--win-bg", "--pane-bg");
  } else if (m.win_name) {
    leftHtml += _makeSeg(m.win_name, "win", "--win-bg");
    leftHtml += _makeSepLeft(sepL, "--win-bg", "--pane-bg");
  }

  if (_sbStyle.show_pane_index && m.pane) {
    var nextBg = (m.cmd && _sbStyle.show_command) ? "--cmd-bg" : "--pane-bg";
    leftHtml += _makeSeg(m.pane, "pane", "--pane-bg");
    if (m.cmd && _sbStyle.show_command) {
      leftHtml += _makeSepLeft(sepL, "--pane-bg", "--cmd-bg");
    } else {
      leftHtml += _makeSepLeft(sepL, "--pane-bg", nextBg);
    }
  }

  if (m.cmd && _sbStyle.show_command) {
    leftHtml += _makeSeg(m.cmd, "cmd", "--cmd-bg");
    leftHtml += _makeSepLeft(sepL, "--cmd-bg", "--pane-bg");
  } else {
    var lastBg = _sbStyle.show_pane_index ? "--pane-bg" : "--win-bg";
    if (_sbStyle.separator.startsWith("powerline")) {
      leftHtml += '<span class="sb-sep" style="color:var(' + lastBg + ');background:var(--pane-bg)">' + sepL + '</span>';
    } else if (sepL.trim()) {
      leftHtml += '<span class="sb-sep" style="color:var(' + lastBg + ')">' + sepL + '</span>';
    }
  }

  if (m.sync) {
    leftHtml += _makeSeg("SYNC", "sync", "--bat-ok-bg");
    leftHtml += _makeSepLeft(sepL, "--bat-ok-bg", "--pane-bg");
  }

  if (m.dead) {
    leftHtml += _makeSeg("DEAD:" + m.dead, "dead", "--bat-low-bg");
    leftHtml += _makeSepLeft(sepL, "--bat-low-bg", "--pane-bg");
  }

  var rightItems = m.right_items || [];
  for (var i = 0; i < rightItems.length; i++) {
    var item = rightItems[i];
    var styleClass = "bat-" + (item.style || "ok");
    var bgVar = "--bat-" + (item.style || "ok") + "-bg";
    leftHtml += _makeSeg(item.text, styleClass, bgVar);
    leftHtml += _makeSepLeft(sepL, bgVar, "--pane-bg");
  }

  document.getElementById("sb-left").innerHTML = leftHtml;

  var rightHtml = "";

  if (_sbStyle.right_sections === "clock_host" || _sbStyle.right_sections === "clock") {
    rightHtml += _makeSeg(m.clock || "--:--:--", "clock", "--clock-bg");
  }

  if (_sbStyle.right_sections === "clock_host") {
    rightHtml += _makeSepRight(sepR, "--host-bg", "--clock-bg");
  } else if (_sbStyle.right_sections === "host") {
    rightHtml += _makeSepRight(sepR, "--host-bg", "--pane-bg");
  }

  if (_sbStyle.right_sections === "clock_host" || _sbStyle.right_sections === "host") {
    rightHtml += _makeSeg(m.host || "plmux", "host", "--host-bg");
  }

  document.getElementById("sb-right").innerHTML = rightHtml;

  if (m.cmdline_active) {
    updateCmdline({ active: true, buffer: m.cmdline_buffer || "" });
  } else if (state.currentMode !== "CMDLINE") {
    updateCmdline({ active: false });
  }
}

export function updateCmdline(m) {
  var ind = document.getElementById("cl-indicator");
  var hint = document.getElementById("cl-hint");
  var buf = document.getElementById("cl-buffer");
  var cur = document.getElementById("cl-cursor");

  if (m.active) {
    ind.textContent = "COMMAND";
    ind.className = "indicator command";
    hint.style.display = "none";
    buf.textContent = ":" + (m.buffer || "");
    buf.style.display = "";
    cur.style.display = "";
  } else {
    ind.textContent = "READY";
    ind.className = "indicator ready";
    hint.style.display = "";
    buf.style.display = "none";
    cur.style.display = "none";
  }
}
