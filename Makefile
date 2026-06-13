CC=gcc
CFLAGS=-std=c11 -Wall -Wextra -O2 -Iinclude -fopenmp -pthread
LDFLAGS=-fopenmp -pthread

SRC=src/main.c src/utils.c src/scanner.c src/analyzer_seq.c src/analyzer_parallel.c src/analyzer_omp.c
OBJ=$(SRC:.c=.o)
BIN=bin/file_analyzer

all: $(BIN)

$(BIN): $(OBJ) | bin
	$(CC) $(OBJ) -o $(BIN) $(LDFLAGS)

bin:
	mkdir -p bin

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(BIN)

run: $(BIN)
	./$(BIN)

.PHONY: all clean run
