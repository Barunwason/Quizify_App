from flask import Flask,render_template,request,jsonify
from main import generate_quiz

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    topic = None
    if request.method == 'POST':
        topic = request.form['topic']
        generate_quiz(topic)   # generate questions.json
    return render_template('home.html', topic=topic)
if __name__ == "__main__":
    app.run(debug=True)