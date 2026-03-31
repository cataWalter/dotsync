# ~/.zshrc - Alternative dotfile for testing diff

# Different path configuration
export PATH="$HOME/bin:/usr/local/bin:$PATH"
export EDITOR="vim"
export TERM="screen-256color"

# Different aliases
alias ll="ls -l"
alias gs="git status"
alias gc="git commit -m"

# Different functions
function mkcd() {
    mkdir -p "$1" && cd "$1"
}

function cleanup() {
    rm -rf "$1"
}

# Different plugin manager (oh-my-zsh instead of zinit)
export ZSH="$HOME/.oh-my-zsh"
source "$ZSH/oh-my-zsh.sh"

# Different prompt (powerlevel10k instead of starship)
source ~/.p10k.zsh

# FZF configuration
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Different tools (autojump instead of zoxide)
[ -f /etc/profile.d/autojump.sh ] && . /etc/profile.d/autojump.sh

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Different custom scripts path
export PATH="$HOME/bin/scripts:$PATH"
