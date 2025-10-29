from flask import Flask,render_template,request,jsonify
from pathlib import Path
from werkzeug.utils import secure_filename
from main import generate_quiz, generate_quiz_from_pdf

app = Flask(__name__)
UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
UPLOAD_FOLDER.mkdir(exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def home():
    topic = None
    if request.method == 'POST':
        topic = request.form['topic']
        generate_quiz(topic)   # generate questions.json
    return render_template('home.html', topic=topic)

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF allowed'}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_FOLDER / filename
    file.save(str(save_path))
    # Generate quiz from uploaded PDF
    try:
        generate_quiz_from_pdf(str(save_path))
        return jsonify({'message': 'Uploaded and quiz generated', 'path': str(save_path), 'questions_url': '/static/questions.json'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == "__main__":
    
    app.run(debug=True)