from setuptools import setup
from setuptools import find_packages
import os

requirements = ['numpy',
                'netCDF4',
                'pyresample',
                'pyyaml',
                'pillow',
                'rasterio']

readme_contents = ""

setup(
      name='satmaps',
      version=0.1,
      author='Mikhail Itkin',
      description='satellite processing suite',
      packages=['satmaps'],
      install_requires=requirements,
      test_suite='tests',
      classifiers=[
      'Development Status :: 5 - Production/Stable',
      'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
      'Programming Language :: Python',
      'Operating System :: OS Independent',
      'Intended Audience :: Science/Research',
      'Topic :: Scientific/Engineering'
      ],
      include_package_data = False,
      )
