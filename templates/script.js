let currentQuestionIndex = 0;
let score = 0;
let quizData = {};

const questionContainer = document.getElementById("question-container");
const questionElement = document.getElementById("question");
const answerButtons = document.getElementById("answer-buttons");
const resultElement = document.getElementById("result");
const nextButton = document.getElementById("next-btn");
const topicInputForm = document.getElementById("topicInput1");
const toggleBtn = document.getElementById("theme-switch");
const app = document.getElementsByClassName("app");

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

questionContainer.style.display = "none";

// Handle form submit
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
      // Send topic to backend
      let response = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `topic=${encodeURIComponent(topic)}`,
      });

      if (!response.ok) {
        throw new Error("Failed to generate quiz");
      }

      // Now fetch generated questions.json
      let quizResponse = await fetch("/static/questions.json");
      quizData = await quizResponse.json();

      topicInputForm.style.display = "none";
      questionContainer.style.display = "block";

      showQuestion();
    } catch (error) {
      console.error("Error:", error);
      alert("Something went wrong while generating quiz.");
    }
  });
}

function showQuestion() {
  resetState();
  let currentQuestion = quizData.questions[currentQuestionIndex];
  questionElement.innerText = `${currentQuestionIndex + 1}. ${
    currentQuestion.question_text
  }`;

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
