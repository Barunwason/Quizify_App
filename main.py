from pathlib import Path
import json
import os
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

try:
    # Optional dependency, only needed for PDF → text flow
    import pdfplumber
except Exception:
    pdfplumber = None

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
MCQ_SCHEMA_PATH = PROJECT_ROOT / "schema.json"
SUBJECTIVE_SCHEMA_PATH = PROJECT_ROOT / "schema_subjective.json"
REVIEW_SCHEMA_PATH = PROJECT_ROOT / "schema_review.json"
OUTPUT_PATH = PROJECT_ROOT / "static" / "questions.json"

with MCQ_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    mcq_schema = json.load(file)

with SUBJECTIVE_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    subjective_schema = json.load(file)

with REVIEW_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    review_schema = json.load(file)

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Make sure it is defined in your .env file or environment."
    )

model = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_api_key)


class QuizState(TypedDict, total=False):
    topic: Optional[str]
    content: Optional[str]
    result: dict


class ReviewState(TypedDict, total=False):
    questions: list
    answers: list
    review: dict


# -------- MCQ generation chains --------

mcq_structured_model = model.with_structured_output(mcq_schema)

mcq_topic_template = PromptTemplate(
    template="Create 10 high-quality MCQ questions on {topic} following the provided JSON schema.",
    input_variables=["topic"],
)
mcq_topic_chain = mcq_topic_template | mcq_structured_model

mcq_pdf_template = PromptTemplate(
    template=(
        "You are a tutor. Create 10 high-quality MCQ questions strictly based on the given PDF content. "
        "Cover key concepts, avoid trivial facts, and vary difficulty. "
        "Return JSON matching the provided schema.\n\n"
        "Content:\n{content}"
    ),
    input_variables=["content"],
)
mcq_pdf_chain = mcq_pdf_template | mcq_structured_model


def _generate_mcq_from_topic(state: QuizState) -> QuizState:
    if not state.get("topic"):
        raise ValueError("State must include 'topic' to generate MCQ quiz.")
    result = mcq_topic_chain.invoke({"topic": state["topic"]})
    result["mode"] = "mcq"
    return {"result": result}


def _generate_mcq_from_pdf_content(state: QuizState) -> QuizState:
    if not state.get("content"):
        raise ValueError("State must include 'content' to generate MCQ quiz from PDF.")
    result = mcq_pdf_chain.invoke({"content": state["content"]})
    result["mode"] = "mcq"
    return {"result": result}


# -------- Subjective generation chains --------

subjective_structured_model = model.with_structured_output(subjective_schema)

subjective_topic_template = PromptTemplate(
    template=(
        "Create 10 high-quality subjective questions on {topic} that require short paragraph answers. "
        "For each question, provide a concise ideal answer that can be used for grading. "
        "Return JSON matching the provided schema."
    ),
    input_variables=["topic"],
)
subjective_topic_chain = subjective_topic_template | subjective_structured_model

subjective_pdf_template = PromptTemplate(
    template=(
        "You are a tutor. Create 10 high-quality subjective questions strictly based on the given PDF content. "
        "Questions should test conceptual understanding and require short paragraph answers. "
        "For each question, provide a concise ideal answer that can be used for grading. "
        "Return JSON matching the provided schema.\n\n"
        "Content:\n{content}"
    ),
    input_variables=["content"],
)
subjective_pdf_chain = subjective_pdf_template | subjective_structured_model


def _generate_subjective_from_topic(state: QuizState) -> QuizState:
    if not state.get("topic"):
        raise ValueError("State must include 'topic' to generate subjective quiz.")
    result = subjective_topic_chain.invoke({"topic": state["topic"]})
    result["mode"] = "subjective"
    return {"result": result}


def _generate_subjective_from_pdf_content(state: QuizState) -> QuizState:
    if not state.get("content"):
        raise ValueError("State must include 'content' to generate subjective quiz from PDF.")
    result = subjective_pdf_chain.invoke({"content": state["content"]})
    result["mode"] = "subjective"
    return {"result": result}


# Build LangGraph agents (graphs) for topic and PDF flows

mcq_topic_graph_builder = StateGraph(QuizState)
mcq_topic_graph_builder.add_node("generate_mcq_from_topic", _generate_mcq_from_topic)
mcq_topic_graph_builder.set_entry_point("generate_mcq_from_topic")
mcq_topic_graph_builder.add_edge("generate_mcq_from_topic", END)
mcq_topic_graph = mcq_topic_graph_builder.compile()

