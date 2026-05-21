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
  "ESC_WAIT": "mode-esc_wait",
};

var MODE_BG_VAR_MAP = {
  "NORMAL": "--mode-normal-bg",
  "PREFIX": "--mode-prefix-bg",
  "CMDLINE": "--mode-cmdline-bg",
  "COPY": "--border-active",
  "HELP": "--border-active",
  "THEME_LIST": "--border-active",
  "SESSION_LIST": "--border-active",
  "PLUGIN_LIST": "--border-active",
  "LAYOUT_LIST": "--border-active",
  "ESC_WAIT": "--mode-normal-bg",
};

export function updateMode(mode) {
  var modeEl = document.getElementById("sb-mode");
  var arrMode = document.getElementById("arr-mode");
  modeEl.textContent = mode;
  modeEl.className = "sb-seg";

  var cls = MODE_CLASS_MAP[mode] || "mode-normal";
  modeEl.classList.add(cls);

  var bgVar = MODE_BG_VAR_MAP[mode] || "--mode-normal-bg";
  arrMode.style.borderRightColor = "var(" + bgVar + ")";
}

export function updateStatus(m, state) {
  var modeText = (m.mode || "NORMAL").toUpperCase();
  state.currentMode = modeText;
  updateMode(modeText);

  document.getElementById("sb-win").innerHTML = '<span class="icon">\u{1F5B9}</span> ' + (m.win || "W1");
  document.getElementById("sb-pane").innerHTML = '<span class="icon">\u25A6</span> ' + (m.pane || "P1");

  var cmdEl = document.getElementById("sb-cmd");
  var cmdArrow = document.getElementById("arr-cmd");
  if (m.cmd) {
    cmdEl.textContent = " " + m.cmd + " ";
    cmdEl.style.display = "";
    cmdArrow.style.display = "";
  } else {
    cmdEl.style.display = "none";
    cmdArrow.style.display = "none";
  }

  document.getElementById("sb-clock").innerHTML = '<span class="icon">\u{1F552}</span> ' + (m.clock || "--:--:--");
  document.getElementById("sb-host").innerHTML = '<span class="icon">\u2318</span> ' + (m.host || "plmux");

  var batEl = document.getElementById("sb-bat");
  var batArrow = document.getElementById("arr-bat");
  if (m.bat) {
    batEl.innerHTML = '<span class="icon">\u{1F50B}</span> ' + m.bat;
    batEl.className = "sb-seg bat-" + (m.bat_style || "ok");
    batEl.style.display = "";
    batArrow.style.display = "";
    batArrow.style.borderLeftColor = "var(--bat-" + (m.bat_style || "ok") + "-bg)";
  } else {
    batEl.style.display = "none";
    batArrow.style.display = "none";
  }

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
