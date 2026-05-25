#include "_fastscreen_types.h"

int
screen_init(FastScreen *s, int cols, int rows) {
    memset(s, 0, sizeof(*s));
    s->cols = cols;
    s->rows = rows;
    s->cells = (FastCell *)calloc((size_t)(rows * cols), sizeof(FastCell));
    if (!s->cells) return -1;
    for (int i = 0; i < rows * cols; i++) cell_clear(&s->cells[i]);

    s->dirty_words = (rows + 63) / 64;
    s->dirty_bits = (uint64_t *)calloc((size_t)s->dirty_words, sizeof(uint64_t));
    if (!s->dirty_bits) { free(s->cells); return -1; }

    s->tab_stops = (uint8_t *)calloc((size_t)cols, 1);
    if (!s->tab_stops) { free(s->cells); free(s->dirty_bits); return -1; }
    for (int x = 0; x < cols; x++) s->tab_stops[x] = (x % 8 == 0) ? 1 : 0;

    s->cursor_visible = 1;
    s->cursor_saved_visible = 1;
    s->scroll_bottom = rows - 1;
    s->cur_fg = COLOR_DEFAULT;
    s->cur_bg = COLOR_DEFAULT;
    s->saved_fg = COLOR_DEFAULT;
    s->saved_bg = COLOR_DEFAULT;
    s->auto_wrap = 1;
    return 0;
}

void
screen_free(FastScreen *s) {
    free(s->cells);
    free(s->dirty_bits);
    free(s->tab_stops);
    free(s->alt_cells);
    free(s->saved_main_cells);
}

void
screen_scroll_up(FastScreen *s, int n) {
    int top = s->scroll_top;
    int bot = s->scroll_bottom;
    int region_h = bot - top + 1;
    if (n > region_h) n = region_h;
    if (n <= 0) return;

    if (top == 0 && !s->use_alt_screen) {
        s->scroll_count += n;
    }

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    int stride = s->cols;
    for (int y = top; y <= bot - n; y++) {
        memmove(&base[y * stride], &base[(y + n) * stride],
                (size_t)stride * sizeof(FastCell));
    }
    for (int y = bot - n + 1; y <= bot; y++) {
        for (int x = 0; x < s->cols; x++) {
            cell_erase(&base[y * stride + x], s->cur_fg, s->cur_bg, s->cur_flags);
        }
    }
    screen_mark_dirty_range(s, top, bot);
}

void
screen_scroll_down(FastScreen *s, int n) {
    int top = s->scroll_top;
    int bot = s->scroll_bottom;
    int region_h = bot - top + 1;
    if (n > region_h) n = region_h;
    if (n <= 0) return;

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    int stride = s->cols;
    for (int y = bot; y >= top + n; y--) {
        memcpy(&base[y * stride], &base[(y - n) * stride],
               (size_t)stride * sizeof(FastCell));
    }
    for (int y = top; y < top + n; y++) {
        for (int x = 0; x < s->cols; x++) {
            cell_erase(&base[y * stride + x], s->cur_fg, s->cur_bg, s->cur_flags);
        }
    }
    screen_mark_dirty_range(s, top, bot);
}

void
screen_line_feed(FastScreen *s) {
    if (s->cursor_y == s->scroll_bottom) {
        screen_scroll_up(s, 1);
    } else {
        s->cursor_y++;
    }
}

void
screen_reverse_index(FastScreen *s) {
    s->pending_wrap = 0;
    if (s->cursor_y == s->scroll_top) {
        screen_scroll_down(s, 1);
    } else {
        s->cursor_y--;
    }
}

void
screen_put_char(FastScreen *s, uint32_t cp, int width) {
    int wrap_was_pending = s->pending_wrap;
    if (s->pending_wrap) {
        s->cursor_x = 0;
        screen_line_feed(s);
        s->pending_wrap = 0;
    }
    int auto_wrapped = 0;
    if (s->cursor_x >= s->cols) {
        if (s->auto_wrap) {
            s->cursor_x = 0;
            screen_line_feed(s);
            auto_wrapped = 1;
        } else {
            s->cursor_x = s->cols - 1;
        }
    }
    FastCell *c = screen_cell(s, s->cursor_x, s->cursor_y);
    if (c) {
        if (c->width == 0 && s->cursor_x > 0) {
            FastCell *prev = screen_cell(s, s->cursor_x - 1, s->cursor_y);
            if (prev && prev->width > 1) {
                cell_erase(prev, s->cur_fg, s->cur_bg, s->cur_flags);
            }
        }
        if (c->width > 1 && s->cursor_x + 1 < s->cols) {
            FastCell *next = screen_cell(s, s->cursor_x + 1, s->cursor_y);
            if (next && next->width == 0) {
                cell_erase(next, s->cur_fg, s->cur_bg, s->cur_flags);
            }
        }
        c->codepoint = cp;
        c->fg_color = s->cur_fg;
        c->bg_color = s->cur_bg;
        c->flags = s->cur_flags;
        c->width = (uint8_t)width;
    }
    if (width > 1 && s->cursor_x + 1 < s->cols) {
        FastCell *next = screen_cell(s, s->cursor_x + 1, s->cursor_y);
        if (next) {
            next->codepoint = 0;
            next->fg_color = s->cur_fg;
            next->bg_color = s->cur_bg;
            next->flags = s->cur_flags;
            next->width = 0;
        }
    }
    screen_mark_dirty(s, s->cursor_y);
    s->cursor_x += width;
    if (s->cursor_x >= s->cols) {
        s->pending_wrap = 1;
    }
}

