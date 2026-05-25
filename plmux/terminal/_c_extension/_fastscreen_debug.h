#ifndef FASTSCREEN_DEBUG_H
#define FASTSCREEN_DEBUG_H

#ifdef _WIN32
#include <windows.h>
#else
#include <pthread.h>
#endif
#include <stdint.h>
#include <stdio.h>
#include <time.h>

/* ================================================================
   C-side async debug logging, mirroring plmux/debug_log.py
   Activated via _fastscreen.enable_debug(log_path) from Python.
   ================================================================ */

#define FS_DEBUG_BUF_SIZE  4096
#define FS_DEBUG_RING_SIZE 256

typedef struct {
    char    data[FS_DEBUG_BUF_SIZE];
    int     len;
} FsDebugEntry;

typedef struct {
    int             enabled;
    FILE           *file;
#ifdef _WIN32
    HANDLE              thread;
    CRITICAL_SECTION    mutex;
    CONDITION_VARIABLE  cond;
#else
    pthread_t       thread;
    pthread_mutex_t mutex;
    pthread_cond_t  cond;
#endif
    int             running;

    FsDebugEntry   ring[FS_DEBUG_RING_SIZE];
    volatile int    write_idx;
    volatile int    read_idx;
} FsDebugCtx;

extern FsDebugCtx g_fs_debug;

int  fs_debug_init(const char *path);
void fs_debug_shutdown(void);
void fs_debug_write(const char *fmt, ...)
#ifndef _WIN32
    __attribute__((format(printf, 1, 2)))
#endif
    ;

static inline int fs_debug_enabled(void) {
    return g_fs_debug.enabled;
}

#endif /* FASTSCREEN_DEBUG_H */
