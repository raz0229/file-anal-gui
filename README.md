# Parallel File Analyzer

A CLI-based directory analyzer that counts files, bytes, lines, and words across a directory tree.

It supports three modes:

- **Mode 1:** Sequential
- **Mode 2:** Parallel using `fork()` + `pthreads` + `mutex`
- **Mode 3:** Parallel using OpenMP

## Build

```bash
make
```

## Run

```bash
./bin/file_analyzer --mode 1 --path /path/to/dir
./bin/file_analyzer --mode 2 --path /path/to/dir --workers 4
./bin/file_analyzer --mode 3 --path /path/to/dir
```

## Notes

- The program scans recursively and processes regular files only.
- The parallel mode splits work between child processes, and each child uses threads.
- The OpenMP mode uses a parallel `for` loop with a critical section for aggregation.

Features:
- Select a directory and choose a scan mode (Sequential, Parallel Pthreads, OpenMP).
- When `Parallel Scan (Pthreads)` is selected, enter the number of `--workers` to use.
- Displays analysis summary (files, bytes in MB, lines, words, largest file) and a list of all files.
- Shows execution time and a "Scanning..." status while running.
