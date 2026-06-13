#define _XOPEN_SOURCE 700
#include "common.h"

#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define MAX_CHILDREN 64

typedef struct {
    const char **paths;
    size_t start;
    size_t end;
    Stats *shared;
    pthread_mutex_t *mutex;
} ThreadJob;

static void *thread_worker(void *arg) {
    ThreadJob *job = (ThreadJob *)arg;
    Stats local;
    stats_init(&local);

    for (size_t i = job->start; i < job->end; ++i) {
        Stats fs;
        if (analyze_file(job->paths[i], &fs) == 0) {
            stats_merge(&local, &fs);
        }
    }

    pthread_mutex_lock(job->mutex);
    stats_merge(job->shared, &local);
    pthread_mutex_unlock(job->mutex);
    return NULL;
}

static int process_chunk_with_threads(const char **paths, size_t start, size_t end, Stats *out) {
    stats_init(out);
    size_t count = end - start;
    if (count == 0) return 0;

    long cpu = sysconf(_SC_NPROCESSORS_ONLN);
    if (cpu < 1) cpu = 2;
    size_t nthreads = (size_t)cpu;
    if (nthreads > count) nthreads = count;
    if (nthreads < 1) nthreads = 1;

    pthread_t *threads = calloc(nthreads, sizeof(pthread_t));
    ThreadJob *jobs = calloc(nthreads, sizeof(ThreadJob));
    if (!threads || !jobs) {
        free(threads);
        free(jobs);
        return -1;
    }

    pthread_mutex_t mutex;
    if (pthread_mutex_init(&mutex, NULL) != 0) {
        free(threads);
        free(jobs);
        return -1;
    }

    size_t base = count / nthreads;
    size_t rem = count % nthreads;
    size_t cursor = start;

    for (size_t i = 0; i < nthreads; ++i) {
        size_t span = base + (i < rem ? 1 : 0);
        jobs[i].paths = paths;
        jobs[i].start = cursor;
        jobs[i].end = cursor + span;
        jobs[i].shared = out;
        jobs[i].mutex = &mutex;
        cursor += span;
        if (pthread_create(&threads[i], NULL, thread_worker, &jobs[i]) != 0) {
            fprintf(stderr, "parallel: failed to create thread\n");
            nthreads = i;
            break;
        }
    }

    int status = 0;
    for (size_t i = 0; i < nthreads; ++i) {
        if (pthread_join(threads[i], NULL) != 0) status = -1;
    }

    pthread_mutex_destroy(&mutex);
    free(threads);
    free(jobs);
    return status;
}

static void child_work(const char **paths, size_t start, size_t end, int write_fd) {
    Stats chunk;
    if (process_chunk_with_threads(paths, start, end, &chunk) != 0) {
        stats_init(&chunk);
    }
    ssize_t expected = (ssize_t)sizeof(chunk);
    ssize_t written = write(write_fd, &chunk, sizeof(chunk));
    (void)expected;
    (void)written;
    close(write_fd);
    _exit(0);
}

int parallel_run(const FileList *files, Stats *out, int requested_workers) {
    if (!files || !out) return -1;
    stats_init(out);
    if (files->count == 0) return 0;

    long cpu = sysconf(_SC_NPROCESSORS_ONLN);
    if (cpu < 1) cpu = 2;
    size_t workers = requested_workers > 0 ? (size_t)requested_workers : (size_t)cpu;
    if (workers < 1) workers = 1;
    if (workers > files->count) workers = files->count;
    if (workers > MAX_CHILDREN) workers = MAX_CHILDREN;

    const char **paths = (const char **)files->items;
    size_t base = files->count / workers;
    size_t rem = files->count % workers;
    size_t cursor = 0;

    pid_t pids[MAX_CHILDREN];
    int pipes[MAX_CHILDREN][2];
    size_t launched = 0;

    for (size_t i = 0; i < workers; ++i) {
        size_t span = base + (i < rem ? 1 : 0);
        if (pipe(pipes[i]) != 0) {
            fprintf(stderr, "parallel: pipe failed: %s\n", strerror(errno));
            break;
        }

        pid_t pid = fork();
        if (pid < 0) {
            fprintf(stderr, "parallel: fork failed: %s\n", strerror(errno));
            close(pipes[i][0]);
            close(pipes[i][1]);
            break;
        }
        if (pid == 0) {
            close(pipes[i][0]);
            child_work(paths, cursor, cursor + span, pipes[i][1]);
        }

        close(pipes[i][1]);
        pids[i] = pid;
        launched++;
        cursor += span;
    }

    for (size_t i = 0; i < launched; ++i) {
        Stats partial;
        stats_init(&partial);
        ssize_t got = read(pipes[i][0], &partial, sizeof(partial));
        close(pipes[i][0]);
        if (got == (ssize_t)sizeof(partial)) {
            stats_merge(out, &partial);
        }
        (void)waitpid(pids[i], NULL, 0);
    }

    return 0;
}
