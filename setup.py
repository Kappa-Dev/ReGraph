"""Setup of regraph library."""

from setuptools import setup
setup(name='ReGraph',
      version='0.3',
      description='Graph rewriting tool',
      author='Eugenia Oshurko',
      license='MIT License',
      packages=['regraph',
                'regraph.library'
                ],
      zip_safe=False)
