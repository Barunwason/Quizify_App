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

template = PromptTemplate(template="give 10 questions on {topic}", input_variables=["topic"]) 

chain = template | structured_model


def generate_quiz(topic: str) -> None:
    result = chain.invoke({"topic": topic})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


# PDF → quiz
pdf_template = PromptTemplate(
    template=(
        "You are a tutor. Create 10 high-quality MCQs strictly based on the given PDF content. "
        "Cover key concepts, avoid trivial facts, and vary difficulty. "
        "Return JSON matching the provided schema.\n\n"
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
    # Keep prompt within a reasonable size for the model
    content = content[:20000]

    result = pdf_chain.invoke({"content": content})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
