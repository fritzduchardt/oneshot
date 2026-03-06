#!/bin/bash

SCRIPT_DIR="$(dirname -- "${BASH_SOURCE[0]:-${0}}")"

activate_env() {
  source "$SCRIPT_DIR"/.venv/bin/activate
}

os() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli "$@"
}

ai() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot "$@"
}

ai_general_prompt() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p general "$@"
}

ai_devops_question() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_quick_question "$@"
}

ai_code_bash() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_bash -o -s "$@"
}

ai_code_js() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_js -o -s "$@"
}

ai_code_python() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_python -o -s "$@"
}

ai_code_helm() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_helm -o -s "$@"
}

ai_code() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code -o -s "$@"
}

# git
ai_git() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_gitcommit -s "$@"
}

collect() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli collect "$@"
}

# pattern generator
generate() {
  activate_env
  PYTHONPATH=$SCRIPT_DIR python3 -m src.oneshot.cli patterns generate \
      -o $HOME/.config/fabric/patterns \
      -t $HOME/projects/github/oneshot/patterns \
      -t $HOME/projects/github/oneshot/patterns/templates \
      -t $HOME/Sync/FritzSync/patterns \
      -t $HOME/Sync/FritzSync/patterns/templates \
      "$@"
}

# configuration
model_claude() {
  export DEFAULT_MODEL=claude-sonnet-4-6
}

model_claude_opus() {
  export DEFAULT_MODEL=claude-opus-4-6
}

model_claude_haiku() {
  export DEFAULT_MODEL=claude-haiku-4-5
}

model_chatgpt5() {
  export DEFAULT_MODEL=gpt-5.2
}

model_chatgpt5_codex() {
  export DEFAULT_MODEL=gpt-5.2-codex
}

model_grok_code() {
  export DEFAULT_MODEL=grok-code-fast-1
}

model_grok() {
  export DEFAULT_MODEL=grok-4-0709
}

model() {
  echo $DEFAULT_MODEL
}

model_chatgpt5_codex
