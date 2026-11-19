
# IPMA

## Access via API

https://api.ipma.pt/

##  Live station observations

 [Hourly observations API, covering the last 24 hours](https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json). 
 
 ![Observations API](screenshot_obs_api.png "Observations API")

 
 The data refresh hourly. The [station list](https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json) gives station names, IDs and coordinates. 
 
 IPMA also provides a GeoJSON feed with recent observations.

Station names from main webpage: https://www.ipma.pt/pt/enciclopedia/redes.observacao/meteo/index.jsp

## Store in sqlite database

Update the DB:

    python ipma_observations_to_sqlite.py


Query the DB:

```sql
.tables
.schema obs
.headers on
.mode column
SELECT time, station, varname, value
FROM obs
ORDER BY time DESC
LIMIT 20;
```

Plot a station’s latest 24 hours in eight aligned panels, including wind direction and both hourly and running accumulated precipitation.

:x

 

