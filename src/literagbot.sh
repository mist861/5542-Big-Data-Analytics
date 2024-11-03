#!/bin/bash

if grep -Fq "INIT = True" ./literagbot.config ; then

    version=$(python -V 2>&1 | grep -Po '(?<=Python )(.+)')
    if [[ -z "$version" ]]
    then
        echo "No Python detected, installing Python 3..."
        sudo apt install python3.11 
    else
        echo "Python $version installed"
    fi


    pip_version=$(pip -V 2>&1 | grep -Po '(?<=pip )(.+)')
    if [[ -z "$pip_version" ]]
    then
        echo "No pip detected, installing pip..."
        sudo apt install python3-pip -y
    else
        echo "pip $pip_version installed"
    fi

    echo "Installing virtualenv..."
    pip install virtualenv
    virtualenv literagbot_env

    echo "Activating virtualenv..."
    source literagbot_env/bin/activate

    echo "Installing dependencies..."
    pip install -r ./requirements.txt

    echo "Installing Vector Store..."
    python3 ./scripts/literagbot_init.py

    sed -i -e 's/INIT \= True/INIT \= False/g' ./literagbot.config

fi

echo "Initializing LiteRagBot..."
source literagbot_env/bin/activate
streamlit run ./scripts/literagbot_streamlit.py