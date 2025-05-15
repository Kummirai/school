// Clear all highlights
function resetHighlights(element) {
  element.querySelectorAll("p").forEach((p) => {
    p.innerHTML = p.textContent;
  });
}

// Escape special characters for regex
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Highlight matching words
function applyHighlights(element, className, wordsToHighlight) {
  const paragraph = element.querySelector("p");
  let text = paragraph.textContent;

  wordsToHighlight.forEach((word) => {
    const regex = new RegExp(`\\b${escapeRegExp(word)}\\b`, "gi");
    text = text.replace(
      regex,
      (match) => `<span class="${className}">${match}</span>`
    );
  });

  paragraph.innerHTML = text;
}

// ===== Highlighting Functions =====

function highlightVerb(element) {
  resetHighlights(element);

  const sentence = element.querySelector("p").textContent;
  const words = sentence.split(/\s+/);

  const verbs = words.filter(
    (word) =>
      /(ing|ed|s)$/i.test(word) ||
      [
        "is",
        "am",
        "are",
        "was",
        "were",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "can",
        "could",
        "shall",
        "should",
        "may",
        "might",
        "must",
      ].includes(word.toLowerCase())
  );

  applyHighlights(element, "highlight-verb", verbs);
}

function highlightNoun(element) {
  resetHighlights(element);

  const sentence = element.querySelector("p").textContent;
  const words = sentence.split(/\s+/);

  const nouns = words.filter(
    (word) =>
      /^[A-Z][a-z]*$/.test(word) || // Proper nouns
      ["the", "a", "an"].includes(word.toLowerCase()) ||
      /(tion|ment|ness|ity|ance|ence)$/i.test(word)
  );

  applyHighlights(element, "highlight-noun", nouns);
}

function highlightPronoun(element) {
  resetHighlights(element);

  const sentence = element.querySelector("p").textContent;
  const pronouns = [
    "I",
    "me",
    "my",
    "mine",
    "myself",
    "you",
    "your",
    "yours",
    "yourself",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "we",
    "us",
    "our",
    "ours",
    "ourselves",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "this",
    "that",
    "these",
    "those",
    "who",
    "whom",
    "whose",
    "which",
    "what",
    "each",
    "either",
    "neither",
    "some",
    "any",
    "none",
    "all",
    "most",
  ];

  applyHighlights(element, "highlight-pronoun", pronouns);
}

// ===== Validation Logic =====

// Modify the validateAnswers function
function validateAnswers(type, correctAnswers) {
  const questions = document.querySelectorAll(`.quiz-question`);
  let allCorrect = true;
  const feedbackDiv = document.querySelector(".feedback");
  let correctCount = 0;

  questions.forEach((question, index) => {
    if (index >= correctAnswers.length) return;

    const input = question.querySelector("input");
    const userAnswer = input.value.trim().toLowerCase();
    const correct = correctAnswers[index].toLowerCase();

    if (correct.includes(",")) {
      const userSet = new Set(userAnswer.split(",").map((a) => a.trim()));
      const correctSet = new Set(correct.split(",").map((a) => a.trim()));

      const isCorrect =
        userSet.size === correctSet.size &&
        [...userSet].every((val) => correctSet.has(val));

      input.classList.toggle("is-valid", isCorrect);
      input.classList.toggle("is-invalid", !isCorrect);
      if (isCorrect) correctCount++;
      if (!isCorrect) allCorrect = false;
    } else {
      const isCorrect = userAnswer === correct;
      input.classList.toggle("is-valid", isCorrect);
      input.classList.toggle("is-invalid", !isCorrect);
      if (isCorrect) correctCount++;
      if (!isCorrect) allCorrect = false;
    }
  });

  // Record score to leaderboard
  fetch("/api/record-practice", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      subject: "English",
      topic: "Parts of Speech",
      score: correctCount,
      total_questions: correctAnswers.length,
    }),
  });

  if (feedbackDiv) {
    feedbackDiv.innerHTML = allCorrect
      ? '<div class="alert alert-success">All answers correct! Well done!</div>'
      : `<div class="alert alert-warning">You got ${correctCount}/${correctAnswers.length} correct. Try again!</div>`;
  }
}

// ===== Mixed Practice Checker =====

function checkAnswer(button) {
  const container = button.closest(".sentence-analysis");
  const sentence = container.querySelector(".sentence").textContent.trim();
  const verbInput = container.querySelector("input:nth-of-type(1)");
  const nounInput = container.querySelector("input:nth-of-type(2)");
  const pronounInput = container.querySelector("input:nth-of-type(3)");
  const feedbackDiv = container.querySelector(".feedback");

  // Sentence-specific answers
  let correct = {
    verbs: [],
    nouns: [],
    pronouns: [],
  };

  if (sentence === "The quick brown fox jumps over the lazy dog.") {
    correct = {
      verbs: ["jumps"],
      nouns: ["fox", "dog"],
      pronouns: [],
    };
  }

  const check = (input, correctArr) => {
    const userValues = input.value
      .trim()
      .toLowerCase()
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
    const correctValues = correctArr.map((v) => v.toLowerCase());
    const isMatch = arraysEqual(userValues, correctValues);

    input.classList.toggle("is-valid", isMatch);
    input.classList.toggle("is-invalid", !isMatch);

    return isMatch;
  };

  const isVerbCorrect = check(verbInput, correct.verbs);
  const isNounCorrect = check(nounInput, correct.nouns);
  const isPronounCorrect = check(pronounInput, correct.pronouns);

  if (isVerbCorrect && isNounCorrect && isPronounCorrect) {
    feedbackDiv.innerHTML =
      '<div class="alert alert-success">Perfect! All parts of speech identified correctly!</div>';
  } else {
    let feedback =
      '<div class="alert alert-warning"><p>Some corrections needed:</p><ul>';
    if (!isVerbCorrect)
      feedback += `<li>Verbs: ${correct.verbs.join(", ")}</li>`;
    if (!isNounCorrect)
      feedback += `<li>Nouns: ${correct.nouns.join(", ")}</li>`;
    if (!isPronounCorrect && correct.pronouns.length > 0)
      feedback += `<li>Pronouns: ${correct.pronouns.join(", ")}</li>`;
    feedback += "</ul></div>";
    feedbackDiv.innerHTML = feedback;
  }
}

// ===== Utility Function =====

function arraysEqual(a, b) {
  if (a.length !== b.length) return false;
  const sortedA = [...a].sort();
  const sortedB = [...b].sort();
  return sortedA.every((val, index) => val === sortedB[index]);
}

// ===== Styles =====

const style = document.createElement("style");
style.textContent = `
  .highlight-verb { background-color: #ffcccc; border-radius: 3px; padding: 0 2px; }
  .highlight-noun { background-color: #ccffcc; border-radius: 3px; padding: 0 2px; }
  .highlight-pronoun { background-color: #ccccff; border-radius: 3px; padding: 0 2px; }
  .is-valid { border-color: #28a745; background-color: #e6ffe6; }
  .is-invalid { border-color: #dc3545; background-color: #ffe6e6; }
`;
document.head.appendChild(style);
