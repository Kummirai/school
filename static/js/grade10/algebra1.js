// validation.js
document.addEventListener("DOMContentLoaded", function () {
  // Define correct answers for all problems
  const correctAnswers = {
    // Exercise 1
    "1a": "2y² + 8y",
    "1b": "y² + 7y + 10",
    "1c": "2 - 5t + 2t²",
    "1d": "x² - 16",
    "1e": "x² - 16",
    "1f": "a² - b²",

    // Exercise 2
    "2g": "6p² + 29p + 9",
    "2h": "3k² + 16k - 12",
    "2i": "s² + 12s + 36",
    "2j": "x² - 49",
    "2k": "9x² - 1",
    "2l": "21k - 14k² + 6 - 4k",

    // Exercise 3
    "3m": "1 - 8x + 16x²",
    "3n": "y² - 2y - 15",
    "3o": "64 - x²",
    "3p": "81 + 18x + x²",
    "3q": "84y² - 117y + 33",
    "3r": "g² - 10g + 25",

    // Exercise 4
    "4s": "d² + 18d + 81",
    "4t": "36d² - 49",
    "4u": "25z² - 1",
    "4v": "1 - 9h²",
    "4w": "4p² + 10p + 6",
    "4x": "8a² + 60a + 28",

    // Exercise 5
    "5y": "10r² + 28r + 16",
    "5z": "w² - 1",
  };

  // Validate all answers
  window.validateExpansionSet1 = function () {
    let correctCount = 0;
    const totalQuestions = Object.keys(correctAnswers).length;
    const feedbackDiv = document.querySelector(".feedback");
    feedbackDiv.innerHTML = "";

    // Check each answer
    for (const [id, correctAnswer] of Object.entries(correctAnswers)) {
      const inputElement = document.querySelector(`input[data-id="${id}"]`);
      const userAnswer = inputElement ? inputElement.value.trim() : "";

      if (userAnswer === correctAnswer) {
        correctCount++;
        if (inputElement) {
          inputElement.classList.remove("is-invalid");
          inputElement.classList.add("is-valid");
        }
      } else {
        if (inputElement) {
          inputElement.classList.remove("is-valid");
          inputElement.classList.add("is-invalid");
        }
      }
    }

    // Display results
    const scorePercentage = Math.round((correctCount / totalQuestions) * 100);
    feedbackDiv.innerHTML = `
      <div class="alert ${
        scorePercentage >= 80 ? "alert-success" : "alert-info"
      }">
        <h5>Results: ${correctCount}/${totalQuestions} (${scorePercentage}%)</h5>
        ${generateFeedbackMessage(scorePercentage)}
      </div>
    `;

    // Send results to database
    recordPracticeResults(correctCount, totalQuestions);
  };

  // Generate feedback message based on score
  function generateFeedbackMessage(percentage) {
    if (percentage >= 90)
      return "<p>Excellent work! You've mastered these expansions.</p>";
    if (percentage >= 70)
      return "<p>Good job! Review the incorrect answers for improvement.</p>";
    if (percentage >= 50)
      return "<p>Keep practicing! Focus on the problems you missed.</p>";
    return "<p>Review the concepts and try again. You'll improve with practice!</p>";
  }

  // Record practice results to database
  function recordPracticeResults(correct, total) {
    fetch("/api/record-practice", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        subject: "Mathematics",
        topic: "Algebraic Expressions",
        score: correct,
        total_questions: total,
        timestamp: new Date().toISOString(),
      }),
    })
      .then((response) => {
        if (!response.ok) {
          console.error("Failed to record practice results");
        }
        return response.json();
      })
      .catch((error) => {
        console.error("Error recording practice:", error);
      });
  }

  // Add event listeners to all input fields
  document.querySelectorAll(".form-control").forEach((input) => {
    input.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        validateExpansionSet1();
      }
    });
  });

  // Add data-id attributes to inputs (if not already in HTML)
  document.querySelectorAll(".quiz-question").forEach((question, index) => {
    const exerciseNum = Math.floor(index / 6) + 1; // Group by 6 questions per exercise
    const questionLetter = String.fromCharCode(97 + (index % 6)); // a-f
    const input = question.querySelector("input");
    if (input) {
      input.dataset.id = `${exerciseNum}${questionLetter}`;
    }
  });
});
