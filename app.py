from flask import Flask, render_template, request, jsonify
import os
from openai import OpenAI
import requests
from dotenv import load_dotenv
from datetime import datetime
from werkzeug.utils import secure_filename
import glob

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def cleanup_old_images(max_files=50):
    """Cleanup old generated images keeping only the most recent ones"""
    files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], 'generated_*.png'))
    if len(files) > max_files:
        for old_file in sorted(files)[:-max_files]:
            try:
                os.remove(old_file)
            except Exception as e:
                print(f"Error cleaning up file {old_file}: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        prompt = request.form.get('prompt', '').strip()
        style = request.form.get('style', 'modern')
        size = request.form.get('size', '1024x1024')

        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        # Validate size format
        if size not in ['1024x1024', '1792x1024', '1024x1792']:
            return jsonify({'error': 'Invalid size format'}), 400

        # Enhanced prompt engineering
        full_prompt = f"""Create a marketing image: {prompt}
                         Style: {style}
                         Additional requirements: professional quality, high resolution,
                         marketing-focused, attention-grabbing, commercial use ready"""

        # Generate image
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size=size,
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        image_response = requests.get(image_url)

        if image_response.status_code == 200:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = secure_filename(f"generated_{timestamp}.png")
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            with open(img_path, 'wb') as f:
                f.write(image_response.content)

            # Cleanup old files
            cleanup_old_images()

            return render_template('result.html',
                                image_path=f'images/{filename}',
                                prompt=prompt,
                                style=style,
                                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            return jsonify({'error': 'Failed to download image'}), 400

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File is too large'}), 413

if __name__ == '__main__':
    app.run(debug=True)
