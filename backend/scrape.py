import requests
import json
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def calculate_age(birth_date):
    if birth_date:
        birth_date = datetime.strptime(birth_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return None

def fetch_all_profiles():
    url = 'https://api.gotinder.com/v2/recs/core'
    headers = {
        'X-Auth-Token': 'a645c3d9-964f-4a87-8cd9-f19d83e90edd',  # Replace with your Tinder API token
        'Content-Type': 'application/json'
    }

    # Set up retry logic
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    profiles = []
    request_count = 0

    while True:
        try:
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            new_profiles = []
            for result in data.get('data', {}).get('results', []):
                user = result.get('user', {})
                name = user.get('name', 'Unknown')
                birth_date = user.get('birth_date', None)
                age = calculate_age(birth_date)
                location = user.get('city', {}).get('name', 'Unknown')
                last_active = user.get('ping_time', 'Unknown')

                # Get all profile pictures
                profile_pictures = []
                for photo in user.get('photos', []):
                    photo_url = photo.get('url')
                    if photo_url:
                        profile_pictures.append(photo_url)

                # Only create profile if there's at least one picture
                if profile_pictures:
                    profile = {
                        'name': name,
                        'age': age,
                        'location': location,
                        'profile_pictures': profile_pictures,  # Store all pictures
                        'last_active': last_active,
                        'bio': user.get('bio', ''),  # Added bio field
                        'gender': user.get('gender', 'Unknown'),  # Added gender field
                        'distance_mi': result.get('distance_mi', 'Unknown'),  # Added distance field
                        'is_verified': user.get('verified', False)  # Added verification status
                    }
                    new_profiles.append(profile)

            # If no new profiles are received, break the loop
            if not new_profiles:
                print("No more profiles available. Fetching complete.")
                break

            profiles.extend(new_profiles)
            request_count += 1
            print(f"Request {request_count}: Fetched {len(new_profiles)} new profiles. Total so far: {len(profiles)}")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Tinder API: {e}")
            break

    return profiles

def scrape_tinder_profiles():
    # Fetch all available profiles
    new_profiles = fetch_all_profiles()

    if not new_profiles:
        print("No new profiles fetched.")
        return

    # Load existing data if file exists
    existing_profiles = []
    if os.path.exists('profiles.json'):
        with open('profiles.json', 'r') as f:
            try:
                existing_profiles = json.load(f)
            except json.JSONDecodeError:
                existing_profiles = []

    # Create a set of existing profile IDs (using name+age+location as a unique identifier)
    existing_profile_ids = {
        f"{p['name']}_{p['age']}_{p['location']}" 
        for p in existing_profiles
    }

    # Only add profiles that don't already exist
    profiles_to_add = []
    for profile in new_profiles:
        profile_id = f"{profile['name']}_{profile['age']}_{profile['location']}"
        if profile_id not in existing_profile_ids:
            profiles_to_add.append(profile)
            existing_profile_ids.add(profile_id)

    # Append new unique profiles to existing ones
    existing_profiles.extend(profiles_to_add)

    # Save updated data back to JSON file
    with open('profiles.json', 'w') as f:
        json.dump(existing_profiles, f, indent=4)

    print(f"Added {len(profiles_to_add)} new unique profiles. Total profiles stored: {len(existing_profiles)}")

if __name__ == '__main__':
    scrape_tinder_profiles()