let currentQuestionIndex = 0;
let score = 0;
let quizData = {};

const questionContainer = document.getElementById("question-container");
const questionElement = document.getElementById("question");
const answerButtons = document.getElementById("answer-buttons");
const resultElement = document.getElementById("result");
const nextButton = document.getElementById("next-btn");
const topicButton = document.getElementById("topic_btn");
const pdfButton = document.getElementById("pdf_btn");
const topicInputForm = document.getElementById("topicInput1");
const option2Container = document.getElementById("card2");
const option1Container = document.getElementById("card1");
const toggleBtn = document.getElementById("theme-switch");
// Removed unused: const app = document.getElementsByClassName("app");
const uploadForm = document.getElementById("uploadForm");
const uploadResult1 = document.getElementById("uploadResult1");
const uploadResult2 = document.getElementById("uploadResult2");

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

topicButton.addEventListener("click", ()=>{
  if(questionContainer.style.display == "block" && currentQuestionIndex < quizData.questions.length){
    alert("Please complete the quiz");
    return;
  }
  option2Container.style.display = "none";
  option1Container.style.display = "block";
})
pdfButton.addEventListener("click", ()=>{
  if(questionContainer.style.display == "block"){
    alert("Please complete the quiz");
    return;
  }
  option1Container.style.display = "none";
  option2Container.style.display = "block";
})
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
    uploadResult1.textContent = "Generating quiz...";
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
      // Hide entire cards section
      option1Container.style.display = "none";
      option2Container.style.display = "none";
      questionContainer.style.display = "block";

      showQuestion();
    } catch (error) {
      console.error("Error:", error);
      alert("Something went wrong while generating quiz.");
    }
  });
}

// Handle PDF upload to generate quiz from PDF
if (uploadForm) {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(uploadForm);
    uploadResult2.textContent = "Uploading and generating quiz...";
    try {
      const res = await fetch("/upload-pdf", { method: "POST", body: formData });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      // Fetch the generated questions and show quiz
      const quizRes = await fetch("/static/questions.json?" + Date.now());
      quizData = await quizRes.json();

      option1Container.style.display = "none";
      option2Container.style.display = "none";
      questionContainer.style.display = "block";
      currentQuestionIndex = 0;
      score = 0;
      showQuestion();
      uploadResult2.textContent = "Quiz generated from PDF.";
    } catch (err) {
      console.error(err);
      uploadResult2.textContent = "Error: " + err.message;
    }
  });
}

function showQuestion() {
  resetState();
  let currentQuestion = quizData.questions[currentQuestionIndex];
  questionElement.innerText = `${currentQuestionIndex + 1}. ${currentQuestion.question_text
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
