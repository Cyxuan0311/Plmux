#include "_fastscreen_types.h"
#include "_fastscreen_debug.h"
#include "_fastscreen_color.h"
#include "_fastscreen_render.h"
#include "_fastscreen_ansi.h"

/* ================================================================
   Python FastScreen type
   ================================================================ */
typedef struct {
    PyObject_HEAD
    FastScreen screen;
    PyObject *weakreflist;
} FastScreenObject;

static void
FastScreen_dealloc(FastScreenObject *self) {
    if (self->weakreflist) PyObject_ClearWeakRefs((PyObject *)self);
    screen_free(&self->screen);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
FastScreen_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    FastScreenObject *self = (FastScreenObject *)type->tp_alloc(type, 0);
    if (self) {
        memset(&self->screen, 0, sizeof(FastScreen));
        self->weakreflist = NULL;
    }
    return (PyObject *)self;
}

static int
FastScreen_init(FastScreenObject *self, PyObject *args, PyObject *kwds) {
    int cols, rows;
    if (!PyArg_ParseTuple(args, "ii", &cols, &rows)) return -1;
    if (screen_init(&self->screen, cols, rows) < 0) {
        PyErr_NoMemory();
        return -1;
    }
    return 0;
}

static PyObject *
FastScreen_get_cursor(FastScreenObject *self, void *closure) {
    PyObject *cx = PyLong_FromLong(self->screen.cursor_x);
    PyObject *cy = PyLong_FromLong(self->screen.cursor_y);
    if (!cx || !cy) { Py_XDECREF(cx); Py_XDECREF(cy); return NULL; }
    PyObject *tup = PyTuple_Pack(2, cx, cy);
    Py_DECREF(cx); Py_DECREF(cy);
    return tup;
}

static PyObject *
FastScreen_get_dirty(FastScreenObject *self, void *closure) {
    PyObject *set = PySet_New(NULL);
    if (!set) return NULL;
    FastScreen *s = &self->screen;
    for (int y = 0; y < s->rows; y++) {
        if (s->dirty_bits[y / 64] & ((uint64_t)1 << (y % 64))) {
            PyObject *py_y = PyLong_FromLong(y);
            if (!py_y || PySet_Add(set, py_y) < 0) {
                Py_XDECREF(py_y);
                Py_DECREF(set);
                return NULL;
            }
            Py_DECREF(py_y);
        }
    }
    return set;
}

static PyObject *
FastScreen_clear_dirty(FastScreenObject *self, void *closure) {
    FastScreen *s = &self->screen;
    memset(s->dirty_bits, 0, (size_t)s->dirty_words * sizeof(uint64_t));
    Py_RETURN_NONE;
}

static PyObject *
FastScreen_resize(FastScreenObject *self, PyObject *args) {
    int rows, cols;
    if (!PyArg_ParseTuple(args, "ii", &rows, &cols)) return NULL;
    screen_resize(&self->screen, cols, rows);
    Py_RETURN_NONE;
}

PyObject *
cell_to_dict(FastCell *c) {
    PyObject *dict = PyDict_New();
    if (!dict) return NULL;

    PyObject *data = PyUnicode_FromOrdinal((int)c->codepoint);
    if (!data) { Py_DECREF(dict); return NULL; }
    PyObject *fg = color_to_pystr(c->fg_color);
    if (!fg) { Py_DECREF(data); Py_DECREF(dict); return NULL; }
    PyObject *bg = color_to_pystr(c->bg_color);
    if (!bg) { Py_DECREF(data); Py_DECREF(fg); Py_DECREF(dict); return NULL; }

    PyObject *bold = PyLong_FromLong((c->flags & FLAG_BOLD) ? 1 : 0);
    PyObject *dim = PyLong_FromLong((c->flags & FLAG_DIM) ? 1 : 0);
    PyObject *italic = PyLong_FromLong((c->flags & FLAG_ITALIC) ? 1 : 0);
    PyObject *underscore = PyLong_FromLong((c->flags & FLAG_UNDERLINE) ? 1 : 0);
    PyObject *strike = PyLong_FromLong((c->flags & FLAG_STRIKE) ? 1 : 0);
    PyObject *reverse = PyLong_FromLong((c->flags & FLAG_REVERSE) ? 1 : 0);
    PyObject *overline = PyLong_FromLong((c->flags & FLAG_OVERLINE) ? 1 : 0);

    int ok = 1;
    ok &= (PyDict_SetItemString(dict, "data", data) == 0);
    ok &= (PyDict_SetItemString(dict, "fg", fg) == 0);
    ok &= (PyDict_SetItemString(dict, "bg", bg) == 0);
    ok &= (PyDict_SetItemString(dict, "bold", bold) == 0);
    ok &= (PyDict_SetItemString(dict, "dim", dim) == 0);
    ok &= (PyDict_SetItemString(dict, "italics", italic) == 0);
    ok &= (PyDict_SetItemString(dict, "underscore", underscore) == 0);
    ok &= (PyDict_SetItemString(dict, "strikethrough", strike) == 0);
    ok &= (PyDict_SetItemString(dict, "reverse", reverse) == 0);
    ok &= (PyDict_SetItemString(dict, "overline", overline) == 0);

    Py_DECREF(data); Py_DECREF(fg); Py_DECREF(bg);
    Py_DECREF(bold); Py_DECREF(dim); Py_DECREF(italic); Py_DECREF(underscore);
    Py_DECREF(strike); Py_DECREF(reverse); Py_DECREF(overline);

    if (!ok) { Py_DECREF(dict); return NULL; }
    return dict;
}

