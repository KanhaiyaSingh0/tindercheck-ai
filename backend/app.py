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

# Add this near the top of the file, after imports
TINDER_TOKENS = [
    'e4d30f8b-3607-48a0-a10d-df1675f0f90f',  # Original token    # Add more tokens here
    'b857a6ec-a5aa-4f8d-aace-f4952585f3ef',
]
current_token_index = 0

def get_tinder_token():
    """Rotate through available Tinder tokens"""
    global current_token_index
    token = TINDER_TOKENS[current_token_index]
    current_token_index = (current_token_index + 1) % len(TINDER_TOKENS)
    return token

def fetch_new_profiles():
    """Fetch new profiles from Tinder API using multiple tokens"""
    try:
        all_new_profiles = []
        errors = 0
        
        for _ in range(len(TINDER_TOKENS)):
            try:
                token = get_tinder_token()
                headers = {
                    'X-Auth-Token': token,
                    'Content-Type': 'application/json'
                }
                
                url = 'https://api.gotinder.com/v2/recs/core'
                print(f"\nTrying to fetch profiles with token: {token[:8]}...")
                
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('data', {}).get('results', []):
                    print(f"No results in response for token {token[:8]}")
                    continue
                
                current_time = time.time()
                
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
                        
                        profile_id = f"{profile['name']}_{profile['age']}"
                        print(f"Adding new profile: {profile_id}")
                        profile_database[profile_id] = profile
                        all_new_profiles.append(profile)
                
                if len(all_new_profiles) >= 10:
                    break
                    
            except Exception as e:
                print(f"Error with token {token[:8]}: {str(e)}")
                errors += 1
                continue
        
        print(f"\nFetch summary:")
        print(f"- New profiles added: {len(all_new_profiles)}")
        print(f"- Successful tokens: {len(TINDER_TOKENS) - errors}")
        print(f"- Failed tokens: {errors}")
        return all_new_profiles
    
    except Exception as e:
        print(f"Error in fetch_new_profiles: {str(e)}")
        traceback.print_exc()
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
    
    matches = []
    exact_matches = []
    search_count = 0
    
    # Debug info
    print(f"\nStarting search with criteria:")
    print(f"Name: '{name}', Location: '{location}', Age: '{age}'")
    print(f"Current database size: {len(profile_database)} profiles")
    
    while True:
        search_count += 1
        print(f"\nSearch iteration #{search_count}")
        
        # Search in existing profiles
        for profile_id, profile in profile_database.items():
            # Debug info for each profile check
            print(f"\nChecking profile: {profile_id}")
            print(f"Profile details: Name='{profile['name']}', Location='{profile['location']}', Age='{profile['age']}'")
            
            # Check for exact matches
            name_match = not name or name.lower() == profile['name'].lower()
            location_match = not location or location.lower() == str(profile['location']).lower()
            age_match = not age or str(age) == str(profile['age'])
            
            # Debug match info
            print(f"Match results - Name: {name_match}, Location: {location_match}, Age: {age_match}")
            
            if name_match and location_match and age_match:
                if profile not in exact_matches:
                    exact_matches.append(profile)
                    print(f"Found exact match: {profile['name']}")
            else:
                # Check for partial matches
                name_partial = not name or name.lower() in profile['name'].lower()
                location_partial = not location or location.lower() in str(profile['location']).lower()
                age_partial = not age or str(age) == str(profile['age'])
                
                if name_partial and location_partial and age_partial:
                    if profile not in matches:
                        matches.append(profile)
                        print(f"Found partial match: {profile['name']}")
        
        if exact_matches:
            print(f"\nFound {len(exact_matches)} exact matches after {search_count} iterations!")
            return exact_matches
            
        if len(matches) >= 5:
            print(f"\nFound {len(matches)} partial matches after {search_count} iterations")
            return matches
            
        print("\nFetching new profiles...")
        new_profiles = fetch_new_profiles()
        
        if not new_profiles:
            print("No new profiles fetched, waiting 2 seconds...")
            print(f"Current database state: {len(profile_database)} total profiles")
            time.sleep(2)
            continue

    return matches if matches else exact_matches

@app.route('/search', methods=['POST'])
def search():
    try:
        print("Received search request")
        
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        age = request.form.get('age', '').strip()
        
        print(f"Search parameters - Name: {name}, Location: {location}, Age: {age}")
        
        if not any([name, location, age]):
            return jsonify({
                "status": "error",
                "message": "Please provide at least one search criteria (name, location, or age)"
            }), 200
        
        # Search profiles continuously until matches are found
        matches = search_profiles(name, location, age)
        
        if not matches:
            search_criteria = []
            if name: search_criteria.append(f"name: {name}")
            if location: search_criteria.append(f"location: {location}")
            if age: search_criteria.append(f"age: {age}")
            
            return jsonify({
                "status": "searching",
                "message": f"Still searching for profiles matching ({', '.join(search_criteria)}). Please try again in a moment.",
                "suggestions": [
                    "Try the search again",
                    "Wait a few moments",
                    "Check if the search criteria are correct"
                ]
            }), 200
        
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