# -*- mode: sh -*-
# k-s theme
# derived from avit
#  - always show exit-status (✔ or ✗)
#  - display time (%T) colored with exit-status
#  - GIT: own line, great for larger branch names and nested directories
#  - GIT: no time since last commit
#  - GIT: if dirty, display only changed bits inside (), not a dirty icon.
#  - GIT: master branch shows ⬆ and white color, others show  and magenta
#  - do not mess with LSCOLORS/LS_COLOR or GREP_COLOR
#  - no vi or ruby
#
# Note: needs powerline-patched font!

local ret_status="%(?:%{$fg_bold[green]%}✔:%{$fg_bold[red]%}✗)"

local EMULATED=""
if [ `uname -s` = 'Darwin' ]; then
    local IS_ARM=`sysctl -n hw.optional.arm64 2>/dev/null || echo 0`
    if [ $IS_ARM -eq 1 ] && [ `uname -m` = 'x86_64' ]; then
        EMULATED="🌹"
    fi
fi

PROMPT='${EMULATED}${ret_status}%T$(_user_host) %{$fg_bold[blue]%}$(_current_dir)%{$resetcolor%}$(_extra_prompt)
%{$fg[$CARETCOLOR]%}%(!.#.$)%{$resetcolor%} '

function _extra_prompt() {
    local _status=""

    # git
    local _gpi=$(_git_prompt_info)
    if [[ -n "$_gpi" ]]; then
        _status="$_status$_gpi$(_git_status)"
        if [[ "$ZSH_THEME_GIT_PROMPT_REMOTE_STATUS" = 1 ]]; then
            local _grs=$(git_remote_status)
            if [[ -n "$_grs" ]]; then
                _status="$_status %{$fg_bold[white]%}$_grs"
            fi
        fi
    fi

    if [[ -n "$_status" ]]; then
        echo -e "\n$_status%{$reset_color%}"
    fi
}

function _git_prompt_info() {
    local ref
    if [[ "$(command git config --get oh-my-zsh.hide-status 2>/dev/null)" != "1" ]]; then
        ref=$(git_current_branch)
        if [[ -z "$ref" ]]; then
            return 0
        elif [[ "$ref" = "master" ]]; then
            echo "${ZSH_THEME_GIT_PROMPT_PREFIX_MASTER:-${ZSH_THEME_GIT_PROMPT_PREFIX}} $ref $(parse_git_dirty)$ZSH_THEME_GIT_PROMPT_SUFFIX"
        else
            echo "${ZSH_THEME_GIT_PROMPT_PREFIX_BRANCH:-${ZSH_THEME_GIT_PROMPT_PREFIX}} $ref $(parse_git_dirty)$ZSH_THEME_GIT_PROMPT_SUFFIX"
        fi
    fi
}

function _git_status() {
    local _s="$(git_prompt_status)"
    if [[ -n "$_s" ]]; then
        echo "%{$reset_color$fg_bold[white]%}($_s%{$reset_color$fg_bold[white]%})%{$reset_color%}"
    fi
}

function _current_dir() {
    local _max_pwd_length="72"
    if [[ $(echo -n $PWD | wc -c) -gt ${_max_pwd_length} ]]; then
        echo "%-2~/…/%3~"
    else
        echo "%~"
    fi
}

function _user_host() {
    if [[ -n $SSH_CONNECTION ]]; then
        echo " %{$fg[cyan]%}%n%{$reset_color%}@%{$fg[cyan]%}%m%{$reset_color%}"
    elif [[ $LOGNAME != $USER ]]; then
        echo " %{$fg[cyan]%}%n%{$reset_color%}"
    fi
}

if [[ $USER == "root" ]]; then
    CARETCOLOR="red"
else
    CARETCOLOR="cyan"
fi

ZSH_THEME_GIT_PROMPT_PREFIX_MASTER="%{$fg_bold[white]%}⬆%{$reset_color$fg[cyan]%}"
ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg_bold[white]%}%{$reset_color$fg[magenta]%}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%}"

ZSH_THEME_GIT_PROMPT_DIRTY=""
ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg_bold[green]%}✔%{$reset_color%}"
ZSH_THEME_GIT_PROMPT_ADDED="%{$fg_bold[green]%}✚"
ZSH_THEME_GIT_PROMPT_MODIFIED="%{$fg_bold[yellow]%}⚑"
ZSH_THEME_GIT_PROMPT_DELETED="%{$fg_bold[red]%}✖"
ZSH_THEME_GIT_PROMPT_RENAMED="%{$fg_bold[green]%}⇒"
ZSH_THEME_GIT_PROMPT_UNMERGED="%{$fg_bold[yellow]%}§"
ZSH_THEME_GIT_PROMPT_UNTRACKED="%{$fg_bold[yellow]%}!"
ZSH_THEME_GIT_PROMPT_STASHED="%{$fg_bold[magenta]%}★"

ZSH_THEME_GIT_PROMPT_EQUAL_REMOTE=" %{$fg_bold[green]%}✔ "
ZSH_THEME_GIT_PROMPT_AHEAD_REMOTE=" %{$fg_bold[green]%}↦ "
ZSH_THEME_GIT_PROMPT_BEHIND_REMOTE=" %{$fg_bold[yellow]%}↤ "
ZSH_THEME_GIT_PROMPT_DIVERGED_REMOTE=" %{$fg_bold[red]%}↮ "

if [ -z $ZSH_THEME_GIT_PROMPT_REMOTE_STATUS ]; then
    ZSH_THEME_GIT_PROMPT_REMOTE_STATUS=1
fi

if [ -z $ZSH_THEME_GIT_PROMPT_REMOTE_STATUS_DETAILED ]; then
    ZSH_THEME_GIT_PROMPT_REMOTE_STATUS_DETAILED=1
fi
