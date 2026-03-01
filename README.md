# CLI for Oneshot AI coding

## General Usage

```bash
# basic
./src/oneshot/cli.py shoot \
  --pattern|-p my-pattern \
  --pattern-dir=dir-path \
  --env-file=file-path \
  --mcp-url|-m \
  --output-to-disk|-o \
  --model|-m \
  [Specific User Request]

# generate patterns
./src/oneshot/cli.py pattern generate \
  --output-dir|-o=dir-path
  --template-dir|-t=dir-path
  --template-dir|-t=dir-path-2

# list patterns
./src/oneshot/cli.py pattern list
```
