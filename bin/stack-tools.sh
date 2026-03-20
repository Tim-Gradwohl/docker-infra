stackbackup() {
    local stack backupdir outfile

    # ensure we are exactly inside ~/stacks/apps/<stack>
    if [[ "$(dirname "$PWD")" != "$HOME/stacks/apps" ]]; then
        echo "❌ stackbackup must be run inside ~/stacks/apps/<stack-folder>"
        return 1
    fi

    stack="$(basename "$PWD")"
    backupdir="$HOME/stacks/backups/apps/$stack"

    mkdir -p "$backupdir"

    outfile="$backupdir/${stack}_$(date +%F_%H%M).tar.zst"

    echo "📦 Creating backup:"
    echo "   stack : $stack"
    echo "   file  : $outfile"

    tar -I zstd -cvf "$outfile" -C .. "$stack"

    echo "✅ Backup completed"
}

#stack: command but shorter: stk up immich
stk() {
    "$HOME/stacks/bin/stack" "$@"
}

#stack: stackcd immich
stackcd() {
    cd "$HOME/stacks/apps/$1"
}
