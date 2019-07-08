import googlemaps
import os

gmaps = googlemaps.Client(key=os.environ.get("GOOGLE_MAPS_API_KEY", "test"))
