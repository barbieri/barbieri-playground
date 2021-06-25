#!/bin/sh

OLD_EMAIL=${1:?Missing old email}
NEW_EMAIL=${2}
shift 2

if [ -z "$NEW_EMAIL" ]; then
    NEW_EMAIL=`git config user.email`
fi

exec git filter-branch --commit-filter "
if [ \"\$GIT_COMMITTER_EMAIL\" = \"$OLD_EMAIL\" ]; then
    export GIT_COMMITTER_EMAIL=\"$NEW_EMAIL\"
fi
if [ \"\$GIT_AUTHOR_EMAIL\" = \"$OLD_EMAIL\" ]; then
    export GIT_AUTHOR_EMAIL=\"$NEW_EMAIL\"
fi
git commit-tree \"\$@\"
" "$@"
