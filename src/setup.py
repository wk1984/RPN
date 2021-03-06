__author__="huziy"
__date__ ="$Aug 19, 2011 8:37:46 PM$"

from setuptools import setup,find_packages

setup (
  name = 'RPN',
  version = '0.1',
  packages = find_packages(),

  # Declare your packages' dependencies here, for eg:
  install_requires=["matplotlib", "numpy", "netCDF4", "osgeo", "descartes", "shapely", "scipy",
                    "GChartWrapper", "pykml", "lxml", "pandas", "pyresample", "fiona", "tables", "brewer2mpl",
                    'iris', 'seaborn', 'lmoments3',],

  # Fill in these to make your Egg ready for upload to
  # PyPI
  author = 'huziy',
  author_email = '',

  summary = 'rpn',
  url = '',
  license = '',
  long_description= 'Long description of the package',

  # could also include long_description, download_url, classifiers, etc.

  
)