#ifndef FASTSCREEN_TYPES_H
#define FASTSCREEN_TYPES_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ================================================================
   Color encoding: 32-bit packed
   type 0 = default, 1 = 16-color name index, 2 = 256-color idx, 3 = RGB
   ================================================================ */

#define COLOR_DEFAULT  0x00000000u
#define COLOR_TYPE_MASK 0x03000000u
#define COLOR_TYPE_16   0x01000000u
#define COLOR_TYPE_256  0x02000000u
#define COLOR_TYPE_RGB  0x03000000u
#define COLOR_VAL_MASK  0x00FFFFFFu

static inline uint32_t
color_default(void) { return COLOR_DEFAULT; }

static inline uint32_t
color_16(int idx) { return COLOR_TYPE_16 | (uint32_t)(idx & 0xFF); }

static inline uint32_t
color_256(int idx) { return COLOR_TYPE_256 | (uint32_t)(idx & 0xFF); }

static inline uint32_t
color_rgb(int r, int g, int b) {
    return COLOR_TYPE_RGB | ((uint32_t)(r & 0xFF) << 16)
           | ((uint32_t)(g & 0xFF) << 8) | (uint32_t)(b & 0xFF);
}

static inline int
color_is_default(uint32_t c) { return c == COLOR_DEFAULT; }

static inline int
color_type(uint32_t c) { return (int)((c & COLOR_TYPE_MASK) >> 24); }

static inline int
color_16_idx(uint32_t c) { return (int)(c & 0xFF); }

static inline int
color_256_idx(uint32_t c) { return (int)(c & 0xFF); }

static inline void
color_rgb_val(uint32_t c, int *r, int *g, int *b) {
    *r = (int)((c >> 16) & 0xFF);
    *g = (int)((c >> 8) & 0xFF);
    *b = (int)(c & 0xFF);
}

/* ================================================================
   Cell flags
   ================================================================ */
#define FLAG_BOLD         0x01
#define FLAG_ITALIC       0x02
#define FLAG_UNDERLINE    0x04
#define FLAG_STRIKE       0x08
#define FLAG_REVERSE      0x10
#define FLAG_BLINK        0x20
#define FLAG_DIM          0x40
#define FLAG_OVERLINE     0x80

/* ================================================================
   Cell: 24 bytes, packed
   ================================================================ */
typedef struct {
    uint32_t codepoint;
    uint32_t fg_color;
    uint32_t bg_color;
    uint8_t  flags;
    uint8_t  _pad[3];
    uint8_t  width;
    uint8_t  _pad2[3];
} FastCell;

static inline void
cell_clear(FastCell *c) {
    c->codepoint = 0;
    c->fg_color = COLOR_DEFAULT;
    c->bg_color = COLOR_DEFAULT;
    c->flags = 0;
    c->width = 1;
}

static inline void
cell_erase(FastCell *c, uint32_t fg, uint32_t bg, uint8_t flags) {
    c->codepoint = 0;
    c->fg_color = fg;
    c->bg_color = bg;
    c->flags = flags;
    c->width = 1;
}

static inline int
cell_is_empty(const FastCell *c) {
    return c->codepoint == 0;
}

/* ================================================================
   Screen buffer
   ================================================================ */
typedef struct {
    FastCell *cells;
    int       rows;
    int       cols;
    int       cursor_x;
    int       cursor_y;
    int       cursor_saved_x;
    int       cursor_saved_y;
    int       cursor_visible;
    int       cursor_saved_visible;
    uint32_t  saved_fg;
    uint32_t  saved_bg;
    uint8_t   saved_flags;
    int       scroll_top;
    int       scroll_bottom;
    uint64_t *dirty_bits;
    int       dirty_words;
    uint32_t  cur_fg;
    uint32_t  cur_bg;
    uint8_t   cur_flags;
    uint8_t  *tab_stops;
    int       charset_G[2];
    int       charset_active;
    FastCell *alt_cells;
    int       alt_cursor_x;
    int       alt_cursor_y;
    int       use_alt_screen;
    FastCell *saved_main_cells;
    int       saved_main_cursor_x;
    int       saved_main_cursor_y;
    int       origin_mode;
    int       auto_wrap;
    int       pending_wrap;
    int       mouse_mode;
    int       scroll_count;
    uint8_t  *wrapped;
    uint32_t  cursor_color;     /* 0 = default (reverse video), RGB otherwise */
    uint32_t  default_fg_color; /* 0 = terminal default, RGB if set via OSC 10 */
    uint32_t  default_bg_color; /* 0 = terminal default, RGB if set via OSC 11 */
} FastScreen;

