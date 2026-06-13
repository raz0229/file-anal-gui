#define _XOPEN_SOURCE 700
#include "common.h"

#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int scan_recursive(const char *dir, FileList *list) {
    DIR *dp = opendir(dir);
    if (!dp) {
        fprintf(stderr, "scan: cannot open directory '%s': %s\n", dir, strerror(errno));
        return -1;
    }

    struct dirent *entry;
    int status = 0;
    while ((entry = readdir(dp)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;

        char path[PATH_MAX];
        int n = snprintf(path, sizeof(path), "%s/%s", dir, entry->d_name);
        if (n < 0 || (size_t)n >= sizeof(path)) {
            fprintf(stderr, "scan: path too long under '%s'\n", dir);
            status = -1;
            continue;
        }

        struct stat st;
        if (lstat(path, &st) != 0) {
            fprintf(stderr, "scan: lstat failed on '%s': %s\n", path, strerror(errno));
            status = -1;
            continue;
        }

        if (S_ISDIR(st.st_mode)) {
            if (scan_recursive(path, list) != 0) status = -1;
        } else if (S_ISREG(st.st_mode)) {
            if (filelist_push(list, path) != 0) {
                fprintf(stderr, "scan: out of memory while adding '%s'\n", path);
                status = -1;
            }
        }
    }

    closedir(dp);
    return status;
}

int scan_directory(const char *root, FileList *list) {
    if (!root || !list) return -1;
    struct stat st;
    if (stat(root, &st) != 0) {
        fprintf(stderr, "scan: cannot stat '%s': %s\n", root, strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        fprintf(stderr, "scan: '%s' is not a directory\n", root);
        return -1;
    }
    return scan_recursive(root, list);
}
