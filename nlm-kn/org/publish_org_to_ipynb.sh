#!/usr/bin/env bash

# Publish each Org mode fie in the directory containing this script to
# its corresponding Jupyter notebook.

# Assign home directory of this script
home=$(dirname $(dirname $(realpath $0)))

# Tangle, and convert to a Jupyter notebook file, each Org mode file
org_files=$(ls $home/org/*.org)
for org_file in $org_files; do
    ipynb_file=$(basename $org_file | sed s/.org/.ipynb/)

    echo "Tangling $(basename $org_file)"
    emacs --batch --eval "(require 'org)" --eval "(org-babel-tangle-file \"$org_file\")"

    echo "Converting $(basename $org_file) to $ipynb_file"
    cat $org_file | sed 's/src python/src jupyter-python/' > tmp.org
    pandoc tmp.org --wrap=preserve -o $home/ipynb/$ipynb_file
    rm tmp.org

done

# Blacken all Python files
black $home/py/*.py
