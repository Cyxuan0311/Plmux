#include "_fastscreen_types.h"
#include "_fastscreen_debug.h"

FsPerfStats _feed_stats;
FsPerfStats _csi_stats;
FsPerfStats _ground_stats;
FsPerfStats _esc_stats;
FsPerfStats _putchar_stats;
static int _stats_inited = 0;

static void
_ensure_stats(void) {
    if (!_stats_inited) {
        fs_stats_init(&_feed_stats, "cparser.feed");
        fs_stats_init(&_csi_stats, "cparser.csi_dispatch");
        fs_stats_init(&_ground_stats, "cparser.ground");
        fs_stats_init(&_esc_stats, "cparser.esc");
        fs_stats_init(&_putchar_stats, "cparser.put_char");
        _stats_inited = 1;
    }
}

int
utf8_feed(Utf8Decoder *d, uint8_t b, uint32_t *cp) {
    if (d->remaining == 0) {
        if (b < 0x80) {
            *cp = (uint32_t)b;
            return 1;
        }
        if ((b & 0xE0) == 0xC0) {
            d->codepoint = b & 0x1F;
            d->remaining = 1;
        } else if ((b & 0xF0) == 0xE0) {
            d->codepoint = b & 0x0F;
            d->remaining = 2;
        } else if ((b & 0xF8) == 0xF0) {
            d->codepoint = b & 0x07;
            d->remaining = 3;
        } else {
            return -1;
        }
        return 0;
    }
    if ((b & 0xC0) != 0x80) {
        d->remaining = 0;
        return -1;
    }
    d->codepoint = (d->codepoint << 6) | (b & 0x3F);
    d->remaining--;
    if (d->remaining == 0) {
        *cp = d->codepoint;
        return 1;
    }
    return 0;
}

int
char_width(uint32_t cp) {
    if (cp < 0x80) return 1;
    if (cp < 0x300) return 1;
    if (cp >= 0x1100 && cp <= 0x115F) return 2;
    if (cp >= 0x2329 && cp <= 0x232A) return 2;
    if (cp >= 0x2E80 && cp <= 0x303E) return 2;
    if (cp >= 0x3040 && cp <= 0x33BF) return 2;
    if (cp >= 0x3400 && cp <= 0x4DBF) return 2;
    if (cp >= 0x4E00 && cp <= 0xA4CF) return 2;
    if (cp >= 0xA960 && cp <= 0xA97F) return 2;
    if (cp >= 0xAC00 && cp <= 0xD7AF) return 2;
    if (cp >= 0xF900 && cp <= 0xFAFF) return 2;
    if (cp >= 0xFE10 && cp <= 0xFE1F) return 2;
    if (cp >= 0xFE30 && cp <= 0xFE6F) return 2;
    if (cp >= 0xFF01 && cp <= 0xFF60) return 2;
    if (cp >= 0xFFE0 && cp <= 0xFFE6) return 2;
    if (cp >= 0x1F000 && cp <= 0x1F9FF) return 2;
    if (cp >= 0x20000 && cp <= 0x2FFFD) return 2;
    if (cp >= 0x30000 && cp <= 0x3FFFD) return 2;
    return 1;
}

void
parser_init(FastParser *p, FastScreen *screen) {
    memset(p, 0, sizeof(*p));
    p->screen = screen;
    p->state = ST_GROUND;
    p->charset_designate = -1;
    p->decaln_pending = 0;
    utf8_init(&p->utf8);
}

void
parser_reset_params(FastParser *p) {
    memset(p->params, 0, sizeof(p->params));
    p->param_count = 0;
    p->param_idx = 0;
    p->param_has_val = 0;
    p->private_marker = 0;
    p->final_byte = 0;
}

int
parser_get_param(FastParser *p, int idx, int defval) {
    if (idx < p->param_count) {
        int v = p->params[idx];
        return v > 0 ? v : defval;
    }
    return defval;
}

