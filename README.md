# Oneshot AI Coding CLI

A lightweight CLI for single-shot prompts and prompt pattern management.

## Usage

### Basic

./src/oneshot/cli.py shoot \
  --pattern|-p my-pattern \
  --pattern-dir dir-path \
  --env-file file-path \
  --mcp-url url \
  --output-to-disk|-o \
  --model model-name \
  [Specific User Request]

### Generate patterns

./src/oneshot/cli.py pattern generate \
  --output-dir|-o dir-path \
  --template-dir|-t dir-path \
  --template-dir|-t dir-path-2

### List patterns

./src/oneshot/cli.py pattern list