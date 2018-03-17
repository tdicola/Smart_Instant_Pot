# Base this container on the official Jupyter tensorflow notebook container.
# However pin to the current master version as recommended to prevent problems
# with future notebook changes (it is a moving target of releases).
FROM jupyter/tensorflow-notebook:30f16d52126f

# Install OpenCV with contrib package.
# There are _many_ ways to do this and this method with pip is required.
# Although the Anaconda environment is available and an option for installing
# OpenCV, the version installed with Anaconda _does not_ contain the OpenCV 3.0+
# contrib package compiled inside.  This package is very handy and contains
# non-commercial algorithms that are useful for academic and personal use like
# with this project.  Luckily there's a convenient binary wheel available with
# OpenCV 3.0+ and its contrib package, that's why pip is used to install OpenCV
# as below.  Be warned if you try to install OpenCV any other way you likely
# won't get the contrib package and will run into major issues.
RUN pip install opencv-contrib-python

# Install smart instant pot application code.
# This is installed in develop mode (-e) so it can be modified and run in place.
# Also note instead of being copied explicitly into the container it is expected
# to be there already from the file system sync of the parent directory to
# the Jupyter user work directory.
RUN pip install -e /home/jovyan/work/smart_instant_pot

# Run Jupyter lab instead of just the Jupyter notebook.
CMD ["start.sh", "jupyter", "lab"]
