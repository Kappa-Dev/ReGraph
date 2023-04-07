"""Setup for ReGraph."""

import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name='regraph',
    version='2.0.1',
    description='Graph rewriting and graph-based knowledge representation framework',
    author='Eugenia Oshurko',
    author_email='yarutoua@gmail.com',
    license='MIT License',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://dev.executableknowledge.org/ReGraph/",
    packages=[
        'regraph',
        'regraph.backends.neo4j',
        'regraph.backends.neo4j.cypher_utils',
        'regraph.backends.networkx'],
    package_dir={"regraph": "regraph"},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "matplotlib",
        "networkx",
        "numpy",
        "pyparsing",
        "lrparsing",
        "sympy",
        "greenery==3.3.1",
        "neo4j-driver==1.7.4",
        "neobolt"
    ]
)