void
parser_dispatch_csi(FastParser *p, int cmd) {
    FastScreen *s = p->screen;
    int pm = p->private_marker;

    FsPerfTimer _csi_t;
    if (fs_debug_enabled()) fs_timer_start(&_csi_t);

    switch (cmd) {
    case 'A': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_y -= n;
        if (s->cursor_y < 0) s->cursor_y = 0;
        break;
    }
    case 'B': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_y += n;
        if (s->cursor_y >= s->rows) s->cursor_y = s->rows - 1;
        break;
    }
    case 'C': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_x += n;
        if (s->cursor_x >= s->cols) s->cursor_x = s->cols - 1;
        break;
    }
    case 'D': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_x -= n;
        if (s->cursor_x < 0) s->cursor_x = 0;
        break;
    }
    case 'E': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_x = 0;
        s->cursor_y += n;
        if (s->cursor_y >= s->rows) s->cursor_y = s->rows - 1;
        break;
    }
    case 'F': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_x = 0;
        s->cursor_y -= n;
        if (s->cursor_y < 0) s->cursor_y = 0;
        break;
    }
    case 'G': {
        int n = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_x = n - 1;
        if (s->cursor_x < 0) s->cursor_x = 0;
        if (s->cursor_x >= s->cols) s->cursor_x = s->cols - 1;
        break;
    }
    case 'H': case 'f': {
        int row = parser_get_param(p, 0, 1);
        int col = parser_get_param(p, 1, 1);
        s->pending_wrap = 0;
        if (s->origin_mode) {
            s->cursor_y = s->scroll_top + row - 1;
        } else {
            s->cursor_y = row - 1;
        }
        s->cursor_x = col - 1;
        if (s->cursor_y < 0) s->cursor_y = 0;
        if (s->cursor_y >= s->rows) s->cursor_y = s->rows - 1;
        if (s->cursor_x < 0) s->cursor_x = 0;
        if (s->cursor_x >= s->cols) s->cursor_x = s->cols - 1;
        break;
    }
    case 'J': {
        int mode = parser_get_param(p, 0, 0);
        if (pm == '?') mode = parser_get_param(p, 0, 0);
        screen_erase_display(s, mode);
        break;
    }
    case 'K': {
        int mode = parser_get_param(p, 0, 0);
        if (pm == '?') mode = parser_get_param(p, 0, 0);
        screen_erase_line(s, mode);
        break;
    }
    case 'L': {
        int n = parser_get_param(p, 0, 1);
        screen_insert_lines(s, n);
        break;
    }
    case 'M': {
        int n = parser_get_param(p, 0, 1);
        screen_delete_lines(s, n);
        break;
    }
    case 'P': {
        int n = parser_get_param(p, 0, 1);
        screen_delete_chars(s, n);
        break;
    }
    case '@': {
        int n = parser_get_param(p, 0, 1);
        screen_insert_chars(s, n);
        break;
    }
    case 'X': {
        int n = parser_get_param(p, 0, 1);
        screen_erase_chars(s, n);
        break;
    }
    case 'S': {
        int n = parser_get_param(p, 0, 1);
        screen_scroll_up(s, n);
        break;
    }
    case 'T': {
        if (pm == 0 && p->param_count > 0 && p->params[0] > 0) {
            int n = parser_get_param(p, 0, 1);
            screen_scroll_down(s, n);
        }
        break;
    }
    case 'b': {
        if (p->param_count > 0 && p->params[0] > 0) {
            int n = p->params[0];
            int px = s->cursor_x - 1;
            if (px < 0) px = 0;
            FastCell *prev = screen_cell(s, px, s->cursor_y);
            if (prev && !cell_is_empty(prev)) {
                for (int i = 0; i < n; i++) {
                    screen_put_char(s, prev->codepoint, prev->width);
                }
            }
        }
        break;
    }
    case 'c': {
        if (parser_get_param(p, 0, 0) == 0) {
            /* VT102/ANSI response: \033[?6c - acknowledged */
        }
        break;
    }
    case 'd': {
        int row = parser_get_param(p, 0, 1);
        s->pending_wrap = 0;
        s->cursor_y = row - 1;
        if (s->cursor_y < 0) s->cursor_y = 0;
        if (s->cursor_y >= s->rows) s->cursor_y = s->rows - 1;
        break;
    }
    case 'm': {
        if (p->param_count == 0) {
            s->cur_fg = COLOR_DEFAULT;
            s->cur_bg = COLOR_DEFAULT;
            s->cur_flags = 0;
        }
        for (int i = 0; i < p->param_count; i++) {
            int v = p->params[i];
            if (v == 0) {
                s->cur_fg = COLOR_DEFAULT;
                s->cur_bg = COLOR_DEFAULT;
                s->cur_flags = 0;
            } else if (v == 1) { s->cur_flags |= FLAG_BOLD; s->cur_flags &= ~FLAG_DIM; }
            else if (v == 2) { s->cur_flags |= FLAG_DIM; s->cur_flags &= ~FLAG_BOLD; }
            else if (v == 3) s->cur_flags |= FLAG_ITALIC;
            else if (v == 4) s->cur_flags |= FLAG_UNDERLINE;
            else if (v == 5) s->cur_flags |= FLAG_BLINK;
            else if (v == 7) s->cur_flags |= FLAG_REVERSE;
            else if (v == 8) { /* concealed */ }
            else if (v == 9) s->cur_flags |= FLAG_STRIKE;
            else if (v == 21) { s->cur_flags |= FLAG_UNDERLINE; }
            else if (v == 22) { s->cur_flags &= ~(FLAG_BOLD | FLAG_DIM); }
            else if (v == 23) s->cur_flags &= ~FLAG_ITALIC;
            else if (v == 24) s->cur_flags &= ~FLAG_UNDERLINE;
            else if (v == 25) s->cur_flags &= ~FLAG_BLINK;
            else if (v == 27) s->cur_flags &= ~FLAG_REVERSE;
            else if (v == 28) { /* concealed off */ }
            else if (v == 29) s->cur_flags &= ~FLAG_STRIKE;
            else if (v == 53) s->cur_flags |= FLAG_OVERLINE;
            else if (v == 55) s->cur_flags &= ~FLAG_OVERLINE;
            else if (v >= 30 && v <= 37) s->cur_fg = color_16(v - 30);
            else if (v == 38) {
                if (i + 2 < p->param_count && p->params[i + 1] == 5) {
                    s->cur_fg = color_256(p->params[i + 2]);
                    i += 2;
                } else if (i + 4 < p->param_count && p->params[i + 1] == 2) {
                    s->cur_fg = color_rgb(p->params[i + 2], p->params[i + 3], p->params[i + 4]);
                    i += 4;
                }
            } else if (v == 39) s->cur_fg = COLOR_DEFAULT;
            else if (v >= 40 && v <= 47) s->cur_bg = color_16(v - 40);
            else if (v == 48) {
                if (i + 2 < p->param_count && p->params[i + 1] == 5) {
                    s->cur_bg = color_256(p->params[i + 2]);
                    i += 2;
                } else if (i + 4 < p->param_count && p->params[i + 1] == 2) {
                    s->cur_bg = color_rgb(p->params[i + 2], p->params[i + 3], p->params[i + 4]);
                    i += 4;
                }
            } else if (v == 49) s->cur_bg = COLOR_DEFAULT;
            else if (v >= 90 && v <= 97) s->cur_fg = color_16(v - 90 + 8);
            else if (v >= 100 && v <= 107) s->cur_bg = color_16(v - 100 + 8);
        }
        break;
    }
    case 'g': {
        int mode = parser_get_param(p, 0, 0);
        if (mode == 0 && s->cursor_x < s->cols) {
            s->tab_stops[s->cursor_x] = 0;
        } else if (mode == 3) {
            memset(s->tab_stops, 0, (size_t)s->cols);
        }
        break;
    }
    case 'n': {
        if (parser_get_param(p, 0, 0) == 6) {
            /* cursor position report - ignore */
        }
        break;
    }
    case 'r': {
        int top = parser_get_param(p, 0, 1);
        int bot = parser_get_param(p, 1, s->rows);
        s->pending_wrap = 0;
        screen_set_scrolling_region(s, top - 1, bot - 1);
        break;
    }
    case 's': {
        if (pm == 0) {
            s->cursor_saved_x = s->cursor_x;
            s->cursor_saved_y = s->cursor_y;
            s->saved_fg = s->cur_fg;
            s->saved_bg = s->cur_bg;
            s->saved_flags = s->cur_flags;
        }
        break;
    }
    case 'u': {
        if (pm == 0) {
            s->pending_wrap = 0;
            s->cursor_x = s->cursor_saved_x;
            s->cursor_y = s->cursor_saved_y;
            s->cur_fg = s->saved_fg;
            s->cur_bg = s->saved_bg;
            s->cur_flags = s->saved_flags;
        }
        break;
    }
    case 'h': case 'l': {
        int set = (cmd == 'h');
        if (pm == '?') {
            for (int i = 0; i < p->param_count; i++) {
                int v = p->params[i];
                if (v == 1) { /* DECCKM */ }
                else if (v == 3) { /* DECCOLM */ }
                else if (v == 5) { /* DECSCNM */ }
                else if (v == 6) s->origin_mode = set;
                else if (v == 7) s->auto_wrap = set;
                else if (v == 12) { /* att610 */ }
                else if (v == 25) s->cursor_visible = set;
                else if (v == 1000) { s->mouse_mode = set ? 1 : 0; }
                else if (v == 1002) { s->mouse_mode = set ? 2 : 0; }
                else if (v == 1003) { s->mouse_mode = set ? 3 : 0; }
                else if (v == 1004) { /* focus */ }
                else if (v == 1005) { /* mouse */ }
                else if (v == 1006) { /* mouse */ }
                else if (v == 1015) { /* mouse */ }
                else if (v == 1047) {
                    screen_switch_alt(s, set);
                }
                else if (v == 1048) {
                    if (set) {
                        s->cursor_saved_x = s->cursor_x;
                        s->cursor_saved_y = s->cursor_y;
                    } else {
                        s->pending_wrap = 0;
                        s->cursor_x = s->cursor_saved_x;
                        s->cursor_y = s->cursor_saved_y;
                    }
                }
                else if (v == 1049) {
                    if (set) {
                        s->cursor_saved_x = s->cursor_x;
                        s->cursor_saved_y = s->cursor_y;
                    }
                    screen_switch_alt(s, set);
                    if (!set) {
                        s->pending_wrap = 0;
                        s->cursor_x = s->cursor_saved_x;
                        s->cursor_y = s->cursor_saved_y;
                    }
                }
                else if (v == 2004) { /* bracketed paste */ }
            }
        } else {
            for (int i = 0; i < p->param_count; i++) {
                int v = p->params[i];
                if (v == 4) { /* IRM */ }
                else if (v == 20) { /* LNM */ }
            }
        }
        break;
    }
    default:
        break;
    }

    if (fs_debug_enabled()) {
        double ms = fs_timer_elapsed_ms(&_csi_t);
        fs_stats_record(&_csi_stats, ms);
    }
}

