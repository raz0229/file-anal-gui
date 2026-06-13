#ifndef COMMON_H
#define COMMON_H

#define _XOPEN_SOURCE 700

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char **items;
    size_t count;
    size_t capacity;
} FileList;

typedef struct {
    uint64_t files;
    uint64_t bytes;
    uint64_t lines;
    uint64_t words;
    uint64_t largest_size;
    char largest_file[PATH_MAX];
} Stats;

void stats_init(Stats *s);
void stats_merge(Stats *dst, const Stats *src);
void stats_update_largest(Stats *s, const char *path, uint64_t size);
void stats_print(const Stats *s);

void filelist_init(FileList *list);
void filelist_free(FileList *list);
int filelist_push(FileList *list, const char *path);
int scan_directory(const char *root, FileList *list);

int analyze_file(const char *path, Stats *out);

int sequential_run(const FileList *files, Stats *out);
int parallel_run(const FileList *files, Stats *out, int requested_workers);
int omp_run(const FileList *files, Stats *out);

#ifdef __cplusplus
}
#endif

#endif
