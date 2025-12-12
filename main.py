from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image
import io

app = Flask(__name__)
CORS(app, expose_headers=['Content-Disposition']) # IMPORTANT: Expose header for filename

# This is a new constant to define the maximum size
MAX_IMAGE_SIZE = (1920, 1920)

@app.route('/')
def hello_world():
    return {"message": "Gtoverloads Back-End is running!"}

# --- UPDATED Image Converter Endpoint ---
@app.route('/convert-image', methods=['POST'])
def convert_image():
    if 'file' not in request.files:
        return {"error": "No file part"}, 400

    file = request.files['file']
    if file.filename == '':
        return {"error": "No selected file"}, 400

    convert_to = request.form.get('format', 'png').lower()
    
    if convert_to not in ['png', 'jpg', 'webp', 'gif', 'bmp']:
        return {"error": "Unsupported format"}, 400

    try:
        image = Image.open(file.stream)
        
        # --- NEW: RESIZE THE IMAGE ---
        # This makes the process much faster and uses less memory
        image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        # Handle transparency for JPG conversion
        if convert_to == 'jpg' and image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert("RGB")

        # Save the converted image to a memory buffer
        byte_arr = io.BytesIO()
        image.save(byte_arr, format=convert_to.upper())
        byte_arr.seek(0)

        original_name = file.filename.rsplit('.', 1)[0]
        new_filename = f"{original_name}_converted.{convert_to}"

        return send_file(
            byte_arr,
            mimetype=f'image/{convert_to}',
            as_attachment=True,
            download_name=new_filename
        )

    except Exception as e:
        return {"error": str(e)}, 500

# --- UPDATED Image Compressor Endpoint ---
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
        original_format = image.format.lower() if image.format else 'jpeg'

        # --- NEW: RESIZE THE IMAGE ---
        image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

        byte_arr = io.BytesIO()
        # Ensure we save as JPEG if that's the format, as PNG doesn't use "quality"
        if original_format in ['jpeg', 'jpg']:
            image.save(byte_arr, format='JPEG', quality=quality, optimize=True)
            mimetype = 'image/jpeg'
            new_filename = f"compressed_{file.filename.rsplit('.', 1)[0]}.jpg"
        else: # Handle PNG and others which compress differently
            image.save(byte_arr, format=original_format, optimize=True)
            mimetype = f'image/{original_format}'
            new_filename = f"compressed_{file.filename}"

        byte_arr.seek(0)
        
        return send_file(
            byte_arr,
            mimetype=mimetype,
            as_attachment=True,
            download_name=new_filename
        )

    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
