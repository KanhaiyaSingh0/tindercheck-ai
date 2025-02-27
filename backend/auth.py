import requests

def get_tinder_token_with_facebook():
    # Replace with your Facebook access token
    fb_token = 'your-facebook-token'
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        'token': fb_token
    }
    
    response = requests.post('https://api.gotinder.com/v2/auth/login/facebook', 
                           headers=headers, 
                           json=data)
    
    if response.status_code == 200:
        return response.json().get('data', {}).get('api_token')
    else:
        raise Exception(f"Failed to get Tinder token: {response.text}")

def get_tinder_token_with_phone(phone_number):
    # First request OTP
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        'phone_number': phone_number
    }
    
    response = requests.post('https://api.gotinder.com/v2/auth/sms/send', 
                           headers=headers, 
                           json=data)
    
    if response.status_code != 200:
        raise Exception(f"Failed to request OTP: {response.text}")
    
    # Get OTP from user
    otp = input("Enter the OTP received on your phone: ")
    
    # Validate OTP
    data = {
        'phone_number': phone_number,
        'otp_code': otp
    }
    
    response = requests.post('https://api.gotinder.com/v2/auth/sms/validate', 
                           headers=headers, 
                           json=data)
    
    if response.status_code == 200:
        return response.json().get('data', {}).get('api_token')
    else:
        raise Exception(f"Failed to validate OTP: {response.text}") 