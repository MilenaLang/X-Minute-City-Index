# X-Minute-City Composite Index

Create your own accessibility analysis for your city and needs!
Forked and improved based on https://github.com/MilenaLang/X-Minute-City-Index.

This repository is used to calculate an x-minute city composite index for every GHSL settlement area. 
The goal of this project is to assess pedestrian acccessibility and walkability at different timeframes.
It can be used for urban planning purposes or individual assessment of cities.


## Relevance 
The 15-minute city concept envisions access to all essential services - 
including living, working, commerce, healthcare, education and entertainment - 
within a 15-minute walk or bike ride. 

As accessibility is not equal throughout a city or across cities, a tool to measure pedestrian accessibility is necessary for urban planners and stakeholders to implement the concept. 
Existing composite indices often lack timeframe-adaptability and inclusivity by assuming uniform service needs. 
Thus, this composite index includes the adaptable timeframe of the x-minute city.  

## Methodology
The script uses open-source OpenStreetmap (OSM) Points of Interest (POIs) for amenities and WorldPop data for population density. 
POIs for healthcare, commerce, education and entertainment are fetched via [OSMnx](https://osmnx.readthedocs.io/en/stable/) and cleaned for routing. 
Small neighborhood units are represented as [h3](https://h3geo.org) hexagonal grid cells of approximately 1km x 1km and filtered to habited areas. 
Walking time matrices are generated using [openrouteservice (ORS)](https://openrouteservice.org/) with manual speed adjustments per population group. 

The time matrices are calculated between POIs and each hexagon's center. 
The number of reachable POIs per category is scaled to 0-100 by using benchmarks (e.g. 5 healthcare facilities). 
The final index score is the sum of normalized scores across categories. 

## Requirements


## Usage
Usage of the script: 
1. Install all software requirements if necessary
2. Fork the repository 
3. Deploy and activate ORS docker
4. Deploy the worldpop data as postresql database & provide it at `.env` file (please copy `.env_template` and rename it as `.env`)
5. Run the following command:
```shell
$ python -m xmin_core.main_xmin_urcls
```
6. Run the script with your self-defined work directory (Don't forget moving `resources/urcls_4229_int_poly` into your directory).

Note: The script  can be adapted to different amenities, priorities and walking speeds. It can also be transfered to other countries by using country-specific osm.pbf files and eurostat/worldpop demographic data.
- to switch category priorities, change the weighting in the code
- to change demographic data, specify another dataset as population data
## Author 
This project is part of a master's thesis in geoinformatics by Milena Bremer.

