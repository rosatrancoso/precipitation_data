https://faq.hidrografico.pt/books/hidrografico/page/ogc-api-edr-rede-de-estacoes-maregraficas-ativas-observacoes

## Instituto Hidrográfico 

APIs Swagger Interfance: https://ogcapi.hidrografico.pt/openapi?f=html

Network of active tide gauge stations - Observations

https://ogcapi.hidrografico.pt/collections/tide_obs_nrt

Currently available data:

- **tide_obs_data_nrt_l1**: NRT data without QC (L1), sampled at 10- or 60-second intervals, with a latency of 1 minute and a rolling temporal window of 8 days
- **tide_obs_data_nrt_l2**: Data with automatic QC (L2), sampled at 5-minute intervals, with a latency of approximately 1 day and a rolling temporal window of **15 days**

URLS: 

- Stations Browser: https://ogcapi.hidrografico.pt/collections/tide_obs_nrt/items
- List stations: https://ogcapi.hidrografico.pt/collections/tide_obs_nrt/instances/l2/locations?f=json
- Get data: 
    https://ogcapi.hidrografico.pt/collections/tide_obs_nrt/instances/l2/locations/{station_id}?sea_surface_height,sea_surface_height_qc
     
    https://ogcapi.hidrografico.pt/collections/tide_obs_nrt/locations/152-303
    https://ogcapi.hidrografico.pt/collections/tide_obs_nrt/locations/152-303?f=json



|---------------------------|----------|-----------|------------------|--------------------|-----------------------|
|station_name               |station_id|lon        |lat               |last_date_time      |last_sea_surface_height|
|---------------------------|----------|-----------|------------------|--------------------|-----------------------|
|Funchal - B                |1001-307  |-16.9107824|32.6447835        |2026-11-18T23:55:00Z|1.774                  |
|Funchal                    |121-183   |-16.9107824|32.6447835        |2026-11-18T23:55:00Z|1.786                  |
|Leixões                    |12-184    |-8.7040444 |41.1854734        |2026-11-18T23:55:36Z|2.815                  |
|Vila Real de S. António - B|151-281   |-7.4133917 |37.1934389        |2026-11-18T23:55:00Z|2.531                  |
|Lisboa - Alcântara         |152-303   |-9.16325   |38.700193999999996|2026-11-18T23:55:00Z|2.809                  |
|Sesimbra - C               |156-279   |-9.1103589 |38.4397973        |2026-11-18T23:55:00Z|2.577                  |
|Base Naval de Lisboa       |157-280   |-9.1460925 |38.6732122        |2026-11-18T23:55:00Z|2.911                  |
|Leixões - B                |159-294   |-8.7040444 |41.1854734        |2026-11-18T23:55:00Z|2.755                  |
|Aveiro-B                   |160-285   |-8.7454002 |40.6441018        |2026-11-18T23:55:00Z|2.691                  |
|Peniche - C                |162-309   |-9.3674056 |39.3535667        |2026-11-18T23:55:00Z|2.727                  |
|---------------------------|----------|-----------|------------------|--------------------|-----------------------|




