## Quizify App - Cross-platform Setup

### Prerequisites
- Python 3.12+
- A Groq API key

### 1) Clone and enter the project
```bash
git clone <your-repo-url>
cd Quizify_App
```

### 2) Create and activate a virtual environment
- macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```
- Windows (PowerShell)
```powershell
py -3 -m venv myenv
./myenv/Scripts/Activate.ps1
```

### 3) Install dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4) Configure environment variables
Create a `.env` file (copy from `.env.example`) at the project root:
```
GROQ_API_KEY=your_groq_api_key
```

### 5) Run the app
```bash
python app.py
```
Open http://127.0.0.1:5000

### Usage
- Enter a topic to generate a quiz, or upload a PDF. The generated quiz is saved to `static/questions.json` and rendered in the UI.

### Notes
- Paths are project-relative via `pathlib`, so the app runs on Windows/macOS/Linux.
- Use `python -m pip` consistently to avoid pip path issues.

