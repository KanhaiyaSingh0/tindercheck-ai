import React, { useState } from 'react';
import './App.css';
import ImageUpload from './ImageUpload';

// Make sure this line is here and correct
const API_URL = process.env.REACT_APP_API_URL || 'https://tindercheck-ai-backend.onrender.com';

function App() {
    const [name, setName] = useState('');
    const [location, setLocation] = useState('');
    const [age, setAge] = useState('');
    const [selectedImage, setSelectedImage] = useState(null);
    const [results, setResults] = useState([]);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);
        
        try {
            console.log('Starting search with API URL:', API_URL);
            const formData = new FormData();
            formData.append('name', name);
            formData.append('location', location);
            formData.append('age', age);
            
            if (selectedImage) {
                console.log('Adding image to form data');
                formData.append('image', selectedImage);
            }

            // Updated fetch call
            console.log('API URL:', API_URL);
            console.log('Full request URL:', `${API_URL}/search`);
            const response = await fetch(`${API_URL}/search`, {
                method: 'POST',
                body: formData,
                // Remove any headers when sending FormData
            });

            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.length === 0) {
                setError('No matches found. Try different search criteria.');
            } else {
                console.log('Search results:', data);
                setResults(data);
            }
            
        } catch (error) {
            console.error('Detailed error:', error);
            setError(error.message);
            setResults([]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="App">
            <h1>TinderCheck AI</h1>
            <ImageUpload onImageSelect={setSelectedImage} />
            {selectedImage && <p className="success-message">Image selected successfully!</p>}
            
            <form onSubmit={handleSubmit} className="search-form">
                <input
                    type="text"
                    placeholder="First Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={isLoading}
                />
                <input
                    type="text"
                    placeholder="Location"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    disabled={isLoading}
                />
                <input
                    type="number"
                    placeholder="Age"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading}>
                    {isLoading ? 'Searching...' : 'Search'}
                </button>
            </form>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {isLoading && (
                <div className="loading-message">
                    Searching Tinder profiles...
                </div>
            )}

            <div className="results">
                {results.map((profile, index) => (
                    <div key={index} className="profile">
                        <div className="profile-images">
                            {profile.profile_pictures.map((pic, picIndex) => (
                                <img key={picIndex} src={pic} alt={`${profile.name} - ${picIndex + 1}`} />
                            ))}
                        </div>
                        <div className="profile-info">
                            <p><strong>Name:</strong> {profile.name}</p>
                            <p><strong>Age:</strong> {profile.age}</p>
                            <p><strong>Location:</strong> {profile.location}</p>
                            {profile.bio && <p><strong>Bio:</strong> {profile.bio}</p>}
                            <p><strong>Last Active:</strong> {new Date(profile.last_active).toLocaleString()}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default App;