void
parser_handle_esc(FastParser *p, int c) {
    FastScreen *s = p->screen;

    FsPerfTimer _esc_t;
    if (fs_debug_enabled()) fs_timer_start(&_esc_t);

    switch (c) {
    case '7':
        s->cursor_saved_x = s->cursor_x;
        s->cursor_saved_y = s->cursor_y;
        s->saved_fg = s->cur_fg;
        s->saved_bg = s->cur_bg;
        s->saved_flags = s->cur_flags;
        s->cursor_saved_visible = s->cursor_visible;
        break;
    case '8':
        s->cursor_x = s->cursor_saved_x;
        s->cursor_y = s->cursor_saved_y;
        s->cur_fg = s->saved_fg;
        s->cur_bg = s->saved_bg;
        s->cur_flags = s->saved_flags;
        s->cursor_visible = s->cursor_saved_visible;
        break;
    case 'M':
        screen_reverse_index(s);
        break;
    case 'D':
        screen_line_feed(s);
        break;
    case 'E':
        s->cursor_x = 0;
        screen_line_feed(s);
        break;
    case 'H':
        if (s->cursor_x >= 0 && s->cursor_x < s->cols)
            s->tab_stops[s->cursor_x] = 1;
        break;
    case 'c':
        screen_erase_cells(s, 0, 0, s->cols - 1, s->rows - 1);
        s->cursor_x = 0; s->cursor_y = 0;
        s->cur_fg = COLOR_DEFAULT;
        s->cur_bg = COLOR_DEFAULT;
        s->cur_flags = 0;
        s->scroll_top = 0;
        s->scroll_bottom = s->rows - 1;
        s->charset_G[0] = 0; s->charset_G[1] = 0;
        s->charset_active = 0;
        s->origin_mode = 0;
        s->auto_wrap = 1;
        s->cursor_visible = 1;
        memset(s->tab_stops, 0, (size_t)s->cols);
        for (int x = 0; x < s->cols; x++) s->tab_stops[x] = (x % 8 == 0) ? 1 : 0;
        break;
    default:
        break;
    }

    if (fs_debug_enabled()) {
        double ms = fs_timer_elapsed_ms(&_esc_t);
        fs_stats_record(&_esc_stats, ms);
    }
}

