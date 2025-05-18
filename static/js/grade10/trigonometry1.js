// validationManager.js
const ValidationManager = {
  /**
   * Validate and record quiz results to database and leaderboard
   * @param {string} userId - Current user ID
   * @param {object} results - Quiz results object
   * @param {string} subject - Subject area
   * @param {string} topic - Specific topic
   * @returns {Promise<object>} - Response from server
   */
  recordResults: async function (
    userId,
    results,
    subject = "Mathematics",
    topic = "Trigonometry"
  ) {
    if (!userId || !results) {
      throw new Error("Missing required parameters");
    }

    // Validate results structure
    if (
      !results.hasOwnProperty("correct") ||
      !results.hasOwnProperty("total") ||
      !results.hasOwnProperty("details")
    ) {
      throw new Error("Invalid results format");
    }

    // Prepare data payload
    const payload = {
      user_id: userId,
      subject: subject,
      topic: topic,
      score: results.correct,
      total_questions: results.total,
      percentage: Math.round((results.correct / results.total) * 100),
      details: results.details,
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch("/api/record-results", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("authToken")}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Update leaderboard if successful
      if (data.success) {
        await this.updateLeaderboard(userId, payload);
      }

      return data;
    } catch (error) {
      console.error("Recording failed:", error);
      // Fallback to local storage if server fails
      this.cacheResultsLocally(payload);
      throw error;
    }
  },

  /**
   * Update leaderboard with new results
   * @param {string} userId
   * @param {object} results
   */
  updateLeaderboard: async function (userId, results) {
    try {
      const response = await fetch("/api/update-leaderboard", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("authToken")}`,
        },
        body: JSON.stringify({
          user_id: userId,
          subject: results.subject,
          topic: results.topic,
          score: results.score,
          percentage: results.percentage,
          timestamp: results.timestamp,
        }),
      });

      if (!response.ok) {
        throw new Error("Leaderboard update failed");
      }

      return await response.json();
    } catch (error) {
      console.error("Leaderboard update error:", error);
      this.cacheResultsLocally({
        ...results,
        type: "leaderboard",
      });
    }
  },

  /**
   * Cache results in localStorage when server unavailable
   * @param {object} data
   */
  cacheResultsLocally: function (data) {
    try {
      const cached = JSON.parse(localStorage.getItem("pendingResults") || "[]");
      cached.push(data);
      localStorage.setItem("pendingResults", JSON.stringify(cached));

      // Set flag to retry later
      if (!localStorage.getItem("retryResults")) {
        localStorage.setItem("retryResults", "true");
        setTimeout(this.retryPendingResults, 30000); // Retry in 30 seconds
      }
    } catch (e) {
      console.error("Local storage caching failed");
    }
  },

  /**
   * Retry any pending results
   */
  retryPendingResults: async function () {
    const pending = JSON.parse(localStorage.getItem("pendingResults") || "[]");
    if (pending.length === 0) {
      localStorage.removeItem("retryResults");
      return;
    }

    for (const result of pending) {
      try {
        if (result.type === "leaderboard") {
          await this.updateLeaderboard(result.user_id, result);
        } else {
          await this.recordResults(
            result.user_id,
            result,
            result.subject,
            result.topic
          );
        }
        // Remove successful submission
        const updated = pending.filter((r) => r.timestamp !== result.timestamp);
        localStorage.setItem("pendingResults", JSON.stringify(updated));
      } catch (e) {
        console.error("Retry failed for result:", result);
      }
    }

    // Check if more retries needed
    const remaining = JSON.parse(
      localStorage.getItem("pendingResults") || "[]"
    );
    if (remaining.length > 0) {
      setTimeout(this.retryPendingResults, 60000); // Retry again in 1 minute
    } else {
      localStorage.removeItem("retryResults");
    }
  },

  /**
   * Validate user input before submission
   * @param {object} answers
   * @returns {object} validated results
   */
  validateQuizAnswers: function (answers) {
    if (!answers || typeof answers !== "object") {
      throw new Error("Invalid answers format");
    }

    const results = {
      correct: 0,
      incorrect: 0,
      unanswered: 0,
      total: Object.keys(answers).length,
      details: [],
    };

    for (const [questionId, answer] of Object.entries(answers)) {
      const detail = {
        question: questionId,
        answered: answer !== null && answer !== "",
        correct: false,
      };

      if (!detail.answered) {
        results.unanswered++;
      } else {
        // Here you would validate against correct answers
        // This is a placeholder - implement your actual validation logic
        const isValid = this.validateAnswer(questionId, answer);
        if (isValid) {
          results.correct++;
          detail.correct = true;
        } else {
          results.incorrect++;
        }
      }

      results.details.push(detail);
    }

    return results;
  },

  /**
   * Validate individual answer (implementation specific)
   */
  validateAnswer: function (questionId, answer) {
    // Implement your specific answer validation logic
    // This would compare against known correct answers
    return true; // placeholder
  },
};

// Global access for backward compatibility
function recordQuizResults(userId, results, subject, topic) {
  return ValidationManager.recordResults(userId, results, subject, topic);
}

function validateQuizAnswers(answers) {
  return ValidationManager.validateQuizAnswers(answers);
}

// Initialize retry mechanism on load
document.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("retryResults") === "true") {
    setTimeout(
      ValidationManager.retryPendingResults.bind(ValidationManager),
      10000
    );
  }
});