static PyObject *
FastScreen_get_cell(FastScreenObject *self, PyObject *args) {
    int y, x;
    if (!PyArg_ParseTuple(args, "ii", &y, &x)) return NULL;
    FastCell *c = screen_cell(&self->screen, x, y);
    if (!c || cell_is_empty(c)) Py_RETURN_NONE;
    return cell_to_dict(c);
}

static PyObject *
FastScreen_get_buffer_line(FastScreenObject *self, PyObject *args) {
    int y;
    if (!PyArg_ParseTuple(args, "i", &y)) return NULL;
    FastScreen *s = &self->screen;
    if (y < 0 || y >= s->rows) { Py_RETURN_NONE; }

    PyObject *dict = PyDict_New();
    if (!dict) return NULL;
    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    for (int x = 0; x < s->cols; x++) {
        FastCell *c = &base[y * s->cols + x];
        if (cell_is_empty(c)) continue;

        PyObject *cell = cell_to_dict(c);
        if (!cell) { Py_DECREF(dict); return NULL; }

        PyObject *key = PyLong_FromLong(x);
        if (!key || PyDict_SetItem(dict, key, cell) < 0) {
            Py_XDECREF(key); Py_DECREF(cell); Py_DECREF(dict);
            return NULL;
        }
        Py_DECREF(key); Py_DECREF(cell);
    }
    return dict;
}

static PyObject *
FastScreen_get_rows(FastScreenObject *self, void *closure) {
    return PyLong_FromLong(self->screen.rows);
}

static PyObject *
FastScreen_get_cols(FastScreenObject *self, void *closure) {
    return PyLong_FromLong(self->screen.cols);
}

static PyObject *
FastScreen_render_row(FastScreenObject *self, PyObject *args) {
    int y;
    if (!PyArg_ParseTuple(args, "i", &y)) return NULL;

    FastScreen *s = &self->screen;
    if (y < 0 || y >= s->rows) {
        PyErr_SetString(PyExc_IndexError, "row index out of range");
        return NULL;
    }

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = base + (size_t)y * s->cols;

    PyObject *result = PyList_New(s->cols);
    if (!result) return NULL;

    for (int x = 0; x < s->cols; x++) {
        FastCell *c = &row[x];

        PyObject *glyph = cell_glyph(c);
        if (!glyph) { Py_DECREF(result); return NULL; }

        PyObject *style = cell_style_str(c);
        if (!style) { Py_DECREF(glyph); Py_DECREF(result); return NULL; }

        PyObject *width = PyLong_FromLong((long)c->width);
        if (!width) { Py_DECREF(glyph); Py_DECREF(style); Py_DECREF(result); return NULL; }

        PyObject *tup = PyTuple_Pack(3, glyph, style, width);
        Py_DECREF(glyph);
        Py_DECREF(style);
        Py_DECREF(width);
        if (!tup) { Py_DECREF(result); return NULL; }

        PyList_SET_ITEM(result, x, tup);
    }

    return result;
}

