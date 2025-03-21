import os, random
from django.shortcuts import render, redirect
from .models import HarassmentReport, Upvote
from .forms import HarassmentReportForm
from geopy.geocoders import Nominatim
import json
from scipy.stats import gaussian_kde
#from reports.crime_prediction import predict_crime_hotspot  # ✅ Absolute Import
import numpy as np  # Add this line at the top
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import HarassmentReport, Upvote

def upvote_report(request, report_id):
    if request.method == "POST":
        try:
            # Retrieve the report
            report = get_object_or_404(HarassmentReport, id=report_id)
            
            # Get the user's IP address
            ip_address = request.META.get('REMOTE_ADDR')
            if not ip_address:
                return JsonResponse({'status': 'error', 'message': 'Unable to determine IP address.'}, status=400)
            
            # Check if the user has already upvoted this report
            if Upvote.objects.filter(ip_address=ip_address, report=report).exists():
                return JsonResponse({'status': 'already_upvoted', 'upvotes': report.upvotes})
            
            # Add upvote
            Upvote.objects.create(
                ip_address=ip_address,
                report=report
            )
            report.upvotes += 1
            report.save()
            
            return JsonResponse({'status': 'success', 'upvotes': report.upvotes})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        
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
    sorted_indices = np.unique(np.argsort(densities)[::-1])[:20]  # Sort in descending order and pick top 20

    # Get the top 20 hotspot locations
    hotspots = []
    for index in sorted_indices:
        hotspot_lat, hotspot_lng = locations[:, index]
        hotspots.append({'lat': hotspot_lat, 'lng': hotspot_lng, 'title': f"Hotspot {index+1}", 'description': "Predicted crime hotspot"})
    
    return hotspots

def home(request):
    # Get predicted hotspots
    reports = HarassmentReport.objects.all()
    
    # Convert reports to a format suitable for JavaScript
    reports_data = [
        {
            'lat': report.latitude,  # Make sure these match your model field names
            'lng': report.longitude,
            'location': report.location,
            'type': report.harassment_type
        } for report in reports
    ]  # Ensuring empty list if None
    predicted_hotspot = predict_crime_hotspot()
    context = {
        'reports': json.dumps(reports_data) , # Pass the formatted hotspots data
        'hotspot': json.dumps(predicted_hotspot)
    }

    return render(request, 'home.html', context)


def reports_list(request):
    reports = HarassmentReport.objects.all().order_by('-timestamp')

    # Apply filters
    type_filter = request.GET.get('type')
    location_filter = request.GET.get('location')
    if type_filter:
        reports = reports.filter(harassment_type=type_filter)
    if location_filter:
        reports = reports.filter(location__icontains=location_filter)

    # Assign random profile images
    images = os.listdir('harassment_platform/static/images/profile_pictures/')
    for report in reports:
        report.random_image = random.choice(images)

    return render(request, 'reports.html', {'reports': reports})

def report_submission(request):
    if request.method == "POST":
        location = request.POST.get('location')
        date = request.POST.get('date')
        time = request.POST.get('time')
        harassment_type = request.POST.get('harassment_type')
        reported_by = request.POST.get('role')
        description = request.POST.get('description')
        

        # Validate harassment_type
        if not harassment_type:
            return render(request, 'report_submission.html', {'error': 'Harassment type is required.'})

        try:
            # Geocode the location to get latitude and longitude
            geolocator = Nominatim(user_agent="harassment_report_app")
            location_data = geolocator.geocode(location)
            
            if location_data:
                latitude = location_data.latitude
                longitude = location_data.longitude
            else:
                return render(request, 'report_submission.html', 
                            {'error': 'Could not find coordinates for the given location.'})

            # Save the data to the database
            HarassmentReport.objects.create(
                location=location,
                date=date,
                time=time,
                harassment_type=harassment_type,
                reported_by=reported_by,
                description=description,
                latitude=latitude,
                longitude=longitude
            )

            # Add a success message and redirect to the same page
            return render(request, 'report_submission.html', {'success': True})
            
        except Exception as e:
            return render(request, 'report_submission.html', 
                        {'error': f'Error processing location: {str(e)}'})
    
    return render(request, 'report_submission.html')
