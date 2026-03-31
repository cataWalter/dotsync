# ~/.bashrc - Sample bash configuration for testing

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# Path configuration
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
export EDITOR="vim"
export TERM="xterm-256color"

# Aliases
alias ll="ls -la"
alias gs="git status"
alias gc="git commit"

# Functions
function mkcd() {
    mkdir -p "$1" && cd "$1"
}

# Git completion
if [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
fi

# Starship prompt
eval "$(starship init bash)"

# FZF
[ -f ~/.fzf.bash ] && source ~/.fzf.bash

# Check for tools
if command -v fzf &>/dev/null; then
    export FZF_DEFAULT_COMMAND="fd --type f"
fi

# Zoxide
eval "$(zoxide init bash)"
