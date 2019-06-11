#!/bin/bash

bindir=$(dirname $0)
source $bindir/functions

echo $0 $*
echo

function usage {
    echo "add_py3_train_job.sh WORKDIR TEAM TASK"
}

workdir=$1
team="$2"
task="$3"

if [ -z "$workdir" ]; then
    usage
    exit 1
fi

if [ -z "$team" ]; then
    usage
    exit 1
fi

if [ -z "$task" ]; then
    usage
    exit 1
fi

enable_tox

commit_message="Add Python 3 Train unit tests

This is a mechanically generated patch to ensure unit testing is in place
for all of the Tested Runtimes for Train.

See the Train python3-updates goal document for details:
https://governance.openstack.org/tc/goals/train/python3-updates.html

Story: #2005924
Task: #$task

"

tracking_file="$workdir/master"
for repo in $(ls -d $workdir/openstack/*/); do

    echo
    echo "=== $repo python3-train jobs ==="
    echo

    repo_dir="$repo"
    (cd "$repo_dir" && git checkout python3-train)
    if python3-train -v --debug jobs add py3 train "$repo_dir"
    then
        (cd "$repo_dir" &&
                git add . &&
                git commit -m "$commit_message" &&
                git show)
    fi
done
