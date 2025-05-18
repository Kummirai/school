// validation-algebra3.js
const AlgebraPracticeManager3 = {
  init: function() {
    this.addEventListeners();
    this.markInputsWithIds();
  },

  correctAnswers: {
    // Exercise 1
    '1a': '3x² + 16x + 5',
    '1b': '2a⁴ + 5a³ - 3a² - 5a - 2',
    
    // Exercise 2
    '2c': '-y⁴ - 8y³ - 14y² + 8y - 1',
    '2d': '2x³ - 4x²y + 2xy² - 4x²y - 8xy² - 4y³',
    
    // Exercise 3
    '3e': '3a³ - 27a²b + 18ab² + 27b³',
    '3f': '8a⁴ - 12a³b + 2a²b² + 6ab³ - b⁴',
    
    // Exercise 4
    '4g': '9x² + 6xy - y²',
    '4h': '5x² - 4xy - 2y²',
    
    // Exercise 5
    '54': '3',
    '55': '-4',
    
    // Exercise 6
    '6a': '5',
    '6b': '-3, -1',
    '6c': 'k < 4',
    '6d': 'k > 4',
    
    // Exercise 7
    '7a': 'x² + 8 + 16/x²',
    '7b': '6',
    
    // Exercise 8
    '8a': 'a² + 2 + 1/a²',
    '8b': '9',
    '8c': '11',
    
    // Exercise 9
    '9a': '9y² + 3 + 1/(4y²)',
    '9b': '16',
    
    // Exercise 10
    '10a': 'a² + 2/3 + 1/(9a²)',
    '10b': 'a³ + 1/(27a³)',
    '10c': '8'
  },

  addEventListeners: function() {
    document.querySelectorAll('.form-control').forEach(input => {
      input.addEventListener('keypress', e => {
        if (e.key === 'Enter') this.validateAll();
      });
    });

    if (document.querySelector('.btn-check-answers')) {
      document.querySelector('.btn-check-answers').addEventListener('click', () => this.validateAll());
    }
  },

  markInputsWithIds: function() {
    let questionCounter = 1;
    document.querySelectorAll('.interactive-exercise').forEach((exercise, exIndex) => {
      exercise.querySelectorAll('.quiz-question').forEach((question, qIndex) => {
        const inputs = question.querySelectorAll('input');
        inputs.forEach((input, iIndex) => {
          const id = `${exIndex+1}${qIndex+1}${iIndex > 0 ? String.fromCharCode(97+iIndex) : ''}`;
          input.dataset.id = id;
        });
      });
    });
  },

  validateAll: function() {
    const results = {
      total: Object.keys(this.correctAnswers).length,
      correct: 0,
      incorrect: 0,
      unanswered: 0,
      details: []
    };

    for (const [id, correctAnswer] of Object.entries(this.correctAnswers)) {
      const input = document.querySelector(`input[data-id="${id}"]`);
      const userAnswer = input ? input.value.trim() : '';
      const isAnswered = userAnswer !== '';
      let isCorrect = false;

      input?.classList.remove('is-valid', 'is-invalid');
      const existingHint = input?.parentNode.querySelector('.correct-answer-hint');
      if (existingHint) existingHint.remove();

      if (!isAnswered) {
        results.unanswered++;
        input?.classList.add('is-invalid');
        if (input) {
          const hint = document.createElement('small');
          hint.className = 'text-success correct-answer-hint ms-2';
          hint.textContent = `Correct: ${correctAnswer}`;
          input.parentNode.appendChild(hint);
        }
      } else {
        isCorrect = this.normalizeAnswer(userAnswer) === this.normalizeAnswer(correctAnswer);
        
        if (isCorrect) {
          results.correct++;
          input.classList.add('is-valid');
        } else {
          results.incorrect++;
          input.classList.add('is-invalid');
          const hint = document.createElement('small');
          hint.className = 'text-success correct-answer-hint ms-2';
          hint.textContent = `Correct: ${correctAnswer}`;
          input.parentNode.appendChild(hint);
        }
      }

      results.details.push({
        questionId: id,
        correct: isCorrect,
        answered: isAnswered,
        userAnswer: userAnswer,
        correctAnswer: correctAnswer
      });
    }

    this.showResults(results);
    this.recordPracticeSession(results);
    return results;
  },

  normalizeAnswer: function(answer) {
    return answer
      .replace(/\s+/g, '')
      .replace(/(\d)([a-z(])/g, '$1*$2')
      .replace(/\^/g, '')
      .replace(/²/g, '2')
      .replace(/³/g, '3')
      .replace(/⁴/g, '4')
      .toLowerCase();
  },

  showResults: function(results) {
    const feedbackDiv = document.querySelector('.feedback');
    if (!feedbackDiv) return;

    const percentage = Math.round((results.correct / results.total) * 100);
    const alertClass = percentage === 100 ? 'alert-success' : 
                      percentage >= 70 ? 'alert-info' :
                      percentage >= 50 ? 'alert-warning' : 'alert-danger';

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

    feedbackDiv.scrollIntoView({ behavior: 'smooth' });
  },

  getFeedbackMessage: function(percentage) {
    if (percentage === 100) return 'Perfect! You\'ve mastered advanced algebraic techniques!';
    if (percentage >= 90) return 'Brilliant work! You clearly understand these concepts.';
    if (percentage >= 70) return 'Well done! Review the few mistakes for perfection.';
    if (percentage >= 50) return 'Good effort! Focus on the patterns you missed.';
    return 'Keep practicing! These advanced techniques take time to master.';
  },

  recordPracticeSession: function(results) {
    fetch("/api/record-practice", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        subject: "Mathematics",
        topic: "Advanced Algebraic Techniques",
        score: results.correct,
        total_questions: results.total,
        unanswered: results.unanswered,
        percentage: Math.round((results.correct / results.total) * 100),
        timestamp: new Date().toISOString(),
        details: results.details
      }),
    })
    .then(response => {
      if (!response.ok) console.error('Failed to record practice results');
      return response.json();
    })
    .catch(error => {
      console.error('Error recording practice:', error);
    });
  },

  showAnswers: function() {
    for (const [id, correctAnswer] of Object.entries(this.correctAnswers)) {
      const input = document.querySelector(`input[data-id="${id}"]`);
      if (input) {
        input.value = correctAnswer;
        input.classList.add('is-valid');
        const existingHint = input.parentNode.querySelector('.correct-answer-hint');
        if (existingHint) existingHint.remove();
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', function() {
  AlgebraPracticeManager3.init();
});

window.validateAlgebraSet3 = function() {
  return AlgebraPracticeManager3.validateAll();
};

window.showAlgebraAnswers3 = function() {
  return AlgebraPracticeManager3.showAnswers();
};