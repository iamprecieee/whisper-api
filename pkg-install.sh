#!/bin/bash

# Exit on error
set -e

# Simple script to install and add packages/dependencies to 'requirements.txt' simultaneously
for arg in "$@"
do 
    if [ $arg = "requirements" ]; then
        echo "installing requirements..."
        python3 -m pip install -r requirements.txt
        echo "done."
    elif [ $arg != "requirements" ]; then
        echo "installing $arg..."
        python3 -m pip install $arg

        echo "copying $arg to 'requirements.txt' file..."
        python3 -m pip freeze > requirements.txt
        echo "done."
    fi
done