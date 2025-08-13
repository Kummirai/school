// snake_and_ladder_game.js

const canvas = document.getElementById('gameBoard');
const ctx = canvas.getContext('2d');
const boardSize = 10; // 10x10 board
const cellSize = canvas.width / boardSize;

let players = [];
let currentPlayerIndex = 0;
let currentQuestion = null;
let timer = 30;
let timerInterval = null;

// Snakes and Ladders (example, will be more comprehensive later)
const snakes = {
    16: 6,
    47: 26,
    49: 11,
    56: 53,
    62: 19,
    64: 60,
    87: 24,
    93: 73,
    95: 75,
    98: 78
};

const ladders = {
    1: 38,
    4: 14,
    9: 31,
    21: 42,
    28: 84,
    36: 44,
    51: 67,
    71: 91,
    80: 100
};

// Player colors
const playerColors = [
    'red', 'blue', 'green', 'purple', 'orange', 'brown', 'pink', 'teal'
];

// Function to draw the board
function drawBoard() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let row = 0; row < boardSize; row++) {
        for (let col = 0; col < boardSize; col++) {
            const x = col * cellSize;
            const y = row * cellSize;
            ctx.strokeRect(x, y, cellSize, cellSize);

            // Number the cells
            let cellNumber;
            if (row % 2 === 0) { // Even rows (0, 2, 4...) go left to right
                cellNumber = (boardSize - 1 - row) * boardSize + col + 1;
            } else { // Odd rows (1, 3, 5...) go right to left
                cellNumber = (boardSize - 1 - row) * boardSize + (boardSize - 1 - col) + 1;
            }
            ctx.font = '12px Arial';
            ctx.fillText(cellNumber, x + 5, y + 15);
        }
    }
}

// Function to get cell coordinates from position (1-100)
function getCellCoordinates(position) {
    const row = Math.floor((position - 1) / boardSize);
    const col = (row % 2 === 0) ? (position - 1) % boardSize : boardSize - 1 - ((position - 1) % boardSize);
    const x = col * cellSize + cellSize / 2;
    const y = (boardSize - 1 - row) * cellSize + cellSize / 2;
    return { x, y };
}

// Function to draw players
function drawPlayers() {
    players.forEach((player, index) => {
        const { x, y } = getCellCoordinates(player.position);
        ctx.beginPath();
        ctx.arc(x + (index * 5), y + (index * 5), cellSize / 4, 0, Math.PI * 2);
        ctx.fillStyle = player.color;
        ctx.fill();
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1;
        ctx.stroke();
    });
}

// Function to update player info display
function updatePlayerInfo() {
    const playerListDiv = document.getElementById('player-list');
    playerListDiv.innerHTML = '';
    players.forEach((player, index) => {
        const playerDiv = document.createElement('div');
        playerDiv.className = 'player-item';
        if (index === currentPlayerIndex) {
            playerDiv.classList.add('current-player');
        }
        playerDiv.innerHTML = `
            <div class="player-color-box" style="background-color: ${player.color};"></div>
            <span>${player.name}: Pos ${player.position}</span>
        `;
        playerListDiv.appendChild(playerDiv);
    });
}

