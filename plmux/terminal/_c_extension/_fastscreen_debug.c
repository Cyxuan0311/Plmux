#include "_fastscreen_debug.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#ifndef _WIN32
#include <unistd.h>
#endif

FsDebugCtx g_fs_debug = {0};

#ifdef _WIN32
static DWORD WINAPI
fs_debug_thread(LPVOID arg) {
    (void)arg;
    EnterCriticalSection(&g_fs_debug.mutex);
    while (g_fs_debug.running) {
        while (g_fs_debug.read_idx == g_fs_debug.write_idx && g_fs_debug.running) {
            SleepConditionVariableCS(&g_fs_debug.cond, &g_fs_debug.mutex, INFINITE);
        }
        if (!g_fs_debug.running) break;

        while (g_fs_debug.read_idx != g_fs_debug.write_idx) {
            int ri = g_fs_debug.read_idx % FS_DEBUG_RING_SIZE;
            FsDebugEntry *e = &g_fs_debug.ring[ri];

            LeaveCriticalSection(&g_fs_debug.mutex);
            if (g_fs_debug.file) {
                fwrite(e->data, 1, (size_t)e->len, g_fs_debug.file);
                fflush(g_fs_debug.file);
            }
            EnterCriticalSection(&g_fs_debug.mutex);

            g_fs_debug.read_idx++;
        }
    }
    LeaveCriticalSection(&g_fs_debug.mutex);
    return 0;
}
#else
static void *
fs_debug_thread(void *arg) {
    (void)arg;
    pthread_mutex_lock(&g_fs_debug.mutex);
    while (g_fs_debug.running) {
        while (g_fs_debug.read_idx == g_fs_debug.write_idx && g_fs_debug.running) {
            pthread_cond_wait(&g_fs_debug.cond, &g_fs_debug.mutex);
        }
        if (!g_fs_debug.running) break;

        while (g_fs_debug.read_idx != g_fs_debug.write_idx) {
            int ri = g_fs_debug.read_idx % FS_DEBUG_RING_SIZE;
            FsDebugEntry *e = &g_fs_debug.ring[ri];

            pthread_mutex_unlock(&g_fs_debug.mutex);
            if (g_fs_debug.file) {
                fwrite(e->data, 1, (size_t)e->len, g_fs_debug.file);
                fflush(g_fs_debug.file);
            }
            pthread_mutex_lock(&g_fs_debug.mutex);

            g_fs_debug.read_idx++;
        }
    }
    pthread_mutex_unlock(&g_fs_debug.mutex);
    return NULL;
}
#endif

int
fs_debug_init(const char *path) {
    if (g_fs_debug.enabled) return 0;

    memset(&g_fs_debug, 0, sizeof(g_fs_debug));

    g_fs_debug.file = fopen(path, "a");
    if (!g_fs_debug.file) return -1;

    setvbuf(g_fs_debug.file, NULL, _IONBF, 0);

#ifdef _WIN32
    InitializeCriticalSection(&g_fs_debug.mutex);
    InitializeConditionVariable(&g_fs_debug.cond);

    g_fs_debug.running = 1;
    g_fs_debug.enabled = 1;

    g_fs_debug.thread = CreateThread(NULL, 0, fs_debug_thread, NULL, 0, NULL);
    if (g_fs_debug.thread == NULL) {
        g_fs_debug.running = 0;
        g_fs_debug.enabled = 0;
        fclose(g_fs_debug.file);
        g_fs_debug.file = NULL;
        DeleteCriticalSection(&g_fs_debug.mutex);
        return -1;
    }
#else
    pthread_mutex_init(&g_fs_debug.mutex, NULL);
    pthread_cond_init(&g_fs_debug.cond, NULL);

    g_fs_debug.running = 1;
    g_fs_debug.enabled = 1;

    if (pthread_create(&g_fs_debug.thread, NULL, fs_debug_thread, NULL) != 0) {
        g_fs_debug.running = 0;
        g_fs_debug.enabled = 0;
        fclose(g_fs_debug.file);
        g_fs_debug.file = NULL;
        pthread_mutex_destroy(&g_fs_debug.mutex);
        pthread_cond_destroy(&g_fs_debug.cond);
        return -1;
    }
#endif

    fs_debug_write("C_DEBUG === fastscreen debug logging started ===\n");
    return 0;
}

