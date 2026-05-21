#ifndef FASTSCREEN_ANSI_H
#define FASTSCREEN_ANSI_H

#include "_fastscreen_types.h"

int  _append_sgr_color(char *buf, int pos, int is_bg, uint32_t color);
int  _append_sgr_flags(char *buf, int pos, uint8_t flags);
int  _append_sgr_reset_flags(char *buf, int pos, uint8_t old_flags, uint8_t new_flags);
int  _append_sgr_set_flags(char *buf, int pos, uint8_t old_flags, uint8_t new_flags);

#endif
