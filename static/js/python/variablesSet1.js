function validateVariableSet1() {
  // Get all input elements within the quiz questions
  const inputs = document.querySelectorAll(
    '.interactive-exercise input[type="text"], .practice-sets input[type="text"]'
  );

  // Correct answers in order of appearance in the HTML
  const correctAnswers = [
    "x = 10",
    'greeting = "hello"',
    "int",
    "str",
    "score = 5",
    "variable_name = 25",
    'message = "Python is fun"',
    "12", // For age = [input]
    '"John"', // For name = [input]
    "5", // Final x value
  ];

  let correctCount = 0;
  const feedbackElement = document.querySelector(".feedback");

  inputs.forEach((input, index) => {
    const userAnswer = input.value.trim();
    const correctAnswer = correctAnswers[index];

    // Special case handling for different answer formats
    let isCorrect = false;

    if (
      index === 0 &&
      (userAnswer === "x=10" ||
        userAnswer === "x =10" ||
        userAnswer === "x= 10")
    ) {
      isCorrect = true; // Accept various spacing formats for x assignment
    } else if (
      index === 1 &&
      userAnswer.toLowerCase().includes("greeting") &&
      userAnswer.includes("hello")
    ) {
      isCorrect = true; // More flexible check for greeting assignment
    } else if (index === 7 && !isNaN(userAnswer)) {
      isCorrect = true; // Any number is acceptable for age
    } else if (
      index === 8 &&
      (userAnswer.includes('"') || userAnswer.includes("'"))
    ) {
      isCorrect = true; // Any quoted string is acceptable for name
    } else {
      isCorrect = userAnswer === correctAnswer;
    }

    if (isCorrect) {
      input.classList.add("is-valid");
      input.classList.remove("is-invalid");
      correctCount++;
    } else {
      input.classList.add("is-invalid");
      input.classList.remove("is-valid");
    }
  });

  // Calculate percentage
  const percentage = Math.round((correctCount / inputs.length) * 100);

  // Display results
  if (feedbackElement) {
    let message = "";
    let alertClass = "";

    if (percentage === 100) {
      message = "Perfect! You got all answers correct!";
      alertClass = "alert-success";
    } else if (percentage >= 70) {
      message = `Good job! You got ${correctCount} out of ${inputs.length} correct.`;
      alertClass = "alert-info";
    } else {
      message = `You got ${correctCount} out of ${inputs.length} correct. Keep practicing!`;
      alertClass = "alert-warning";
    }

    feedbackElement.innerHTML = `
      <div class="alert ${alertClass}">
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    `;
  }

  // Send results to the database (if endpoint exists)
  fetch("/api/record-practice", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      subject: "Python",
      topic: "Variables",
      score: correctCount,
      total_questions: inputs.length,
      percentage: percentage,
    }),
  }).catch((error) => console.error("Error recording practice:", error));
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Add click event to the button if it exists
  const validateButton = document.querySelector(".btn-success");
  if (validateButton) {
    validateButton.addEventListener("click", validateVariableSet1);
  }

  // Also allow Enter key to submit answers
  const inputs = document.querySelectorAll('input[type="text"]');
  inputs.forEach((input) => {
    input.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        validateVariableSet1();
      }
    });
  });
});