void
fs_debug_shutdown(void) {
    if (!g_fs_debug.enabled) return;

    fs_debug_write("C_DEBUG === fastscreen debug logging stopped ===\n");

#ifdef _WIN32
    EnterCriticalSection(&g_fs_debug.mutex);
    g_fs_debug.running = 0;
    WakeConditionVariable(&g_fs_debug.cond);
    LeaveCriticalSection(&g_fs_debug.mutex);

    WaitForSingleObject(g_fs_debug.thread, INFINITE);
    CloseHandle(g_fs_debug.thread);

    if (g_fs_debug.file) {
        fclose(g_fs_debug.file);
        g_fs_debug.file = NULL;
    }

    DeleteCriticalSection(&g_fs_debug.mutex);
#else
    pthread_mutex_lock(&g_fs_debug.mutex);
    g_fs_debug.running = 0;
    pthread_cond_signal(&g_fs_debug.cond);
    pthread_mutex_unlock(&g_fs_debug.mutex);

    pthread_join(g_fs_debug.thread, NULL);

    if (g_fs_debug.file) {
        fclose(g_fs_debug.file);
        g_fs_debug.file = NULL;
    }

    pthread_mutex_destroy(&g_fs_debug.mutex);
    pthread_cond_destroy(&g_fs_debug.cond);
#endif

    g_fs_debug.enabled = 0;
}

void
fs_debug_write(const char *fmt, ...) {
    if (!g_fs_debug.enabled) return;

    char buf[FS_DEBUG_BUF_SIZE];
    va_list ap;
    va_start(ap, fmt);
    int len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len <= 0) return;
    if (len >= FS_DEBUG_BUF_SIZE) len = FS_DEBUG_BUF_SIZE - 1;

#ifdef _WIN32
    EnterCriticalSection(&g_fs_debug.mutex);
    if (!g_fs_debug.running) {
        LeaveCriticalSection(&g_fs_debug.mutex);
        return;
    }

    int wi = g_fs_debug.write_idx % FS_DEBUG_RING_SIZE;
    FsDebugEntry *e = &g_fs_debug.ring[wi];

    if (g_fs_debug.write_idx - g_fs_debug.read_idx >= FS_DEBUG_RING_SIZE) {
        g_fs_debug.read_idx++;
    }

    memcpy(e->data, buf, (size_t)len);
    e->data[len] = '\0';
    e->len = len;
    g_fs_debug.write_idx++;

    WakeConditionVariable(&g_fs_debug.cond);
    LeaveCriticalSection(&g_fs_debug.mutex);
#else
    pthread_mutex_lock(&g_fs_debug.mutex);
    if (!g_fs_debug.running) {
        pthread_mutex_unlock(&g_fs_debug.mutex);
        return;
    }

    int wi = g_fs_debug.write_idx % FS_DEBUG_RING_SIZE;
    FsDebugEntry *e = &g_fs_debug.ring[wi];

    if (g_fs_debug.write_idx - g_fs_debug.read_idx >= FS_DEBUG_RING_SIZE) {
        g_fs_debug.read_idx++;
    }

    memcpy(e->data, buf, (size_t)len);
    e->data[len] = '\0';
    e->len = len;
    g_fs_debug.write_idx++;

    pthread_cond_signal(&g_fs_debug.cond);
    pthread_mutex_unlock(&g_fs_debug.mutex);
#endif
}

void
fs_stats_report(FsPerfStats *s, double interval_s) {
    if (!g_fs_debug.enabled) return;

#ifdef _WIN32
    LARGE_INTEGER freq, now_li;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&now_li);
    double now = (double)now_li.QuadPart / (double)freq.QuadPart;
#else
    struct timespec now_ts;
    clock_gettime(CLOCK_MONOTONIC, &now_ts);
    double now = (double)now_ts.tv_sec + (double)now_ts.tv_nsec / 1e9;
#endif

    if (now - s->last_report_time < interval_s) return;
    s->last_report_time = now;

    if (s->count == 0) return;

    double avg = s->total_ms / (double)s->count;
    fs_debug_write("C_STATS [%s] count=%d avg=%.3fms min=%.3fms max=%.3fms total=%.1fms\n",
                   s->name, s->count, avg, s->min_ms, s->max_ms, s->total_ms);
}