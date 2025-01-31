## Amsterdam carbage thesis
_By Corné Heijnen 12230170_

This repository is the code for the master thesis research project for the master Data Science in the year 2019-2020. The goal of this thesis is to optimize the configuration of the different fraction of underground garbage containers in the city of Amsterdam.

### Requirements
All code is produced for running in Python 3.7. The additional needed packages can be installed by running:
```
pip install -r requirements.txt
```

Or using Conda

```
conda install --file requirements.txt
```

### Usage
An example code can be run using the command:
```
python main.py
```

If the user has no access to the Amsterdam OIS analyse ruimte PostgreSQL database, the initial data should be request by emailing me or downloading from.... The data should be included in a folder with the destination ('../Data/postgres_db').


### Structure
All coding has been initially done in Jupyter Notebooks. All succesfull and reusable parts of these notebooks are encapsulated into codes and eventually added as Python-files (.py). These Python files in turn contain functions that can be loaded in into other Notebooks.
- The Code folder contains all .py files that are used for reused functions. The final code will also be in here.
- The Data folder contains a wide array of data, including some shapefiles, .csv-data and multiple .json files that are intermediate results. Files from this folder are loaded into notebooks or other code for use.
- The Images folder is filled with images that are results of algorithms and optimization attemps. These images are formed as output from code. Some of these images will be actually used in the final thesis.
- The Notebooks folder is filled with .ipynb files that are used for exploration. The use of these iPython Notebooks allows for easy exploration, but substantial results will be encapsulated in functions in .py files in the Code folder
- Presentations shows presentations done.

### Figures referred in paper
The figures reffered to in the paper are in the Bokeh for GIT folder. These are html based visualisations that can be viewed in the browser after downloading these.
