#!/bin/bash

OS_SCRIPT_DIR="$(dirname -- "${BASH_SOURCE[0]:-${0}}")"

activate_oneshot_env() {
  source "$OS_SCRIPT_DIR"/.venv/bin/activate
}

os() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli "$@"
}

ai() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot "$@"
}

ais() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -s "$@" | os md
}

aim() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -o -s "$@"
}

ai_general_prompt() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p general "$@" | os md
}

ai_devops_question() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_quick_question "$@" | os md
}

ai_code_bash() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_bash -o -s "$@"
}

ai_code_js() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_js -o -s "$@"
}

ai_code_python() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_python -o -s "$@"
}

ai_code_helm() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code_helm -o -s "$@"
}

ai_code() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_code -o -s "$@"
}

# git
ai_git() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli shoot -p devops_gitcommit -s "$@"
}

collect() {
  activate_oneshot_env
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli collect "$@"
}

# pattern generator
generate() {
  activate_oneshot_env
  pattern_templates_dir="${OS_PATTERN_TEMPLATE_DIR:-"$HOME"/projects/github/oneshot/patterns}"
  PYTHONPATH=$OS_SCRIPT_DIR python3 -m src.oneshot.cli patterns generate \
      -o "$HOME"/.config/fabric/patterns \
      -t "$pattern_templates_dir" \
      "$@"
}

# configuration
model_claude() {
  export DEFAULT_MODEL=claude-sonnet-5
}

model_claude_opus() {
  export DEFAULT_MODEL=claude-opus-5
}

model_claude_fable() {
  export DEFAULT_MODEL=claude-fable-5
}

model_claude_haiku() {
  export DEFAULT_MODEL=claude-haiku-5
}

model_gpt5_sol() {
  export DEFAULT_MODEL=gpt-5.6-sol
}

model_gpt5_terra() {
  export DEFAULT_MODEL=gpt-5.6-terra
}

model_gpt5_luna() {
  export DEFAULT_MODEL=gpt-5.6-luna
}

model_gpt5_codex() {
  export DEFAULT_MODEL=gpt-5-codex
}

model_grok_code() {
  export DEFAULT_MODEL=grok-code-fast-1
}

model_grok() {
  export DEFAULT_MODEL=grok-4-0709
}

model_gemini_flash() {
  export DEFAULT_MODEL=gemini-3.8-flash
}

model_gemini_pro() {
  export DEFAULT_MODEL=gemini-3.1-pro-preview
}

model_deepseek_flash() {
  export DEFAULT_MODEL=deepseek-v4-flash
}

model_deepseek_pro() {
  export DEFAULT_MODEL=deepseek-v4-pro
}

model_openrouter_qwen() {
  export DEFAULT_MODEL=qwen/qwen3.7-flash
}

model_openrouter_mercury() {
  export DEFAULT_MODEL=inception/mercury-2.5:nitro
}

model_openrouter_oss() {
  export DEFAULT_MODEL=openai/gpt-oss-120b:nitro
}

model_openrouter_solar() {
  export DEFAULT_MODEL=upstage/solar-pro4
}

model_openrouter_gpt_oss() {
  export DEFAULT_MODEL=openai/gpt-oss-120b
}


model() {
  echo $DEFAULT_MODEL
}

model_deepseek_flash