// Function to fetch a question from the API
async function fetchQuestion(grade) {
    try {
        const response = await fetch(`/gamehub/api/get_question?grade=${grade}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        // Map the fetched data to the expected format
        return {
            question: data.question_text,
            options: [data.option_a, data.option_b, data.option_c, data.option_d],
            answer: data.correct_option
        };
    } catch (error) {
        console.error("Error fetching question:", error);
        // Fallback or error handling for the game
        alert("Failed to load question. Please try again.");
        return null; // Or a default question to prevent game from breaking
    }
}

// Function to display question
async function displayQuestion() {
    currentQuestion = await fetchQuestion(players[currentPlayerIndex].grade);

    if (!currentQuestion) {
        document.getElementById('question-text').textContent = "Failed to load question. Please try another grade.";
        document.getElementById('options-container').innerHTML = ''; // Clear options
        document.getElementById('next-question-btn').style.display = 'block'; // Allow to proceed
        stopTimer(); // Stop any running timer
        return;
    }

    document.getElementById('question-text').textContent = currentQuestion.question;
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';
    
    // Filter out any null or empty options before creating buttons
    const validOptions = currentQuestion.options.filter(option => option !== null && option !== undefined && option.trim() !== '');

    if (validOptions.length === 0) {
        document.getElementById('question-text').textContent = "No valid options for this question. Please try another grade.";
        document.getElementById('next-question-btn').style.display = 'block';
        stopTimer();
        return;
    }

    validOptions.forEach(option => {
        const button = document.createElement('button');
        button.className = 'option-btn';
        button.textContent = option;
        button.onclick = () => selectOption(option);
        optionsContainer.appendChild(button);
    });
    document.getElementById('next-question-btn').style.display = 'none';
    document.getElementById('feedback').textContent = '';
    startTimer();
}

// Function to handle option selection
function selectOption(selectedAnswer) {
    stopTimer();
    const isCorrect = (selectedAnswer === currentQuestion.answer);
    const feedbackElement = document.getElementById('feedback');
    const options = document.querySelectorAll('.option-btn');

    options.forEach(button => {
        button.disabled = true; // Disable all buttons after selection
        if (button.textContent === currentQuestion.answer) {
            button.classList.add('correct');
        } else if (button.textContent === selectedAnswer) {
            button.classList.add('incorrect');
        }
    });

    if (isCorrect) {
        feedbackElement.textContent = 'Correct!';
        feedbackElement.className = 'alert alert-success';
        movePlayer(players[currentPlayerIndex], 1); // Move forward 1 step
    } else {
        feedbackElement.textContent = 'Incorrect!';
        feedbackElement.className = 'alert alert-danger';
        movePlayer(players[currentPlayerIndex], -1); // Move backward 1 step
    }
    document.getElementById('next-question-btn').style.display = 'block';
}

// Function to start the timer
function startTimer() {
    timer = 30;
    document.getElementById('timer').textContent = timer;
    timerInterval = setInterval(() => {
        timer--;
        document.getElementById('timer').textContent = timer;
        if (timer <= 0) {
            stopTimer();
            selectOption(null); // Treat as incorrect if time runs out
        }
    }, 1000);
}

// Function to stop the timer
function stopTimer() {
    clearInterval(timerInterval);
}

// Function to move player
function movePlayer(player, steps) {
    player.position += steps;
    if (player.position < 1) player.position = 1; // Cannot go below 1
    if (player.position > 100) player.position = 100; // Cannot go beyond 100 (for now)

    // Check for snakes and ladders
    if (snakes[player.position]) {
        player.position = snakes[player.position];
        showFeedback(`${player.name} landed on a snake! Moving to ${player.position}`, false);
    } else if (ladders[player.position]) {
        player.position = ladders[player.position];
        showFeedback(`${player.name} found a ladder! Moving to ${player.position}`, true);
    }

    drawBoard();
    drawPlayers();
    updatePlayerInfo();
}

// Function to switch to next player
function nextPlayer() {
    currentPlayerIndex = (currentPlayerIndex + 1) % players.length;
    updatePlayerInfo();
    displayQuestion();
}

// Event listener for next question button
document.getElementById('next-question-btn').addEventListener('click', nextPlayer);

// Initialize game
document.addEventListener('DOMContentLoaded', () => {
    // Get game parameters from URL
    const urlParams = new URLSearchParams(window.location.search);
    const numPlayers = parseInt(urlParams.get('players')) || 1;
    // Grade will be selected via modal, not from URL

    // Initialize players without grade for now
    for (let i = 0; i < numPlayers; i++) {
        const playerName = urlParams.get(`player${i + 1}`) || `Player ${i + 1}`;
        players.push({
            id: i,
            name: playerName,
            position: 1,
            color: playerColors[i % playerColors.length],
            grade: null // Grade will be set after selection
        });
    }

    drawBoard();
    updatePlayerInfo();

    // Show grade selection modal
    const gradeSelectionModalElement = document.getElementById('gradeSelectionModal');
    console.log('Before Modal Init - gradeSelectionModalElement:', gradeSelectionModalElement); // New debug line
    const gradeSelectionModal = new bootstrap.Modal(gradeSelectionModalElement);
    gradeSelectionModal.show();

        const questionGradeSelect = document.getElementById('questionGradeSelect');
        const startGameWithGradeBtn = document.getElementById('startGameWithGradeBtn');

        questionGradeSelect.addEventListener('change', function() {
            if (this.value) {
                startGameWithGradeBtn.disabled = false;
            } else {
                startGameWithGradeBtn.disabled = true;
            }
        });

        startGameWithGradeBtn.addEventListener('click', function() {
            const selectedGrade = parseInt(questionGradeSelect.value);
            if (selectedGrade) {
                // Set the selected grade for all players
                players.forEach(player => {
                    player.grade = selectedGrade;
                });
                gradeSelectionModal.hide();
                displayQuestion(); // Start the first question with the selected grade
            } else {
                alert("Please select a grade to start the game.");
            }
        });
    } else {
        console.error("Grade selection modal element not found!");
    }
});