void
screen_erase_cells(FastScreen *s, int x1, int y1, int x2, int y2) {
    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    int stride = s->cols;
    uint32_t fg = s->cur_fg;
    uint32_t bg = s->cur_bg;
    uint8_t flags = s->cur_flags;
    for (int y = y1; y <= y2; y++) {
        for (int x = x1; x <= x2; x++) {
            FastCell *c = &base[y * stride + x];
            if (c->width > 1 && x + 1 < s->cols) {
                FastCell *next = &base[y * stride + x + 1];
                if (next->width == 0) {
                    cell_erase(next, fg, bg, flags);
                }
            }
            if (c->width == 0 && x > 0) {
                FastCell *prev = &base[y * stride + x - 1];
                if (prev->width > 1) {
                    cell_erase(prev, fg, bg, flags);
                }
            }
            cell_erase(c, fg, bg, flags);
        }
        screen_mark_dirty(s, y);
    }
}

void
screen_erase_display(FastScreen *s, int mode) {
    int cx = s->cursor_x, cy = s->cursor_y;
    switch (mode) {
    case 0:
        screen_erase_cells(s, cx, cy, s->cols - 1, cy);
        if (cy + 1 < s->rows)
            screen_erase_cells(s, 0, cy + 1, s->cols - 1, s->rows - 1);
        break;
    case 1:
        screen_erase_cells(s, 0, 0, s->cols - 1, cy - 1);
        screen_erase_cells(s, 0, cy, cx, cy);
        break;
    case 2:
    case 3:
        screen_erase_cells(s, 0, 0, s->cols - 1, s->rows - 1);
        break;
    }
}

void
screen_erase_line(FastScreen *s, int mode) {
    int cx = s->cursor_x, cy = s->cursor_y;
    switch (mode) {
    case 0: screen_erase_cells(s, cx, cy, s->cols - 1, cy); break;
    case 1: screen_erase_cells(s, 0, cy, cx, cy); break;
    case 2: screen_erase_cells(s, 0, cy, s->cols - 1, cy); break;
    }
}

void
screen_insert_lines(FastScreen *s, int n) {
    int top = s->cursor_y;
    int bot = s->scroll_bottom;
    if (top > bot) return;
    int region_h = bot - top + 1;
    if (n > region_h) n = region_h;
    if (n <= 0) return;

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    int stride = s->cols;
    for (int y = bot; y >= top + n; y--) {
        memcpy(&base[y * stride], &base[(y - n) * stride],
               (size_t)stride * sizeof(FastCell));
    }
    for (int y = top; y < top + n; y++) {
        for (int x = 0; x < s->cols; x++) {
            cell_erase(&base[y * stride + x], s->cur_fg, s->cur_bg, s->cur_flags);
        }
    }
    screen_mark_dirty_range(s, top, bot);
}

void
screen_delete_lines(FastScreen *s, int n) {
    int top = s->cursor_y;
    int bot = s->scroll_bottom;
    if (top > bot) return;
    int region_h = bot - top + 1;
    if (n > region_h) n = region_h;
    if (n <= 0) return;

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    int stride = s->cols;
    for (int y = top; y <= bot - n; y++) {
        memcpy(&base[y * stride], &base[(y + n) * stride],
               (size_t)stride * sizeof(FastCell));
    }
    for (int y = bot - n + 1; y <= bot; y++) {
        for (int x = 0; x < s->cols; x++) {
            cell_erase(&base[y * stride + x], s->cur_fg, s->cur_bg, s->cur_flags);
        }
    }
    screen_mark_dirty_range(s, top, bot);
}

