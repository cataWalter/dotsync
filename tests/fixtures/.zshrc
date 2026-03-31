# ~/.zshrc - Sample dotfile for testing

# Path configuration
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
export EDITOR="nvim"
export TERM="xterm-256color"

# Aliases
alias ll="ls -la"
alias gs="git status"
alias gc="git commit"
alias gp="git push"

# Functions
function mkcd() {
    mkdir -p "$1" && cd "$1"
}

function extract() {
    if [ -f "$1" ]; then
        case "$1" in
            *.tar.bz2)   tar xjf "$1"   ;;
            *.tar.gz)    tar xzf "$1"   ;;
            *.zip)       unzip "$1"     ;;
            *)           echo "Unknown format" ;;
        esac
    fi
}

# Plugin manager (zinit)
source "$HOME/.zinit/bin/zinit.zsh"

# Plugins
zinit light zsh-users/zsh-autosuggestions
zinit light zsh-users/zsh-syntax-highlighting
zinit light romkatv/powerlevel10k

# Starship prompt
eval "$(starship init zsh)"

# FZF configuration
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Check for required commands
if command -v fzf &>/dev/null; then
    export FZF_DEFAULT_COMMAND="fd --type f"
fi

if command -v rg &>/dev/null; then
    export FZF_DEFAULT_OPTS="--preview 'bat --color=always {}'"
fi

# Zoxide
eval "$(zoxide init zsh)"

# Homebrew
if [ -d "/opt/homebrew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Custom scripts path
export PATH="$HOME/.scripts:$PATH"
