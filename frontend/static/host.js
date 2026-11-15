const questionSelect = document.getElementById("question-select");
const customQuestion = document.getElementById("custom-question");
const customField = document.getElementById("custom-question-field");
const roundCount = document.getElementById("round-count");

function updateQuestion() {
  const isCustom = questionSelect.value === "custom";
  customField.hidden = !isCustom;
  customQuestion.required = isCustom;
  const text = isCustom ? customQuestion.value.trim() : questionSelect.value;
  for (const question of document.querySelectorAll("[data-question]")) {
    question.textContent = text;
  }
}

function updateRoundBalance() {
  const perSource = Number(roundCount.value) / 2;
  document.getElementById("balance-note").textContent =
    `${perSource} human answers · ${perSource} AI answers`;
}

async function loadQuestions() {
  try {
    const response = await fetch("/static/questions.json");
    if (!response.ok) throw new Error("Question list unavailable");
    const questions = await response.json();
    if (!Array.isArray(questions) || !questions.length ||
        questions.some((question) => typeof question !== "string" || !question.trim())) {
      throw new Error("Invalid question list");
    }
    const options = questions.map((question) => {
      const option = document.createElement("option");
      option.value = question;
      option.textContent = question;
      return option;
    });
    questionSelect.prepend(...options);
    if (!customQuestion.value.trim()) questionSelect.value = questions[0];
    updateQuestion();
  } catch {
    const message = document.getElementById("question-error");
    message.textContent = "The question list couldn’t load. You can still write your own.";
    message.hidden = false;
  }
}

questionSelect.addEventListener("change", updateQuestion);
customQuestion.addEventListener("input", updateQuestion);
roundCount.addEventListener("change", updateRoundBalance);

// Prevent accidental navigation or a success claim while room creation is unavailable.
document.getElementById("setup-form").addEventListener("submit", (event) => event.preventDefault());
updateQuestion();
updateRoundBalance();
loadQuestions();
