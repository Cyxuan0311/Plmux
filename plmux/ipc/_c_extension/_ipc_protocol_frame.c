#include "_ipc_protocol.h"

int
ipc_parse_frames(IPCReadBuffer *buf, PyObject **out_list) {
    PyObject *list = PyList_New(0);
    if (!list) return -1;

    Py_ssize_t pos = 0;
    Py_ssize_t avail = buf->buf_len;

    while (avail >= IPC_HEADER_SIZE) {
        uint8_t *p = buf->buf + pos;

        uint32_t length = ((uint32_t)p[0] << 24) |
                          ((uint32_t)p[1] << 16) |
                          ((uint32_t)p[2] << 8)  |
                          ((uint32_t)p[3]);

        if (length < 1 || length > IPC_FRAME_MAX_PAYLOAD) {
            Py_DECREF(list);
            return -2;
        }

        Py_ssize_t total = 4 + (Py_ssize_t)length;

        if (avail < total) break;

        uint8_t msg_type = p[4];
        Py_ssize_t payload_len = (Py_ssize_t)length - 1;
        const uint8_t *payload = p + 5;

        PyObject *py_type = PyLong_FromLong((long)msg_type);
        PyObject *py_payload;
        if (payload_len > 0) {
            py_payload = PyBytes_FromStringAndSize((const char *)payload, payload_len);
        } else {
            py_payload = PyBytes_FromStringAndSize("", 0);
        }

        if (!py_type || !py_payload) {
            Py_XDECREF(py_type);
            Py_XDECREF(py_payload);
            Py_DECREF(list);
            return -1;
        }

        PyObject *tup = PyTuple_Pack(2, py_type, py_payload);
        Py_DECREF(py_type);
        Py_DECREF(py_payload);

        if (!tup) {
            Py_DECREF(list);
            return -1;
        }

        if (PyList_Append(list, tup) < 0) {
            Py_DECREF(tup);
            Py_DECREF(list);
            return -1;
        }
        Py_DECREF(tup);

        pos += total;
        avail -= total;
    }

    if (pos > 0) {
        ipc_buf_consume(buf, pos);
    }

    *out_list = list;
    return 0;
}

Py_ssize_t
ipc_encode_frame(uint8_t msg_type, const uint8_t *payload, Py_ssize_t payload_len,
                 uint8_t *out, Py_ssize_t out_cap) {
    uint32_t length = (uint32_t)(1 + payload_len);
    Py_ssize_t total = 4 + (Py_ssize_t)length;

    if (out_cap < total) return -1;

    out[0] = (uint8_t)((length >> 24) & 0xFF);
    out[1] = (uint8_t)((length >> 16) & 0xFF);
    out[2] = (uint8_t)((length >> 8) & 0xFF);
    out[3] = (uint8_t)(length & 0xFF);
    out[4] = msg_type;

    if (payload && payload_len > 0) {
        memcpy(out + 5, payload, (size_t)payload_len);
    }

    return total;
}
