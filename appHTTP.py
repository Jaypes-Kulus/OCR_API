from flask import Flask, request, jsonify
import easyocr
import os
from werkzeug.utils import secure_filename
import base64
from PIL import Image
from io import BytesIO

app = Flask(__name__)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'OCR service is running'
    })

@app.route('/api/v1/ocr/file', methods=['POST'])
def extract_text_from_file():
    """
    Extract text from an uploaded file
    
    Expects form-data with a file field named 'image'
    """
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided',
                'required_format': 'Send image as form-data with key "image"'
            }), 400

        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No selected file'
            }), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process with EasyOCR
            results = reader.readtext(filepath)
            text = ' '.join([result[1] for result in results])

            # Clean up
            os.remove(filepath)

            return jsonify({
                'success': True,
                'text': text.strip(),
                'confidence': sum(result[2] for result in results) / len(results) if results else 0
            })

        return jsonify({
            'success': False,
            'error': 'Invalid file type',
            'allowed_extensions': list(ALLOWED_EXTENSIONS)
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/v1/ocr/base64', methods=['POST'])
def extract_text_from_base64():
    """
    Extract text from a base64 encoded image
    
    Expects JSON payload: {
        "image": "base64_encoded_image_string",
        "filename": "optional_filename.jpg"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided',
                'required_format': {
                    'image': 'base64_encoded_image_string',
                    'filename': 'optional_filename.jpg'
                }
            }), 400

        # Decode base64 image
        try:
            image_data = base64.b64decode(data['image'])
            image = Image.open(BytesIO(image_data))
            
            # Save temporarily
            filename = secure_filename(data.get('filename', 'temp.png'))
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            # Process with EasyOCR
            results = reader.readtext(filepath)
            text = ' '.join([result[1] for result in results])

            # Clean up
            os.remove(filepath)

            return jsonify({
                'success': True,
                'text': text.strip(),
                'confidence': sum(result[2] for result in results) / len(results) if results else 0
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Invalid base64 image data',
                'details': str(e)
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) 