int
parser_dec_special(int cp) {
    switch (cp) {
    case '_': return 0x00A0;
    case '`': return 0x2666;
    case 'a': return 0x2592;
    case 'b': return 0x2409;
    case 'c': return 0x240C;
    case 'd': return 0x240D;
    case 'e': return 0x240A;
    case 'f': return 0x00B0;
    case 'g': return 0x00B1;
    case 'h': return 0x2424;
    case 'i': return 0x240B;
    case 'j': return 0x2518;
    case 'k': return 0x2510;
    case 'l': return 0x250C;
    case 'm': return 0x2514;
    case 'n': return 0x253C;
    case 'o': return 0x23BA;
    case 'p': return 0x23BB;
    case 'q': return 0x2500;
    case 'r': return 0x23BC;
    case 's': return 0x23BD;
    case 't': return 0x251C;
    case 'u': return 0x2524;
    case 'v': return 0x2534;
    case 'w': return 0x252C;
    case 'x': return 0x2502;
    case 'y': return 0x2264;
    case 'z': return 0x2265;
    case '{': return 0x03C0;
    case '|': return 0x2260;
    case '}': return 0x00A3;
    case '~': return 0x00B7;
    default: return cp;
    }
}

void
parser_feed_byte(FastParser *p, uint8_t b) {
    FastScreen *s = p->screen;

    switch (p->state) {
    case ST_GROUND:
        if (b == 0x1B) {
            p->state = ST_ESC;
        } else if (p->utf8.remaining > 0 || (b >= 0xA0 && b <= 0xBF)) {
            uint32_t cp;
            int result = utf8_feed(&p->utf8, b, &cp);
            if (result == 1) {
                if (s->charset_G[s->charset_active] == 1 && cp < 0x80) {
                    cp = (uint32_t)parser_dec_special((int)cp);
                }
                int w = char_width(cp);
                screen_put_char(s, cp, w);
            } else if (result == -1) {
                screen_put_char(s, 0xFFFD, 1);
            }
        } else if (b >= 0x80 && b <= 0x9F) {
            switch (b) {
            case 0x84: screen_line_feed(s); break;
            case 0x85: s->cursor_x = 0; screen_line_feed(s); break;
            case 0x88: if (s->cursor_x < s->cols) s->tab_stops[s->cursor_x] = 1; break;
            case 0x8D: screen_reverse_index(s); break;
            case 0x8E: break;
            case 0x8F: break;
            case 0x90: p->dcs_collect_len = 0; p->state = ST_DCS_ENTRY; break;
            case 0x9A: break;
            case 0x9B: parser_reset_params(p); p->state = ST_CSI_ENTRY; break;
            case 0x9C: p->state = ST_GROUND; break;
            case 0x9D: p->osc_len = 0; p->state = ST_OSC_STRING; break;
            case 0x9E: p->state = ST_SOS_PM_APC; break;
            case 0x9F: p->state = ST_SOS_PM_APC; break;
            default: break;
            }
        } else if (b <= 0x1F || b == 0x7F) {
            switch (b) {
            case 0x00: break;
            case 0x05: break;
            case 0x07: break;
            case 0x08:
                s->pending_wrap = 0;
                if (s->cursor_x > 0) s->cursor_x--;
                break;
            case 0x09: {
                s->pending_wrap = 0;
                int nx = s->cursor_x + 1;
                while (nx < s->cols && !s->tab_stops[nx]) nx++;
                if (nx >= s->cols) nx = s->cols - 1;
                s->cursor_x = nx;
                break;
            }
            case 0x0A: case 0x0B: case 0x0C:
                s->pending_wrap = 0;
                screen_line_feed(s);
                break;
            case 0x0D:
                s->cursor_x = 0;
                s->pending_wrap = 0;
                break;
            case 0x0E:
                s->charset_active = 1;
                break;
            case 0x0F:
                s->charset_active = 0;
                break;
            case 0x7F: break;
            default: break;
            }
        } else {
            uint32_t cp;
            int result = utf8_feed(&p->utf8, b, &cp);
            if (result == 1) {
                if (s->charset_G[s->charset_active] == 1 && cp < 0x80) {
                    cp = (uint32_t)parser_dec_special((int)cp);
                }
                int w = char_width(cp);
                screen_put_char(s, cp, w);
            } else if (result == -1) {
                screen_put_char(s, 0xFFFD, 1);
            }
        }
        break;

    case ST_ESC:
        if (p->charset_designate >= 0) {
            int g = p->charset_designate;
            p->charset_designate = -1;
            if (b == 'B') s->charset_G[g] = 0;
            else if (b == '0') s->charset_G[g] = 1;
            else if (b == 'A') s->charset_G[g] = 0;
            else if (b == '1') s->charset_G[g] = 0;
            else if (b == '2') s->charset_G[g] = 0;
            p->state = ST_GROUND;
        } else if (p->decaln_pending) {
            p->decaln_pending = 0;
            if (b == '8') {
                FastCell *base = s->use_alt_screen ? s->alt_cells : s->cells;
                int stride = s->cols;
                for (int y = 0; y < s->rows; y++) {
                    for (int x = 0; x < s->cols; x++) {
                        FastCell *c = &base[y * stride + x];
                        c->codepoint = 'E';
                        c->fg_color = COLOR_DEFAULT;
                        c->bg_color = COLOR_DEFAULT;
                        c->flags = 0;
                        c->width = 1;
                    }
                }
                screen_mark_dirty_range(s, 0, s->rows - 1);
            }
            p->state = ST_GROUND;
        } else if (b == '[') {
            parser_reset_params(p);
            p->state = ST_CSI_ENTRY;
        } else if (b == ']') {
            p->osc_len = 0;
            p->state = ST_OSC_STRING;
        } else if (b == 'P') {
            p->dcs_collect_len = 0;
            p->state = ST_DCS_ENTRY;
        } else if (b == 'X' || b == '^' || b == '_') {
            p->state = ST_SOS_PM_APC;
        } else if (b == '(') {
            p->charset_designate = 0;
        } else if (b == ')') {
            p->charset_designate = 1;
        } else if (b == '*') {
            p->charset_designate = 2;
        } else if (b == '+') {
            p->charset_designate = 3;
        } else if (b == '#') {
            p->decaln_pending = 1;
        } else if (b == ' ') {
            p->state = ST_GROUND;
        } else {
            parser_handle_esc(p, b);
            p->state = ST_GROUND;
        }
        break;

    case ST_CSI_ENTRY:
        if (b >= 0x30 && b <= 0x39) {
            p->params[0] = (b - 0x30);
            p->param_idx = 0;
            p->param_count = 1;
            p->param_has_val = 1;
            p->state = ST_CSI_PARAM;
        } else if (b == ';') {
            p->param_idx = 1;
            p->param_count = 2;
            p->param_has_val = 0;
            p->state = ST_CSI_PARAM;
        } else if (b >= 0x3C && b <= 0x3F) {
            p->private_marker = b;
            p->state = ST_CSI_PARAM;
        } else if (b >= 0x40 && b <= 0x7E) {
            p->final_byte = b;
            parser_dispatch_csi(p, b);
            p->state = ST_GROUND;
        } else {
            p->state = ST_GROUND;
        }
        break;

    case ST_CSI_PARAM:
        if (b >= 0x30 && b <= 0x39) {
            if (!p->param_has_val) {
                p->params[p->param_idx] = 0;
                p->param_has_val = 1;
            }
            p->params[p->param_idx] = p->params[p->param_idx] * 10 + (b - 0x30);
        } else if (b == ';') {
            p->param_idx++;
            if (p->param_idx >= MAX_PARAMS) p->param_idx = MAX_PARAMS - 1;
            p->param_count = p->param_idx + 1;
            p->param_has_val = 0;
        } else if (b >= 0x3C && b <= 0x3F) {
            p->private_marker = b;
        } else if (b == 0x20) {
            p->state = ST_CSI_INTER;
        } else if (b >= 0x40 && b <= 0x7E) {
            if (p->param_has_val) p->param_count = p->param_idx + 1;
            p->final_byte = b;
            parser_dispatch_csi(p, b);
            p->state = ST_GROUND;
        } else {
            p->state = ST_GROUND;
        }
        break;

    case ST_CSI_INTER:
        if (b >= 0x30 && b <= 0x39) {
            p->state = ST_CSI_PARAM;
        } else if (b >= 0x40 && b <= 0x7E) {
            parser_dispatch_csi(p, b);
            p->state = ST_GROUND;
        } else {
            p->state = ST_GROUND;
        }
        break;

    case ST_OSC_STRING:
        if (b == 0x07 || b == 0x9C) {
            p->osc_buf[p->osc_len] = '\0';
            p->state = ST_GROUND;
        } else if (b == 0x1B) {
            p->state = ST_ESC;
        } else if (b >= 0x20 && p->osc_len < OSC_BUF_SIZE - 1) {
            p->osc_buf[p->osc_len++] = (char)b;
        }
        break;

    case ST_DCS_ENTRY:
    case ST_DCS_PARAM:
    case ST_DCS_DATA:
        if (b == 0x1B) {
            p->state = ST_DCS_IGNORE;
        } else if (b == 0x9C) {
            p->state = ST_GROUND;
        } else if (b >= 0x40 && p->state == ST_DCS_ENTRY) {
            p->state = ST_DCS_DATA;
        } else if (b >= 0x30 && b <= 0x3B && p->state == ST_DCS_ENTRY) {
            p->state = ST_DCS_PARAM;
        }
        break;

    case ST_DCS_IGNORE:
        if (b == 0x9C || (b == '\\')) {
            p->state = ST_GROUND;
        }
        break;

    case ST_SOS_PM_APC:
        if (b == 0x1B) {
            /* might be ST */
        } else if (b == 0x9C || (b == '\\')) {
            p->state = ST_GROUND;
        }
        break;

    default:
        p->state = ST_GROUND;
        break;
    }
}

