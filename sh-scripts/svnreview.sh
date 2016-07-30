#!/bin/bash

svnstatus()
{
    echo -e "\033[1;32mSummary of Changes:"
    echo -e "\033[1;32m===================================================================\033[0m"
    svn status "$@" | while read ln; do
        op=`echo $ln | cut -d' ' -f1`
        case $op in
            M)
                echo -en "\033[1;33m"
                ;;
            D)
                echo -en "\033[1;31m"
                ;;
            A)
                echo -en "\033[1;32m"
                ;;
            ?)
                echo -en "\033[1;35m"
                ;;
            *)
                ;;
        esac
        echo -n "$ln"
        echo -e "\033[0m"
    done
    echo
}

svndiff()
{
    svn diff -x '-u -p' "$@" | colordiff
}

if test `basename $0` = "svnreview.sh"; then
    (svnstatus "$@"; svndiff "$@") | less -R
fi

