.PHONY: build test lint install clean

BIN_EXT := $(if $(filter windows,$(shell go env GOOS)),.exe,)

build:
	go build -trimpath -o bin/swerpicommerce-pp-cli$(BIN_EXT) ./cmd/swerpicommerce-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/swerpicommerce-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -trimpath -o bin/swerpicommerce-pp-mcp$(BIN_EXT) ./cmd/swerpicommerce-pp-mcp

install-mcp:
	go install ./cmd/swerpicommerce-pp-mcp

build-all: build build-mcp
