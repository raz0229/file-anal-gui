CC      = gcc
CFLAGS  = -std=c11 -Wall -Wextra -O2 -Iinclude -fopenmp -pthread
LDFLAGS = -fopenmp -pthread

SRC = src/main.c src/utils.c src/scanner.c \
      src/analyzer_seq.c src/analyzer_parallel.c src/analyzer_omp.c
OBJ = $(SRC:.c=.o)
BIN = bin/file_analyzer

.PHONY: all clean run gui help

all: $(BIN)       ## Build the CLI binary (default)

$(BIN): $(OBJ) | bin
	$(CC) $(OBJ) -o $(BIN) $(LDFLAGS)

bin:
	mkdir -p bin

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:            ## Remove compiled objects and binary
	rm -f $(OBJ) $(BIN)

run: $(BIN)       ## Quick test: sequential scan of the current directory
	./$(BIN) --mode 1 --path .

gui: $(BIN)       ## Launch the Python GUI (requires Python 3 + tkinter)
	python3 gui.py

help:             ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*##"} {printf "  %-10s %s\n", $$1, $$2}'