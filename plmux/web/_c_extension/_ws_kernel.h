#ifndef WS_KERNEL_H
#define WS_KERNEL_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WS_OPCODE_TEXT   0x1
#define WS_OPCODE_BINARY 0x2
#define WS_OPCODE_CLOSE  0x8
#define WS_OPCODE_PING   0x9
#define WS_OPCODE_PONG   0xA

#define WS_FRAME_MAX_PAYLOAD (16 * 1024 * 1024)

typedef struct {
    int       opcode;
    uint8_t  *payload;
    Py_ssize_t payload_len;
    int       fin;
    int       masked;
    uint8_t   mask_key[4];
} WSFrame;

typedef struct {
    uint8_t  *buf;
    Py_ssize_t buf_len;
    Py_ssize_t buf_cap;
    Py_ssize_t pos;
} WSReadBuffer;

static inline void
ws_buf_init(WSReadBuffer *b) {
    b->buf = NULL;
    b->buf_len = 0;
    b->buf_cap = 0;
    b->pos = 0;
}

static inline void
ws_buf_free(WSReadBuffer *b) {
    if (b->buf) { free(b->buf); b->buf = NULL; }
    b->buf_len = 0;
    b->buf_cap = 0;
    b->pos = 0;
}

static inline int
ws_buf_ensure(WSReadBuffer *b, Py_ssize_t need) {
    if (b->pos + need <= b->buf_cap) return 0;
    Py_ssize_t new_cap = b->buf_cap ? b->buf_cap : 4096;
    while (new_cap < b->pos + need) new_cap *= 2;
    uint8_t *new_buf = (uint8_t *)realloc(b->buf, (size_t)new_cap);
    if (!new_buf) return -1;
    b->buf = new_buf;
    b->buf_cap = new_cap;
    return 0;
}

static inline void
ws_buf_compact(WSReadBuffer *b) {
    if (b->pos > 0 && b->pos < b->buf_len) {
        memmove(b->buf, b->buf + b->pos, (size_t)(b->buf_len - b->pos));
        b->buf_len -= b->pos;
        b->pos = 0;
    } else if (b->pos >= b->buf_len) {
        b->buf_len = 0;
        b->pos = 0;
    }
}

int  ws_parse_frames(WSReadBuffer *buf, WSFrame **out_frames, int *out_count);
void ws_free_frames(WSFrame *frames, int count);

Py_ssize_t ws_encode_frame(int opcode, const uint8_t *payload, Py_ssize_t payload_len,
                            int mask, uint8_t *out, Py_ssize_t out_cap);

Py_ssize_t ws_handshake_response(const char *key, Py_ssize_t key_len,
                                  uint8_t *out, Py_ssize_t out_cap);

#endif
