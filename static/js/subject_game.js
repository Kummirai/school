function initializeSubjectGame(questions) {
    const gameConfig = {
        grade: parseInt(new URLSearchParams(window.location.search).get('grade')) || 7,
        players: parseInt(new URLSearchParams(window.location.search).get('players')) || 1,
        playerNames: [],
        currentPlayer: 0,
    };

    for (let i = 0; i < gameConfig.players; i++) {
        gameConfig.playerNames.push(new URLSearchParams(window.location.search).get(`player${i+1}`) || `Player ${i+1}`);
    }

    let currentQuestionIndex = 0;
    let playerScores = Array(gameConfig.players).fill(0);
    let currentQuestion = {};

    const questionTextEl = document.getElementById('question-text');
    const optionsContainerEl = document.getElementById('options-container');
    const fillBlankContainerEl = document.getElementById('fill-blank-container');
    const fillBlankTextEl = document.getElementById('fill-blank-text');
    const checkBlankBtnEl = document.getElementById('check-blank-btn');
    const feedbackEl = document.getElementById('feedback');
    const scoreEl = document.getElementById('score');
    const hintBtn = document.getElementById('hint-btn');
    const nextBtn = document.getElementById('next-btn');

    function startGame() {
        currentQuestionIndex = 0;
        playerScores = Array(gameConfig.players).fill(0);
        scoreEl.textContent = 0;
        shuffleQuestions();
        displayQuestion();
        if (window.resetCountdown) {
            window.resetCountdown();
        }
    }

    function shuffleQuestions() {
        for (let i = questions.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [questions[i], questions[j]] = [questions[j], questions[i]];
        }
    }

    function displayQuestion() {
        if (currentQuestionIndex >= questions.length) {
            if(window.endGame) window.endGame("You've answered all questions!");
            return;
        }
        currentQuestion = questions[currentQuestionIndex];
        questionTextEl.textContent = currentQuestion.question;
        
        if (optionsContainerEl) optionsContainerEl.style.display = 'none';
        if (fillBlankContainerEl) fillBlankContainerEl.style.display = 'none';
        if (optionsContainerEl) optionsContainerEl.innerHTML = '';
        if (fillBlankTextEl) fillBlankTextEl.innerHTML = '';

        if (currentQuestion.type === 'mcq') {
            optionsContainerEl.style.display = 'grid';
            currentQuestion.options.forEach(option => {
                const button = document.createElement('button');
                button.textContent = option;
                button.classList.add('btn', 'btn-outline-primary', 'option-btn');
                button.onclick = () => checkAnswer(option);
                optionsContainerEl.appendChild(button);
            });
        } else if (currentQuestion.type === 'fillblank') {
            fillBlankContainerEl.style.display = 'block';
            if (currentQuestion.textBefore) {
                fillBlankTextEl.append(document.createTextNode(currentQuestion.textBefore + ' '));
            }
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'blank-input form-control d-inline-block';
            input.style.width = '150px';
            fillBlankTextEl.appendChild(input);
            if (currentQuestion.textAfter) {
                fillBlankTextEl.append(document.createTextNode(' ' + currentQuestion.textAfter));
            }
            checkBlankBtnEl.onclick = () => checkFillBlankAnswer(input);
        }

        if(nextBtn) nextBtn.disabled = true;
        if(hintBtn) hintBtn.disabled = false;
        if(feedbackEl) feedbackEl.textContent = '';
    }

    function checkAnswer(selectedOption) {
        document.querySelectorAll('.option-btn').forEach(btn => btn.disabled = true);
        if (selectedOption === currentQuestion.options[currentQuestion.answer]) {
            playerScores[gameConfig.currentPlayer] += 10;
            scoreEl.textContent = playerScores[gameConfig.currentPlayer];
            showFeedback('Correct!', true);
            if (window.resetCountdown) {
                window.resetCountdown();
            }
            setTimeout(() => {
                currentQuestionIndex++;
                displayQuestion();
            }, 1000);
        } else {
            showFeedback('Incorrect!', false);
            if(window.endGame) window.endGame("Wrong answer!");
        }
    }

    function checkFillBlankAnswer(inputElement) {
        const userAnswer = inputElement.value.trim().toLowerCase();
        const correctAnswer = currentQuestion.blank.toLowerCase();
        if (userAnswer === correctAnswer) {
            playerScores[gameConfig.currentPlayer] += 10;
            scoreEl.textContent = playerScores[gameConfig.currentPlayer];
            showFeedback('Correct!', true);
            if (window.resetCountdown) {
                window.resetCountdown();
            }
            setTimeout(() => {
                currentQuestionIndex++;
                displayQuestion();
            }, 1000);
        } else {
            showFeedback(`Incorrect. The correct answer is: ${currentQuestion.blank}`, false);
            if(window.endGame) window.endGame("Wrong answer!");
        }
    }

    function showFeedback(message, isCorrect) {
        feedbackEl.textContent = message;
        feedbackEl.className = isCorrect ? 'feedback correct mt-3' : 'feedback incorrect mt-3';
    }

    if(hintBtn) {
        hintBtn.addEventListener('click', () => {
            showFeedback(`Hint: ${currentQuestion.hint}`, false);
            hintBtn.disabled = true;
        });
    }

    if(nextBtn) {
        nextBtn.addEventListener('click', () => {
            currentQuestionIndex++;
            displayQuestion();
        });
    }

    window.onCountdownEnd = function(reason) {
        const finalScore = playerScores.reduce((a, b) => a + b, 0);
        const finalScoreEl = document.getElementById('final-score');
        const gameAreaContainer = document.getElementById('game-area-container');
        const gameOverScreen = document.getElementById('game-over-screen');

        if(finalScoreEl) finalScoreEl.textContent = finalScore;
        if(gameAreaContainer) gameAreaContainer.style.display = 'none';
        if(gameOverScreen) gameOverScreen.style.display = 'block';
    }

    startGame();
}
