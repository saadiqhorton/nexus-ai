"Shell completion script generation for Nexus CLI"

BASH_COMPLETION = r"""#!/bin/bash

# Bash completion for Nexus CLI
# Properly formatted and syntax-correct bash completion script

_nexus_completion() {
    local cur prev words cword
    _get_comp_words_by_ref -n : cur prev words cword || return 1

    # Main commands
    local commands="chat models providers config default sessions prompts completion version"

    # Subcommands
    local session_commands="list show export delete search rename"
    local prompt_commands="list show new edit delete"

    # Options list
    local opts="-m --model -p --provider -t --temperature -s --system -u --use -f --file --session -d --default --fuzzy --no-stream --allow-sensitive -h --help --max-tokens"

    # Check if current word starts with dash (option)
    case "${cur}" in
        -*)
            COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
            return 0
            ;;
    esac

    # Handle completion based on previous word
    case "${prev}" in
        nexus)
            COMPREPLY=($(compgen -W "${commands}" -- "${cur}"))
            return 0
            ;;
        sessions)
            COMPREPLY=($(compgen -W "${session_commands}" -- "${cur}"))
            return 0
            ;;
        prompts)
            COMPREPLY=($(compgen -W "${prompt_commands}" -- "${cur}"))
            return 0
            ;;
        -p|--provider)
            local providers="openai anthropic ollama openrouter"
            COMPREPLY=($(compgen -W "${providers}" -- "${cur}"))
            return 0
            ;;
        -u|--use)
            # Complete prompt names from library
            local prompts_dir="${HOME}/.nexus/prompts"
            if [[ -d "${prompts_dir}" ]]; then
                local prompts=$(command ls -1 "${prompts_dir}" 2>/dev/null | command sed 's/.md$//')
                COMPREPLY=($(compgen -W "${prompts}" -- "${cur}"))
            fi
            return 0
            ;;
        --session)
            # Complete session names
            local sessions_dir="${HOME}/.nexus/sessions"
            if [[ -d "${sessions_dir}" ]]; then
                local sessions=$(command ls -1 "${sessions_dir}" 2>/dev/null | command sed 's/.json$//' | command grep -v "^.temp")
                COMPREPLY=($(compgen -W "${sessions}" -- "${cur}"))
            fi
            return 0
            ;;
        show|export|delete|edit|rename)
            # Context-aware completion for session/prompt files
            local parent_cmd=""

            # Find the parent command (sessions or prompts)
            for ((i=cword-2; i>=0; i--)); do
                if [[ "${words[i]}" == "sessions" || "${words[i]}" == "prompts" ]]; then
                    parent_cmd="${words[i]}"
                    break
                fi
            done

            if [[ "${parent_cmd}" == "sessions" ]]; then
                local sessions_dir="${HOME}/.nexus/sessions"
                if [[ -d "${sessions_dir}" ]]; then
                    local sessions=$(command ls -1 "${sessions_dir}" 2>/dev/null | command sed 's/.json$//' | command grep -v "^.temp")
                    COMPREPLY=($(compgen -W "${sessions}" -- "${cur}"))
                fi
            elif [[ "${parent_cmd}" == "prompts" ]]; then
                local prompts_dir="${HOME}/.nexus/prompts"
                if [[ -d "${prompts_dir}" ]]; then
                    local prompts=$(command ls -1 "${prompts_dir}" 2>/dev/null | command sed 's/.md$//')
                    COMPREPLY=($(compgen -W "${prompts}" -- "${cur}"))
                fi
            fi
            return 0
            ;;
        -m|--model)
            # Complete common model names
            local common_models="gpt-4o gpt-4-turbo claude-sonnet-4 claude-3-5-sonnet llama3"
            COMPREPLY=($(compgen -W "${common_models}" -- "${cur}"))
            return 0
            ;;
    esac

    # Handle subcommand contexts
    for ((i=1; i<${#words[@]}; i++)); do
        case "${words[i]}" in
            sessions)
                COMPREPLY=($(compgen -W "${session_commands}" -- "${cur}"))
                return 0
                ;;
            prompts)
                COMPREPLY=($(compgen -W "${prompt_commands}" -- "${cur}"))
                return 0
                ;;
        esac
    done

    # Default case - complete main commands
    COMPREPLY=($(compgen -W "${commands}" -- "${cur}"))
    return 0
}

# Apply completion function
complete -F _nexus_completion nexus
"""