void
screen_delete_chars(FastScreen *s, int n) {
    int y = s->cursor_y;
    if (n > s->cols - s->cursor_x) n = s->cols - s->cursor_x;
    if (n <= 0) return;
    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = &base[y * s->cols];
    if (s->cursor_x > 0 && row[s->cursor_x].width == 0) {
        cell_erase(&row[s->cursor_x - 1], s->cur_fg, s->cur_bg, s->cur_flags);
    }
    int move_count = s->cols - s->cursor_x - n;
    if (move_count > 0) {
        memmove(&row[s->cursor_x], &row[s->cursor_x + n],
                (size_t)move_count * sizeof(FastCell));
    }
    for (int x = s->cols - n; x < s->cols; x++) {
        cell_erase(&row[x], s->cur_fg, s->cur_bg, s->cur_flags);
    }
    screen_mark_dirty(s, y);
}

void
screen_insert_chars(FastScreen *s, int n) {
    int y = s->cursor_y;
    if (n > s->cols - s->cursor_x) n = s->cols - s->cursor_x;
    if (n <= 0) return;
    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = &base[y * s->cols];
    if (s->cursor_x > 0 && row[s->cursor_x].width == 0) {
        cell_erase(&row[s->cursor_x - 1], s->cur_fg, s->cur_bg, s->cur_flags);
    }
    int move_count = s->cols - s->cursor_x - n;
    if (move_count > 0) {
        memmove(&row[s->cursor_x + n], &row[s->cursor_x],
                (size_t)move_count * sizeof(FastCell));
    }
    for (int x = s->cursor_x; x < s->cursor_x + n; x++) {
        cell_erase(&row[x], s->cur_fg, s->cur_bg, s->cur_flags);
    }
    screen_mark_dirty(s, y);
}

void
screen_erase_chars(FastScreen *s, int n) {
    int y = s->cursor_y;
    if (n > s->cols - s->cursor_x) n = s->cols - s->cursor_x;
    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    FastCell *row = &base[y * s->cols];
    if (s->cursor_x > 0 && row[s->cursor_x].width == 0) {
        cell_erase(&row[s->cursor_x - 1], s->cur_fg, s->cur_bg, s->cur_flags);
    }
    for (int x = s->cursor_x; x < s->cursor_x + n; x++) {
        if (row[x].width > 1 && x + 1 < s->cols && row[x + 1].width == 0) {
            cell_erase(&row[x + 1], s->cur_fg, s->cur_bg, s->cur_flags);
        }
        cell_erase(&row[x], s->cur_fg, s->cur_bg, s->cur_flags);
    }
    screen_mark_dirty(s, y);
}

void
screen_set_scrolling_region(FastScreen *s, int top, int bot) {
    if (top < 0) top = 0;
    if (bot >= s->rows) bot = s->rows - 1;
    if (top > bot) return;
    s->scroll_top = top;
    s->scroll_bottom = bot;
    s->cursor_x = 0;
    s->cursor_y = 0;
}

void
screen_switch_alt(FastScreen *s, int enable) {
    if (enable == s->use_alt_screen) return;
    if (enable) {
        /* Save main screen state before switching to alt */
        if (!s->saved_main_cells) {
            size_t sz = (size_t)(s->rows * s->cols) * sizeof(FastCell);
            s->saved_main_cells = (FastCell *)malloc(sz);
            if (!s->saved_main_cells) return;
        }
        memcpy(s->saved_main_cells, s->cells,
               (size_t)(s->rows * s->cols) * sizeof(FastCell));
        s->saved_main_cursor_x = s->cursor_x;
        s->saved_main_cursor_y = s->cursor_y;

        /* Initialize alt screen as blank */
        if (!s->alt_cells) {
            size_t sz = (size_t)(s->rows * s->cols) * sizeof(FastCell);
            s->alt_cells = (FastCell *)malloc(sz);
            if (!s->alt_cells) return;
        }
        for (int i = 0; i < s->rows * s->cols; i++) cell_clear(&s->alt_cells[i]);
        s->cursor_x = 0;
        s->cursor_y = 0;
        s->use_alt_screen = 1;
        screen_mark_dirty_range(s, 0, s->rows - 1);
    } else {
        /* Restore main screen from saved state */
        if (s->saved_main_cells) {
            memcpy(s->cells, s->saved_main_cells,
                   (size_t)(s->rows * s->cols) * sizeof(FastCell));
            s->cursor_x = s->saved_main_cursor_x;
            s->cursor_y = s->saved_main_cursor_y;
        }
        s->use_alt_screen = 0;
        screen_mark_dirty_range(s, 0, s->rows - 1);
    }
}

