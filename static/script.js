// Global quiz state
let currentQuestionIndex = 0;
let score = 0;
let quizData = {};
let quizMode = "mcq"; // "mcq" or "subjective"
let subjectiveAnswers = [];

// Cached DOM elements
const questionContainer = document.getElementById("question-container");
const questionElement = document.getElementById("question");
const answerButtons = document.getElementById("answer-buttons");
const resultElement = document.getElementById("result");
const nextButton = document.getElementById("next-btn");
const topicInputForm = document.getElementById("topicInput1");
const option2Container = document.getElementById("card2");
const option1Container = document.getElementById("card1");
const toggleBtn = document.getElementById("theme-switch");
const uploadForm = document.getElementById("uploadForm");
const uploadResult = document.getElementById("uploadResult");

// Load saved preference
if (localStorage.getItem("theme") === "dark") {
  document.body.classList.add("darkmode");
}

toggleBtn.addEventListener("click", () => {
  document.body.classList.toggle("darkmode");

  // Save preference
  if (document.body.classList.contains("darkmode")) {
    localStorage.setItem("theme", "dark");
  } else {
    localStorage.setItem("theme", "light");
  }
});

document.addEventListener("DOMContentLoaded", () => {
  questionContainer.style.display = "none";
});

// Handle topic form submit
submit_topic();
function submit_topic() {
  topicInputForm.addEventListener("submit", async (e) => {
    e.preventDefault(); // Stop page reload

    const topic = document.getElementById("topicInput").value;
    if (!topic) {
      alert("Please enter a topic!");
      return;
    }

    try {
      // Show loading message while quiz is being generated
      resultElement.innerText = "Generating quiz...";

      // Read selected question type
      const questionTypeSelect = document.getElementById("questionTypeSelect");
      const questionType = questionTypeSelect ? questionTypeSelect.value : "mcq";

      // Send topic + question type to backend
      let response = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `topic=${encodeURIComponent(topic)}&question_type=${encodeURIComponent(
          questionType
        )}`,
      });

      if (!response.ok) {
        throw new Error("Failed to generate quiz");
      }

      // Now fetch generated questions.json
      let quizResponse = await fetch("/static/questions.json?" + Date.now());
      quizData = await quizResponse.json();
      quizMode =
        quizData.mode ||
        (quizData.questions && quizData.questions[0].options ? "mcq" : "subjective");
      subjectiveAnswers = [];

      topicInputForm.style.display = "none";
      // Hide entire cards section
      option1Container.style.display = "none";
      option2Container.style.display = "none";
      questionContainer.style.display = "block";

      // Clear loading message once questions are ready
      resultElement.innerText = "";

      showQuestion();
    } catch (error) {
      console.error("Error:", error);
      resultElement.innerText = "Something went wrong while generating quiz.";
    }
  });
}

// Handle PDF upload to generate quiz from PDF
if (uploadForm) {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(uploadForm);
    uploadResult.textContent = "Uploading and generating quiz...";
    try {
      const res = await fetch("/upload-pdf", { method: "POST", body: formData });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      // Fetch the generated questions and show quiz
      const quizRes = await fetch("/static/questions.json?" + Date.now());
      quizData = await quizRes.json();
      quizMode =
        quizData.mode ||
        (quizData.questions && quizData.questions[0].options ? "mcq" : "subjective");
      subjectiveAnswers = [];

      option1Container.style.display = "none";
      option2Container.style.display = "none";
      questionContainer.style.display = "block";
      currentQuestionIndex = 0;
      score = 0;
      showQuestion();
      uploadResult.textContent = "Quiz generated from PDF.";
    } catch (err) {
      console.error(err);
      uploadResult.textContent = "Error: " + err.message;
    }
  });
}

// Render either MCQ question (single at a time) or all subjective questions.
function showQuestion() {
  resetState();

  if (quizMode === "subjective") {
    renderSubjectiveQuiz();
    return;
  }

  let currentQuestion = quizData.questions[currentQuestionIndex];
  questionElement.innerText = `${currentQuestionIndex + 1}. ${currentQuestion.question_text}`;

  currentQuestion.options.forEach((option) => {
    const button = document.createElement("button");
    button.innerText = option;
    button.classList.add("btn");

    if (option === currentQuestion.correct_answer) {
      button.dataset.correct = "true";
    }

    button.addEventListener("click", selectAnswer);
    answerButtons.appendChild(button);
  });
}

function resetState() {
  nextButton.style.display = "none";
  nextButton.onclick = null;
  resultElement.innerText = "";
  while (answerButtons.firstChild) {
    answerButtons.removeChild(answerButtons.firstChild);
  }
}

