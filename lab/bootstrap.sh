#!/bin/bash

# Ensure smart instant pot code is installed in develop mode.  This is done
# here before every start of the container because we're assuming the code is
# coming from a mounted volume.  If we tried to do this setup in the build of
# the Dockerfile it will fail because the mounted volume isn't available.
pip install -e /home/jovyan/work/smart_instant_pot

# Start Jupyter lab.
start.sh jupyter lab
