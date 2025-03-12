**EC-LHC (PT-BR)**

This repository contains codes/programs related to the **Master’s Degree in Hydraulic Engineering and Sanitation** by **Alex Naoki Asato Kobayashi** from the Department of Hydraulic Engineering and Sanitation at the São Carlos School of Engineering (University of São Paulo).

Master’s Program Period: **February/2019** until **April 14, 2021** (deadline for thesis deposit).

Qualification approved: **March 3, 2020** (Committee: Edson Wendland, Rodrigo Porto, Maria Mercedes)

Master’s Defense: **Approved on May 19, 2021** (Committee: Edson Wendland, Osvaldo Cabral, Debora Regina Roberti)

---

## Phases of the Master’s Project
The Master’s project presented during the qualification basically consists of three main parts:
1. Definition of the processing program for “Eddy Covariance” using low-frequency data from the monitoring tower (IAB3).
2. Determination of the “Footprint” (contribution area) of the monitoring tower (IAB3).
3. Gap filling to generate the monitoring tower’s time series (Evapotranspiration/Energy Balance).

Achieving the objectives listed above requires the use of computational tools for data analysis.

### Analysis of Data Processed by EddyPro
The processed data analysis is the final step after converting and merging the binary data. In this step, various permutations are performed, measuring two main metrics (slope and correlation). By employing different computational tools, it was possible to vary day/time conditions and apply filters to improve understanding of the data, enabling classification of these permutations and identifying the one that achieves the best energy closure.

This processed data analysis, because it uses a contribution analysis filter, is closely related to the topic below.

### Analysis of the “Footprint” (Contribution Area)
Contribution analysis has three essential parts: (i) processed data, (ii) the Kljun et al. (2015) method, and (iii) the acceptance classification map. The processed data can be generated using either 2D coordinate rotation or planar fit, with the latter being more appropriate. The Kljun et al. (2015) method was chosen because it accounts for field heterogeneity, and the authors provided the code for its use. The vegetation classification map was created using **MapBiomas**, a widely used tool.

### Analysis of Gap Filling
The goal of gap filling is to create an evapotranspiration time series, allowing the determination of ET values for different times of the year at various scales: daily, seasonal, and annual.

Various gap-filling techniques are employed and evaluated based on correlation and the energy balance closure when comparing ET data to ET_estimated.

---

## Description of the Codes

### Raw Data Processing
This section explains the steps needed to obtain a raw data series for processing.

A tutorial on how to use and follow the recommended workflow for data processing is available [here](https://github.com/alexnaoki/EC-LHC/blob/master/info/etapas_processamento_dados_brutos.md).

### Bokeh
To use files with the **Bokeh** library, you must follow a few steps described [here](https://github.com/alexnaoki/EC-LHC/blob/master/info/descricao_arquivos_bokeh.md).

Programs developed with **Bokeh** primarily focus on data interactivity and analysis. Among the analyses performed are: contribution area analysis over different time periods, data visualization and analysis for energy balance closure using **Mauder and Foken (2004)** filters, rain filters, signal strength filters, and **Footprint** filters.

### Gap Filling
The gap-filling code is in `.py` format; however, the chosen workflow for performance visualization and general usage is through a Jupyter Notebook (or JupyterLab) with `.ipynb`.

The code containing the gap-filling methods can be found [here](https://github.com/alexnaoki/EC-LHC/blob/master/gapfilling/gapfilling_iab3.py).

Some prerequisites must be followed to use the gap-filling methods, which are described [here](https://github.com/alexnaoki/EC-LHC/blob/master/info/descricao_arquivo_gapfilling.md).

### bqplot **(DEPRECATED)**
The bqplot folder is no longer updated.  
> While bqplot is interesting, its performance is poor and it was mainly used to learn some interaction tools.
