#include "_ipc_protocol.h"

typedef struct {
    PyObject_HEAD
    IPCReadBuffer rbuf;
} FrameReaderObject;

static void
FrameReader_dealloc(FrameReaderObject *self) {
    ipc_buf_free(&self->rbuf);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
FrameReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    FrameReaderObject *self = (FrameReaderObject *)type->tp_alloc(type, 0);
    if (self) ipc_buf_init(&self->rbuf);
    return (PyObject *)self;
}

static PyObject *
FrameReader_feed(FrameReaderObject *self, PyObject *data_obj) {
    if (!PyBytes_Check(data_obj)) {
        PyErr_SetString(PyExc_TypeError, "expected bytes");
        return NULL;
    }
    Py_ssize_t len = PyBytes_GET_SIZE(data_obj);
    const uint8_t *data = (const uint8_t *)PyBytes_AS_STRING(data_obj);

    if (ipc_buf_ensure(&self->rbuf, len) < 0) {
        return PyErr_NoMemory();
    }
    memcpy(self->rbuf.buf + self->rbuf.buf_len, data, (size_t)len);
    self->rbuf.buf_len += len;

    Py_RETURN_NONE;
}

static PyObject *
FrameReader_read_one(FrameReaderObject *self, PyObject *Py_UNUSED(ignored)) {
    IPCReadBuffer *buf = &self->rbuf;

    if (buf->buf_len < IPC_HEADER_SIZE) Py_RETURN_NONE;

    uint8_t *p = buf->buf;
    uint32_t length = ((uint32_t)p[0] << 24) |
                      ((uint32_t)p[1] << 16) |
                      ((uint32_t)p[2] << 8)  |
                      ((uint32_t)p[3]);

    if (length < 1 || length > IPC_FRAME_MAX_PAYLOAD) {
        PyErr_SetString(PyExc_RuntimeError, "invalid frame length");
        return NULL;
    }

    Py_ssize_t total = 4 + (Py_ssize_t)length;
    if (buf->buf_len < total) Py_RETURN_NONE;

    uint8_t msg_type = p[4];
    Py_ssize_t payload_len = (Py_ssize_t)length - 1;

    PyObject *py_type = PyLong_FromLong((long)msg_type);
    PyObject *py_payload;
    if (payload_len > 0) {
        py_payload = PyBytes_FromStringAndSize((const char *)(p + 5), payload_len);
    } else {
        py_payload = PyBytes_FromStringAndSize("", 0);
    }

    if (!py_type || !py_payload) {
        Py_XDECREF(py_type);
        Py_XDECREF(py_payload);
        return NULL;
    }

    PyObject *tup = PyTuple_Pack(2, py_type, py_payload);
    Py_DECREF(py_type);
    Py_DECREF(py_payload);

    ipc_buf_consume(buf, total);

    return tup;
}

static PyObject *
FrameReader_read_all(FrameReaderObject *self, PyObject *Py_UNUSED(ignored)) {
    PyObject *list = PyList_New(0);
    if (!list) return NULL;

    while (1) {
        PyObject *frame = FrameReader_read_one(self, NULL);
        if (frame == Py_None) {
            Py_DECREF(frame);
            break;
        }
        if (!frame) {
            Py_DECREF(list);
            return NULL;
        }
        if (PyList_Append(list, frame) < 0) {
            Py_DECREF(frame);
            Py_DECREF(list);
            return NULL;
        }
        Py_DECREF(frame);
    }

    return list;
}

static PyObject *
FrameReader_get_pending(FrameReaderObject *self, void *closure) {
    return PyLong_FromSsize_t(self->rbuf.buf_len);
}

static PyMethodDef FrameReader_methods[] = {
    {"feed", (PyCFunction)FrameReader_feed, METH_O,
     "Feed raw bytes into the reader buffer."},
    {"read_one", (PyCFunction)FrameReader_read_one, METH_NOARGS,
     "Read one frame, returning (msg_type, payload) or None."},
    {"read_all", (PyCFunction)FrameReader_read_all, METH_NOARGS,
     "Read all available frames, returning list of (msg_type, payload)."},
    {NULL, NULL, 0, NULL}
};

static PyGetSetDef FrameReader_getset[] = {
    {"pending", (getter)FrameReader_get_pending, NULL,
     "Number of bytes pending in the read buffer.", NULL},
    {NULL, NULL, NULL, NULL, NULL}
};

static PyTypeObject FrameReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "plmux.ipc._c_extension._ipc_protocol.FrameReader",
    .tp_basicsize = sizeof(FrameReaderObject),
    .tp_dealloc = (destructor)FrameReader_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = FrameReader_new,
    .tp_methods = FrameReader_methods,
    .tp_getset = FrameReader_getset,
};

