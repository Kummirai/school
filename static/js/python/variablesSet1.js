// validateVariablesPythonSet1.js

function validateVariableSet1(category, correctAnswers) {
  const inputFields = document.querySelectorAll(".quiz-question input");
  let results = {
    correct: 0,
    total: correctAnswers.length,
  };

  inputFields.forEach((input, index) => {
    const userAnswer = input.value.trim().toLowerCase();
    const correctAnswer = correctAnswers[index].trim().toLowerCase();

    if (userAnswer === correctAnswer) {
      input.classList.add("is-valid");
      input.classList.remove("is-invalid");
      results.correct++;
    } else {
      input.classList.add("is-invalid");
      input.classList.remove("is-valid");
    }
  });

  // Show feedback
  const feedbackDiv =
    inputFields[inputFields.length - 1].closest(
      ".quiz-question"
    ).nextElementSibling;
  if (feedbackDiv) {
    feedbackDiv.innerHTML = `<strong>Score:</strong> ${results.correct} / ${results.total}`;
  }

  // Send results to server
  fetch("/api/record-practice", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      subject: "Python",
      topic: "Variables",
      score: results.correct,
      total_questions: results.total,
    }),
  })
    .then((response) => {
      if (response.ok) {
        console.log("Results recorded successfully.");
      } else {
        console.error("Failed to record results.");
      }
    })
    .catch((error) => {
      console.error("Error recording results:", error);
    });
}