static PyObject *
FastScreen_render_row_runs(FastScreenObject *self, PyObject *args) {
    int y;
    if (!PyArg_ParseTuple(args, "i", &y)) return NULL;

    FastScreen *s = &self->screen;
    if (y < 0 || y >= s->rows) {
        PyErr_SetString(PyExc_IndexError, "row index out of range");
        return NULL;
    }

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = base + (size_t)y * s->cols;

    if (s->cols <= 0) {
        return PyList_New(0);
    }

    PyObject *result = PyList_New(0);
    if (!result) return NULL;

    int max_buf = s->cols * 5 + 16;
    char *run_buf = (char *)malloc((size_t)max_buf);
    if (!run_buf) {
        Py_DECREF(result);
        return PyErr_NoMemory();
    }

    int run_len = 0;
    int first_non_cont = -1;
    for (int x = 0; x < s->cols; x++) {
        if (row[x].width != 0) { first_non_cont = x; break; }
    }
    uint8_t  run_flags = (first_non_cont >= 0) ? row[first_non_cont].flags : 0;
    uint32_t run_fg = (first_non_cont >= 0) ? row[first_non_cont].fg_color : COLOR_DEFAULT;
    uint32_t run_bg = (first_non_cont >= 0) ? row[first_non_cont].bg_color : COLOR_DEFAULT;
    int run_is_empty = (first_non_cont >= 0) ? (row[first_non_cont].codepoint == 0) : 1;

    for (int x = 0; x < s->cols; x++) {
        FastCell *c = &row[x];
        if (c->width == 0) continue;

        int c_is_empty = (c->codepoint == 0);

        if (c->flags != run_flags || c->fg_color != run_fg || c->bg_color != run_bg || c_is_empty != run_is_empty) {
            if (flush_run(result, run_buf, run_len, run_flags, run_fg, run_bg) < 0) {
                free(run_buf);
                return NULL;
            }
            run_len = 0;
            run_flags = c->flags;
            run_fg = c->fg_color;
            run_bg = c->bg_color;
            run_is_empty = c_is_empty;
        }

        int char_len = glyph_to_utf8_buf(c->codepoint, run_buf + run_len);
        run_len += char_len;
    }

    if (run_len > 0) {
        if (flush_run(result, run_buf, run_len, run_flags, run_fg, run_bg) < 0) {
            free(run_buf);
            return NULL;
        }
    }

    free(run_buf);
    return result;
}

static PyObject *
FastScreen_render_row_runs_to_text(FastScreenObject *self, PyObject *args) {
    int y;
    if (!PyArg_ParseTuple(args, "i", &y)) return NULL;

    FastScreen *s = &self->screen;
    if (y < 0 || y >= s->rows) {
        PyErr_SetString(PyExc_IndexError, "row index out of range");
        return NULL;
    }

    PyObject *text_cls = _get_rich_text_class();
    if (!text_cls) return NULL;

    PyObject *kwargs = PyDict_New();
    if (!kwargs) return NULL;
    PyDict_SetItemString(kwargs, "no_wrap", Py_True);
    PyObject *ovf = PyUnicode_FromString("ignore");
    PyDict_SetItemString(kwargs, "overflow", ovf);
    Py_DECREF(ovf);

    PyObject *empty = PyTuple_New(0);
    PyObject *text_obj = PyObject_Call(text_cls, empty, kwargs);
    Py_DECREF(empty);
    Py_DECREF(kwargs);
    if (!text_obj) return NULL;

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = base + (size_t)y * s->cols;

    if (s->cols <= 0) {
        return text_obj;
    }

    int max_buf = s->cols * 5 + 16;
    char *run_buf = (char *)malloc((size_t)max_buf);
    if (!run_buf) {
        Py_DECREF(text_obj);
        return PyErr_NoMemory();
    }

    int run_len = 0;
    int first_non_cont = -1;
    for (int x = 0; x < s->cols; x++) {
        if (row[x].width != 0) { first_non_cont = x; break; }
    }
    uint8_t  run_flags = (first_non_cont >= 0) ? row[first_non_cont].flags : 0;
    uint32_t run_fg = (first_non_cont >= 0) ? row[first_non_cont].fg_color : COLOR_DEFAULT;
    uint32_t run_bg = (first_non_cont >= 0) ? row[first_non_cont].bg_color : COLOR_DEFAULT;
    int run_is_empty = (first_non_cont >= 0) ? (row[first_non_cont].codepoint == 0) : 1;

    for (int x = 0; x < s->cols; x++) {
        FastCell *c = &row[x];
        if (c->width == 0) continue;

        int c_is_empty = (c->codepoint == 0);

        if (c->flags != run_flags || c->fg_color != run_fg || c->bg_color != run_bg || c_is_empty != run_is_empty) {
            if (flush_run_to_textobj(text_obj, run_buf, run_len,
                                     run_flags, run_fg, run_bg) < 0) {
                free(run_buf);
                Py_DECREF(text_obj);
                return NULL;
            }
            run_len = 0;
            run_flags = c->flags;
            run_fg = c->fg_color;
            run_bg = c->bg_color;
            run_is_empty = c_is_empty;
        }

        int char_len = glyph_to_utf8_buf(c->codepoint, run_buf + run_len);
        run_len += char_len;
    }

    if (run_len > 0) {
        if (flush_run_to_textobj(text_obj, run_buf, run_len,
                                 run_flags, run_fg, run_bg) < 0) {
            free(run_buf);
            Py_DECREF(text_obj);
            return NULL;
        }
    }

    free(run_buf);
    return text_obj;
}