static PyObject *
py_encode_frame(PyObject *self, PyObject *args) {
    int msg_type;
    Py_buffer payload_buf;
    if (!PyArg_ParseTuple(args, "iy*", &msg_type, &payload_buf)) return NULL;

    Py_ssize_t payload_len = payload_buf.len;
    const uint8_t *payload = (const uint8_t *)payload_buf.buf;

    Py_ssize_t total = 4 + 1 + payload_len;
    PyObject *out = PyBytes_FromStringAndSize(NULL, total);
    if (!out) {
        PyBuffer_Release(&payload_buf);
        return NULL;
    }

    uint8_t *out_ptr = (uint8_t *)PyBytes_AS_STRING(out);
    Py_ssize_t written = ipc_encode_frame((uint8_t)msg_type, payload, payload_len,
                                           out_ptr, total);

    PyBuffer_Release(&payload_buf);

    if (written < 0) {
        Py_DECREF(out);
        PyErr_SetString(PyExc_RuntimeError, "encode error");
        return NULL;
    }

    if (written < total) {
        _PyBytes_Resize(&out, written);
    }

    return out;
}

static PyObject *
py_decode_frame(PyObject *self, PyObject *args) {
    Py_buffer data_buf;
    if (!PyArg_ParseTuple(args, "y*", &data_buf)) return NULL;

    Py_ssize_t len = data_buf.len;
    const uint8_t *data = (const uint8_t *)data_buf.buf;

    if (len < IPC_HEADER_SIZE) {
        PyBuffer_Release(&data_buf);
        Py_RETURN_NONE;
    }

    uint32_t length = ((uint32_t)data[0] << 24) |
                      ((uint32_t)data[1] << 16) |
                      ((uint32_t)data[2] << 8)  |
                      ((uint32_t)data[3]);

    if (length < 1 || length > IPC_FRAME_MAX_PAYLOAD) {
        PyBuffer_Release(&data_buf);
        Py_RETURN_NONE;
    }

    Py_ssize_t total = 4 + (Py_ssize_t)length;
    if (len < total) {
        PyBuffer_Release(&data_buf);
        Py_RETURN_NONE;
    }

    uint8_t msg_type = data[4];
    Py_ssize_t payload_len = (Py_ssize_t)length - 1;

    PyObject *py_type = PyLong_FromLong((long)msg_type);
    PyObject *py_payload;
    if (payload_len > 0) {
        py_payload = PyBytes_FromStringAndSize((const char *)(data + 5), payload_len);
    } else {
        py_payload = PyBytes_FromStringAndSize("", 0);
    }

    PyBuffer_Release(&data_buf);

    if (!py_type || !py_payload) {
        Py_XDECREF(py_type);
        Py_XDECREF(py_payload);
        return NULL;
    }

    PyObject *result = PyTuple_Pack(3, py_type, py_payload, PyLong_FromSsize_t(total));
    Py_DECREF(py_type);
    Py_DECREF(py_payload);

    return result;
}

static PyMethodDef module_methods[] = {
    {"encode_frame", py_encode_frame, METH_VARARGS,
     "Encode a frame: encode_frame(msg_type, payload_bytes) -> bytes"},
    {"decode_frame", py_decode_frame, METH_VARARGS,
     "Decode a frame: decode_frame(data_bytes) -> (msg_type, payload, total) or None"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef ipc_protocol_module = {
    PyModuleDef_HEAD_INIT,
    "plmux.ipc._c_extension._ipc_protocol",
    "C extension for plmux IPC binary protocol frame encoding/decoding.",
    -1,
    module_methods,
};

PyMODINIT_FUNC
PyInit__ipc_protocol(void) {
    PyObject *m = PyModule_Create(&ipc_protocol_module);
    if (!m) return NULL;

    if (PyType_Ready(&FrameReaderType) < 0) {
        Py_DECREF(m);
        return NULL;
    }

    Py_INCREF(&FrameReaderType);
    if (PyModule_AddObject(m, "FrameReader", (PyObject *)&FrameReaderType) < 0) {
        Py_DECREF(&FrameReaderType);
        Py_DECREF(m);
        return NULL;
    }

    PyModule_AddIntConstant(m, "MSG_INIT", IPC_MSG_INIT);
    PyModule_AddIntConstant(m, "MSG_PANE_OUTPUT", IPC_MSG_PANE_OUTPUT);
    PyModule_AddIntConstant(m, "MSG_STATE_UPDATE", IPC_MSG_STATE_UPDATE);
    PyModule_AddIntConstant(m, "MSG_PANE_CLOSED", IPC_MSG_PANE_CLOSED);
    PyModule_AddIntConstant(m, "MSG_BELL", IPC_MSG_BELL);
    PyModule_AddIntConstant(m, "MSG_KEY", IPC_MSG_KEY);
    PyModule_AddIntConstant(m, "MSG_RESIZE", IPC_MSG_RESIZE);
    PyModule_AddIntConstant(m, "MSG_COMMAND", IPC_MSG_COMMAND);
    PyModule_AddIntConstant(m, "MSG_MOUSE", IPC_MSG_MOUSE);
    PyModule_AddIntConstant(m, "MSG_DETACH", IPC_MSG_DETACH);
    PyModule_AddIntConstant(m, "HEADER_SIZE", IPC_HEADER_SIZE);

    return m;
}
