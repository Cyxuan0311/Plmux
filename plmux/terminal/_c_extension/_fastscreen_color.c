#include "_fastscreen_color.h"

const char *COLOR_16_NAMES[16] = {
    "black", "red", "green", "brown", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
};

const char *ANSI16_TO_HEX[16] = {
    "#262626", "#cc5555", "#55cc55", "#cdcd55",
    "#5555ff", "#cc55cc", "#55cccc", "#e5e5e5",
    "#666666", "#ff5555", "#55ff55", "#ffff55",
    "#5555ff", "#ff55ff", "#55ffff", "#ffffff",
};

PyObject *
color_to_pystr(uint32_t c) {
    int t = color_type(c);
    if (t == 0) return PyUnicode_FromString("default");
    if (t == 1) {
        int idx = color_16_idx(c);
        if (idx >= 0 && idx < 16) return PyUnicode_FromString(COLOR_16_NAMES[idx]);
        return PyUnicode_FromString("default");
    }
    if (t == 2) {
        char buf[8];
        snprintf(buf, sizeof(buf), "%d", color_256_idx(c));
        return PyUnicode_FromString(buf);
    }
    if (t == 3) {
        int r, g, b;
        color_rgb_val(c, &r, &g, &b);
        char buf[16];
        snprintf(buf, sizeof(buf), "#%02x%02x%02x", r, g, b);
        return PyUnicode_FromString(buf);
    }
    return PyUnicode_FromString("default");
}

PyObject *
color_to_rich(uint32_t c) {
    int t = color_type(c);
    if (t == 0) Py_RETURN_NONE;
    if (t == 1) {
        int idx = color_16_idx(c);
        if (idx >= 0 && idx < 16) return PyUnicode_FromString(ANSI16_TO_HEX[idx]);
        Py_RETURN_NONE;
    }
    if (t == 2) {
        char buf[16];
        snprintf(buf, sizeof(buf), "color(%d)", color_256_idx(c));
        return PyUnicode_FromString(buf);
    }
    if (t == 3) {
        int r, g, b;
        color_rgb_val(c, &r, &g, &b);
        char buf[16];
        snprintf(buf, sizeof(buf), "#%02x%02x%02x", r, g, b);
        return PyUnicode_FromString(buf);
    }
    Py_RETURN_NONE;
}
