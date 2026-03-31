# ~/.vimrc - Sample vim configuration

" Plugin manager: vim-plug
call plug#begin('~/.vim/plugged')

" Plugins
Plug 'preservim/nerdtree'
Plug 'tpope/vim-fugitive'
Plug 'neoclide/coc.nvim', {'branch': 'release'}

call plug#end()

" Basic settings
set number
set relativenumber
set tabstop=4
set shiftwidth=4
set expandtab

" External commands
if executable('rg')
    set grepprg=rg\ --vimgrep
endif
