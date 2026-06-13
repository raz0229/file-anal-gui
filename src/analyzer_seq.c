#define _XOPEN_SOURCE 700
#include "common.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

int analyze_file(const char *path, Stats *out) {
    if (!path || !out) return -1;

    FILE *fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "analyze: cannot open '%s': %s\n", path, strerror(errno));
        return -1;
    }

    Stats local;
    stats_init(&local);
    local.files = 1;

    struct stat st;
    if (stat(path, &st) == 0) {
        local.bytes = (uint64_t)st.st_size;
        stats_update_largest(&local, path, (uint64_t)st.st_size);
    }

    char buf[8192];
    size_t nread;
    int in_word = 0;
    while ((nread = fread(buf, 1, sizeof(buf), fp)) > 0) {
        local.bytes += 0; /* already accounted from stat for robustness and speed */
        for (size_t i = 0; i < nread; ++i) {
            unsigned char c = (unsigned char)buf[i];
            if (c == '\n') local.lines++;
            if (c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\f' || c == '\v') {
                in_word = 0;
            } else if (!in_word) {
                local.words++;
                in_word = 1;
            }
        }
    }

    if (ferror(fp)) {
        fprintf(stderr, "analyze: read error on '%s'\n", path);
        fclose(fp);
        return -1;
    }

    fclose(fp);
    *out = local;
    return 0;
}

int sequential_run(const FileList *files, Stats *out) {
    if (!files || !out) return -1;
    Stats total;
    stats_init(&total);

    for (size_t i = 0; i < files->count; ++i) {
        Stats file_stats;
        if (analyze_file(files->items[i], &file_stats) == 0) {
            stats_merge(&total, &file_stats);
        }
    }

    *out = total;
    return 0;
}
