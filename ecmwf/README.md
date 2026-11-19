
https://www.ecmwf.int/en/computing/software/ecmwf-web-api


ECMWF’s forecast charts are available here: [ECMWF Charts](https://www.ecmwf.int/en/forecasts/charts).

ECMWF publishes griddedforecasts as GRIB2 through its free Open Data service. The simplest command-line workflow is to use ECMWF’s Python client:

```python
import sys
from ecmwf.opendata import Client

model = sys.argv[1] if len(sys.argv) > 1 else "ifs"
client = Client(model=model, resol="0p25")

result = client.retrieve(
    type="fc",
    stream="oper",
    step=[0, 24, 48, 72],
    param=["2t", "tp", "msl", "10u", "10v"],
    target=f"{model}_portugal.grib2",
)

print(f"Run: {result.datetime}")
````

Model names can be `ifs`, `aifs-single`, and `aifs-ens`. 

For IFS at 0.1° resolution, change resol="0p25" to resol="0p1".  
AIFS is available only at 0.25°. 

The download is a global grid. To extract a bounding box locally, use a GRIB tool such as wgrib2 or CDO after downloading. 

Forecast files are retained on a rolling basis for roughly 2–3 days, and a requested run may not be available immediately. 

The ECMWF client and parameter options are documented in the [ecmwf-opendata repository](https://github.com/ecmwf/ecmwf-opendata); the [Open Data page](https://www.ecmwf.int/en/forecasts/datasets/open-data) lists available fields.

