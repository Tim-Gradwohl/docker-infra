stack() {
    local target

    if [[ "${1:-}" == "cd" ]]; then
        target="$("$HOME/stacks/bin/stack" "$@")" || return $?
        builtin cd -- "$target"
        return $?
    fi

    "$HOME/stacks/bin/stack" "$@"
}

#stack: command but shorter: stk up immich
stk() {
    stack "$@"
}
