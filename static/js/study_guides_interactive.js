// study_guides_interactive.js
document.addEventListener('DOMContentLoaded', function() {
    initializeInteractiveElements();
});

function initializeInteractiveElements() {
    // Quiz answer checking
    function checkAnswer(element, result) {
        element.classList.add(result === 'correct' ? 'correct' : 'incorrect');
    }

    // Fraction operations
    function updateFraction() {
        const slider = document.getElementById('fractionSlider');
        const valueDisplay = document.getElementById('fractionValue');
        if (slider && valueDisplay) {
            const value = slider.value;
            valueDisplay.textContent = '1/' + value;
            
            const circles = document.querySelectorAll('.fraction-circle');
            circles.forEach(function(circle) {
                const filled = circle.querySelector('div');
                if (filled) filled.style.height = (100/value) + '%';
            });
        }
    }

    function greatestCommonDivisor(a, b) {
        return b ? greatestCommonDivisor(b, a % b) : a;
    }

    function simplifyFraction() {
        const numInput = document.getElementById('simplifyNum');
        const denInput = document.getElementById('simplifyDen');
        const result = document.getElementById('simplifiedResult');
        
        if (numInput && denInput && result) {
            const num = parseInt(numInput.value) || 0;
            const den = parseInt(denInput.value) || 1;
            const gcd = greatestCommonDivisor(num, den);
            
            result.textContent = gcd === 1 ? 
                num + '/' + den + ' is already in simplest form' : 
                'Simplified: ' + (num/gcd) + '/' + (den/gcd);
        }
    }

    function findEquivalents() {
        const numInput = document.getElementById('numerator');
        const denInput = document.getElementById('denominator');
        const container = document.getElementById('equivalentFractions');
        
        if (numInput && denInput && container) {
            const num = parseInt(numInput.value) || 0;
            const den = parseInt(denInput.value) || 1;
            container.innerHTML = '';
            
            for (let i = 2; i <= 5; i++) {
                const equivNum = num * i;
                const equivDen = den * i;
                const fraction = document.createElement('span');
                fraction.className = 'badge bg-secondary me-2 mb-2';
                fraction.textContent = equivNum + '/' + equivDen;
                container.appendChild(fraction);
            }
        }
    }

    function calculateFraction(operation) {
        const num1Input = document.getElementById(operation + 'Num1');
        const den1Input = document.getElementById(operation + 'Den1');
        const num2Input = document.getElementById(operation + 'Num2');
        const den2Input = document.getElementById(operation + 'Den2');
        const resultElement = document.getElementById(operation + 'FractionResult');
        
        if (num1Input && den1Input && num2Input && den2Input && resultElement) {
            const num1 = parseInt(num1Input.value) || 0;
            const den1 = parseInt(den1Input.value) || 1;
            const num2 = parseInt(num2Input.value) || 0;
            const den2 = parseInt(den2Input.value) || 1;
            
            if (operation === 'add') {
                const commonDen = den1 * den2;
                const newNum = num1 * den2 + num2 * den1;
                const gcd = greatestCommonDivisor(newNum, commonDen);
                resultElement.textContent = 'Result: ' + (newNum/gcd) + '/' + (commonDen/gcd);
            } else {
                const resultNum = num1 * num2;
                const resultDen = den1 * den2;
                const gcd = greatestCommonDivisor(resultNum, resultDen);
                resultElement.textContent = 'Result: ' + (resultNum/gcd) + '/' + (resultDen/gcd);
            }
        }
    }

    // Make functions available globally
    window.checkAnswer = checkAnswer;
    window.updateFraction = updateFraction;
    window.simplifyFraction = simplifyFraction;
    window.findEquivalents = findEquivalents;
    window.calculateFraction = calculateFraction;
}