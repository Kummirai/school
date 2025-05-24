document.addEventListener("DOMContentLoaded", function () {
  // DOM Elements
  const inputField = document.getElementById("expression-input");
  const calculateBtn = document.getElementById("calculate-btn");
  const solutionContainer = document.getElementById("solution-container");
  const solutionSteps = document.getElementById("solution-steps");
  const plotBtn = document.getElementById("plot-btn");
  const clearGraphBtn = document.getElementById("clear-graph-btn");
  const saveEquationBtn = document.getElementById("save-equation-btn");
  const savedEquationsList = document.getElementById("saved-equations-list");
  const graphContainer = document.getElementById("graph-container");

  // Initialize Plotly graph
  let plotData = [];
  Plotly.newPlot(graphContainer, [], {
    title: "Equation Graph",
    xaxis: { title: "x" },
    yaxis: { title: "y" },
  });

  // Load saved equations if user is logged in
  if (savedEquationsList) {
    loadSavedEquations();
  }

  // Keypad buttons
  document.querySelectorAll(".keypad-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      insertAtCursor(this.getAttribute("data-value"));
    });
  });

  // Example buttons
  document.querySelectorAll(".example-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      inputField.value = this.getAttribute("data-expr");
      inputField.focus();
    });
  });

  // Calculator functions
  calculateBtn.addEventListener("click", solveAlgebra);
  inputField.addEventListener("keypress", function (e) {
    if (e.key === "Enter") solveAlgebra();
  });

  // Graphing functions
  plotBtn.addEventListener("click", plotEquation);
  clearGraphBtn.addEventListener("click", clearGraph);

  // Save equation handler
  if (saveEquationBtn) {
    saveEquationBtn.addEventListener("click", saveEquation);
  }

  // Helper function to insert text at cursor position
  function insertAtCursor(value) {
    const startPos = inputField.selectionStart;
    const endPos = inputField.selectionEnd;
    const currentValue = inputField.value;

    inputField.value =
      currentValue.substring(0, startPos) +
      value +
      currentValue.substring(endPos);

    // Move cursor after inserted value
    const newPos = startPos + value.length;
    inputField.selectionStart = newPos;
    inputField.selectionEnd = newPos;
    inputField.focus();
  }

  // Main algebra solver function using math.js
  async function solveAlgebra() {
    const expression = inputField.value.trim();

    if (!expression) {
      showError("Please enter an algebraic expression");
      return;
    }

    try {
      // Validate input
      if (!isValidExpression(expression)) {
        throw new Error("Invalid algebraic expression");
      }

      // Parse and solve the equation
      const solution = await solveWithMathJS(expression);

      // Display solution
      displaySolution(solution);

      // Auto-plot if it's a solvable equation
      if (expression.includes("=") && expression.includes("x")) {
        plotEquation();
      }
    } catch (error) {
      showError(error.message || "Could not solve the equation");
      console.error("Solving error:", error);
    }
  }

  // Enhanced math.js solver with steps
  async function solveWithMathJS(expr) {
    try {
      const steps = [];
      let currentExpr = expr;

      // Step 1: Original equation
      steps.push({
        description: "Original equation",
        equation: currentExpr,
      });

      // Parse the expression
      const parsed = math.parse(currentExpr);

      // If it's an equation (contains =)
      if (expr.includes("=")) {
        const parts = expr.split("=");
        const lhs = math.parse(parts[0]);
        const rhs = math.parse(parts[1]);

        // Step 2: Rewrite as f(x) = 0
        const rewritten = math.simplify(math.subtract(lhs, rhs));
        currentExpr = `${rewritten.toString()} = 0`;
        steps.push({
          description: "Rewrite as f(x) = 0",
          equation: currentExpr,
        });

        // Solve for x
        const solutions = math.solve(rewritten, "x");

        if (solutions.length === 0) {
          throw new Error("No solution found");
        }

        // Format solutions
        const solutionText = solutions
          .map((sol) => {
            if (typeof sol === "object" && sol.isComplex) {
              return `${math.round(sol.re, 3)} + ${math.round(sol.im, 3)}i`;
            }
            return math.round(sol, 3);
          })
          .join(", ");

        return {
          input: expr,
          steps: steps,
          solution: `x = ${solutionText}`,
        };
      }
      // If it's just an expression to simplify
      else {
        const simplified = math.simplify(parsed);
        steps.push({
          description: "Simplified expression",
          equation: simplified.toString(),
        });

        return {
          input: expr,
          steps: steps,
          solution: simplified.toString(),
        };
      }
    } catch (error) {
      throw new Error(`Math processing error: ${error.message}`);
    }
  }

  // Input validation
  function isValidExpression(expr) {
    // Basic checks
    if (expr.length > 100) return false;
    if (/[^xyd0-9+\-*\/^=()√|!.\s]/.test(expr)) return false;

    // More advanced checks could be added here
    return true;
  }

  // Display solution steps
  function displaySolution(solution) {
    solutionSteps.innerHTML = "";

    solution.steps.forEach((step) => {
      const stepEl = document.createElement("div");
      stepEl.className = "step";
      stepEl.innerHTML = `
                <p class="mb-1 text-muted">${step.description}</p>
                <p class="mb-0 fw-bold">${step.equation}</p>
            `;
      solutionSteps.appendChild(stepEl);
    });

    // Final solution
    const solutionEl = document.createElement("div");
    solutionEl.className = "step pt-3 mt-3 border-top";
    solutionEl.innerHTML = `
            <p class="mb-1 text-success">Solution:</p>
            <p class="mb-0 fw-bold fs-5">${solution.solution}</p>
        `;
    solutionSteps.appendChild(solutionEl);

    solutionContainer.classList.remove("d-none");
  }

  // Plot equation using Plotly
  function plotEquation() {
    const expr = inputField.value.trim();
    if (!expr) return;

    try {
      // Extract both sides if it's an equation
      let fnExpr = expr;
      if (expr.includes("=")) {
        const parts = expr.split("=");
        fnExpr = `(${parts[0]})-(${parts[1]})`;
      }

      // Generate x values
      const xValues = [];
      for (let x = -10; x <= 10; x += 0.1) {
        xValues.push(x);
      }

      // Evaluate y values
      const yValues = xValues.map((x) => {
        try {
          const scope = { x: x };
          return math.evaluate(fnExpr, scope);
        } catch {
          return null;
        }
      });

      // Create plot data
      const trace = {
        x: xValues,
        y: yValues,
        type: "scatter",
        mode: "lines",
        name: expr,
        line: { color: "#dc3545", width: 2 },
      };

      // Add to existing plot data
      plotData.push(trace);
      Plotly.newPlot(graphContainer, plotData, {
        title: "Equation Graph",
        xaxis: { title: "x" },
        yaxis: { title: "y" },
      });
    } catch (error) {
      showError("Could not plot the equation");
      console.error("Plotting error:", error);
    }
  }

  function clearGraph() {
    plotData = [];
    Plotly.newPlot(graphContainer, [], {
      title: "Equation Graph",
      xaxis: { title: "x" },
      yaxis: { title: "y" },
    });
  }

  // Save equation to user's history
  async function saveEquation() {
    const expr = inputField.value.trim();
    if (!expr) return;

    try {
      const response = await fetch("/api/save-equation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ equation: expr }),
      });

      if (!response.ok) throw new Error("Failed to save");

      const result = await response.json();
      if (result.success) {
        showToast("Equation saved successfully");
        loadSavedEquations();
      }
    } catch (error) {
      showError("Failed to save equation");
      console.error("Save error:", error);
    }
  }

  // Load user's saved equations
  async function loadSavedEquations() {
    try {
      const response = await fetch("/api/get-saved-equations");
      if (!response.ok) throw new Error("Failed to load");

      const equations = await response.json();
      renderSavedEquations(equations);
    } catch (error) {
      savedEquationsList.innerHTML = `
                <div class="alert alert-danger">
                    Failed to load saved equations
                </div>
            `;
      console.error("Load error:", error);
    }
  }

  function renderSavedEquations(equations) {
    if (equations.length === 0) {
      savedEquationsList.innerHTML = `
                <div class="text-center py-3 text-muted">
                    No saved equations yet
                </div>
            `;
      return;
    }

    savedEquationsList.innerHTML = equations
      .map(
        (eq) => `
            <div class="list-group-item saved-equation d-flex justify-content-between align-items-center">
                <span>${eq.equation}</span>
                <div>
                    <button class="btn btn-sm btn-outline-primary load-equation-btn me-1" 
                            data-equation="${eq.equation}">
                        <i class="bi bi-arrow-repeat"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-equation-btn" 
                            data-id="${eq.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `
      )
      .join("");

    // Add event listeners to new buttons
    document.querySelectorAll(".load-equation-btn").forEach((btn) => {
      btn.addEventListener("click", function () {
        inputField.value = this.getAttribute("data-equation");
        inputField.focus();
      });
    });

    document.querySelectorAll(".delete-equation-btn").forEach((btn) => {
      btn.addEventListener("click", async function () {
        if (confirm("Delete this equation?")) {
          await deleteEquation(this.getAttribute("data-id"));
          loadSavedEquations();
        }
      });
    });
  }

  async function deleteEquation(id) {
    try {
      const response = await fetch(`/api/delete-equation/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Failed to delete");
      showToast("Equation deleted");
    } catch (error) {
      showError("Failed to delete equation");
      console.error("Delete error:", error);
    }
  }

  function showError(message) {
    solutionSteps.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                ${message}
            </div>
        `;
    solutionContainer.classList.remove("d-none");
  }

  function showToast(message) {
    // Implement toast notification
    const toast = document.createElement("div");
    toast.className = "position-fixed bottom-0 end-0 p-3";
    toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header bg-success text-white">
                    <strong class="me-auto">Success</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }
});