static PyObject *
FastScreen_dump_raw(FastScreenObject *self, PyObject *Py_UNUSED(ignored)) {
    FastScreen *s = &self->screen;
    Py_ssize_t size = screen_dump_size(s);
    if (size <= 0) {
        PyErr_SetString(PyExc_RuntimeError, "screen dump size calculation failed");
        return NULL;
    }
    PyObject *bytes_obj = PyBytes_FromStringAndSize(NULL, size);
    if (!bytes_obj) return NULL;
    char *buf = PyBytes_AS_STRING(bytes_obj);
    if (screen_dump_raw(s, (uint8_t *)buf, size) < 0) {
        Py_DECREF(bytes_obj);
        PyErr_SetString(PyExc_RuntimeError, "screen dump failed");
        return NULL;
    }
    return bytes_obj;
}

static PyObject *
FastScreen_restore_raw(FastScreenObject *self, PyObject *data_obj) {
    if (!PyBytes_Check(data_obj)) {
        PyErr_SetString(PyExc_TypeError, "argument must be bytes");
        return NULL;
    }
    const char *buf = PyBytes_AS_STRING(data_obj);
    Py_ssize_t len = PyBytes_GET_SIZE(data_obj);
    int rc = screen_restore_raw(&self->screen, (const uint8_t *)buf, len);
    if (rc < 0) {
        if (rc == -1) PyErr_SetString(PyExc_ValueError, "dump data too short");
        else if (rc == -2) PyErr_SetString(PyExc_ValueError, "dump data truncated");
        else PyErr_SetString(PyExc_RuntimeError, "screen restore allocation failed");
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *
FastScreen_render_row_to_ansi(FastScreenObject *self, PyObject *args) {
    int y;
    int cursor_x = -1, cursor_y = -1;
    int sel_x1 = -1, sel_x2 = -1, sel_y1 = -1, sel_y2 = -1;
    int draw_cursor = 0;
    if (!PyArg_ParseTuple(args, "i|iiiiiii",
                          &y, &draw_cursor, &cursor_x, &cursor_y,
                          &sel_y1, &sel_x1, &sel_y2, &sel_x2))
        return NULL;

    FastScreen *s = &self->screen;
    if (y < 0 || y >= s->rows) {
        PyErr_SetString(PyExc_IndexError, "row index out of range");
        return NULL;
    }

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = base + (size_t)y * s->cols;

    int max_size = s->cols * 60 + 64;
    char *buf = (char *)malloc((size_t)max_size);
    if (!buf) return PyErr_NoMemory();

    int pos = 0;
    int first_cell = 1;
    uint32_t prev_fg = COLOR_DEFAULT;
    uint32_t prev_bg = COLOR_DEFAULT;
    uint8_t prev_flags = 0;

    int at_cursor = draw_cursor && y == cursor_y;
    int in_selection = 0;
    if (sel_y1 >= 0 && sel_y2 >= 0) {
        int sy1, sy2;
        if (sel_y1 <= sel_y2) { sy1 = sel_y1; sy2 = sel_y2; }
        else { sy1 = sel_y2; sy2 = sel_y1; }
        in_selection = (sy1 <= y && y <= sy2);
    }

    for (int x = 0; x < s->cols; x++) {
        FastCell *c = &row[x];
        if (c->width == 0) continue;

        uint8_t eff_flags = c->flags;
        uint32_t eff_fg = c->fg_color;
        uint32_t eff_bg = c->bg_color;

        if (at_cursor && x == cursor_x) {
            eff_flags |= FLAG_REVERSE | FLAG_BOLD;
        }

        if (in_selection) {
            int selected = 0;
            if (sel_y1 == sel_y2 && y == sel_y1) {
                int sx1, sx2;
                if (sel_x1 <= sel_x2) { sx1 = sel_x1; sx2 = sel_x2; }
                else { sx1 = sel_x2; sx2 = sel_x1; }
                selected = (sx1 <= x && x <= sx2);
            } else if (y == sel_y1) {
                int sx1 = (sel_x1 <= sel_x2) ? sel_x1 : sel_x2;
                selected = (x >= sx1);
            } else if (y == sel_y2) {
                int sx2 = (sel_x1 <= sel_x2) ? sel_x2 : sel_x1;
                selected = (x <= sx2);
            } else {
                selected = 1;
            }
            if (selected) {
                eff_flags |= FLAG_REVERSE;
            }
        }

        int fg_changed = (eff_fg != prev_fg);
        int bg_changed = (eff_bg != prev_bg);
        int flags_changed = (eff_flags != prev_flags);

        if (first_cell || fg_changed || bg_changed || flags_changed) {
            char sgr[128];
            int sgr_pos = 0;

            if (first_cell) {
                sgr_pos = _append_sgr_flags(sgr, sgr_pos, eff_flags);
                sgr_pos = _append_sgr_color(sgr, sgr_pos, 0, eff_fg);
                sgr_pos = _append_sgr_color(sgr, sgr_pos, 1, eff_bg);
            } else {
                if (flags_changed) {
                    uint8_t cleared = prev_flags & ~eff_flags;
                    uint8_t added = eff_flags & ~prev_flags;
                    if (cleared) {
                        sgr_pos = _append_sgr_reset_flags(sgr, sgr_pos, prev_flags, eff_flags);
                    }
                    if (added) {
                        sgr_pos = _append_sgr_set_flags(sgr, sgr_pos, prev_flags, eff_flags);
                    }
                }

                if (fg_changed) {
                    sgr_pos = _append_sgr_color(sgr, sgr_pos, 0, eff_fg);
                }
                if (bg_changed) {
                    sgr_pos = _append_sgr_color(sgr, sgr_pos, 1, eff_bg);
                }
            }

            if (sgr_pos > 0) {
                pos += sprintf(buf + pos, "\x1b[%sm", sgr);
            }
            first_cell = 0;
        }

        int char_len = glyph_to_utf8_buf(c->codepoint, buf + pos);
        pos += char_len;

        prev_fg = eff_fg;
        prev_bg = eff_bg;
        prev_flags = eff_flags;
    }

    PyObject *result = PyUnicode_FromStringAndSize(buf, pos);
    free(buf);
    return result;
}

static PyGetSetDef FastScreen_getset[] = {
    {"cursor", (getter)FastScreen_get_cursor, NULL, NULL, NULL},
    {"dirty", (getter)FastScreen_get_dirty, NULL, NULL, NULL},
    {"rows", (getter)FastScreen_get_rows, NULL, NULL, NULL},
    {"cols", (getter)FastScreen_get_cols, NULL, NULL, NULL},
    {NULL},
};

static PyMethodDef FastScreen_methods[] = {
    {"resize", (PyCFunction)FastScreen_resize, METH_VARARGS, NULL},
    {"get_cell", (PyCFunction)FastScreen_get_cell, METH_VARARGS, NULL},
    {"get_buffer_line", (PyCFunction)FastScreen_get_buffer_line, METH_VARARGS, NULL},
    {"render_row", (PyCFunction)FastScreen_render_row, METH_VARARGS, NULL},
    {"render_row_runs", (PyCFunction)FastScreen_render_row_runs, METH_VARARGS, NULL},
    {"render_row_runs_to_text", (PyCFunction)FastScreen_render_row_runs_to_text, METH_VARARGS, NULL},
    {"render_row_to_ansi", (PyCFunction)FastScreen_render_row_to_ansi, METH_VARARGS, NULL},
    {"clear_dirty", (PyCFunction)FastScreen_clear_dirty, METH_NOARGS, NULL},
    {"dump_raw", (PyCFunction)FastScreen_dump_raw, METH_NOARGS, NULL},
    {"restore_raw", (PyCFunction)FastScreen_restore_raw, METH_O, NULL},
    {NULL},
};

static PyTypeObject FastScreenType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_fastscreen.Screen",
    .tp_basicsize = sizeof(FastScreenObject),
    .tp_dealloc = (destructor)FastScreen_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = FastScreen_methods,
    .tp_getset = FastScreen_getset,
    .tp_init = (initproc)FastScreen_init,
    .tp_new = FastScreen_new,
    .tp_weaklistoffset = offsetof(FastScreenObject, weakreflist),
};

/* ================================================================
   Python FastStream type
   ================================================================ */
typedef struct {
    PyObject_HEAD
    FastParser parser;
    FastScreenObject *screen_obj;
} FastStreamObject;

static void
FastStream_dealloc(FastStreamObject *self) {
    Py_XDECREF(self->screen_obj);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
FastStream_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    FastStreamObject *self = (FastStreamObject *)type->tp_alloc(type, 0);
    if (self) {
        memset(&self->parser, 0, sizeof(FastParser));
        self->screen_obj = NULL;
    }
    return (PyObject *)self;
}

static PyObject *
FastStream_attach(FastStreamObject *self, PyObject *screen_obj) {
    if (!PyObject_TypeCheck(screen_obj, &FastScreenType)) {
        PyErr_SetString(PyExc_TypeError, "expected _fastscreen.Screen");
        return NULL;
    }
    Py_XDECREF(self->screen_obj);
    Py_INCREF(screen_obj);
    self->screen_obj = (FastScreenObject *)screen_obj;
    parser_init(&self->parser, &self->screen_obj->screen);
    Py_RETURN_NONE;
}

static PyObject *
FastStream_feed(FastStreamObject *self, PyObject *data_obj) {
    if (!self->screen_obj) {
        PyErr_SetString(PyExc_RuntimeError, "stream not attached to a screen");
        return NULL;
    }
    char *buf;
    Py_ssize_t len;
    if (PyBytes_AsStringAndSize(data_obj, &buf, &len) < 0) return NULL;
    parser_feed(&self->parser, (const uint8_t *)buf, len);
    Py_RETURN_NONE;
}

static PyMethodDef FastStream_methods[] = {
    {"attach", (PyCFunction)FastStream_attach, METH_O, NULL},
    {"feed", (PyCFunction)FastStream_feed, METH_O, NULL},
    {NULL},
};

static PyTypeObject FastStreamType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_fastscreen.Stream",
    .tp_basicsize = sizeof(FastStreamObject),
    .tp_dealloc = (destructor)FastStream_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = FastStream_methods,
    .tp_new = FastStream_new,
};

