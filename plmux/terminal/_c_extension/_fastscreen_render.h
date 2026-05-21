#ifndef FASTSCREEN_RENDER_H
#define FASTSCREEN_RENDER_H

#include "_fastscreen_types.h"

PyObject *cell_style_str(FastCell *c);
PyObject *cell_glyph(FastCell *c);
int       glyph_to_utf8_buf(uint32_t cp, char *buf);

int  flush_run(PyObject *result, const char *buf, int len,
               uint8_t flags, uint32_t fg, uint32_t bg);
int  flush_run_to_textobj(PyObject *text_obj, const char *buf, int len,
                          uint8_t flags, uint32_t fg, uint32_t bg);

PyObject *_get_rich_text_class(void);

#endif