void
screen_resize(FastScreen *s, int new_cols, int new_rows) {
    if (new_cols <= 0 || new_rows <= 0) return;
    int old_cols = s->cols, old_rows = s->rows;

    FastCell *new_cells = (FastCell *)calloc((size_t)(new_rows * new_cols), sizeof(FastCell));
    if (!new_cells) return;
    for (int i = 0; i < new_rows * new_cols; i++) cell_clear(&new_cells[i]);

    int copy_rows = old_rows < new_rows ? old_rows : new_rows;
    int copy_cols = old_cols < new_cols ? old_cols : new_cols;
    for (int y = 0; y < copy_rows; y++) {
        memcpy(&new_cells[y * new_cols], &s->cells[y * old_cols],
               (size_t)copy_cols * sizeof(FastCell));
    }

    free(s->cells);
    s->cells = new_cells;
    s->cols = new_cols;
    s->rows = new_rows;

    if (s->cursor_x >= new_cols) s->cursor_x = new_cols - 1;
    if (s->cursor_y >= new_rows) s->cursor_y = new_rows - 1;
    s->scroll_bottom = new_rows - 1;

    free(s->dirty_bits);
    s->dirty_words = (new_rows + 63) / 64;
    s->dirty_bits = (uint64_t *)calloc((size_t)s->dirty_words, sizeof(uint64_t));

    free(s->tab_stops);
    s->tab_stops = (uint8_t *)calloc((size_t)new_cols, 1);
    for (int x = 0; x < new_cols; x++) s->tab_stops[x] = (x % 8 == 0) ? 1 : 0;

    if (s->alt_cells) {
        free(s->alt_cells);
        s->alt_cells = NULL;
    }
    if (s->saved_main_cells) {
        free(s->saved_main_cells);
        s->saved_main_cells = NULL;
    }
    s->use_alt_screen = 0;
    screen_mark_dirty_range(s, 0, new_rows - 1);
}

/* ================================================================
   Fast buffer dump / restore (compact binary serialization)
   Binary format:
     [uint16 cols][uint16 rows][uint16 cursor_x][uint16 cursor_y]
     [FastCell[rows * cols]]   (sizeof(FastCell) bytes each)
   ================================================================ */

Py_ssize_t
screen_dump_size(FastScreen *s) {
    return (Py_ssize_t)(8 + (size_t)s->rows * (size_t)s->cols * sizeof(FastCell));
}

int
screen_dump_raw(FastScreen *s, uint8_t *out, Py_ssize_t out_len) {
    Py_ssize_t expected = screen_dump_size(s);
    if (out_len < expected) return -1;

    uint16_t cols16 = (uint16_t)s->cols;
    uint16_t rows16 = (uint16_t)s->rows;
    uint16_t cx16   = (uint16_t)s->cursor_x;
    uint16_t cy16   = (uint16_t)s->cursor_y;

    memcpy(out,     &cols16, 2); out += 2;
    memcpy(out,     &rows16, 2); out += 2;
    memcpy(out,     &cx16,   2); out += 2;
    memcpy(out,     &cy16,   2); out += 2;

    FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
    size_t cell_bytes = (size_t)s->rows * (size_t)s->cols * sizeof(FastCell);
    memcpy(out, base, cell_bytes);

    return 0;
}

int
screen_restore_raw(FastScreen *s, const uint8_t *data, Py_ssize_t data_len) {
    if (data_len < 8) return -1;

    uint16_t cols16, rows16, cx16, cy16;
    memcpy(&cols16, data,     2); data += 2;
    memcpy(&rows16, data,     2); data += 2;
    memcpy(&cx16,   data,     2); data += 2;
    memcpy(&cy16,   data,     2); data += 2;

    int new_cols = (int)cols16;
    int new_rows = (int)rows16;

    Py_ssize_t cell_bytes = (Py_ssize_t)new_rows * (Py_ssize_t)new_cols * (Py_ssize_t)sizeof(FastCell);
    if (data_len - 8 < cell_bytes) return -2;

    screen_free(s);
    if (screen_init(s, new_cols, new_rows) < 0) return -3;

    FastCell *base = s->cells;
    memcpy(base, data, (size_t)cell_bytes);

    s->cursor_x = (int)cx16;
    s->cursor_y = (int)cy16;
    if (s->cursor_x >= s->cols) s->cursor_x = s->cols - 1;
    if (s->cursor_y >= s->rows) s->cursor_y = s->rows - 1;

    for (int y = 0; y < s->rows; y++) {
        uint8_t has_content = 0;
        FastCell *row = &base[y * s->cols];
        for (int x = 0; x < s->cols; x++) {
            if (row[x].codepoint != 0 && row[x].codepoint != 0x20) {
                has_content = 1;
                break;
            }
        }
        if (has_content) {
            screen_mark_dirty(s, y);
        }
    }

    return 0;
}