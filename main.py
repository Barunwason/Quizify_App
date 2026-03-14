from pathlib import Path
import json

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
try:
    import pdfplumber  # Optional; required only for PDF flow
except Exception:
    pdfplumber = None

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = PROJECT_ROOT / "schema.json"
OUTPUT_PATH = PROJECT_ROOT / "static" / "questions.json"

with SCHEMA_PATH.open("r", encoding="utf-8") as file:
    quiz_schema = json.load(file)

model = ChatGroq(model="llama-3.3-70b-versatile")
structured_model = model.with_structured_output(quiz_schema)

def generate_quiz(topic: str) -> None:
    
    template = PromptTemplate(template="Generate a quiz on the topic '{topic}' with exactly 10 multiple-choice questions. Each question must have: id (integer), question_text (string), options (array of 4 strings), correct_answer (string matching one option), explanation (string). The quiz must have: quiz_title, subject, difficulty (easy/medium/hard), questions (array). Do not add any extra fields. Return only valid JSON matching the schema.", input_variables=["topic"]) 
    chain = template | structured_model
    result = chain.invoke({"topic": topic})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


# PDF → quiz
pdf_template = PromptTemplate(
    template=(
        "You are a tutor. Create a quiz with exactly 10 high-quality MCQs strictly based on the given PDF content. "
        "Cover key concepts, avoid trivial facts, and vary difficulty. "
        "Each question must have: id (integer), question_text (string), options (array of 4 strings), correct_answer (string matching one option), explanation (string). "
        "The quiz must have: quiz_title, subject, difficulty (easy/medium/hard), questions (array). "
        "Do not add any extra fields like 'type'. Return only valid JSON matching the schema.\n\n"
        "Content:\n{content}"
    ),
    input_variables=["content"],
)

pdf_chain = pdf_template | structured_model


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 20) -> str:
    if pdfplumber is None:
        raise ImportError(
            "pdfplumber is not installed. Activate your venv and run: pip install pdfplumber"
        )
    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def generate_quiz_from_pdf(pdf_path: str) -> None:
    source = Path(pdf_path)
    if not source.exists():
        raise FileNotFoundError(f"PDF not found: {source}")

    content = extract_text_from_pdf(source)
    if not content.strip():
        raise ValueError("No extractable text found in PDF. Please upload a text-based PDF (not scanned images).")
    # Keep prompt within a reasonable size for the model
    content = content[:20000]

    result = pdf_chain.invoke({"content": content})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
