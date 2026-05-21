#ifndef FASTSCREEN_COLOR_H
#define FASTSCREEN_COLOR_H

#include "_fastscreen_types.h"

extern const char *COLOR_16_NAMES[16];
extern const char *ANSI16_TO_HEX[16];

PyObject *color_to_pystr(uint32_t c);
PyObject *color_to_rich(uint32_t c);

#endif
