#include "_fastscreen_types.h"
#include "_fastscreen_ansi.h"

int
_append_sgr_color(char *buf, int pos, int is_bg, uint32_t color) {
    int t = color_type(color);
    if (t == 0) {
        pos += sprintf(buf + pos, "%s%d", (pos > 0 ? ";" : ""), is_bg ? 49 : 39);
        return pos;
    }
    if (t == 1) {
        int idx = color_16_idx(color);
        int code;
        if (is_bg) {
            if (idx < 8) code = 40 + idx;
            else code = 100 + (idx - 8);
        } else {
            if (idx < 8) code = 30 + idx;
            else code = 90 + (idx - 8);
        }
        pos += sprintf(buf + pos, "%s%d", (pos > 0 ? ";" : ""), code);
        return pos;
    }
    if (t == 2) {
        int idx = color_256_idx(color);
        pos += sprintf(buf + pos, "%s%d;5;%d", (pos > 0 ? ";" : ""), is_bg ? 48 : 38, idx);
        return pos;
    }
    if (t == 3) {
        int r, g, b;
        color_rgb_val(color, &r, &g, &b);
        pos += sprintf(buf + pos, "%s%d;2;%d;%d;%d", (pos > 0 ? ";" : ""), is_bg ? 48 : 38, r, g, b);
        return pos;
    }
    return pos;
}

int
_append_sgr_flags(char *buf, int pos, uint8_t flags) {
    if (flags & FLAG_BOLD)      pos += sprintf(buf + pos, "%s1",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_DIM)       pos += sprintf(buf + pos, "%s2",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_ITALIC)    pos += sprintf(buf + pos, "%s3",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_UNDERLINE) pos += sprintf(buf + pos, "%s4",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_BLINK)     pos += sprintf(buf + pos, "%s5",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_REVERSE)   pos += sprintf(buf + pos, "%s7",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_STRIKE)    pos += sprintf(buf + pos, "%s9",  (pos > 0 ? ";" : ""));
    if (flags & FLAG_OVERLINE)  pos += sprintf(buf + pos, "%s53", (pos > 0 ? ";" : ""));
    return pos;
}

int
_append_sgr_reset_flags(char *buf, int pos, uint8_t old_flags, uint8_t new_flags) {
    uint8_t cleared = old_flags & ~new_flags;
    if (cleared & FLAG_BOLD)      pos += sprintf(buf + pos, "%s22", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_DIM)       pos += sprintf(buf + pos, "%s22", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_ITALIC)    pos += sprintf(buf + pos, "%s23", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_UNDERLINE) pos += sprintf(buf + pos, "%s24", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_BLINK)     pos += sprintf(buf + pos, "%s25", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_REVERSE)   pos += sprintf(buf + pos, "%s27", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_STRIKE)    pos += sprintf(buf + pos, "%s29", (pos > 0 ? ";" : ""));
    if (cleared & FLAG_OVERLINE)  pos += sprintf(buf + pos, "%s55", (pos > 0 ? ";" : ""));
    return pos;
}

int
_append_sgr_set_flags(char *buf, int pos, uint8_t old_flags, uint8_t new_flags) {
    uint8_t added = new_flags & ~old_flags;
    return _append_sgr_flags(buf, pos, added);
}
