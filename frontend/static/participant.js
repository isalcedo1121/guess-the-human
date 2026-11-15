const answer = document.getElementById("submission");
const total = document.getElementById("character-total");

function updateCharacterCount() {
  total.textContent = String(answer.value.length);
}

answer.addEventListener("input", updateCharacterCount);
// Do not acknowledge a submission before a working submission endpoint exists.
document.getElementById("answer-form").addEventListener("submit", (event) => event.preventDefault());
updateCharacterCount();