mcq_pdf_graph_builder = StateGraph(QuizState)
mcq_pdf_graph_builder.add_node("generate_mcq_from_pdf_content", _generate_mcq_from_pdf_content)
mcq_pdf_graph_builder.set_entry_point("generate_mcq_from_pdf_content")
mcq_pdf_graph_builder.add_edge("generate_mcq_from_pdf_content", END)
mcq_pdf_graph = mcq_pdf_graph_builder.compile()

subjective_topic_graph_builder = StateGraph(QuizState)
subjective_topic_graph_builder.add_node("generate_subjective_from_topic", _generate_subjective_from_topic)
subjective_topic_graph_builder.set_entry_point("generate_subjective_from_topic")
subjective_topic_graph_builder.add_edge("generate_subjective_from_topic", END)
subjective_topic_graph = subjective_topic_graph_builder.compile()

subjective_pdf_graph_builder = StateGraph(QuizState)
subjective_pdf_graph_builder.add_node(
    "generate_subjective_from_pdf_content", _generate_subjective_from_pdf_content
)
subjective_pdf_graph_builder.set_entry_point("generate_subjective_from_pdf_content")
subjective_pdf_graph_builder.add_edge("generate_subjective_from_pdf_content", END)
subjective_pdf_graph = subjective_pdf_graph_builder.compile()


# -------- Subjective answer review agent --------

review_model = model.with_structured_output(review_schema)

review_prompt = PromptTemplate(
    template=(
        "You are an expert teacher. You are given subjective questions and a student's answers.\n"
        "Evaluate each answer from 1 (poor) to 5 (excellent) and provide brief feedback.\n"
        "Also provide an overall score out of 10 and summary feedback.\n"
        "Return data that matches the JSON schema you were given.\n\n"
        "Questions:\n{questions}\n\n"
        "Answers:\n{answers}\n"
    ),
    input_variables=["questions", "answers"],
)
review_chain = review_prompt | review_model


def _review_subjective_answers(state: ReviewState) -> ReviewState:
    if not state.get("questions") or not state.get("answers"):
        raise ValueError("State must include 'questions' and 'answers' for review.")

    review = review_chain.invoke(
        {
            "questions": state["questions"],
            "answers": state["answers"],
        }
    )
    return {"review": review}


review_graph_builder = StateGraph(ReviewState)
review_graph_builder.add_node("review_subjective_answers", _review_subjective_answers)
review_graph_builder.set_entry_point("review_subjective_answers")
review_graph_builder.add_edge("review_subjective_answers", END)
review_graph = review_graph_builder.compile()


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


def _write_quiz_to_disk(result: dict) -> None:
    """Save a generated quiz JSON object to the shared questions file."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def generate_mcq_quiz(topic: str) -> None:
    """Generate MCQ quiz from topic using the MCQ LangGraph agent."""
    final_state = mcq_topic_graph.invoke({"topic": topic})
    result = final_state["result"]
    _write_quiz_to_disk(result)


def generate_subjective_quiz(topic: str) -> None:
    """Generate subjective quiz from topic using the subjective LangGraph agent."""
    final_state = subjective_topic_graph.invoke({"topic": topic})
    result = final_state["result"]
    _write_quiz_to_disk(result)


def generate_mcq_quiz_from_pdf(pdf_path: str) -> None:
    """Generate MCQ quiz from PDF using the MCQ LangGraph agent."""
    source = Path(pdf_path)
    if not source.exists():
        raise FileNotFoundError(f"PDF not found: {source}")

    content = extract_text_from_pdf(source)
    content = content[:20000]

    final_state = mcq_pdf_graph.invoke({"content": content})
    result = final_state["result"]
    _write_quiz_to_disk(result)


def generate_subjective_quiz_from_pdf(pdf_path: str) -> None:
    """Generate subjective quiz from PDF using the subjective LangGraph agent."""
    source = Path(pdf_path)
    if not source.exists():
        raise FileNotFoundError(f"PDF not found: {source}")

    content = extract_text_from_pdf(source)
    content = content[:20000]

    final_state = subjective_pdf_graph.invoke({"content": content})
    result = final_state["result"]
    _write_quiz_to_disk(result)


def review_subjective_answers(questions: list, answers: list) -> dict:
    """Run the subjective answer review agent and return its structured output."""
    final_state = review_graph.invoke({"questions": questions, "answers": answers})
    return final_state["review"]
