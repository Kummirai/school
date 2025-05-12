/**
 * STUDY GUIDE APPLICATION
 * A dynamic learning platform for grade-based educational content
 */

class StudyGuideApp {
    constructor() {
        // State management
        this.currentSubject = null;
        this.currentGrade = null;
        this.currentTopic = null;
        this.studyData = null;
        
        // DOM Elements
        this.dom = {
            gradeList: document.getElementById('gradeList'),
            topicList: document.getElementById('topicList'),
            contentArea: document.getElementById('contentArea'),
            subjectSelect: document.getElementById('subjectSelect'),
            currentSubjectDisplay: document.getElementById('currentSubjectDisplay')
        };
        
        // Configuration
        this.config = {
            subjects: {
                "Mathematics": { icon: "bi-calculator", color: "text-primary" },
                "Physical Sciences": { icon: "bi-atom", color: "text-danger" },
                "Life Sciences": { icon: "bi-biohazard", color: "text-success" }
            },
            defaultSubject: "Mathematics"
        };
        
        // Initialize app
        this.init();
    }
    
    async init() {
        try {
            await this.loadData();
            this.setupEventListeners();
            this.selectSubject(this.config.defaultSubject);
        } catch (error) {
            console.error("App initialization failed:", error);
            this.showError("Failed to initialize application");
        }
    }
    
    // DATA METHODS
    
    async loadData() {
        try {
            const response = await fetch('static/js/studyGuide.json');
            if (!response.ok) throw new Error("Network response was not ok");
            this.studyData = await response.json();
            this.populateSubjectDropdown();
        } catch (error) {
            console.error("Error loading study data:", error);
            throw error;
        }
    }
    
    populateSubjectDropdown() {
        if (!this.dom.subjectSelect || !this.studyData) return;
        
        this.dom.subjectSelect.innerHTML = Object.keys(this.studyData.subjects)
            .map(subject => `<option value="${subject}">${subject}</option>`)
            .join('');
    }
    
    // UI RENDER METHODS
    
    renderGrades(subjectName) {
        if (!this.dom.gradeList || !this.studyData?.subjects[subjectName]) return;
        
        const grades = Object.keys(this.studyData.subjects[subjectName]).sort();
        this.dom.gradeList.innerHTML = grades.map(grade => `
            <button class="btn btn-outline-secondary w-100 mb-2 text-start 
                ${this.currentGrade === grade ? 'active' : ''}"
                data-grade="${grade}">
                <i class="bi bi-mortarboard me-2"></i>
                Grade ${grade}
            </button>
        `).join('');
    }
    
    renderTopics(subjectName, grade) {
        if (!this.dom.topicList || !this.studyData?.subjects[subjectName]?.[grade]) return;
        
        const topics = this.studyData.subjects[subjectName][grade];
        const hasTopics = Object.keys(topics).length > 0;
        
        this.dom.topicList.innerHTML = hasTopics 
            ? Object.entries(topics).map(([name, topic]) => `
                <button class="btn btn-outline-secondary w-100 mb-2 text-start"
                    data-topic="${name}">
                    <i class="bi bi-journal-bookmark me-2"></i>
                    <strong>${topic.title}</strong><br>
                    <small class="text-muted">${topic.description}</small>
                </button>
            `).join('')
            : '<p class="text-muted">No topics available for this grade</p>';
    }
    
    renderTopicContent(topic) {
        this.dom.contentArea.innerHTML = `
            <div class="card mb-4 shadow-sm">
                <div class="card-header bg-dark text-white">
                    <h3><i class="bi bi-journal-text me-2"></i>${topic.title}</h3>
                    <p class="mb-0">${topic.description}</p>
                </div>
                <div class="card-body">
                    ${topic.content}
                </div>
            </div>
        `;
        this.initInteractiveElements();
    }
    