function selectAnswer(e) {
  const selectedButton = e.target;
  const isCorrect = selectedButton.dataset.correct === "true";
  let currentQuestion = quizData.questions[currentQuestionIndex];

  if (isCorrect) {
    selectedButton.classList.add("correct");
    resultElement.innerText = "✅ Correct!\n" + currentQuestion.explanation;
    score++;
  } else {
    selectedButton.classList.add("incorrect");
    resultElement.innerText = "❌ Wrong!\n" + currentQuestion.explanation;
  }

  Array.from(answerButtons.children).forEach((button) => {
    if (button.dataset.correct === "true") {
      button.classList.add("correct");
    }
    button.disabled = true;
  });

  nextButton.style.display = "block";
}

nextButton.addEventListener("click", () => {
  // Only handle MCQ flow here. Subjective flow uses a custom onclick set in renderSubjectiveQuiz.
  if (quizMode !== "mcq") {
    return;
  }

  currentQuestionIndex++;
  if (currentQuestionIndex < quizData.questions.length) {
    showQuestion();
  } else {
    showScore();
  }
});

function showScore() {
  resetState();
  questionElement.innerText = `🎉 You scored ${score} out of ${quizData.questions.length}!`;
  nextButton.innerText = "Play Again";
  nextButton.style.display = "block";
  nextButton.addEventListener("click", () => {
    currentQuestionIndex = 0;
    score = 0;
    window.location.reload();
    submit_topic();
  });
}

function renderSubjectiveQuiz() {
  questionElement.innerText =
    quizData.quiz_title || "Answer the following subjective questions:";

  quizData.questions.forEach((q, index) => {
    const block = document.createElement("div");
    block.classList.add("subjective-question-block");

    const label = document.createElement("p");
    label.innerText = `${index + 1}. ${q.question_text}`;

    const textarea = document.createElement("textarea");
    textarea.id = `subjective-answer-${index}`;
    textarea.rows = 4;
    textarea.placeholder = "Type your answer here...";
    textarea.classList.add("subjective-area");

    block.appendChild(label);
    block.appendChild(textarea);
    answerButtons.appendChild(block);
  });

  nextButton.innerText = "Submit Answers for Review";
  nextButton.style.display = "block";
  nextButton.onclick = async () => {
    subjectiveAnswers = quizData.questions.map((_, index) => {
      const el = document.getElementById(`subjective-answer-${index}`);
      return el ? el.value.trim() : "";
    });
    await reviewSubjectiveAnswers();
  };
}

async function reviewSubjectiveAnswers() {
  try {
    resultElement.innerText = "Reviewing your answers...";
    const res = await fetch("/review-subjective", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        questions: quizData.questions,
        answers: subjectiveAnswers,
        quiz_title: quizData.quiz_title,
        subject: quizData.subject,
      }),
    });
    if (!res.ok) throw new Error("Failed to review answers");
    const data = await res.json();

    resetState();
    questionElement.innerText = "Your subjective answers review";

    const summaryDiv = document.createElement("div");
    summaryDiv.classList.add("result-summary");

    if (data.overall_score !== undefined) {
      const overall = document.createElement("p");
      overall.innerText = `Overall score: ${data.overall_score} / 10`;
      summaryDiv.appendChild(overall);
    }

    if (data.overall_feedback) {
      const overallFb = document.createElement("p");
      overallFb.innerText = data.overall_feedback;
      summaryDiv.appendChild(overallFb);
    }

    if (Array.isArray(data.per_question)) {
      data.per_question.forEach((item) => {
        const block = document.createElement("div");
        block.classList.add("question-feedback");
        const q = quizData.questions.find((q) => q.id === item.id);
        const title = document.createElement("h4");
        title.innerText = `Q${q ? q.id : ""}: ${q ? q.question_text : ""}`;
        const rating = document.createElement("p");
        rating.innerText = `Rating: ${item.rating} / 5`;
        const fb = document.createElement("p");
        fb.innerText = item.feedback;
        block.appendChild(title);
        block.appendChild(rating);
        block.appendChild(fb);
        summaryDiv.appendChild(block);
      });
    }

    answerButtons.appendChild(summaryDiv);

    nextButton.innerText = "Take Another Quiz";
    nextButton.style.display = "block";
    nextButton.onclick = () => {
      window.location.reload();
    };
  } catch (err) {
    console.error(err);
    resultElement.innerText = "Error while reviewing answers: " + err.message;
  }
}
