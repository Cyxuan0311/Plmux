#include "_ws_kernel.h"

int
ws_parse_frames(WSReadBuffer *buf, WSFrame **out_frames, int *out_count) {
    *out_frames = NULL;
    *out_count = 0;

    int cap = 8;
    WSFrame *frames = (WSFrame *)malloc((size_t)cap * sizeof(WSFrame));
    if (!frames) return -1;

    int count = 0;
    Py_ssize_t avail = buf->buf_len - buf->pos;

    while (avail >= 2) {
        uint8_t *p = buf->buf + buf->pos;

        int fin = (p[0] >> 7) & 1;
        int opcode = p[0] & 0x0F;
        int masked = (p[1] >> 7) & 1;
        uint64_t length = p[1] & 0x7F;

        Py_ssize_t header_len = 2;

        if (length == 126) {
            if (avail < 4) break;
            length = ((uint64_t)p[2] << 8) | p[3];
            header_len = 4;
        } else if (length == 127) {
            if (avail < 10) break;
            length = 0;
            for (int i = 0; i < 8; i++) {
                length = (length << 8) | p[2 + i];
            }
            header_len = 10;
        }

        if (masked) header_len += 4;

        if (length > WS_FRAME_MAX_PAYLOAD) {
            free(frames);
            return -2;
        }

        if (avail < header_len + (Py_ssize_t)length) break;

        if (count >= cap) {
            cap *= 2;
            WSFrame *new_frames = (WSFrame *)realloc(frames, (size_t)cap * sizeof(WSFrame));
            if (!new_frames) { free(frames); return -1; }
            frames = new_frames;
        }

        WSFrame *f = &frames[count];
        f->opcode = opcode;
        f->fin = fin;
        f->masked = masked;
        f->payload_len = (Py_ssize_t)length;

        Py_ssize_t payload_offset = header_len;
        if (masked) {
            memcpy(f->mask_key, p + header_len - 4, 4);
        }

        if (length > 0) {
            f->payload = (uint8_t *)malloc((size_t)length);
            if (!f->payload) {
                for (int i = 0; i < count; i++) free(frames[i].payload);
                free(frames);
                return -1;
            }
            memcpy(f->payload, p + payload_offset, (size_t)length);
            if (masked) {
                for (Py_ssize_t i = 0; i < (Py_ssize_t)length; i++) {
                    f->payload[i] ^= f->mask_key[i % 4];
                }
            }
        } else {
            f->payload = NULL;
        }

        count++;
        buf->pos += payload_offset + (Py_ssize_t)length;
        avail = buf->buf_len - buf->pos;
    }

    ws_buf_compact(buf);

    *out_frames = frames;
    *out_count = count;
    return 0;
}

void
ws_free_frames(WSFrame *frames, int count) {
    if (!frames) return;
    for (int i = 0; i < count; i++) {
        if (frames[i].payload) free(frames[i].payload);
    }
    free(frames);
}

Py_ssize_t
ws_encode_frame(int opcode, const uint8_t *payload, Py_ssize_t payload_len,
                int mask, uint8_t *out, Py_ssize_t out_cap) {
    Py_ssize_t header_len = 2;

    if (payload_len < 126) {
        header_len = 2;
    } else if (payload_len < 65536) {
        header_len = 4;
    } else {
        header_len = 10;
    }

    if (mask) header_len += 4;

    Py_ssize_t total = header_len + payload_len;
    if (out_cap < total) return -1;

    Py_ssize_t pos = 0;
    out[pos++] = (uint8_t)(0x80 | opcode);

    if (payload_len < 126) {
        out[pos++] = (uint8_t)(payload_len | (mask ? 0x80 : 0));
    } else if (payload_len < 65536) {
        out[pos++] = (uint8_t)(126 | (mask ? 0x80 : 0));
        out[pos++] = (uint8_t)((payload_len >> 8) & 0xFF);
        out[pos++] = (uint8_t)(payload_len & 0xFF);
    } else {
        out[pos++] = (uint8_t)(127 | (mask ? 0x80 : 0));
        for (int i = 7; i >= 0; i--) {
            out[pos++] = (uint8_t)((payload_len >> (i * 8)) & 0xFF);
        }
    }

    if (mask) {
        uint8_t mkey[4] = {0x37, 0xFA, 0x21, 0x3D};
        memcpy(out + pos, mkey, 4);
        pos += 4;
        if (payload && payload_len > 0) {
            for (Py_ssize_t i = 0; i < payload_len; i++) {
                out[pos + i] = payload[i] ^ mkey[i % 4];
            }
        }
        pos += payload_len;
    } else {
        if (payload && payload_len > 0) {
            memcpy(out + pos, payload, (size_t)payload_len);
        }
        pos += payload_len;
    }

    return pos;
}
