# ReGraph

Graph Rewriting Library

## About project

## Environment configs 

### Requirement

The following `Python 3` packages are required

```
cycler==0.10.0
decorator==4.0.9
matplotlib==1.5.1
networkx==1.11
numpy==1.11.0
pyparsing==2.1.4
python-dateutil==2.5.3
pytz==2016.4
six==1.10.0
wheel==0.24.0
```

To avoid manual installation and to easily set up development environment you may consider following the instructions below:

### Create virtual environment

```
virtualenv venv -p path/to/your/python3
```

### Setup environment

To activate the virtual environment
```
source venv/bin/activate
```

To install required dependencies
```
pip install -r requirement.txt
```

## Installation

In order to install the **ReGraph** library you have to clone this repository using SSH
```
git clone git@github.com:eugeniashurko/ReGraph.git
```
or using HTTPS
```
https://github.com/eugeniashurko/ReGraph.git
```
Install the library with
```
python setup.py install
```

## Run tests

```
python tests/test.py
```
