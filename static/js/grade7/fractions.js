function updateFraction() {
    const slider = document.getElementById("fractionSlider");
    const valueDisplay = document.getElementById("fractionValue");
    const value = slider.value;
    valueDisplay.textContent = "1/" + value;
    const circles = document.querySelectorAll(".fraction-circle");
    circles.forEach((circle) => {
      const filled = circle.querySelector("div");
      filled.style.height = 100 / value + "%";
    });
  }
  function findEquivalents() {
    const num = parseInt(document.getElementById("numerator").value);
    const den = parseInt(document.getElementById("denominator").value);
    const container = document.getElementById("equivalentFractions");
    container.innerHTML = "";
    for (let i = 2; i <= 5; i++) {
      const equivNum = num * i;
      const equivDen = den * i;
      const fraction = document.createElement("span");
      fraction.className = "badge bg-secondary me-2 mb-2";
      fraction.textContent = equivNum + "/" + equivDen;
      container.appendChild(fraction);
    }
  }
  function simplifyFraction() {
    const num = parseInt(document.getElementById("simplifyNum").value);
    const den = parseInt(document.getElementById("simplifyDen").value);
    const gcd = greatestCommonDivisor(num, den);
    const result = document.getElementById("simplifiedResult");
    if (gcd === 1) {
      result.textContent = num + "/" + den + " is already in simplest form";
    } else {
      result.textContent = "Simplified: " + num / gcd + "/" + den / gcd;
    }
  }
  function greatestCommonDivisor(a, b) {
    return b ? greatestCommonDivisor(b, a % b) : a;
  }
  function calculateFraction(operation) {
    const num1 = parseInt(
      document.getElementById(operation === "add" ? "addNum1" : "multNum1")
        .value
    );
    const den1 = parseInt(
      document.getElementById(operation === "add" ? "addDen1" : "multDen1")
        .value
    );
    const num2 = parseInt(
      document.getElementById(operation === "add" ? "addNum2" : "multNum2")
        .value
    );
    const den2 = parseInt(
      document.getElementById(operation === "add" ? "addDen2" : "multDen2")
        .value
    );
    const resultElement = document.getElementById(
      operation === "add" ? "addFractionResult" : "multFractionResult"
    );
    if (operation === "add") {
      const commonDen = den1 * den2;
      const newNum = num1 * den2 + num2 * den1;
      const gcd = greatestCommonDivisor(newNum, commonDen);
      resultElement.textContent =
        "Result: " + newNum / gcd + "/" + commonDen / gcd;
    } else {
      const resultNum = num1 * num2;
      const resultDen = den1 * den2;
      const gcd = greatestCommonDivisor(resultNum, resultDen);
      resultElement.textContent =
        "Result: " + resultNum / gcd + "/" + resultDen / gcd;
    }
  }
  function toggleQuestions(setId) {
    const element = document.getElementById(setId);
    if (element.style.display === "none") {
      element.style.display = "block";
    } else {
      element.style.display = "none";
    }
  }
  function validateFractionAnswers(setId, answers) {
    let allCorrect = true;
    const feedbackDiv = document.getElementById(`${setId}-feedback`);

    // Check each question in the set
    for (let i = 0; i < answers.length; i++) {
      // Updated ID pattern to match your HTML structure
      const inputId = `${setId.replace("Set", "")}-q${i + 1}`;
      const inputElement = document.getElementById(inputId);

      // Check if element exists before trying to access it
      if (!inputElement) {
        console.error(`Element with ID ${inputId} not found`);
        continue;
      }

      const userAnswer = inputElement.value.trim();
      const correctAnswer = answers[i];
      const questionElement = inputElement.parentNode;

      // Use the compareFractions function for proper fraction comparison
      if (compareFractions(userAnswer, correctAnswer)) {
        inputElement.classList.remove("is-invalid");
        inputElement.classList.add("is-valid");
        questionElement.style.color = "green";
      } else {
        inputElement.classList.remove("is-valid");
        inputElement.classList.add("is-invalid");
        questionElement.style.color = "red";
        allCorrect = false;
      }
    }

    // Provide feedback
    if (feedbackDiv) {
      if (allCorrect) {
        feedbackDiv.textContent = "All answers correct! Great job! 🎉";
        feedbackDiv.style.color = "green";
      } else {
        feedbackDiv.textContent = "Some answers incorrect. Try again! 💪";
        feedbackDiv.style.color = "red";
      }
    }
  }

  // Helper function to compare fractions (accepts equivalent fractions)
  function compareFractions(userAnswer, correctAnswer) {
    // Handle empty answers
    if (!userAnswer) return false;

    // Handle whole numbers
    if (userAnswer === correctAnswer) return true;

    // Parse fractions
    const userParts = userAnswer.split("/");
    const correctParts = correctAnswer.split("/");

    // If not a fraction format, do direct comparison
    if (userParts.length !== 2 || correctParts.length !== 2) {
      return userAnswer === correctAnswer;
    }

    // Convert to numbers
    const userNum = parseInt(userParts[0]);
    const userDen = parseInt(userParts[1]);
    const correctNum = parseInt(correctParts[0]);
    const correctDen = parseInt(correctParts[1]);

    // Check for division by zero
    if (userDen === 0 || correctDen === 0) return false;

    // Cross multiply to check equivalence
    return userNum * correctDen === correctNum * userDen;
  }