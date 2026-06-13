#define _XOPEN_SOURCE 700
#include "common.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void stats_init(Stats *s) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
}

void stats_update_largest(Stats *s, const char *path, uint64_t size) {
    if (!s || !path) return;
    if (size >= s->largest_size) {
        s->largest_size = size;
        snprintf(s->largest_file, sizeof(s->largest_file), "%s", path);
    }
}

void stats_merge(Stats *dst, const Stats *src) {
    if (!dst || !src) return;
    dst->files += src->files;
    dst->bytes += src->bytes;
    dst->lines += src->lines;
    dst->words += src->words;
    if (src->largest_size >= dst->largest_size) {
        dst->largest_size = src->largest_size;
        if (src->largest_file[0] != '\0') {
            snprintf(dst->largest_file, sizeof(dst->largest_file), "%s", src->largest_file);
        }
    }
}

void stats_print(const Stats *s) {
    if (!s) return;
    printf("\n==== Analysis Summary ====\n");
    printf("Files   : %llu\n", (unsigned long long)s->files);
    printf("Bytes   : %llu\n", (unsigned long long)s->bytes);
    printf("Lines   : %llu\n", (unsigned long long)s->lines);
    printf("Words   : %llu\n", (unsigned long long)s->words);
    if (s->largest_file[0] != '\0') {
        printf("Largest : %s (%llu bytes)\n", s->largest_file, (unsigned long long)s->largest_size);
    } else {
        printf("Largest : N/A\n");
    }
}

void filelist_init(FileList *list) {
    if (!list) return;
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

void filelist_free(FileList *list) {
    if (!list) return;
    for (size_t i = 0; i < list->count; ++i) {
        free(list->items[i]);
    }
    free(list->items);
    filelist_init(list);
}

int filelist_push(FileList *list, const char *path) {
    if (!list || !path) return -1;
    if (list->count == list->capacity) {
        size_t new_cap = list->capacity == 0 ? 64 : list->capacity * 2;
        char **new_items = realloc(list->items, new_cap * sizeof(char *));
        if (!new_items) return -1;
        list->items = new_items;
        list->capacity = new_cap;
    }
    list->items[list->count] = strdup(path);
    if (!list->items[list->count]) return -1;
    list->count++;
    return 0;
}
