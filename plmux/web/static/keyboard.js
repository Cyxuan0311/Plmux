export function encodeKittyKey(ev) {
  var shift_value = 1;
  var alt_value = 2;
  var ctrl_value = 4;
  var super_value = 8;
  var modifier_string = 1;
  if (ev.shiftKey) modifier_string += shift_value;
  if (ev.altKey) modifier_string += alt_value;
  if (ev.ctrlKey) modifier_string += ctrl_value;
  if (ev.metaKey) modifier_string += super_value;

  var key_code = ev.keyCode || ev.which;
  if (key_code === 0 && ev.key && ev.key.length === 1) {
    key_code = ev.key.charCodeAt(0);
  }

  return "\x1b[" + key_code + ";" + modifier_string + "u";
}

export function hasModifiersToHandle(ev) {
  var MODIFIER_KEYS = ["Shift", "Control", "Alt", "Meta"];
  var modifiers_count = [ev.altKey, ev.ctrlKey, ev.shiftKey, ev.metaKey].filter(Boolean).length;
  var isModifierKey = MODIFIER_KEYS.includes(ev.key);
  return (modifiers_count > 1 || ev.metaKey) && !isModifierKey;
}

var SPECIAL_KEY_SEQUENCES = {
  "ArrowUp": "\x1b[A",
  "ArrowDown": "\x1b[B",
  "ArrowRight": "\x1b[C",
  "ArrowLeft": "\x1b[D",
  "Home": "\x1b[H",
  "End": "\x1b[F",
  "Delete": "\x1b[3~",
  "Insert": "\x1b[2~",
  "PageUp": "\x1b[5~",
  "PageDown": "\x1b[6~",
  "Backspace": "\x7f",
  "Tab": "\t",
  "Escape": "\x1b",
  "Enter": "\r",
};

export function encodeSpecialKey(key) {
  return SPECIAL_KEY_SEQUENCES[key] || null;
}

export function isSpecialKey(key) {
  return key in SPECIAL_KEY_SEQUENCES;
}

export function isFunctionKey(key) {
  return key.startsWith("F") && key.length <= 3 && key.substring(1).match(/^\d+$/);
}

export function encodeFunctionKey(key) {
  var num = parseInt(key.substring(1));
  if (num === 1) return "\x1bOP";
  if (num === 2) return "\x1bOQ";
  if (num === 3) return "\x1bOR";
  if (num === 4) return "\x1bOS";
  if (num >= 5 && num <= 12) return "\x1b[" + (num + 11) + "~";
  return null;
}

var CTRL_MAP = {
  "a": "\x01", "b": "\x02", "c": "\x03", "d": "\x04",
  "e": "\x05", "f": "\x06", "g": "\x07", "h": "\x08",
  "i": "\x09", "j": "\x0a", "k": "\x0b", "l": "\x0c",
  "m": "\x0d", "n": "\x0e", "o": "\x0f", "p": "\x10",
  "q": "\x11", "r": "\x12", "s": "\x13", "t": "\x14",
  "u": "\x15", "v": "\x16", "w": "\x17", "x": "\x18",
  "y": "\x19", "z": "\x1a",
  "[": "\x1b", "]": "\x1d", "\\": "\x1c",
  ";": "\x1b", "'": "\x1b", " ": "\x00",
  ",": "\x1c", "/": "\x1f", "`": "\x1e",
  "2": "\x00", "6": "\x1e", "-": "\x1f", "=": "\x1d",
};

export function encodeCtrlKey(key) {
  return CTRL_MAP[key.toLowerCase()] || null;
}
