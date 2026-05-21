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

/* ================================================================
   High-resolution performance timer
   ================================================================ */

typedef struct {
#ifdef _WIN32
    LARGE_INTEGER _freq;
    LARGE_INTEGER _start;
#else
    struct timespec _start;
#endif
} FsPerfTimer;

#ifdef _WIN32
static inline void
fs_timer_start(FsPerfTimer *t) {
    QueryPerformanceFrequency(&t->_freq);
    QueryPerformanceCounter(&t->_start);
}

static inline double
fs_timer_elapsed_ms(FsPerfTimer *t) {
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (double)(now.QuadPart - t->_start.QuadPart) * 1000.0 / (double)t->_freq.QuadPart;
}

static inline double
fs_timer_elapsed_us(FsPerfTimer *t) {
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (double)(now.QuadPart - t->_start.QuadPart) * 1000000.0 / (double)t->_freq.QuadPart;
}
#else
static inline void
fs_timer_start(FsPerfTimer *t) {
    clock_gettime(CLOCK_MONOTONIC, &t->_start);
}

static inline double
fs_timer_elapsed_ms(FsPerfTimer *t) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    double s  = (double)(now.tv_sec  - t->_start.tv_sec);
    double ns = (double)(now.tv_nsec - t->_start.tv_nsec);
    return s * 1000.0 + ns / 1000000.0;
}

static inline double
fs_timer_elapsed_us(FsPerfTimer *t) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    double s  = (double)(now.tv_sec  - t->_start.tv_sec);
    double ns = (double)(now.tv_nsec - t->_start.tv_nsec);
    return s * 1000000.0 + ns / 1000000.0;
}
#endif

/* ================================================================
   Cumulative performance stats (mirrors PerfStats in debug_log.py)
   ================================================================ */

typedef struct {
    const char *name;
    int         count;
    double      total_ms;
    double      min_ms;
    double      max_ms;
    double      last_report_time;
} FsPerfStats;

static inline void
fs_stats_init(FsPerfStats *s, const char *name) {
    s->name = name;
    s->count = 0;
    s->total_ms = 0.0;
    s->min_ms = 1e18;
    s->max_ms = 0.0;
    s->last_report_time = 0.0;
}

static inline void
fs_stats_record(FsPerfStats *s, double ms) {
    s->count++;
    s->total_ms += ms;
    if (ms < s->min_ms) s->min_ms = ms;
    if (ms > s->max_ms) s->max_ms = ms;
}

void fs_stats_report(FsPerfStats *s, double interval_s);

static inline void
fs_stats_reset(FsPerfStats *s) {
    s->count = 0;
    s->total_ms = 0.0;
    s->min_ms = 1e18;
    s->max_ms = 0.0;
}

#endif /* FASTSCREEN_DEBUG_H */