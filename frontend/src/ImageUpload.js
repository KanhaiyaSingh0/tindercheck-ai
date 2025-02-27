import React, { useState } from 'react';

const ImageUpload = ({ onImageSelect }) => {
  const [previewImage, setPreviewImage] = useState(null);

  const handleImageChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setPreviewImage(URL.createObjectURL(file));
      onImageSelect(file);
    }
  };

  return (
    <div className="image-upload">
      <label htmlFor="file-upload">
        Choose Profile Picture
      </label>
      <input
        id="file-upload"
        type="file"
        accept="image/*"
        onChange={handleImageChange}
      />
      {previewImage && (
        <div className="preview-container">
          <img 
            src={previewImage} 
            alt="Preview" 
            style={{ 
              maxWidth: '200px',
              maxHeight: '200px',
              objectFit: 'cover',
              borderRadius: '10px',
              marginTop: '15px'
            }} 
          />
        </div>
      )}
    </div>
  );
};

export default ImageUpload;