static inline FastCell *
screen_cell(FastScreen *s, int x, int y) {
    if (x < 0 || x >= s->cols || y < 0 || y >= s->rows) return NULL;
    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    return &base[y * s->cols + x];
}

static inline void
screen_mark_dirty(FastScreen *s, int y) {
    if (y < 0 || y >= s->rows) return;
    s->dirty_bits[y / 64] |= ((uint64_t)1 << (y % 64));
}

static inline void
screen_mark_dirty_range(FastScreen *s, int y1, int y2) {
    if (y1 < 0) y1 = 0;
    if (y2 >= s->rows) y2 = s->rows - 1;
    for (int y = y1; y <= y2; y++) screen_mark_dirty(s, y);
}

int  screen_init(FastScreen *s, int cols, int rows);
void screen_free(FastScreen *s);
void screen_scroll_up(FastScreen *s, int n);
void screen_scroll_down(FastScreen *s, int n);
void screen_line_feed(FastScreen *s);
void screen_reverse_index(FastScreen *s);
void screen_put_char(FastScreen *s, uint32_t cp, int width);
void screen_erase_cells(FastScreen *s, int x1, int y1, int x2, int y2);
void screen_erase_display(FastScreen *s, int mode);
void screen_erase_line(FastScreen *s, int mode);
void screen_insert_lines(FastScreen *s, int n);
void screen_delete_lines(FastScreen *s, int n);
void screen_delete_chars(FastScreen *s, int n);
void screen_insert_chars(FastScreen *s, int n);
void screen_erase_chars(FastScreen *s, int n);
void screen_set_scrolling_region(FastScreen *s, int top, int bot);
void screen_switch_alt(FastScreen *s, int enable);
void screen_resize(FastScreen *s, int new_cols, int new_rows);
Py_ssize_t screen_dump_size(FastScreen *s);
int       screen_dump_raw(FastScreen *s, uint8_t *out, Py_ssize_t out_len);
int       screen_restore_raw(FastScreen *s, const uint8_t *data, Py_ssize_t data_len);

/* ================================================================
   UTF-8 Decoder
   ================================================================ */
typedef struct {
    uint32_t codepoint;
    int      remaining;
} Utf8Decoder;

static inline void
utf8_init(Utf8Decoder *d) {
    d->codepoint = 0;
    d->remaining = 0;
}

int utf8_feed(Utf8Decoder *d, uint8_t b, uint32_t *cp);
int char_width(uint32_t cp);

/* ================================================================
   ANSI Parser State Machine
   ================================================================ */
enum {
    ST_GROUND = 0,
    ST_ESC,
    ST_CSI_ENTRY,
    ST_CSI_PARAM,
    ST_CSI_INTER,
    ST_CSI_IGNORE,
    ST_OSC_STRING,
    ST_DCS_ENTRY,
    ST_DCS_PARAM,
    ST_DCS_DATA,
    ST_DCS_IGNORE,
    ST_SOS_PM_APC,
};

#define MAX_PARAMS 32
#define OSC_BUF_SIZE 256

typedef struct {
    FastScreen *screen;
    int state;
    Utf8Decoder utf8;
    int params[MAX_PARAMS];
    int param_count;
    int param_idx;
    int param_has_val;
    int private_marker;
    int final_byte;
    char osc_buf[OSC_BUF_SIZE];
    int osc_len;
    char dcs_collect[8];
    int dcs_collect_len;
    int charset_designate;
    int decaln_pending;
} FastParser;

void parser_init(FastParser *p, FastScreen *screen);
void parser_reset_params(FastParser *p);
int  parser_get_param(FastParser *p, int idx, int defval);
void parser_dispatch_csi(FastParser *p, int cmd);
void parser_handle_esc(FastParser *p, int c);
int  parser_dec_special(int cp);
void parser_feed_byte(FastParser *p, uint8_t b);
void parser_feed(FastParser *p, const uint8_t *data, Py_ssize_t len);

/* ================================================================
   Python binding helpers
   ================================================================ */
PyObject *cell_to_dict(FastCell *c);

#endif /* FASTSCREEN_TYPES_H */