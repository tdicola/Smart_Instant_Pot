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

# Install bootstrap / start command script and make it executable.
# This bootstrap script installs the smart instant pot code (which can't be
# installed during this build because we want to install it from a mounted
# volume that won't exist yet) and then starts Jupyter lab.  For some peculiar
# reason docker requires us to elevate to root to change permissions.
USER root
COPY bootstrap.sh /bootstrap.sh
RUN chmod a+x /bootstrap.sh

# Go back to the Jupyter lab user and run the bootstrap script.
USER jovyan
CMD /bootstrap.sh
