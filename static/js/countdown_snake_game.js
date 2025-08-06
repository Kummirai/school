document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const scoreEl = document.getElementById('score');
    const questionTextEl = document.getElementById('question-text');
    const optionsContainerEl = document.getElementById('options-container');
    const feedbackEl = document.getElementById('feedback');
    const gameOverScreenEl = document.getElementById('game-over-screen');
    const finalScoreEl = document.getElementById('final-score');
    const playAgainBtn = document.getElementById('play-again-btn');
    const gameArea = document.getElementById('game-area-container');

    const gridSize = 20;
    let snake = [{ x: 10, y: 10 }];
    let food = {};
    let direction = 'right';
    let score = 0;
    let gameLoop;
    let currentQuestion = {};
    let questions = [];

    const questionsData = [
        { question: "What is 5 + 7?", options: ["10", "12", "15"], answer: "12" },
        { question: "What is the capital of Japan?", options: ["Beijing", "Seoul", "Tokyo"], answer: "Tokyo" },
        { question: "Which planet is known as the Red Planet?", options: ["Mars", "Venus", "Jupiter"], answer: "Mars" },
        { question: "What is the chemical symbol for water?", options: ["O2", "H2O", "CO2"], answer: "H2O" },
        { question: "How many continents are there?", options: ["5", "6", "7"], answer: "7" },
    ];

    function startGame() {
        snake = [{ x: 10, y: 10 }];
        direction = 'right';
        score = 0;
        scoreEl.textContent = score;
        gameOverScreenEl.style.display = 'none';
        gameArea.style.display = 'flex';
        feedbackEl.textContent = '';
        questions = [...questionsData];
        
        nextTurn();

        if (gameLoop) clearInterval(gameLoop);
        gameLoop = setInterval(mainLoop, 150);
    }

    function nextTurn() {
        if (questions.length === 0) {
            endGame("You answered all questions! You win!");
            return;
        }
        generateFood();
        displayQuestion();
    }

    function mainLoop() {
        updateSnakePosition();
        if (isGameOver()) {
            return;
        }
        draw();
    }

    function updateSnakePosition() {
        const head = { ...snake[0] };
        switch (direction) {
            case 'up': head.y--; break;
            case 'down': head.y++; break;
            case 'left': head.x--; break;
            case 'right': head.x++; break;
        }
        snake.unshift(head);

        if (head.x === food.x && head.y === food.y) {
            endGame("Time's up! The snake reached the food.");
        } else {
            snake.pop();
        }
    }

    function isGameOver() {
        const head = snake[0];
        if (head.x < 0 || head.x >= canvas.width / gridSize || head.y < 0 || head.y >= canvas.height / gridSize) {
            endGame("Game Over! You hit a wall.");
            return true;
        }
        for (let i = 1; i < snake.length; i++) {
            if (head.x === snake[i].x && head.y === snake[i].y) {
                endGame("Game Over! You ran into yourself.");
                return true;
            }
        }
        return false;
    }

    function draw() {
        ctx.fillStyle = '#2c3e50';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#2ecc71';
        snake.forEach(segment => {
            ctx.fillRect(segment.x * gridSize, segment.y * gridSize, gridSize - 1, gridSize - 1);
        });

        ctx.fillStyle = '#e74c3c';
        ctx.fillRect(food.x * gridSize, food.y * gridSize, gridSize - 1, gridSize - 1);
    }

    function generateFood() {
        food = {
            x: Math.floor(Math.random() * (canvas.width / gridSize)),
            y: Math.floor(Math.random() * (canvas.height / gridSize))
        };
    }

    function displayQuestion() {
        const questionIndex = Math.floor(Math.random() * questions.length);
        currentQuestion = questions.splice(questionIndex, 1)[0];

        questionTextEl.textContent = currentQuestion.question;
        optionsContainerEl.innerHTML = '';
        currentQuestion.options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option;
            button.classList.add('btn', 'btn-outline-primary', 'option-btn');
            button.onclick = () => checkAnswer(option);
            optionsContainerEl.appendChild(button);
        });
    }

    function checkAnswer(selectedOption) {
        if (selectedOption === currentQuestion.answer) {
            score++;
            scoreEl.textContent = score;
            feedbackEl.textContent = "Correct!";
            feedbackEl.className = 'correct mt-3';
            snake = [{ x: 10, y: 10 }];
            nextTurn();
        } else {
            feedbackEl.textContent = "Incorrect!";
            feedbackEl.className = 'incorrect mt-3';
            endGame("Wrong answer!");
        }
    }

    function endGame(reason) {
        clearInterval(gameLoop);
        gameArea.style.display = 'none';
        gameOverScreenEl.style.display = 'block';
        finalScoreEl.textContent = score;
        feedbackEl.textContent = reason;
        if(window.onCountdownEnd) {
            window.onCountdownEnd(reason);
        }
    }
    
    window.resetCountdown = startGame;
    
    playAgainBtn.addEventListener('click', startGame);

    document.addEventListener('keydown', e => {
        switch (e.key) {
            case 'ArrowUp': if (direction !== 'down') direction = 'up'; break;
            case 'ArrowDown': if (direction !== 'up') direction = 'down'; break;
            case 'ArrowLeft': if (direction !== 'right') direction = 'left'; break;
            case 'ArrowRight': if (direction !== 'left') direction = 'right'; break;
        }
    });

    startGame();
});