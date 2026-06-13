# Parallel File Analyzer

A CLI-based directory analyzer that counts files, bytes, lines, and words across a directory tree — now with a full Python GUI wrapper.

It supports three modes:

| Mode | Flag | Description |
|------|------|-------------|
| 1 – Sequential | `--mode 1` or `seq` | Single-threaded, processes files one at a time |
| 2 – Parallel Pthreads | `--mode 2` or `parallel` | Spawns `--workers N` child processes; each uses pthreads internally |
| 3 – OpenMP | `--mode 3` or `omp` | Uses `#pragma omp parallel for` with dynamic scheduling |

---

### Group Members (LabaikGroup)
- **Abdullah Zafar** *(L1F23BSAI0054)*
- Talha Abid *(L1F23BSAI0058)*
- Abdurrehman *(L1F23BSAI0050)*

## Requirements

### CLI binary
- GCC with OpenMP support (`-fopenmp`): `gcc` ≥ 4.9, or `clang` with `libomp`
- POSIX-compliant OS (Linux, macOS)

### GUI
- Python 3.8 or newer
- `tkinter` (ships with the standard CPython installer on Windows and macOS; on Debian/Ubuntu install `python3-tk`)

---

## Build

```bash
# Build the CLI binary
make

# Or build and immediately open the GUI
make gui
```

The compiled binary is written to `bin/file_analyzer`.

---

## Running the CLI

```bash
# Mode 1 — Sequential
./bin/file_analyzer --mode 1 --path /path/to/dir

# Mode 2 — Parallel (fork + pthreads), 8 worker processes
./bin/file_analyzer --mode 2 --path /path/to/dir --workers 8

# Mode 3 — OpenMP
./bin/file_analyzer --mode 3 --path /path/to/dir

# Quick self-test (sequential scan of the project directory)
make run
```

Accepted aliases: `--mode seq`, `--mode sequential`, `--mode parallel`, `--mode omp`, `--mode openmp`.

---

## Running the GUI

```bash
# After building:
make gui

# Or directly:
python3 gui.py

# Point the GUI at a non-default binary location:
FILE_ANALYZER_BIN=/custom/path/file_analyzer python3 gui.py
```

### GUI Features

**Scanner tab**
- Browse for a directory or type a path directly.
- Choose a scan mode from the dropdown:
  - *Sequential Scan*
  - *Parallel Scan (Pthreads)* — reveals a **Workers** input box
  - *Parallel Scan (OpenMP)*
- Press **Scan**. A "Scanning…" status indicator appears while the binary runs.
- Results appear in two panels:
  - **Analysis Summary** — Files, Size (MB), Lines, Words, Execution Time, Largest File
  - **Files in Directory** — scrollable list of every path found

**Scan History tab**
- Every completed scan is automatically saved.
- The left panel lists all past scans: scan number, mode, and execution time.
- Clicking a scan shows its full details (stats + file list) in the right panel.
- Press **Clear** to wipe the history for the current session.

---

## Notes

- The scanner processes regular files only (symlinks to directories are not followed).
- Parallel mode splits work between child processes; each child further parallelises with threads.
- OpenMP mode uses a parallel `for` loop with thread-local accumulation and a `critical` section for the final merge.
- Byte counts are taken from `stat(2)` (file metadata), not from counting bytes read, so sparse files may report differently from their on-disk usage.
- Scan history is kept in memory only and is not persisted across GUI sessions.

---

## Makefile targets

```
make           Build the CLI binary (default)
make clean     Remove compiled objects and the binary
make run       Build + run a sequential scan of the current directory
make gui       Build + launch the Python GUI
make help      List all targets
```