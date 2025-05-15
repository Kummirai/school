// Enhanced QuizManager with unanswered question handling
const QuizManager = {
  // Toggle question sets with animation
  toggleQuestions: function (setId) {
    const set = document.getElementById(setId);
    if (set) {
      set.style.transition = "all 0.3s ease";
      set.style.display = set.style.display === "none" ? "block" : "none";

      if (set.style.display === "block") {
        setTimeout(() => {
          set.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }, 50);
      }
    }
  },

  // Handle answer selection with visual feedback
  selectAnswer: function (option, correctType) {
    if (!option || !correctType) return;

    const questionDiv = option.closest(".quiz-question");
    if (!questionDiv) return;

    const options = questionDiv.querySelectorAll(".quiz-option");
    const correctValue = correctType.toLowerCase();

    options.forEach((opt) => {
      opt.classList.remove("bg-success", "bg-danger");
      if (opt === option) {
        const isCorrect = opt.textContent.toLowerCase().includes(correctValue);
        opt.classList.add(isCorrect ? "bg-success" : "bg-danger");
      }
    });
  },

  // Validate all questions in a set with unanswered handling
  // Modify the validateSet function in QuizManager
  validateSet: function (setId, correctAnswers) {
    const set = document.getElementById(setId);
    if (!set || !correctAnswers) return;

    let score = 0;
    const questions = set.querySelectorAll(".quiz-question");
    const results = {
      total: questions.length,
      correct: 0,
      incorrect: 0,
      unanswered: 0,
      details: [],
    };

    questions.forEach((question, index) => {
      const answer = correctAnswers[index];
      if (!answer) return;

      let isCorrect = false;
      let isAnswered = false;

      // ... (existing validation logic) ...

      results.details.push({
        question: index + 1,
        correct: isCorrect,
        answered: isAnswered,
      });
    });

    // Record score to leaderboard
    fetch("/api/record-practice", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        subject: "Mathematics",
        topic: "Rational Numbers",
        score: results.correct,
        total_questions: results.total,
      }),
    });

    // Display comprehensive results
    const feedback = document.getElementById(`${setId}-feedback`);
    if (feedback) {
      const percentage = Math.round((results.correct / results.total) * 100);
      feedback.innerHTML = `
          <div class="alert ${
            percentage === 100 ? "alert-success" : "alert-warning"
          }">
            <strong>Results:</strong> 
            ${results.correct} correct, 
            ${results.incorrect} incorrect,
            ${results.unanswered} unanswered
            (${percentage}%)
          </div>
        `;
      feedback.scrollIntoView({ behavior: "smooth" });
    }

    return results;
  },

  // Show all correct answers
  showAnswers: function (setId) {
    const set = document.getElementById(setId);
    if (!set) return;

    set.querySelectorAll(".quiz-question").forEach((question) => {
      // Clear previous feedback
      const existingFeedback = question.querySelector(".text-success");
      if (existingFeedback) {
        existingFeedback.remove();
      }

      // For multiple choice
      question.querySelectorAll(".quiz-option").forEach((opt) => {
        opt.classList.remove("bg-success", "bg-danger");
      });

      // For input fields
      question.querySelectorAll("input").forEach((input) => {
        input.classList.remove("is-valid", "is-invalid");
      });
    });
  },

  // Helper functions for specific question types
  validateRational: function (setId, answers) {
    return this.validateSet(setId, answers);
  },
  validateRounding: function (setId, answers) {
    return this.validateSet(setId, answers);
  },
  validateSurds: function (setId, answers) {
    return this.validateSet(setId, answers);
  },
};

// Global shortcuts for backward compatibility
function toggleQuestions(setId) {
  QuizManager.toggleQuestions(setId);
}

function selectAnswer(option, correctType) {
  QuizManager.selectAnswer(option, correctType);
}

function validateAnswers(setId, answers) {
  return QuizManager.validateSet(setId, answers);
}

function validateQuestionSet(setId, answers) {
  return QuizManager.validateSet(setId, answers);
}

function validateRationalSet(setId, answers) {
  return QuizManager.validateRational(setId, answers);
}

function validateRoundingSet(setId, answers) {
  return QuizManager.validateRounding(setId, answers);
}

function validateSurdsSet(setId, answers) {
  return QuizManager.validateSurds(setId, answers);
}

// Add these aliases to handle both naming conventions
function validateRational(setId, answers) {
  return QuizManager.validateRational(setId, answers);
}

function validateRounding(setId, answers) {
  return QuizManager.validateRounding(setId, answers);
}

function validateSurds(setId, answers) {
  return QuizManager.validateSurds(setId, answers);
}

// ===== Helper Functions =====
