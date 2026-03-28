_stack_completion() {
  local cur prev cmd subcmd
  local commands stacks prune_flags

  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  cmd="${COMP_WORDS[1]}"
  subcmd="${COMP_WORDS[2]}"

  commands="list status cd config validate doctor graph up down pull restart logs ps update backup recover"
  prune_flags="--keep --days --dry-run --yes"

  # Complete first argument: command
  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
    return 0
  fi

  stacks="$("$HOME/stacks/bin/stack" list 2>/dev/null) all"

  # Special handling: stack backup ...
  if [[ "$cmd" == "backup" ]]; then
    if [[ $COMP_CWORD -eq 2 ]]; then
      COMPREPLY=( $(compgen -W "$stacks prune" -- "$cur") )
      return 0
    fi

    if [[ "$subcmd" == "prune" ]]; then
      if [[ $COMP_CWORD -eq 3 ]]; then
        COMPREPLY=( $(compgen -W "$stacks" -- "$cur") )
        return 0
      else
        COMPREPLY=( $(compgen -W "$prune_flags" -- "$cur") )
        return 0
      fi
    fi
  fi

  # Commands that accept stack names
  case "$cmd" in
    cd|config|validate|doctor|graph|up|down|pull|restart|logs|ps|update|recover)
      COMPREPLY=( $(compgen -W "$stacks" -- "$cur") )
      return 0
      ;;
    *)
      return 0
      ;;
  esac
}

complete -F _stack_completion stack
complete -F _stack_completion stk
