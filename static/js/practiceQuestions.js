
class PracticeQuestionsApp {
    constructor() {
        this.dom = {
            subjectSelect: document.getElementById("subjectSelect"),
            gradeList: document.getElementById("gradeList"),
            topicList: document.getElementById("topicList"),
            contentArea: document.getElementById("contentArea"),
            currentSubjectDisplay: document.getElementById("currentSubjectDisplay"),
        };

        this.currentSubject = null;
        this.currentGrade = null;
        this.currentTopic = null;
        this.allQuestions = []; // Store all fetched questions

        this.init();
    }

    async init() {
        this.setupEventListeners();
        // Initial load, maybe fetch all questions or a default set
        await this.fetchQuestions();
        this.populateSubjectDropdown();
        this.selectSubject(this.dom.subjectSelect.value); // Select initial subject
    }

    setupEventListeners() {
        this.dom.subjectSelect.addEventListener("change", (e) => this.selectSubject(e.target.value));
        this.dom.gradeList.addEventListener("click", (e) => {
            const gradeBtn = e.target.closest("[data-grade]");
            if (gradeBtn) this.selectGrade(gradeBtn.dataset.grade);
        });
        this.dom.topicList.addEventListener("click", (e) => {
            const topicBtn = e.target.closest("[data-topic]");
            if (topicBtn) this.selectTopic(topicBtn.dataset.topic);
        });
    }

    async fetchQuestions(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        try {
            const response = await fetch(`/practice/questions?${queryString}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            this.allQuestions = await response.json();
            console.log("Fetched questions:", this.allQuestions);
        } catch (error) {
            console.error("Error fetching questions:", error);
            this.showError("Failed to load practice questions.");
        }
    }

    populateSubjectDropdown() {
        // Assuming subjects are pre-defined in HTML or can be extracted from questions
        // For now, use existing HTML options
    }

    selectSubject(subject) {
        this.currentSubject = subject;
        this.currentGrade = null;
        this.currentTopic = null;
        this.updateSubjectDisplay(subject);
        this.renderGrades(subject);
        this.dom.topicList.innerHTML = '<p class="text-muted">Select a grade to see topics</p>';
        this.renderWelcomeScreen("subject", subject);
    }

    renderGrades(subject) {
        const grades = [...new Set(this.allQuestions
            .filter(q => q.subject === subject)
            .map(q => q.grade)
            .filter(grade => grade !== null && grade !== undefined) // Filter out null/undefined grades
        )].sort((a, b) => a - b); // Sort numerically

        this.dom.gradeList.innerHTML = grades.map(grade => `
            <button class="btn btn-outline-secondary w-100 mb-2 text-start" data-grade="${grade}">
                <i class="bi bi-mortarboard me-2"></i>
                Grade ${grade}
            </button>
        `).join('');
    }

    selectGrade(grade) {
        this.currentGrade = parseInt(grade); // Ensure grade is a number
        this.currentTopic = null;
        this.updateActiveGradeButton(grade);
        this.renderTopics(this.currentSubject, this.currentGrade);
        this.renderWelcomeScreen("grade", this.currentSubject, this.currentGrade);
    }

    renderTopics(subject, grade) {
        const topics = [...new Set(this.allQuestions
            .filter(q => q.subject === subject && q.grade === grade)
            .map(q => q.topic)
            .filter(topic => topic !== null && topic !== undefined) // Filter out null/undefined topics
        )].sort();

        this.dom.topicList.innerHTML = topics.map(topic => `
            <button class="btn btn-outline-secondary w-100 mb-2 text-start" data-topic="${topic}">
                <i class="bi bi-journal-bookmark me-2"></i>
                ${topic}
            </button>
        `).join('');
    }

    selectTopic(topic) {
        this.currentTopic = topic;
        this.renderQuestions(this.currentSubject, this.currentGrade, this.currentTopic);
    }

    renderQuestions(subject, grade, topic) {
        const filteredQuestions = this.allQuestions.filter(q =>
            q.subject === subject && q.grade === grade && q.topic === topic
        );

        if (filteredQuestions.length === 0) {
            this.dom.contentArea.innerHTML = '<p class="text-muted text-center py-5">No questions found for this selection.</p>';
            return;
        }

        let htmlContent = '';
        filteredQuestions.forEach((q, index) => {
            htmlContent += `
                <div class="card mb-4 shadow-sm">
                    <div class="card-header bg-dark text-white">
                        <h5>Question ${index + 1}: ${q.question_type || 'General'}</h5>
                    </div>
                    <div class="card-body">
                        <p>${q.question_text}</p>
                        ${q.image_url ? `<img src="${q.image_url}" class="img-fluid mb-3" alt="Question Image">` : ''}
                        ${q.options ? this.renderOptions(q.options, q.id) : ''}
                        <button class="btn btn-info btn-sm mt-3 check-answer-btn" data-question-id="${q.id}" data-correct-answer="${q.answer}">Show Answer</button>
                        <div class="answer-feedback mt-2" id="feedback-${q.id}" style="display:none;">
                            Correct Answer: <strong>${q.answer}</strong>
                        </div>
                    </div>
                </div>
            `;
        });
        this.dom.contentArea.innerHTML = htmlContent;
        this.attachAnswerCheckListeners();
    }

    renderOptions(options, questionId) {
        if (!options || options.length === 0) return '';
        let optionsHtml = '<ul class="list-group">';
        options.forEach((option, index) => {
            optionsHtml += `<li class="list-group-item quiz-option" data-question-id="${questionId}" data-option="${option}">${option}</li>`;
        });
        optionsHtml += '</ul>';
        return optionsHtml;
    }

    attachAnswerCheckListeners() {
        document.querySelectorAll('.check-answer-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const questionId = e.target.dataset.questionId;
                const feedbackDiv = document.getElementById(`feedback-${questionId}`);
                if (feedbackDiv) {
                    feedbackDiv.style.display = 'block';
                }
            });
        });
    }

    updateSubjectDisplay(subjectName) {
        if (!this.dom.currentSubjectDisplay) return;
        this.dom.currentSubjectDisplay.innerHTML = `<i class="bi bi-book me-2"></i><span class="fw-bold">${subjectName}</span>`;
    }

    updateActiveGradeButton(grade) {
        document.querySelectorAll("#gradeList button").forEach((btn) => {
            btn.classList.toggle("active", parseInt(btn.dataset.grade) === grade);
        });
    }

    renderWelcomeScreen(type, subjectName, grade) {
        const templates = {
            subject: () => ({
                icon: "bi-book",
                color: "text-danger",
                title: subjectName,
                message: "Select a grade and topic to begin learning",
            }),
            grade: () => ({
                icon: "bi-mortarboard",
                color: "text-primary",
                title: `${subjectName} - Grade ${grade}`,
                message: "Select a topic to begin learning",
            }),
            default: () => ({
                icon: "bi-book",
                color: "text-secondary",
                title: "Welcome to Practice Questions",
                message: "Select a subject, grade, and topic to begin practicing",
            }),
        };

        const { icon, color, title, message } = templates[type]?.() || templates.default();

        this.dom.contentArea.innerHTML = `
            <div class="text-center py-5">
                <i class="bi ${icon} ${color}" style="font-size: 3rem;"></i>
                <h2 class="mt-3">${title}</h2>
                <p class="lead">${message}</p>
            </div>
        `;
    }

    showError(message) {
        this.dom.contentArea.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                ${message}
            </div>
        `;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new PracticeQuestionsApp();
});
