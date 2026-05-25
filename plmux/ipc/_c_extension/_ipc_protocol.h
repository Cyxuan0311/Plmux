#ifndef IPC_PROTOCOL_H
#define IPC_PROTOCOL_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define IPC_HEADER_SIZE 5

#define IPC_MSG_INIT        0x01
#define IPC_MSG_PANE_OUTPUT 0x02
#define IPC_MSG_STATE_UPDATE 0x03
#define IPC_MSG_PANE_CLOSED 0x04
#define IPC_MSG_BELL        0x05

#define IPC_MSG_KEY     0x80
#define IPC_MSG_RESIZE  0x81
#define IPC_MSG_COMMAND 0x82
#define IPC_MSG_MOUSE   0x83
#define IPC_MSG_DETACH  0x84

#define IPC_FRAME_MAX_PAYLOAD (64 * 1024 * 1024)

typedef struct {
    uint8_t  *buf;
    Py_ssize_t buf_len;
    Py_ssize_t buf_cap;
} IPCReadBuffer;

static inline void
ipc_buf_init(IPCReadBuffer *b) {
    b->buf = NULL;
    b->buf_len = 0;
    b->buf_cap = 0;
}

static inline void
ipc_buf_free(IPCReadBuffer *b) {
    if (b->buf) { free(b->buf); b->buf = NULL; }
    b->buf_len = 0;
    b->buf_cap = 0;
}

static inline int
ipc_buf_ensure(IPCReadBuffer *b, Py_ssize_t need) {
    if (b->buf_len + need <= b->buf_cap) return 0;
    Py_ssize_t new_cap = b->buf_cap ? b->buf_cap : 4096;
    while (new_cap < b->buf_len + need) new_cap *= 2;
    uint8_t *new_buf = (uint8_t *)realloc(b->buf, (size_t)new_cap);
    if (!new_buf) return -1;
    b->buf = new_buf;
    b->buf_cap = new_cap;
    return 0;
}

static inline void
ipc_buf_consume(IPCReadBuffer *b, Py_ssize_t n) {
    if (n <= 0) return;
    if (n >= b->buf_len) {
        b->buf_len = 0;
        return;
    }
    memmove(b->buf, b->buf + n, (size_t)(b->buf_len - n));
    b->buf_len -= n;
}

int ipc_parse_frames(IPCReadBuffer *buf, PyObject **out_list);
Py_ssize_t ipc_encode_frame(uint8_t msg_type, const uint8_t *payload, Py_ssize_t payload_len,
                             uint8_t *out, Py_ssize_t out_cap);

#endif
