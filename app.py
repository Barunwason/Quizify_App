from flask import Flask, render_template, request, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename
from main import (
    generate_mcq_quiz,
    generate_subjective_quiz,
    generate_mcq_quiz_from_pdf,
    generate_subjective_quiz_from_pdf,
    review_subjective_answers,
)

app = Flask(__name__)
UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
UPLOAD_FOLDER.mkdir(exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed extension (currently only PDF)."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def home():
    """Render homepage and, on POST, generate a quiz from a typed topic."""
    topic = None
    if request.method == "POST":
        topic = request.form["topic"]
        question_type = request.form.get("question_type", "mcq")
        if question_type == "subjective":
            generate_subjective_quiz(topic)
        else:
            generate_mcq_quiz(topic)
    return render_template("home.html", topic=topic)


@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    """Handle PDF upload and generate either MCQ or subjective quiz from it."""
    if "pdf" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["pdf"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF allowed"}), 400

    question_type = request.form.get("question_type", "mcq")

    filename = secure_filename(file.filename)
    save_path = UPLOAD_FOLDER / filename
    file.save(str(save_path))

    try:
        if question_type == "subjective":
            generate_subjective_quiz_from_pdf(str(save_path))
        else:
            generate_mcq_quiz_from_pdf(str(save_path))
        return jsonify(
            {
                "message": "Uploaded and quiz generated",
                "path": str(save_path),
                "questions_url": "/static/questions.json",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/review-subjective", methods=["POST"])
def review_subjective_route():
    """Receive subjective answers from the frontend and return model-generated review."""
    data = request.get_json(force=True)
    questions = data.get("questions", [])
    answers = data.get("answers", [])
    if not questions or not answers:
        return jsonify({"error": "questions and answers are required"}), 400

    try:
        review = review_subjective_answers(questions, answers)
        return jsonify(review)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)