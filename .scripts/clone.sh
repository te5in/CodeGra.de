#!/bin/bash

set -o xtrace
set -e

ssh_key_file="$1"
clone_url="$2"
commit="$3"
out_dir="$4"
branch="$5"

export GIT_SSH_COMMAND="ssh -i $ssh_key_file -F /dev/null -o StrictHostKeyChecking=no"
git clone --depth=50 --branch="$branch" "$clone_url" "$out_dir"
cd "$out_dir"
git checkout -qf "$commit"
