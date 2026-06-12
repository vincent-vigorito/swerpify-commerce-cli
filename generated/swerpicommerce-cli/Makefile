.PHONY: build test lint install clean

build:
	go build -o bin/swerpicommerce-pp-cli ./cmd/swerpicommerce-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/swerpicommerce-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/swerpicommerce-pp-mcp ./cmd/swerpicommerce-pp-mcp

install-mcp:
	go install ./cmd/swerpicommerce-pp-mcp

build-all: build build-mcp
