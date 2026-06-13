#define _XOPEN_SOURCE 700
#include "common.h"

#ifdef _OPENMP
#include <omp.h>
#endif

#include <stdio.h>
#include <string.h>

int omp_run(const FileList *files, Stats *out) {
    if (!files || !out) return -1;
    stats_init(out);

    Stats total;
    stats_init(&total);

    #pragma omp parallel
    {
        Stats local;
        stats_init(&local);

        #pragma omp for nowait schedule(dynamic, 8)
        for (size_t i = 0; i < files->count; ++i) {
            Stats fs;
            if (analyze_file(files->items[i], &fs) == 0) {
                stats_merge(&local, &fs);
            }
        }

        #pragma omp critical
        {
            stats_merge(&total, &local);
        }
    }

    *out = total;
    return 0;
}
