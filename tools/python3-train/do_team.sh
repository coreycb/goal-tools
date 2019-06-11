#!/bin/bash -e

bindir=$(dirname $0)
source $bindir/functions

function usage {
    echo "do_team.sh WORKDIR TEAM [REPO...]"
}

workdir="$1"
shift
team="$1"
shift
repos="$@"

if [ -z "$workdir" ]; then
    usage
    exit 1
fi

if [ -z "$team" ]; then
    usage
    exit 1
fi

goal_url="https://governance.openstack.org/tc/goals/train/python3-updates.html"

out_dir=$(get_team_dir "$workdir" "$team")

if [ -e "$out_dir" ]; then
    echo "ERROR: $out_dir already exists!"
    echo "ERROR: These tools cannot be run against the same repository more than once."
    exit 1
fi

mkdir -p "$out_dir"

log_output "$out_dir" do_team

enable_tox

echo
echo "=== Getting storyboard details ==="
echo

story_id=2005924
task_id=$(grep -e "$team" $bindir/taskids.txt | awk '{print $1}')

echo "Story: $story_id"
echo "Task : $task_id"

if [ -z "$task_id" ]; then
    echo "Could not find task for $team"
    exit 1
fi

echo
echo "=== Updating extra project settings ==="
echo

set -x
(cd ../project-config && git checkout master && git pull)
set +x

echo
echo "=== Cloning $team repositories ==="
echo

set -e

python3-train -v --debug repos clone "$out_dir" "$team" $repos

$bindir/add_py3_train_job.sh "$out_dir" "$team" $task_id