void
parser_feed(FastParser *p, const uint8_t *data, Py_ssize_t len) {
    _ensure_stats();

    FsPerfTimer t;
    if (fs_debug_enabled()) {
        fs_timer_start(&t);
        fs_debug_write("C_PARSER feed: len=%zd, cursor=(%d,%d)\n", 
                       len, p->screen ? p->screen->cursor_x : -1, p->screen ? p->screen->cursor_y : -1);
    }

    for (Py_ssize_t i = 0; i < len; i++) {
        parser_feed_byte(p, data[i]);
    }

    if (fs_debug_enabled()) {
        double ms = fs_timer_elapsed_ms(&t);
        fs_stats_record(&_feed_stats, ms);
        if (len > 512 && ms > 1.0) {
            fs_debug_write("C_PERF parser.feed SLOW len=%zd ms=%.3f\n", len, ms);
        }
        fs_debug_write("C_PARSER after feed: cursor=(%d,%d)\n",
                       p->screen ? p->screen->cursor_x : -1, p->screen ? p->screen->cursor_y : -1);
        fs_stats_report(&_feed_stats, 5.0);
        fs_stats_report(&_csi_stats, 5.0);
        fs_stats_report(&_ground_stats, 5.0);
        fs_stats_report(&_esc_stats, 5.0);
        fs_stats_report(&_putchar_stats, 5.0);
    }
}