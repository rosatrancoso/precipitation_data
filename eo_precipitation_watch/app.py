"""Live dashboard for near-real-time satellite precipitation imagery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
import streamlit as st
from bs4 import BeautifulSoup


st.set_page_config(page_title="EO Precipitation Watch", page_icon="🌧️", layout="wide")
st.title("EO Precipitation Watch")
st.caption("Latest available satellite precipitation imagery from operational and near-real-time sources")

HEADERS = {"User-Agent": "EO-Precipitation-Watch/1.0 (dashboard)"}
TIMEOUT = 18


def get_bytes(url: str) -> tuple[bytes | None, str | None]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type.lower():
            return None, f"Endpoint returned {content_type or 'non-image content'}"
        return response.content, None
    except requests.RequestException as exc:
        return None, str(exc)


def page_images(page_url: str, keywords: tuple[str, ...]) -> list[tuple[str, str]]:
    """Return image URLs referenced by a provider page, ranked by useful names."""
    response = requests.get(page_url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[tuple[int, str, str]] = []
    for image in soup.find_all("img"):
        src = image.get("src") or image.get("data-src")
        if not src:
            continue
        absolute = urljoin(page_url, src)
        label = " ".join((image.get("alt", ""), src)).lower()
        score = sum(word in label for word in keywords)
        if absolute.startswith(("http://", "https://")):
            candidates.append((score, absolute, image.get("alt", "Provider image")))
    candidates.sort(reverse=True)
    return [(url, label) for score, url, label in candidates if score > 0][:5]


def show_image_card(title: str, description: str, source_url: str, image_url: str | None = None,
                    note: str | None = None) -> None:
    st.subheader(title)
    st.caption(description)
    if image_url:
        data, error = get_bytes(image_url)
        if data:
            st.image(data, use_container_width=True)
            st.caption(f"Image endpoint: {image_url}")
        else:
            st.info(f"Latest image could not be loaded: {error or 'unknown error'}")
            st.link_button("Open source viewer", source_url, use_container_width=True)
    elif note:
        st.info(note)
        st.link_button("Open source viewer", source_url, use_container_width=True)
    else:
        st.link_button("Open source viewer", source_url, use_container_width=True)


now = datetime.now(timezone.utc)
st.caption(f"Dashboard refreshed: {now:%Y-%m-%d %H:%M UTC}")
if st.button("Refresh latest images", type="primary"):
    st.rerun()

# GIBS exposes the half-hourly IMERG Early precipitation layer as a WMS image.
# Try recent half-hour boundaries because processing and publication can lag.
with st.spinner("Loading latest provider imagery…"):
    imerg_image = None
    imerg_note = None
    for age in range(4, 10):
        sample = now - timedelta(hours=age)
        sample = sample.replace(minute=(sample.minute // 30) * 30, second=0, microsecond=0)
        time_string = sample.strftime("%Y-%m-%dT%H:%M:%SZ")
        imerg_image = (
            "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
            "?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=IMERG_Precipitation_Rate_30min"
            f"&STYLES=&FORMAT=image/png&TRANSPARENT=true&SRS=EPSG:4326"
            f"&BBOX=-180,-90,180,90&WIDTH=1200&HEIGHT=600&TIME={time_string}"
        )
        payload, err = get_bytes(imerg_image)
        if payload:
            break
        imerg_image = None
        imerg_note = err

col1, col2 = st.columns(2)
with col1:
    show_image_card(
        "NASA GPM IMERG Early",
        "Global, half-hourly precipitation rate; imagery is usually several hours behind real time.",
        "https://gpm.nasa.gov/data/visualization",
        imerg_image,
        f"NASA GIBS did not return a usable image ({imerg_note or 'no recent frame found'}).",
    )

with col2:
    # JAXA's public viewer is the authoritative live visualization. Its map is
    # rendered client-side; try any server-rendered rain imagery in the page.
    jaxa_page = "https://sharaku.eorc.jaxa.jp/GSMaP/index.htm"
    jaxa_img = None
    jaxa_note = None
    try:
        images = page_images(jaxa_page, ("rain", "gsmap", "precip"))
        jaxa_img = images[0][0] if images else None
    except requests.RequestException as exc:
        jaxa_note = f"JAXA viewer is not reachable right now ({exc})."
    if not jaxa_img and not jaxa_note:
        jaxa_note = "JAXA renders its current rainfall map interactively; the live viewer is linked below."
    show_image_card("JAXA GSMaP_NRT", "Global, hourly precipitation estimates; NRT product latency is typically about 4 hours.",
                    jaxa_page, jaxa_img, jaxa_note)

col3, col4 = st.columns(2)
with col3:
    # H SAF product downloads can require account registration. The catalog
    # remains available publicly, while restricted images are handled gracefully.
    hsaf_page = "https://hsaf.meteoam.it/service/product_map.php?data_group=precipitation"
    hsaf_img = None
    hsaf_note = None
    try:
        images = page_images(hsaf_page, ("h60", "precip", "rain", "h40", "h61"))
        hsaf_img = images[0][0] if images else None
    except requests.RequestException as exc:
        hsaf_note = f"H SAF catalog could not be reached ({exc})."
    if not hsaf_img and not hsaf_note:
        hsaf_note = "H SAF lists current precipitation products, but product imagery/downloads may require a registered session."
    show_image_card("EUMETSAT H SAF", "Operational regional products include instantaneous rates and accumulated rainfall.",
                    hsaf_page, hsaf_img, hsaf_note)

with col4:
    # CHIRPS v3 Preliminary is updated by pentad and is distributed as gridded
    # data rather than as a single continuously updated global image.
    chirps_page = "https://www.chc.ucsb.edu/data/chirps3"
    chirps_img = None
    chirps_note = None
    try:
        images = page_images(chirps_page, ("chirps", "rain", "precip", "map"))
        chirps_img = images[0][0] if images else None
    except requests.RequestException as exc:
        chirps_note = f"CHIRPS page could not be reached ({exc})."
    if not chirps_img and not chirps_note:
        chirps_note = "CHIRPS Preliminary is a 0.05° land product updated every 5 days (about 2 days after each pentad). The provider distributes gridded files rather than a live map image."
    show_image_card("CHIRPS v3 Preliminary", "Satellite infrared plus station data; land coverage from 60°N to 60°S.",
                    chirps_page, chirps_img, chirps_note)

st.subheader("NOAA blended rain rate")
st.caption("Hourly global blend of recent passive-microwave satellite rain-rate retrievals.")
noaa_page = "https://www.ospo.noaa.gov/products/bRR/index.html"
noaa_animation = "https://origin-east-www-ospo.woc.noaa.gov/products/bRR/product_animation.html"
noaa_img = None
noaa_note = None
try:
    images = page_images(noaa_animation, ("global", "rain", "rr", "blend"))
    noaa_img = images[0][0] if images else None
except requests.RequestException as exc:
    noaa_note = f"NOAA animation page could not be reached ({exc})."
if not noaa_img and not noaa_note:
    noaa_note = "NOAA publishes an animated global blended rain-rate view; open the product viewer for the current frame."
show_image_card("NOAA OSPO Blended Rain Rate", "Global multisatellite rain-rate blend; output is generated hourly.",
                noaa_animation, noaa_img, noaa_note)

st.divider()
st.caption("Images and product availability are controlled by the data providers. Always check each provider's timestamp and quality notes before operational use.")
