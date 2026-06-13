#define _XOPEN_SOURCE 700
#include "common.h"

#include <errno.h>
#include <getopt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static double elapsed_ms(struct timespec a, struct timespec b) {
    return (double)(b.tv_sec - a.tv_sec) * 1000.0 + (double)(b.tv_nsec - a.tv_nsec) / 1000000.0;
}

static void print_usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s --mode <1|2|3|seq|parallel|omp> --path <directory> [--workers N]\n"
        "  Mode 1 = Sequential\n"
        "  Mode 2 = Parallel (fork + pthreads + mutexes)\n"
        "  Mode 3 = Parallel with OpenMP\n",
        prog);
}

static int parse_mode(const char *s) {
    if (!s) return -1;
    if (strcmp(s, "1") == 0 || strcmp(s, "seq") == 0 || strcmp(s, "sequential") == 0) return 1;
    if (strcmp(s, "2") == 0 || strcmp(s, "parallel") == 0) return 2;
    if (strcmp(s, "3") == 0 || strcmp(s, "omp") == 0 || strcmp(s, "openmp") == 0) return 3;
    return -1;
}

int main(int argc, char **argv) {
    const char *path = NULL;
    int mode = -1;
    int workers = 0;

    static struct option long_opts[] = {
        {"mode", required_argument, NULL, 'm'},
        {"path", required_argument, NULL, 'p'},
        {"workers", required_argument, NULL, 'w'},
        {"help", no_argument, NULL, 'h'},
        {0, 0, 0, 0}
    };

    int opt;
    while ((opt = getopt_long(argc, argv, "m:p:w:h", long_opts, NULL)) != -1) {
        switch (opt) {
            case 'm': mode = parse_mode(optarg); break;
            case 'p': path = optarg; break;
            case 'w': workers = atoi(optarg); break;
            case 'h':
            default:
                print_usage(argv[0]);
                return (opt == 'h') ? 0 : 1;
        }
    }

    if (!path || mode < 0) {
        print_usage(argv[0]);
        return 1;
    }

    FileList files;
    filelist_init(&files);
    if (scan_directory(path, &files) != 0) {
        filelist_free(&files);
        return 1;
    }

    printf("Scanned %zu files under %s\n", files.count, path);

    Stats result;
    stats_init(&result);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    int rc = 0;
    if (mode == 1) {
        rc = sequential_run(&files, &result);
    } else if (mode == 2) {
        rc = parallel_run(&files, &result, workers);
    } else if (mode == 3) {
        rc = omp_run(&files, &result);
    } else {
        fprintf(stderr, "Invalid mode. Use 1, 2, 3, seq, parallel, or omp.\n");
        filelist_free(&files);
        return 1;
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    if (rc != 0) {
        fprintf(stderr, "Analysis failed.\n");
        filelist_free(&files);
        return 1;
    }

    stats_print(&result);
    printf("Execution Time: %.3f ms\n", elapsed_ms(start, end));

    filelist_free(&files);
    return 0;
}