def get_bash_completion() -> str:
    """Return bash completion script"""
    return BASH_COMPLETION.replace("\\", "\\\\").strip()


def get_zsh_completion() -> str:
    """Return zsh completion script"""
    zsh_script = r"""#compdef nexus

# ZSH completion for Nexus CLI
# Comprehensive completion with dynamic session and prompt support

# Helper function to complete session names
_nexus_sessions() {
  local sessions_dir="${HOME}/.nexus/sessions"
  local -a sessions

  if [[ -d "${sessions_dir}" ]]; then
    sessions=(${sessions_dir}/*.json(N:t:r))
    # Filter out temp sessions
    sessions=(${sessions:#.temp*})
    _describe 'session' sessions
  fi
}

# Helper function to complete prompt names
_nexus_prompts() {
  local prompts_dir="${HOME}/.nexus/prompts"
  local -a prompts

  if [[ -d "${prompts_dir}" ]]; then
    prompts=(${prompts_dir}/*.md(N:t:r))
    _describe 'prompt' prompts
  fi
}

# Helper function to complete model names
_nexus_models() {
  local -a models
  models=(
    'gpt-4o:OpenAI GPT-4 Optimized'
    'gpt-4-turbo:OpenAI GPT-4 Turbo'
    'claude-sonnet-4:Anthropic Claude Sonnet 4'
    'claude-3-5-sonnet:Anthropic Claude 3.5 Sonnet'
    'llama3:Ollama Llama 3'
  )
  _describe 'model' models
}

# Helper function to complete provider names
_nexus_providers() {
  local -a providers
  providers=(
    'openai:OpenAI API'
    'anthropic:Anthropic API'
    'ollama:Ollama (local)'
    'openrouter:OpenRouter API'
  )
  _describe 'provider' providers
}

# Session subcommand completion
_nexus_session_commands() {
  local -a session_cmds
  session_cmds=(
    'list:List all sessions'
    'show:Show session content'
    'export:Export session to file'
    'delete:Delete a session'
    'search:Search sessions'
    'rename:Rename a session'
  )
  _describe 'session command' session_cmds
}

# Prompt subcommand completion
_nexus_prompt_commands() {
  local -a prompt_cmds
  prompt_cmds=(
    'list:List all prompts'
    'show:Show prompt content'
    'new:Create new prompt'
    'edit:Edit a prompt'
    'delete:Delete a prompt'
  )
  _describe 'prompt command' prompt_cmds
}

# Main completion function
_nexus() {
  local curcontext="$curcontext" state line
  typeset -A opt_args

  # Main commands
  local -a commands
  commands=(
    'chat:Start interactive chat'
    'models:List available models'
    'providers:List configured providers'
    'config:Show configuration'
    'default:Set default model'
    'sessions:Manage chat sessions'
    'prompts:Manage prompt library'
    'completion:Generate shell completion'
    'version:Show version'
  )

  _arguments -C \
    '(-m --model)'{-m,--model}'[Model to use]:model:_nexus_models' \
    '(-p --provider)'{-p,--provider}'[Provider]:provider:_nexus_providers' \
    '(-t --temperature)'{-t,--temperature}'[Temperature (0.0-2.0)]:temperature:(0.0 0.5 0.7 1.0 1.5 2.0)' \
    '--max-tokens[Maximum tokens to generate]:max_tokens:' \
    '--no-stream[Disable streaming output]' \
    '--allow-sensitive[Allow reading sensitive files]' \
    '(-s --system)'{-s,--system}'[System prompt]:system_prompt:' \
    '(-u --use)'{-u,--use}'[Use prompt from library]:prompt:_nexus_prompts' \
    '(-f --file)'{-f,--file}'[Include file/directory content]:file:_files' \
    '(-d --default)'{-d,--default}'[Change default model]' \
    '--fuzzy[Fuzzy search model names]' \
    '--session[Session name]:session:_nexus_sessions' \
    '(-h --help)'{-h,--help}'[Show help message]' \
    '1: :->command' \
    '*:: :->args' && return 0

  case $state in
    command)
      _describe 'command' commands
      ;;
    args)
      case $words[1] in
        sessions)
          _arguments \
            '1: :_nexus_session_commands' \
            '2: :_nexus_sessions'
          ;;
        prompts)
          _arguments \
            '1: :_nexus_prompt_commands' \
            '2: :_nexus_prompts'
          ;;
        *)
          ;;
      esac
      ;;
  esac
}

_nexus "$@"
"""
    return zsh_script.strip()
