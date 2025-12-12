from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import io
import base64
import os

app = Flask(__name__)

CORS(app, origins=[
    "https://*.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173"
], methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_IMAGE_DIMENSION = 4096

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file):
    if not file or file.filename == '':
        return None, 'No file selected'
    
    if not allowed_file(file.filename):
        return None, f'Invalid file type. Allowed: {ALLOWED_EXTENSIONS}'
    
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return None, f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB'
    
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
        
        if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
            return None, f'Image dimensions too large. Maximum: {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}'
        
        return img, None
    except Exception as e:
        return None, 'Invalid or corrupted image file'

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'GTOverloads Backend Server is running!',
        'endpoints': {
            '/': 'Server status',
            '/process': 'POST - Process image',
            '/resize': 'POST - Resize image',
            '/convert': 'POST - Convert image format',
            '/compress-image': 'POST - Compress image with quality setting',
            '/filter': 'POST - Apply filter to image'
        }
    })

@app.route('/process', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        img, error = validate_image(request.files['image'])
        if error:
            return jsonify({'error': error}), 400
        
        info = {
            'format': img.format,
            'mode': img.mode,
            'size': {'width': img.width, 'height': img.height}
        }
        
        return jsonify({
            'success': True,
            'message': 'Image processed successfully',
            'image_info': info
        })
    except Exception as e:
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/resize', methods=['POST'])
def resize_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        img, error = validate_image(request.files['image'])
        if error:
            return jsonify({'error': error}), 400
        
        width = request.form.get('width', type=int)
        height = request.form.get('height', type=int)
        
        if not width or not height:
            return jsonify({'error': 'Width and height are required'}), 400
        
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION or width < 1 or height < 1:
            return jsonify({'error': f'Invalid dimensions. Range: 1-{MAX_IMAGE_DIMENSION}'}), 400
        
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        img_byte_arr = io.BytesIO()
        resized_img.save(img_byte_arr, format=img.format or 'PNG')
        img_byte_arr.seek(0)
        
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': img_base64,
            'new_size': {'width': width, 'height': height}
        })
    except Exception as e:
        return jsonify({'error': 'Failed to resize image'}), 500

@app.route('/convert', methods=['POST'])
def convert_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        img, error = validate_image(request.files['image'])
        if error:
            return jsonify({'error': error}), 400
        
        target_format = request.form.get('format', 'PNG').upper()
        
        valid_formats = ['PNG', 'JPEG', 'JPG', 'WEBP', 'GIF', 'BMP']
        if target_format not in valid_formats:
            return jsonify({'error': f'Invalid format. Supported: {valid_formats}'}), 400
        
        if target_format in ['JPEG', 'JPG'] and img.mode == 'RGBA':
            img = img.convert('RGB')
        
        img_byte_arr = io.BytesIO()
        save_format = 'JPEG' if target_format == 'JPG' else target_format
        img.save(img_byte_arr, format=save_format)
        img_byte_arr.seek(0)
        
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': img_base64,
            'format': target_format
        })
    except Exception as e:
        return jsonify({'error': 'Failed to convert image'}), 500

@app.route('/compress-image', methods=['POST'])
def compress_image():
    if 'file' not in request.files:
        return {"error": "No file part"}, 400

    file = request.files['file']
    if file.filename == '':
        return {"error": "No selected file"}, 400

    quality = int(request.form.get('quality', 75))

    try:
        image = Image.open(file.stream)
        original_format = image.format

        if original_format in ['JPEG', 'JPG'] and image.mode == 'RGBA':
            image = image.convert('RGB')

        byte_arr = io.BytesIO()
        image.save(byte_arr, format=original_format, quality=quality, optimize=True)
        byte_arr.seek(0)

        return send_file(
            byte_arr,
            mimetype=f'image/{original_format.lower()}',
            as_attachment=True,
            download_name=f"compressed_{file.filename}"
        )

    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/filter', methods=['POST'])
def apply_filter():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        img, error = validate_image(request.files['image'])
        if error:
            return jsonify({'error': error}), 400
        
        filter_type = request.form.get('filter', 'grayscale').lower()
        valid_filters = ['grayscale', 'rotate90', 'rotate180', 'rotate270', 'flip_horizontal', 'flip_vertical']
        
        if filter_type not in valid_filters:
            return jsonify({'error': f'Unknown filter. Available: {valid_filters}'}), 400
        
        if filter_type == 'grayscale':
            img = img.convert('L').convert('RGB')
        elif filter_type == 'rotate90':
            img = img.rotate(90, expand=True)
        elif filter_type == 'rotate180':
            img = img.rotate(180)
        elif filter_type == 'rotate270':
            img = img.rotate(270, expand=True)
        elif filter_type == 'flip_horizontal':
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif filter_type == 'flip_vertical':
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': img_base64,
            'filter_applied': filter_type
        })
    except Exception as e:
        return jsonify({'error': 'Failed to apply filter'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
      
