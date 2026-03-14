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

def get_template_for_type(question_type: str) -> str:
    if question_type == "mcq":
        return "give 10 multiple-choice questions (MCQs) on {topic}. Include options and correct answer. Return JSON matching the provided schema."
    elif question_type == "subjective":
        return "give 10 subjective (open-ended) questions on {topic}. Provide a model answer for each. Return JSON matching the provided schema."
    else:  # both
        return "give 5 multiple-choice questions (MCQs) and 5 subjective (open-ended) questions on {topic}. For MCQs, include options and correct answer. For subjective, provide a model answer. Return JSON matching the provided schema."

template = PromptTemplate(template=get_template_for_type("both"), input_variables=["topic"]) 

chain = template | structured_model

# PDF → quiz
def get_pdf_template_for_type(question_type: str) -> str:
    if question_type == "mcq":
        return (
            "You are a tutor. Create 10 high-quality MCQs strictly based on the given PDF content. "
            "Cover key concepts, avoid trivial facts, and vary difficulty. "
            "Include options and correct answer. "
            "Return JSON matching the provided schema.\n\n"
            "Content:\n{content}"
        )
    elif question_type == "subjective":
        return (
            "You are a tutor. Create 10 subjective questions strictly based on the given PDF content. "
            "Cover key concepts, avoid trivial facts, and vary difficulty. "
            "Provide a model answer for each. "
            "Return JSON matching the provided schema.\n\n"
            "Content:\n{content}"
        )
    else:  # both
        return (
            "You are a tutor. Create 5 high-quality MCQs and 5 subjective questions strictly based on the given PDF content. "
            "Cover key concepts, avoid trivial facts, and vary difficulty. "
            "For MCQs, include options and correct answer. For subjective, provide a model answer. "
            "Return JSON matching the provided schema.\n\n"
            "Content:\n{content}"
        )

pdf_template = PromptTemplate(
    template=get_pdf_template_for_type("both"),
    input_variables=["content"],
)

pdf_chain = pdf_template | structured_model

# LangGraph imports and setup
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional

class QuizState(TypedDict):
    topic: Optional[str]
    pdf_path: Optional[str]
    content: Optional[str]
    question_type: str
    result: Optional[dict]

# Node functions
def router(state: QuizState) -> str:
    if state.get("topic"):
        return "topic_quiz"
    elif state.get("pdf_path"):
        return "extract_pdf"
    else:
        raise ValueError("Either topic or pdf_path must be provided")

def generate_topic_quiz(state: QuizState) -> QuizState:
    topic = state["topic"]
    question_type = state["question_type"]
    template_str = get_template_for_type(question_type)
    dynamic_template = PromptTemplate(template=template_str, input_variables=["topic"])
    dynamic_chain = dynamic_template | structured_model
    result = dynamic_chain.invoke({"topic": topic})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return {"result": result}

def extract_pdf_text(state: QuizState) -> QuizState:
    pdf_path = Path(state["pdf_path"])
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdfplumber is None:
        raise ImportError(
            "pdfplumber is not installed. Activate your venv and run: pip install pdfplumber"
        )
    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= 20:  # max_pages
                break
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    content = "\n\n".join(text_parts)[:20000]  # Keep prompt within a reasonable size
    return {"content": content}

def generate_pdf_quiz(state: QuizState) -> QuizState:
    content = state["content"]
    question_type = state["question_type"]
    template_str = get_pdf_template_for_type(question_type)
    dynamic_template = PromptTemplate(template=template_str, input_variables=["content"])
    dynamic_chain = dynamic_template | structured_model
    result = dynamic_chain.invoke({"content": content})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return {"result": result}

# Build the graph
graph = StateGraph(QuizState)
graph.add_node("router", router)
graph.add_node("topic_quiz", generate_topic_quiz)
graph.add_node("extract_pdf", extract_pdf_text)
graph.add_node("pdf_quiz", generate_pdf_quiz)

graph.add_conditional_edges(START, router)
graph.add_edge("topic_quiz", END)
graph.add_edge("extract_pdf", "pdf_quiz")
graph.add_edge("pdf_quiz", END)

quiz_agent = graph.compile()

# Review schema
review_schema = {
  "title": "Review",
  "description": "Schema for reviewing quiz answers",
  "type": "object",
  "properties": {
    "reviews": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "question_id": {"type": "integer"},
          "feedback": {"type": "string"},
          "score": {"type": "integer", "minimum": 0, "maximum": 10}
        },
        "required": ["question_id", "feedback", "score"]
      }
    },
    "overall_rating": {"type": "integer", "minimum": 0, "maximum": 100},
    "summary": {"type": "string"}
  },
  "required": ["reviews", "overall_rating", "summary"]
}

# Review agent
class ReviewState(TypedDict):
    quiz_data: dict
    user_answers: dict  # {question_id: user_answer}
    review_result: Optional[dict]

review_structured_model = model.with_structured_output(review_schema)

def evaluate_answers(state: ReviewState) -> ReviewState:
    quiz_data = state["quiz_data"]
    user_answers = state["user_answers"]
    review_template = PromptTemplate(
        template=(
            "You are an expert evaluator. Review the user's answers to the following quiz.\n\n"
            "Quiz Data:\n{quiz_data}\n\n"
            "User Answers:\n{user_answers}\n\n"
            "For each question:\n"
            "- Provide detailed feedback on the user's answer\n"
            "- Give a score out of 10\n"
            "- For subjective questions, compare to the model answer\n\n"
            "Finally, give an overall rating out of 100 and a summary.\n\n"
            "Return your response as a valid JSON object with this exact structure:\n"
            "{{\n"
            '  "reviews": [\n'
            '    {{"question_id": 1, "feedback": "feedback text", "score": 8}}\n'
            '  ],\n'
            '  "overall_rating": 85,\n'
            '  "summary": "summary text"\n'
            "}}"
        ),
        input_variables=["quiz_data", "user_answers"],
    )
    review_chain = review_template | model
    result = review_chain.invoke({"quiz_data": json.dumps(quiz_data), "user_answers": json.dumps(user_answers)})
    # Parse the JSON response
    try:
        content = result.content.strip()
        # Find JSON if wrapped in text
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            review_result = json.loads(json_str)
        else:
            raise ValueError("No JSON found")
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback
        review_result = {
            "reviews": [{"question_id": q["id"], "feedback": f"Error parsing review for question {q['id']}", "score": 0} for q in quiz_data.get("questions", [])],
            "overall_rating": 0,
            "summary": f"Review failed: {str(e)}. Raw response: {result.content[:500]}"
        }
    return {"review_result": review_result}

# Review graph
review_graph = StateGraph(ReviewState)
review_graph.add_node("evaluate", evaluate_answers)
review_graph.add_edge(START, "evaluate")
review_graph.add_edge("evaluate", END)

review_agent = review_graph.compile()

def review_quiz_answers(quiz_data: dict, user_answers: dict) -> dict:
    initial_state = {"quiz_data": quiz_data, "user_answers": user_answers, "review_result": None}
    result = review_agent.invoke(initial_state)
    return result["review_result"]

# Updated functions to use the agent
def generate_quiz(topic: str, question_type: str = "both") -> None:
    initial_state = {"topic": topic, "pdf_path": None, "content": None, "question_type": question_type, "result": None}
    quiz_agent.invoke(initial_state)

def generate_quiz_from_pdf(pdf_path: str, question_type: str = "both") -> None:
    initial_state = {"topic": None, "pdf_path": pdf_path, "content": None, "question_type": question_type, "result": None}
    quiz_agent.invoke(initial_state)

