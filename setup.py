"""Setup of regraph library."""

from setuptools import setup

setup(
    name='ReGraph',
    version='1.0',
    description='Graph rewriting tool',
    author='Eugenia Oshurko',
    license='MIT License',
    packages=['regraph'],
    package_dir={"regraph": "regraph"},
    zip_safe=False,
    install_requires=[
        "matplotlib",
        "networkx==1.11",
        "numpy",
        "pyparsing",
        "lrparsing",
        "sympy",
        "greenery",
    ]
)
