from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import traceback
from datetime import datetime
import time

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Tinder Check AI Backend is running",
        "endpoints": {
            "search": "/search (POST) - Search for profiles"
        }
    })

# Store all profiles with timestamp
profile_database = {}
PROFILE_EXPIRY = 3600  # 1 hour in seconds

def get_tinder_token():
    return 'bb233480-434e-4c3d-8ce2-1ee5dc5c935a'

def fetch_new_profiles():
    """Fetch new profiles from Tinder API"""
    try:
        token = get_tinder_token()
        headers = {
            'X-Auth-Token': token,
            'Content-Type': 'application/json'
        }
        
        url = 'https://api.gotinder.com/v2/recs/core'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        current_time = time.time()
        new_profiles = []
        
        for result in data.get('data', {}).get('results', []):
            user = result.get('user', {})
            
            profile_pictures = []
            for photo in user.get('photos', []):
                photo_url = photo.get('url')
                if photo_url:
                    profile_pictures.append(photo_url)

            if profile_pictures:
                profile = {
                    'name': user.get('name', ''),
                    'age': user.get('age', ''),
                    'location': user.get('city', {}).get('name', ''),
                    'profile_pictures': profile_pictures,
                    'bio': user.get('bio', ''),
                    'last_active': user.get('ping_time'),
                    'timestamp': current_time
                }
                
                # Use name+age as unique identifier
                profile_id = f"{profile['name']}_{profile['age']}"
                profile_database[profile_id] = profile
                new_profiles.append(profile)
        
        print(f"Fetched {len(new_profiles)} new profiles")
        return new_profiles
    
    except Exception as e:
        print(f"Error fetching profiles: {e}")
        return []

def clean_old_profiles():
    """Remove profiles older than PROFILE_EXPIRY"""
    current_time = time.time()
    expired_profiles = [
        profile_id for profile_id, profile in profile_database.items()
        if current_time - profile['timestamp'] > PROFILE_EXPIRY
    ]
    
    for profile_id in expired_profiles:
        del profile_database[profile_id]

def search_profiles(name='', location='', age=''):
    """Search profiles in database and fetch new ones if needed"""
    clean_old_profiles()
    
    # First search in existing profiles
    matches = []
    for profile in profile_database.values():
        name_match = not name or name.lower() in profile['name'].lower()
        location_match = not location or location.lower() in str(profile['location']).lower()
        age_match = not age or str(age) == str(profile['age'])
        
        if name_match and location_match and age_match:
            matches.append(profile)
    
    # If no matches or few matches, fetch new profiles
    if len(matches) < 5:
        new_profiles = fetch_new_profiles()
        
        # Search through new profiles
        for profile in new_profiles:
            name_match = not name or name.lower() in profile['name'].lower()
            location_match = not location or location.lower() in str(profile['location']).lower()
            age_match = not age or str(age) == str(profile['age'])
            
            if name_match and location_match and age_match and profile not in matches:
                matches.append(profile)
    
    return matches

@app.route('/search', methods=['POST'])
def search():
    try:
        print("Received search request")
        
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        age = request.form.get('age', '').strip()
        
        print(f"Search parameters - Name: {name}, Location: {location}, Age: {age}")
        
        if not any([name, location, age]):
            return jsonify({"error": "Please provide at least one search criteria"}), 400
        
        # Search profiles
        matches = search_profiles(name, location, age)
        
        if not matches:
            # Try one more time with fresh data
            fetch_new_profiles()
            matches = search_profiles(name, location, age)
            
            if not matches:
                return jsonify({"error": "No matches found. Try different search criteria."}), 404
        
        # Handle image upload
        image_file = request.files.get('image')
        if image_file:
            print("Processing image search")
            profiles_with_similarity = []
            image_file.seek(0)
            
            for profile in matches:
                image_file.seek(0)
                profile_images = profile.get('profile_pictures', [])
                if profile_images:
                    similarity = compare_images(image_file, profile_images)
                    print(f"Similarity with {profile['name']}: {similarity}")
                    if similarity > 0.5:
                        profiles_with_similarity.append((profile, similarity))
            
            if profiles_with_similarity:
                sorted_profiles = sorted(profiles_with_similarity, key=lambda x: x[1], reverse=True)
                result = [p[0] for p in sorted_profiles[:5]]
                return jsonify(result)
        
        # Return text-based results
        print(f"Returning {len(matches[:5])} matches")
        return jsonify(matches[:5])

    except Exception as e:
        error_msg = f"Error in search endpoint: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({"error": str(e)}), 500

def compare_images(uploaded_image, profile_image_urls):
    """Compare uploaded image with profile images and return highest similarity score"""
    try:
        # Convert uploaded image to numpy array
        file_bytes = np.frombuffer(uploaded_image.read(), np.uint8)
        uploaded_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        max_similarity = 0
        for url in profile_image_urls:
            # Download and convert profile image
            resp = requests.get(url)
            profile_img_array = np.frombuffer(resp.content, np.uint8)
            profile_img = cv2.imdecode(profile_img_array, cv2.IMREAD_COLOR)
            
            # Resize images to same dimensions
            size = (224, 224)
            uploaded_img_resized = cv2.resize(uploaded_img, size)
            profile_img_resized = cv2.resize(profile_img, size)
            
            # Calculate similarity using Mean Squared Error
            err = np.sum((uploaded_img_resized.astype("float") - profile_img_resized.astype("float")) ** 2)
            err /= float(uploaded_img_resized.shape[0] * uploaded_img_resized.shape[1])
            
            # Convert error to similarity score (0 to 1)
            similarity = 1 - (err / 255**2)
            max_similarity = max(max_similarity, similarity)
            
        return max_similarity
    except Exception as e:
        print(f"Error comparing images: {e}")
        return 0

if __name__ == '__main__':
    # Fetch initial profiles
    fetch_new_profiles()
    app.run(host='0.0.0.0', port=10000)