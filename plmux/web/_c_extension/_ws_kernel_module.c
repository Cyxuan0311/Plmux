#include "_ws_kernel.h"

typedef struct {
    PyObject_HEAD
    WSReadBuffer rbuf;
} FrameParserObject;

static void
FrameParser_dealloc(FrameParserObject *self) {
    ws_buf_free(&self->rbuf);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
FrameParser_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    FrameParserObject *self = (FrameParserObject *)type->tp_alloc(type, 0);
    if (self) ws_buf_init(&self->rbuf);
    return (PyObject *)self;
}

static PyObject *
FrameParser_feed(FrameParserObject *self, PyObject *data_obj) {
    if (!PyBytes_Check(data_obj)) {
        PyErr_SetString(PyExc_TypeError, "expected bytes");
        return NULL;
    }
    Py_ssize_t len = PyBytes_GET_SIZE(data_obj);
    const uint8_t *data = (const uint8_t *)PyBytes_AS_STRING(data_obj);

    if (ws_buf_ensure(&self->rbuf, len) < 0) {
        return PyErr_NoMemory();
    }
    memcpy(self->rbuf.buf + self->rbuf.buf_len, data, (size_t)len);
    self->rbuf.buf_len += len;

    Py_RETURN_NONE;
}

static PyObject *
FrameParser_parse(FrameParserObject *self, PyObject *Py_UNUSED(ignored)) {
    WSFrame *frames = NULL;
    int count = 0;

    int rc = ws_parse_frames(&self->rbuf, &frames, &count);
    if (rc < 0) {
        if (frames) ws_free_frames(frames, count);
        PyErr_SetString(PyExc_RuntimeError, "frame parse error");
        return NULL;
    }

    PyObject *result = PyList_New(count);
    if (!result) {
        ws_free_frames(frames, count);
        return NULL;
    }

    for (int i = 0; i < count; i++) {
        PyObject *tup;
        if (frames[i].payload && frames[i].payload_len > 0) {
            if (frames[i].opcode == WS_OPCODE_TEXT) {
                PyObject *text = PyUnicode_FromStringAndSize(
                    (const char *)frames[i].payload, frames[i].payload_len);
                if (!text) {
                    Py_DECREF(result);
                    ws_free_frames(frames, count);
                    return NULL;
                }
                tup = Py_BuildValue("(iN)", frames[i].opcode, text);
            } else {
                PyObject *bytes = PyBytes_FromStringAndSize(
                    (const char *)frames[i].payload, frames[i].payload_len);
                if (!bytes) {
                    Py_DECREF(result);
                    ws_free_frames(frames, count);
                    return NULL;
                }
                tup = Py_BuildValue("(iN)", frames[i].opcode, bytes);
            }
        } else {
            if (frames[i].opcode == WS_OPCODE_TEXT) {
                PyObject *text = PyUnicode_FromStringAndSize("", 0);
                if (!text) {
                    Py_DECREF(result);
                    ws_free_frames(frames, count);
                    return NULL;
                }
                tup = Py_BuildValue("(iN)", frames[i].opcode, text);
            } else {
                tup = Py_BuildValue("(iy)", frames[i].opcode, "");
            }
        }
        if (!tup) {
            Py_DECREF(result);
            ws_free_frames(frames, count);
            return NULL;
        }
        PyList_SET_ITEM(result, i, tup);
    }

    ws_free_frames(frames, count);
    return result;
}

static PyMethodDef FrameParser_methods[] = {
    {"feed", (PyCFunction)FrameParser_feed, METH_O, NULL},
    {"parse", (PyCFunction)FrameParser_parse, METH_NOARGS, NULL},
    {NULL}
};

static PyTypeObject FrameParserType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_ws_kernel.FrameParser",
    .tp_basicsize = sizeof(FrameParserObject),
    .tp_dealloc = (destructor)FrameParser_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_methods = FrameParser_methods,
    .tp_new = FrameParser_new,
};

static PyObject *
ws_encode(PyObject *self, PyObject *args) {
    int opcode;
    Py_buffer data;
    int mask = 0;

    if (!PyArg_ParseTuple(args, "iy*|i", &opcode, &data, &mask))
        return NULL;

    Py_ssize_t payload_len = data.len;
    const uint8_t *payload = (const uint8_t *)data.buf;

    Py_ssize_t header_len = 2;
    if (payload_len >= 126 && payload_len < 65536) header_len = 4;
    else if (payload_len >= 65536) header_len = 10;
    if (mask) header_len += 4;

    Py_ssize_t total = header_len + payload_len;
    PyObject *out_bytes = PyBytes_FromStringAndSize(NULL, total);
    if (!out_bytes) {
        PyBuffer_Release(&data);
        return NULL;
    }

    uint8_t *out = (uint8_t *)PyBytes_AS_STRING(out_bytes);
    Py_ssize_t written = ws_encode_frame(opcode, payload, payload_len, mask, out, total);

    PyBuffer_Release(&data);

    if (written < 0) {
        Py_DECREF(out_bytes);
        PyErr_SetString(PyExc_RuntimeError, "encode error");
        return NULL;
    }

    if (written != total) {
        _PyBytes_Resize(&out_bytes, written);
    }

    return out_bytes;
}

