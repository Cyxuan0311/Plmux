#include "_fastscreen_types.h"
#include "_fastscreen_color.h"
#include "_fastscreen_render.h"

PyObject *
cell_style_str(FastCell *c) {
    int f = c->flags;
    uint32_t fg = c->fg_color;
    uint32_t bg = c->bg_color;

    if (f == 0 && fg == COLOR_DEFAULT && bg == COLOR_DEFAULT)
        Py_RETURN_NONE;

    char parts[8][32];
    int n = 0;

    if (f & FLAG_BOLD)      { memcpy(parts[n++], "bold", 5); }
    if (f & FLAG_DIM)       { memcpy(parts[n++], "dim", 4); }
    if (f & FLAG_ITALIC)    { memcpy(parts[n++], "italic", 7); }
    if (f & FLAG_UNDERLINE) { memcpy(parts[n++], "underline", 10); }
    if (f & FLAG_STRIKE)    { memcpy(parts[n++], "strike", 7); }
    if (f & FLAG_REVERSE)   { memcpy(parts[n++], "reverse", 8); }
    if (f & FLAG_OVERLINE)  { memcpy(parts[n++], "overline", 9); }

    char fg_buf[32] = {0};
    char bg_buf[32] = {0};
    int has_fg = 0, has_bg = 0;

    int ft = color_type(fg);
    if (ft == 1) {
        int idx = color_16_idx(fg);
        if (idx >= 0 && idx < 16) {
            snprintf(fg_buf, sizeof(fg_buf), "%s", ANSI16_TO_HEX[idx]);
            has_fg = 1;
        }
    } else if (ft == 2) {
        snprintf(fg_buf, sizeof(fg_buf), "color(%d)", color_256_idx(fg));
        has_fg = 1;
    } else if (ft == 3) {
        int r, g, b;
        color_rgb_val(fg, &r, &g, &b);
        snprintf(fg_buf, sizeof(fg_buf), "#%02x%02x%02x", r, g, b);
        has_fg = 1;
    }

    int bt = color_type(bg);
    if (bt == 1) {
        int idx = color_16_idx(bg);
        if (idx >= 0 && idx < 16) {
            snprintf(bg_buf, sizeof(bg_buf), "on %s", ANSI16_TO_HEX[idx]);
            has_bg = 1;
        }
    } else if (bt == 2) {
        snprintf(bg_buf, sizeof(bg_buf), "on color(%d)", color_256_idx(bg));
        has_bg = 1;
    } else if (bt == 3) {
        int r, g, b;
        color_rgb_val(bg, &r, &g, &b);
        snprintf(bg_buf, sizeof(bg_buf), "on #%02x%02x%02x", r, g, b);
        has_bg = 1;
    }

    if (has_fg && has_bg) {
        snprintf(parts[n], sizeof(parts[n]), "%s %s", fg_buf, bg_buf);
        n++;
    } else if (has_fg) {
        memcpy(parts[n++], fg_buf, strlen(fg_buf) + 1);
    } else if (has_bg) {
        memcpy(parts[n++], bg_buf, strlen(bg_buf) + 1);
    }

    char buf[256];
    int pos = 0;
    for (int i = 0; i < n; i++) {
        if (i > 0) buf[pos++] = ' ';
        int len = (int)strlen(parts[i]);
        memcpy(buf + pos, parts[i], (size_t)len);
        pos += len;
    }
    buf[pos] = '\0';
    PyObject *result = PyUnicode_FromString(buf);
    if (result) PyUnicode_InternInPlace(&result);
    return result;
}

PyObject *
cell_glyph(FastCell *c) {
    uint32_t cp = c->codepoint;
    if (cp == 0 || cp == 0x20) {
        return PyUnicode_FromString(" ");
    }
    if (cp < 0x20) {
        if (cp == 9 || cp == 10 || cp == 13) {
            return PyUnicode_FromOrdinal((int)cp);
        }
        char buf[3] = {'^', (char)(cp + 0x40), 0};
        return PyUnicode_FromString(buf);
    }
    if (cp == 0x7F) {
        return PyUnicode_FromString("^?");
    }
    return PyUnicode_FromOrdinal((int)cp);
}

int
glyph_to_utf8_buf(uint32_t cp, char *buf) {
    if (cp == 0 || cp == 0x20) {
        buf[0] = ' ';
        return 1;
    }
    if (cp < 0x20) {
        if (cp == 9 || cp == 10 || cp == 13) {
            buf[0] = (char)cp;
            return 1;
        }
        buf[0] = '^';
        buf[1] = (char)(cp + 0x40);
        return 2;
    }
    if (cp == 0x7F) {
        buf[0] = '^';
        buf[1] = '?';
        return 2;
    }
    if (cp < 0x80) {
        buf[0] = (char)cp;
        return 1;
    }
    if (cp < 0x800) {
        buf[0] = (char)(0xC0 | (cp >> 6));
        buf[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp < 0x10000) {
        buf[0] = (char)(0xE0 | (cp >> 12));
        buf[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        buf[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    }
    buf[0] = (char)(0xF0 | (cp >> 18));
    buf[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
    buf[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
    buf[3] = (char)(0x80 | (cp & 0x3F));
    return 4;
}

int
flush_run(PyObject *result, const char *buf, int len,
          uint8_t flags, uint32_t fg, uint32_t bg) {
    if (len == 0) return 0;

    FastCell tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.flags = flags;
    tmp.fg_color = fg;
    tmp.bg_color = bg;

    PyObject *text = PyUnicode_FromStringAndSize(buf, len);
    if (!text) return -1;

    PyObject *style = cell_style_str(&tmp);
    if (!style) { Py_DECREF(text); return -1; }

    PyObject *tup = PyTuple_Pack(2, text, style);
    Py_DECREF(text);
    Py_DECREF(style);
    if (!tup) return -1;

    int ret = PyList_Append(result, tup);
    Py_DECREF(tup);
    return ret;
}

static PyObject *_rich_text_class = NULL;

PyObject *
_get_rich_text_class(void) {
    if (_rich_text_class == NULL) {
        PyObject *mod = PyImport_ImportModule("rich.text");
        if (!mod) return NULL;
        _rich_text_class = PyObject_GetAttrString(mod, "Text");
        Py_DECREF(mod);
        if (!_rich_text_class) return NULL;
    }
    return _rich_text_class;
}

int
flush_run_to_textobj(PyObject *text_obj, const char *buf, int len,
                     uint8_t flags, uint32_t fg, uint32_t bg) {
    if (len == 0) return 0;

    PyObject *py_text = PyUnicode_FromStringAndSize(buf, len);
    if (!py_text) return -1;

    FastCell tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.flags = flags;
    tmp.fg_color = fg;
    tmp.bg_color = bg;
    PyObject *style = cell_style_str(&tmp);

    PyObject *ret = PyObject_CallMethod(text_obj, "append", "OO",
                                        py_text, style ? style : Py_None);
    Py_DECREF(py_text);
    Py_XDECREF(style);
    if (!ret) return -1;
    Py_DECREF(ret);
    return 0;
}
