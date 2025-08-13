document.addEventListener('DOMContentLoaded', function () {
    const subjectSelect = document.getElementById('subjectSelect');
    const gradeList = document.getElementById('gradeList');
    const topicList = document.getElementById('topicList');
    const contentArea = document.getElementById('contentArea');
    const currentSubjectDisplay = document.getElementById('currentSubjectDisplay');
    const gradesAccordionButton = document.querySelector('[data-bs-target="#collapseGrades"]');
    const topicsAccordionButton = document.querySelector('[data-bs-target="#collapseTopics"]');


    let selectedGrade = null;
    let selectedTopic = null;

    function fetchGrades() {
        const subject = subjectSelect.value;
        currentSubjectDisplay.innerHTML = `<i class="bi bi-book me-2"></i>${subject}`;
        gradeList.innerHTML = '<div class="list-group-item">Loading...</div>';
        topicList.innerHTML = '';
        contentArea.innerHTML = '<div class="text-center py-5"><p class="lead">Please select a grade and topic to see questions.</p></div>';
        
        // Collapse topics and clear it
        document.getElementById('collapseTopics').classList.remove('show');
        topicList.innerHTML = '';


        fetch(`/practice/grades?subject=${encodeURIComponent(subject)}`)
            .then(response => response.json())
            .then(grades => {
                gradeList.innerHTML = '';
                if (grades.length === 0) {
                    gradeList.innerHTML = '<div class="list-group-item">No grades found.</div>';
                } else {
                    grades.forEach(grade => {
                        const gradeItem = document.createElement('a');
                        gradeItem.href = '#';
                        gradeItem.className = 'list-group-item list-group-item-action';
                        gradeItem.textContent = `Grade ${grade}`;
                        gradeItem.dataset.grade = grade;
                        gradeList.appendChild(gradeItem);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching grades:', error);
                gradeList.innerHTML = '<div class="list-group-item">Error loading grades.</div>';
            });
    }

    function fetchTopics(grade) {
        const subject = subjectSelect.value;
        selectedGrade = grade;
        topicList.innerHTML = '<div class="list-group-item">Loading...</div>';
        contentArea.innerHTML = '<div class="text-center py-5"><p class="lead">Please select a topic to see questions.</p></div>';

        // Collapse topics accordion before fetching new topics
        const collapseTopics = document.getElementById('collapseTopics');
        
        fetch(`/practice/topics?subject=${encodeURIComponent(subject)}&grade=${encodeURIComponent(grade)}`)
            .then(response => response.json())
            .then(topics => {
                topicList.innerHTML = '';
                 if (topics.length === 0) {
                    topicList.innerHTML = '<div class="list-group-item">No topics found.</div>';
                } else {
                    topics.forEach(topic => {
                        const topicItem = document.createElement('a');
                        topicItem.href = '#';
                        topicItem.className = 'list-group-item list-group-item-action';
                        topicItem.textContent = topic;
                        topicItem.dataset.topic = topic;
                        topicList.appendChild(topicItem);
                    });
                    // Show the topics accordion
                    new bootstrap.Collapse(collapseTopics, { show: true });
                }
            })
            .catch(error => {
                console.error('Error fetching topics:', error);
                topicList.innerHTML = '<div class="list-group-item">Error loading topics.</div>';
            });
    }

    function fetchQuestions(topic) {
        const subject = subjectSelect.value;
        selectedTopic = topic;
        contentArea.innerHTML = '<div class="text-center py-5">Loading questions...</div>';

        fetch(`/practice/questions?subject=${encodeURIComponent(subject)}&grade=${encodeURIComponent(selectedGrade)}&topic=${encodeURIComponent(topic)}`)
            .then(response => {
                if (!response.ok) {
                    // Handle server errors (like 500)
                    return response.text().then(text => {
                        try {
                            const err = JSON.parse(text);
                            throw new Error(err.error || 'Server error');
                        } catch (e) {
                            // If the error response wasn't JSON
                            throw new Error(`Server returned non-JSON error response: ${text}`);
                        }
                    });
                }
                // Handle successful responses
                return response.text().then(text => {
                    try {
                        return JSON.parse(text);
                    } catch (e) {
                        console.error("Failed to parse JSON:", text);
                        throw new Error("Failed to parse server response.");
                    }
                });
            })
            .then(questions => {
                renderQuestions(questions);
            })
            .catch(error => {
                console.error('Error fetching questions:', error);
                contentArea.innerHTML = `<div class="text-center py-5 alert alert-danger">Error loading questions: ${error.message}</div>`;
            });
    }

    function renderQuestions(questions) {
        contentArea.innerHTML = '';
        if (questions.length === 0) {
            contentArea.innerHTML = '<div class="text-center py-5">No questions found for this topic.</div>';
            return;
        }

        questions.forEach((question, index) => {
            const questionCard = document.createElement('div');
            questionCard.className = 'card mb-3';
            
            let questionBodyContent = '';

            if (question.question_type === 'Numerical') {
                questionBodyContent = `
                    <p class="card-text">${question.question_text}</p>
                    <input type="number" class="form-control numeric-answer-input" placeholder="Enter your answer">
                `;
            } else {
                let optionsHtml = '';
                const options = question.options || {};
                Object.entries(options).forEach(([key, value]) => {
                    optionsHtml += `<div class="quiz-option p-2 my-1 border rounded" data-question-id="${question.id}" data-option-key="${key}">${key}) ${value}</div>`;
                });
                questionBodyContent = `
                    <p class="card-text">${question.question_text}</p>
                    <div class="options-container">${optionsHtml}</div>
                `;
            }

            questionCard.innerHTML = `
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>Question ${index + 1}</span>
                    <span class="badge bg-secondary">${question.difficulty || 'Medium'}</span>
                </div>
                <div class="card-body">
                    ${questionBodyContent}
                    <div class="feedback mt-2"></div>
                </div>
                <div class="card-footer text-end">
                    <button class="btn btn-primary btn-sm check-answer-btn">Check Answer</button>
                </div>
            `;
            contentArea.appendChild(questionCard);

            // Event listener for quiz options (for MCQ type)
            if (question.question_type !== 'Numerical') {
                const optionsContainer = questionCard.querySelector('.options-container');
                // Add a check for optionsContainer before adding event listener
                if (optionsContainer) {
                    optionsContainer.addEventListener('click', (e) => {
                        if (e.target.classList.contains('quiz-option')) {
                            Array.from(optionsContainer.children).forEach(child => child.classList.remove('bg-primary', 'text-white'));
                            e.target.classList.add('bg-primary', 'text-white');
                        }
                    });
                }
            }

            // Event listener for check answer button
            questionCard.querySelector('.check-answer-btn').addEventListener('click', () => {
                const feedbackDiv = questionCard.querySelector('.feedback');
                let userAnswer;

                if (question.question_type === 'Numerical') {
                    const inputField = questionCard.querySelector('.numeric-answer-input');
                    userAnswer = inputField.value;
                    if (userAnswer === '') {
                        feedbackDiv.innerHTML = '<div class="alert alert-warning">Please enter an answer.</div>';
                        return;
                    }
                    userAnswer = parseFloat(userAnswer);
                } else {
                    const selectedOption = questionCard.querySelector('.quiz-option.bg-primary');
                    if (!selectedOption) {
                        feedbackDiv.innerHTML = '<div class="alert alert-warning">Please select an answer.</div>';
                        return;
                    }
                    userAnswer = selectedOption.dataset.optionKey; // FIX: Get the key directly
                }
                
                // console.log("DEBUG: userAnswer:", userAnswer); // Remove debug logs
                // console.log("DEBUG: question.answer:", question.answer); // Remove debug logs
                // console.log("DEBUG: Comparison result:", userAnswer == question.answer); // Remove debug logs

                if (userAnswer == question.answer) {
                    feedbackDiv.innerHTML = '<div class="alert alert-success">Correct!</div>';
                    if (question.question_type !== 'Numerical') { // FIX: 'numeric' to 'Numerical'
                        const selectedOption = questionCard.querySelector('.quiz-option.bg-primary');
                        selectedOption.classList.remove('bg-primary');
                        selectedOption.classList.add('bg-success', 'text-white');
                    }
                } else {
                    feedbackDiv.innerHTML = `<div class="alert alert-danger">Incorrect. The correct answer is ${question.answer}.</div>`;
                    if (question.question_type !== 'Numerical') { // FIX: 'numeric' to 'Numerical'
                        const selectedOption = questionCard.querySelector('.quiz-option.bg-primary');
                        selectedOption.classList.remove('bg-primary');
                        selectedOption.classList.add('bg-danger', 'text-white');
                    }
                }
            });
        });
    }

    subjectSelect.addEventListener('change', fetchGrades);

    gradeList.addEventListener('click', function(e) {
        e.preventDefault();
        if (e.target.matches('.list-group-item-action')) {
            Array.from(gradeList.children).forEach(child => child.classList.remove('active'));
            e.target.classList.add('active');
            const grade = e.target.dataset.grade;
            fetchTopics(grade);
        }
    });

    topicList.addEventListener('click', function(e) {
        e.preventDefault();
        if (e.target.matches('.list-group-item-action')) {
            Array.from(topicList.children).forEach(child => child.classList.remove('active'));
            e.target.classList.add('active');
            const topic = e.target.dataset.topic;
            fetchQuestions(topic);
        }
    });

    // Initial load
    fetchGrades();
});