static PyObject *
ws_encode_text_frame(PyObject *self, PyObject *args) {
    const char *text;
    Py_ssize_t text_len;

    if (!PyArg_ParseTuple(args, "s#", &text, &text_len))
        return NULL;

    Py_ssize_t header_len = 2;
    if (text_len >= 126 && text_len < 65536) header_len = 4;
    else if (text_len >= 65536) header_len = 10;

    Py_ssize_t total = header_len + text_len;
    PyObject *out_bytes = PyBytes_FromStringAndSize(NULL, total);
    if (!out_bytes) return NULL;

    uint8_t *out = (uint8_t *)PyBytes_AS_STRING(out_bytes);
    Py_ssize_t written = ws_encode_frame(
        WS_OPCODE_TEXT, (const uint8_t *)text, text_len, 0, out, total);

    if (written < 0) {
        Py_DECREF(out_bytes);
        PyErr_SetString(PyExc_RuntimeError, "encode error");
        return NULL;
    }

    if (written != total) {
        _PyBytes_Resize(&out_bytes, written);
    }

    return out_bytes;
}

static PyObject *
ws_encode_binary_frame(PyObject *self, PyObject *args) {
    Py_buffer data;
    if (!PyArg_ParseTuple(args, "y*", &data))
        return NULL;

    Py_ssize_t payload_len = data.len;
    const uint8_t *payload = (const uint8_t *)data.buf;

    Py_ssize_t header_len = 2;
    if (payload_len >= 126 && payload_len < 65536) header_len = 4;
    else if (payload_len >= 65536) header_len = 10;

    Py_ssize_t total = header_len + payload_len;
    PyObject *out_bytes = PyBytes_FromStringAndSize(NULL, total);
    if (!out_bytes) {
        PyBuffer_Release(&data);
        return NULL;
    }

    uint8_t *out = (uint8_t *)PyBytes_AS_STRING(out_bytes);
    Py_ssize_t written = ws_encode_frame(
        WS_OPCODE_BINARY, payload, payload_len, 0, out, total);

    PyBuffer_Release(&data);

    if (written < 0) {
        Py_DECREF(out_bytes);
        PyErr_SetString(PyExc_RuntimeError, "encode error");
        return NULL;
    }

    if (written != total) {
        _PyBytes_Resize(&out_bytes, written);
    }

    return out_bytes;
}

static PyObject *
ws_encode_close_frame(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    uint8_t out[2];
    Py_ssize_t written = ws_encode_frame(WS_OPCODE_CLOSE, NULL, 0, 0, out, 2);
    if (written < 0) {
        PyErr_SetString(PyExc_RuntimeError, "encode error");
        return NULL;
    }
    return PyBytes_FromStringAndSize((const char *)out, written);
}

static PyObject *
ws_encode_pong_frame(PyObject *self, PyObject *args) {
    Py_buffer data;
    Py_ssize_t payload_len = 0;
    const uint8_t *payload = NULL;
    int has_payload = 0;

    if (PyTuple_GET_SIZE(args) > 0) {
        if (!PyArg_ParseTuple(args, "y*", &data))
            return NULL;
        payload_len = data.len;
        payload = (const uint8_t *)data.buf;
        has_payload = 1;
    }

    Py_ssize_t header_len = 2;
    if (payload_len >= 126 && payload_len < 65536) header_len = 4;

    Py_ssize_t total = header_len + payload_len;
    PyObject *out_bytes = PyBytes_FromStringAndSize(NULL, total);
    if (!out_bytes) {
        if (has_payload) PyBuffer_Release(&data);
        return NULL;
    }

    uint8_t *out = (uint8_t *)PyBytes_AS_STRING(out_bytes);
    Py_ssize_t written = ws_encode_frame(
        WS_OPCODE_PONG, payload, payload_len, 0, out, total);

    if (has_payload) PyBuffer_Release(&data);

    if (written < 0) {
        Py_DECREF(out_bytes);
        PyErr_SetString(PyExc_RuntimeError, "encode error");
        return NULL;
    }

    if (written != total) {
        _PyBytes_Resize(&out_bytes, written);
    }

    return out_bytes;
}

static PyMethodDef module_methods[] = {
    {"encode", ws_encode, METH_VARARGS, NULL},
    {"encode_text_frame", ws_encode_text_frame, METH_VARARGS, NULL},
    {"encode_binary_frame", ws_encode_binary_frame, METH_VARARGS, NULL},
    {"encode_close_frame", ws_encode_close_frame, METH_NOARGS, NULL},
    {"encode_pong_frame", ws_encode_pong_frame, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef ws_kernel_module = {
    PyModuleDef_HEAD_INIT,
    "_ws_kernel",
    NULL,
    -1,
    module_methods,
};

PyMODINIT_FUNC
PyInit__ws_kernel(void) {
    PyObject *m = PyModule_Create(&ws_kernel_module);
    if (!m) return NULL;

    if (PyType_Ready(&FrameParserType) < 0) {
        Py_DECREF(m);
        return NULL;
    }

    Py_INCREF(&FrameParserType);
    if (PyModule_AddObject(m, "FrameParser", (PyObject *)&FrameParserType) < 0) {
        Py_DECREF(&FrameParserType);
        Py_DECREF(m);
        return NULL;
    }

    PyModule_AddIntConstant(m, "OPCODE_TEXT", WS_OPCODE_TEXT);
    PyModule_AddIntConstant(m, "OPCODE_BINARY", WS_OPCODE_BINARY);
    PyModule_AddIntConstant(m, "OPCODE_CLOSE", WS_OPCODE_CLOSE);
    PyModule_AddIntConstant(m, "OPCODE_PING", WS_OPCODE_PING);
    PyModule_AddIntConstant(m, "OPCODE_PONG", WS_OPCODE_PONG);

    return m;
}
