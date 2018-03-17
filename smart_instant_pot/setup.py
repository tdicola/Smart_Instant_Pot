# Python package configuration.
# Based on information and examples from:
#  https://packaging.python.org/en/latest/distributing.html
#  https://github.com/pypa/sampleproject
# Note this package is _not_ intended for distribution with PyPi, etc. and
# as such omits much of the cruft/configuration available to Python packages.
# Author: Tony DiCola
from setuptools import setup, find_packages


setup(
    name='smart_instant_pot',
    version='0.0.1',
    description='Smart Instant Pot monitor using computer vision.',
    packages=find_packages(),
    install_requires=['opencv-contrib-python'],

    # If there are data files included in your packages that need to be
    # installed, specify them here.
    #
    # If using Python 2.6 or earlier, then these have to be included in
    # MANIFEST.in as well.
    # package_data={  # Optional
    #     'sample': ['package_data.dat'],
    # },
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # `pip` to create the appropriate form of executable for the target
    # platform.
    #
    # For example, the following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    # entry_points={  # Optional
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # }
)