    renderWelcomeScreen(type, subjectName, grade) {
        const templates = {
            subject: () => ({
                icon: this.config.subjects[subjectName]?.icon || 'bi-book',
                color: this.config.subjects[subjectName]?.color || 'text-secondary',
                title: subjectName,
                message: "Select a grade and topic to begin learning"
            }),
            grade: () => ({
                icon: 'bi-mortarboard',
                color: 'text-primary',
                title: `${subjectName} - Grade ${grade}`,
                message: "Select a topic to begin learning"
            }),
            default: () => ({
                icon: 'bi-book',
                color: 'text-secondary',
                title: "Welcome to Study Guides",
                message: "Select a subject, grade, and topic to begin learning"
            })
        };
        
        const {icon, color, title, message} = templates[type]?.() || templates.default();
        
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
    
    // STATE MANAGEMENT METHODS
    
    selectSubject(subjectName) {
        if (!this.studyData?.subjects[subjectName]) return;
        
        this.currentSubject = subjectName;
        this.currentGrade = null;
        this.currentTopic = null;
        
        // Update UI
        this.updateSubjectDisplay(subjectName);
        this.renderGrades(subjectName);
        this.dom.topicList.innerHTML = '<p class="text-muted">Select a grade to see topics</p>';
        this.renderWelcomeScreen('subject', subjectName);
        
        // Update dropdown if exists
        if (this.dom.subjectSelect) this.dom.subjectSelect.value = subjectName;
    }
    
    selectGrade(grade) {
        if (!this.currentSubject || !this.studyData?.subjects[this.currentSubject]?.[grade]) return;
        
        this.currentGrade = grade;
        this.currentTopic = null;
        
        // Update UI
        this.updateActiveGradeButton(grade);
        this.renderTopics(this.currentSubject, grade);
        this.renderWelcomeScreen('grade', this.currentSubject, grade);
    }
    
    selectTopic(topicName) {
        if (!this.currentSubject || !this.currentGrade) return;
        
        const topic = this.studyData.subjects[this.currentSubject][this.currentGrade][topicName];
        if (!topic) return;
        
        this.currentTopic = topicName;
        this.renderTopicContent(topic);
    }
    
    // HELPER METHODS
    
    updateSubjectDisplay(subjectName) {
        if (!this.dom.currentSubjectDisplay) return;
        
        const {icon, color} = this.config.subjects[subjectName] || { icon: 'bi-book', color: 'text-secondary' };
        this.dom.currentSubjectDisplay.innerHTML = `
            <i class="bi ${icon} ${color} me-2"></i>
            <span class="fw-bold">${subjectName}</span>
        `;
    }
    
    updateActiveGradeButton(grade) {
        document.querySelectorAll('#gradeList button').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.grade === grade);
        });
    }
    
    // EVENT HANDLERS
    
    setupEventListeners() {
        // Subject dropdown
        if (this.dom.subjectSelect) {
            this.dom.subjectSelect.addEventListener('change', (e) => {
                this.selectSubject(e.target.value);
            });
        }
        
        // Grade buttons (delegated)
        if (this.dom.gradeList) {
            this.dom.gradeList.addEventListener('click', (e) => {
                const gradeBtn = e.target.closest('[data-grade]');
                if (gradeBtn) this.selectGrade(gradeBtn.dataset.grade);
            });
        }
        
        // Topic buttons (delegated)
        if (this.dom.topicList) {
            this.dom.topicList.addEventListener('click', (e) => {
                const topicBtn = e.target.closest('[data-topic]');
                if (topicBtn) this.selectTopic(topicBtn.dataset.topic);
            });
        }
        
        // Navigation links (if present)
        document.querySelectorAll('[data-subject]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.selectSubject(link.dataset.subject);
                if (this.dom.subjectSelect) this.dom.subjectSelect.value = link.dataset.subject;
            });
        });
    }
    
    initInteractiveElements() {
        // Place value inputs
        document.querySelectorAll('.place-value').forEach(input => {
            input.addEventListener('input', () => {
                input.value = input.value.slice(0, 1);
            });
        });
        
        // Quiz options
        document.querySelectorAll('.quiz-option').forEach(option => {
            option.addEventListener('click', () => {
                const isCorrect = option.getAttribute('onclick').includes('correct');
                option.classList.add(isCorrect ? 'correct' : 'incorrect');
            });
        });
        
        // Calculator functions
        if (typeof calculate === 'function') {
            window.calculate = (operation) => {
                // Calculator implementation
            };
        }
        
        if (typeof updateNumber === 'function') {
            window.updateNumber = () => {
                // Number update implementation
            };
        }
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new StudyGuideApp();
});