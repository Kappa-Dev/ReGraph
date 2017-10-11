"""Setup of regraph library."""

from setuptools import setup

setup(
    name='ReGraph',
    version='0.3',
    description='Graph rewriting tool',
    author='Eugenia Oshurko',
    license='MIT License',
    packages=['regraph'],
    package_dir={"regraph": "regraph"},
    zip_safe=False,
    install_requires=[
        "matplotlib",
        "networkx",
        "numpy",
        "pyparsing",
        "lrparsing",
        "sympy",
    ]
)
