# Oneshot AI Coding CLI

A simple CLI for running single-shot prompts and managing prompt patterns.

## Usage

### Basic

./src/oneshot/cli.py shoot \
  --pattern|-p my-pattern \
  --pattern-dir=dir-path \
  --env-file=file-path \
  --mcp-url|-m \
  --output-to-disk|-o \
  --model|-m \
  [Specific User Request]

### Generate Patterns

./src/oneshot/cli.py pattern generate \
  --output-dir|-o=dir-path \
  --template-dir|-t=dir-path \
  --template-dir|-t=dir-path-2

### List Patterns

./src/oneshot/cli.py pattern list