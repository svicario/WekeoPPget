# WekeoPPget
Python wrapper for [Wekeo API](https://www.wekeo.eu/docs/harmonised-data-access-api) to download [HR-VPP copernicus products](https://land.copernicus.eu/pan-european/biophysical-parameters/high-resolution-vegetation-phenology-and-productivity).
The Wrapper allows to perform in one request the 5 interactions required by WEKEO
Notice that the wrapper accept the term and condition of [Copernicus](https://www.copernicus.eu/en/access-data/copyright-and-licences) 
Further the wrapper, following the cookie-cutter approach of eLTER-PLUS project, use a shapefile to define a bounding box to cut locally the tile downloaded from WEKEO. This had the advantage to download long time series or several statistics without overloading the memory of the computer.
Given the cut is done on the client side, the bandwith to download the full tile is consumed.

usage: WereoPPget [-h] [--user USER] [--pswd PSWD] [--tif] [--start START] [--end END] [--shape SHAPEFILE] [--buffer BUFFER]
             [--tile TILE] (--yearly YEARLY | --daily DAILY | --10daily DAILY10) [--seasons SEASONS]

WekeoPPget options:

    -h, --help         show this help message and exit
    --login LOGIN      json file where to recover user and password for the account on wekeo
    --tif              add option if you want cutted element in tif format and not in netcdf4
    --start START      start time e.g. '2017-01-01' or '2017-01-01 17:02:01'
    --end END          start time e.g. '2020-12-01' or '2020-12-01 17:02:01'
    --shape SHAPEFILE  path for the shapefile of region of interest in WGS84 projection
    --buffer BUFFER    buffer in meter around the shape
    --tile TILE        name of tile of interest
    --yearly YEARLY    write 'TPROD,...' 
    --daily DAILY      write a subset of this list 'PPI,NDVI,FAPAR,LAI,QFLAG'
    --10daily DAILY10  write 'PPI,QFLAG'
    --seasons SEASONS  write a subset of this list 's1,s2'


for the yearly mode the possible statistics are:

  - MAXV,MAXD : value and date of the maximum
  - MINV      : value of the minimum
  - AMPL      : difference in value between minimum and maximum
  - SOSV, SOSD: value and date of the start of the season 
  - EOSV, EOSD: value and date of the end of the season
  - LENGTH    : difference in date between end and start
  - LSLOPE, RSLOPE: slope on the flex point of the increasing and decreasing part of the season
  - TPROD,SPROD: Integral under the full curve or removing minimum value 
