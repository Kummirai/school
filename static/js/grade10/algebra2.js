// validation-algebra2.js
const AlgebraPracticeManager2 = {
  init: function () {
    this.addEventListeners();
    this.markInputsWithIds();
  },

  correctAnswers: {
    // Exercise 1
    "1a": "g² - 121",
    "1b": "8b² - 20b + 8",
    "1c": "8b² - 10b + 3",

    // Exercise 2
    "2d": "18x² + 24x - 24",
    "2e": "6w² + 17w - 14",
    "2f": "4t² - 12t + 9",

    // Exercise 3
    "3g": "25p² - 80p + 64",
    "3h": "16y² + 40y + 25",
    "3i": "-10y⁷ - 24y⁶ - 15y⁶ - 36y⁵",

    // Exercise 4
    "4j": "72y² - 18y + 27",
    "4k": "-10y³ + 24y² - 20y² + 48y + 55y - 132",
    "4l": "-14y³ + 14y² + 12y² - 12y + 16y - 16",

    // Exercise 5
    "5m": "-20y³ - 110y² + 20y - 6y² - 33y + 6",
    "5n": "-24y³ + 132y² - 36y - 6y² + 33y - 9",
    "5o": "-20y² - 80y - 30",

    // Exercise 6
    "6p": "49y³ + 21y² + 70y + 21y² + 9y + 30",
    "6q": "a³ + ab² + 2a²b + 2a²b + 2b³ + 4ab²",
    "6r": "x³ - x²y + xy² + x²y - xy² + y³",

    // Exercise 7
    "7s": "27m³ + 6m + 25m³ + 30m²",
    "7t": "40x⁵ + 16x² + 8x⁵ + 24x³",
    "7u": "3k⁵ + 9k³ + 12k⁵ + 14k²",

    // Exercise 8
    "8v": "81x⁴ - 72x² + 16",
    "8w": "-6y⁶ + 96y⁴ + 11y⁴ - 176y² + 3y³ - 48y",
    "8x": "x⁴ + 2x³ - 3x² - 3x³ - 6x² + 9x + 6x² + 12x - 18",

    // Exercise 9
    "9y": "-3a² + 20a - 12",
  },

  addEventListeners: function () {
    document.querySelectorAll(".form-control").forEach((input) => {
      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") this.validateAll();
      });
    });

    if (document.querySelector(".btn-check-answers")) {
      document
        .querySelector(".btn-check-answers")
        .addEventListener("click", () => this.validateAll());
    }
  },

  markInputsWithIds: function () {
    document.querySelectorAll(".quiz-question").forEach((question, index) => {
      const exerciseNum = Math.floor(index / 3) + 1;
      const questionLetter = String.fromCharCode(97 + (index % 3));
      const input = question.querySelector("input");
      if (input && !input.dataset.id) {
        input.dataset.id = `${exerciseNum}${questionLetter}`;
      }
    });
  },

  validateAll: function () {
    const results = {
      total: Object.keys(this.correctAnswers).length,
      correct: 0,
      incorrect: 0,
      unanswered: 0,
      details: [],
    };

    for (const [id, correctAnswer] of Object.entries(this.correctAnswers)) {
      const input = document.querySelector(`input[data-id="${id}"]`);
      const userAnswer = input ? input.value.trim() : "";
      const isAnswered = userAnswer !== "";
      let isCorrect = false;

      input?.classList.remove("is-valid", "is-invalid");
      const existingHint = input?.parentNode.querySelector(
        ".correct-answer-hint"
      );
      if (existingHint) existingHint.remove();

      if (!isAnswered) {
        results.unanswered++;
        input?.classList.add("is-invalid");
        if (input) {
          const hint = document.createElement("small");
          hint.className = "text-success correct-answer-hint ms-2";
          hint.textContent = `Correct: ${correctAnswer}`;
          input.parentNode.appendChild(hint);
        }
      } else {
        isCorrect =
          this.normalizeAnswer(userAnswer) ===
          this.normalizeAnswer(correctAnswer);

        if (isCorrect) {
          results.correct++;
          input.classList.add("is-valid");
        } else {
          results.incorrect++;
          input.classList.add("is-invalid");
          const hint = document.createElement("small");
          hint.className = "text-success correct-answer-hint ms-2";
          hint.textContent = `Correct: ${correctAnswer}`;
          input.parentNode.appendChild(hint);
        }
      }

      results.details.push({
        questionId: id,
        correct: isCorrect,
        answered: isAnswered,
        userAnswer: userAnswer,
        correctAnswer: correctAnswer,
      });
    }

    this.showResults(results);
    this.recordPracticeSession(results);
    return results;
  },

  normalizeAnswer: function (answer) {
    return answer
      .replace(/\s+/g, "")
      .replace(/(\d)([a-z])/g, "$1*$2")
      .replace(/\^/g, "")
      .toLowerCase();
  },

  showResults: function (results) {
    const feedbackDiv = document.querySelector(".feedback");
    if (!feedbackDiv) return;

    const percentage = Math.round((results.correct / results.total) * 100);
    const alertClass =
      percentage === 100
        ? "alert-success"
        : percentage >= 70
        ? "alert-info"
        : percentage >= 50
        ? "alert-warning"
        : "alert-danger";

    feedbackDiv.innerHTML = `
      <div class="alert ${alertClass}">
        <h5>Results: ${results.correct}/${results.total} (${percentage}%)</h5>
        <p>${this.getFeedbackMessage(percentage)}</p>
        <ul class="mb-0">
          <li>Correct: ${results.correct}</li>
          <li>Incorrect: ${results.incorrect}</li>
          <li>Unanswered: ${results.unanswered}</li>
        </ul>
      </div>
    `;

    feedbackDiv.scrollIntoView({ behavior: "smooth" });
  },

  getFeedbackMessage: function (percentage) {
    if (percentage === 100)
      return "Perfect score! Masterful work with algebraic expansions!";
    if (percentage >= 90)
      return "Excellent! You nearly aced these challenging problems!";
    if (percentage >= 70)
      return "Well done! Review the few mistakes to perfect your technique.";
    if (percentage >= 50)
      return "Good effort! Focus on the patterns you missed.";
    return "Keep practicing! These expansions get easier with repetition.";
  },

  recordPracticeSession: function (results) {
    fetch("/api/record-practice", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        subject: "Mathematics",
        topic: "Advanced Algebraic Expansion",
        score: results.correct,
        total_questions: results.total,
        unanswered: results.unanswered,
        percentage: Math.round((results.correct / results.total) * 100),
        timestamp: new Date().toISOString(),
        details: results.details,
      }),
    })
      .then((response) => {
        if (!response.ok) console.error("Failed to record practice results");
        return response.json();
      })
      .catch((error) => {
        console.error("Error recording practice:", error);
      });
  },

  showAnswers: function () {
    for (const [id, correctAnswer] of Object.entries(this.correctAnswers)) {
      const input = document.querySelector(`input[data-id="${id}"]`);
      if (input) {
        input.value = correctAnswer;
        input.classList.add("is-valid");
        const existingHint = input.parentNode.querySelector(
          ".correct-answer-hint"
        );
        if (existingHint) existingHint.remove();
      }
    }
  },
};

document.addEventListener("DOMContentLoaded", function () {
  AlgebraPracticeManager2.init();
});

window.validateAlgebraSet2 = function () {
  return AlgebraPracticeManager2.validateAll();
};

window.showAlgebraAnswers2 = function () {
  return AlgebraPracticeManager2.showAnswers();
};
