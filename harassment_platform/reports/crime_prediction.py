import numpy as np
from scipy.stats import gaussian_kde
from django.shortcuts import render
from .models import HarassmentReport
import json

def predict_crime_hotspot():
    # Get all reports with latitude & longitude
    reports = HarassmentReport.objects.exclude(latitude=None, longitude=None)

    if reports.count() < 3:  # Ensure enough data points for KDE
        return None  # Not enough data to predict

    # Convert data into numpy array
    locations = np.array([[report.latitude, report.longitude] for report in reports]).T  # Transpose for KDE

    # Apply Kernel Density Estimation (KDE)
    kde = gaussian_kde(locations)

    # Evaluate density at all reported locations
    densities = kde(locations)

    # Get indices of the top 20 highest densities
    sorted_indices = np.argsort(densities)[::-1][:20]  # Sort in descending order and pick top 20

    # Get the top 20 hotspot locations
    hotspots = []
    for index in sorted_indices:
        hotspot_lat, hotspot_lng = locations[:, index]
        hotspots.append({'lat': hotspot_lat, 'lng': hotspot_lng})

    return hotspots