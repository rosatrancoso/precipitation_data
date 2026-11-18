# EO Precipitation Watch

A small Streamlit dashboard for the latest available imagery from five Earth-observation precipitation sources: NASA GPM IMERG Early, JAXA GSMaP_NRT, EUMETSAT H SAF, CHIRPS v3 Preliminary, and NOAA OSPO Blended Rain Rate.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard checks provider pages at runtime and loads NASA's half-hourly IMERG layer through GIBS. Providers can change their page layout or availability; when an image cannot be retrieved, the card links to the official viewer/catalog. H SAF imagery may require registration, and CHIRPS is distributed primarily as gridded files with pentadal updates rather than a continuously refreshed image.