/* ================================================================
   Module definition
   ================================================================ */

static PyObject *
module_enable_debug(PyObject *self, PyObject *args) {
    (void)self;
    const char *path;
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;
    if (fs_debug_init(path) != 0) {
        PyErr_SetString(PyExc_RuntimeError, "failed to open debug log");
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *
module_disable_debug(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    fs_debug_shutdown();
    Py_RETURN_NONE;
}

static PyMethodDef module_methods[] = {
    {"enable_debug",  module_enable_debug,  METH_VARARGS, NULL},
    {"disable_debug", module_disable_debug, METH_NOARGS,  NULL},
    {NULL},
};

static PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_fastscreen",
    .m_size = -1,
    .m_methods = module_methods,
};

PyMODINIT_FUNC
PyInit__fastscreen(void) {
    PyObject *m;

    if (PyType_Ready(&FastScreenType) < 0) return NULL;
    if (PyType_Ready(&FastStreamType) < 0) return NULL;

    m = PyModule_Create(&moduledef);
    if (!m) return NULL;

    Py_INCREF(&FastScreenType);
    PyModule_AddObject(m, "Screen", (PyObject *)&FastScreenType);

    Py_INCREF(&FastStreamType);
    PyModule_AddObject(m, "Stream", (PyObject *)&FastStreamType);

    return m;
}
