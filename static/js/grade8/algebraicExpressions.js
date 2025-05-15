  function checkBasicExpansion() {
    const answers = {
      q1: "2x+6",
      q2: "10y-20",
      q3: "-3a-21",
      q4: "x²+5x",
      q5: "6y²-2y",
      q6: "-4a+a²",
      q7: "6b+3c",
      q8: "8x²-12x",
      q9: "-10+6k",
      q10: "p²+pq",
    };
    checkAnswers(answers, "basic-feedback");
  }
  function checkIntermediateExpansion() {
    const answers = {
      q11: "7x+2",
      q12: "y-11",
      q13: "3a²-2a",
      q14: "5b-10c",
      q15: "3x²+4x-6",
      q16: "11-7k",
      q17: "5m²-mn",
      q18: "5p+7",
      q19: "q²-2qr",
      q20: "14x-6y",
    };
    checkAnswers(answers, "intermediate-feedback");
  }
  function checkAdvancedExpansion() {
    const answers = {
      q21: "x²+5x+6",
      q22: "y²-3y-4",
      q23: "6a²-a-2",
      q24: "6+b-b²",
      q25: "x²+10x+25",
      q26: "4k²-12k+9",
      q27: "m²-n²",
      q28: "6p²-pq-2q²",
      q29: "x³+x²-5x+3",
      q30: "6a³-a²-9a+4",
    };
    checkAnswers(answers, "advanced-feedback");
  }
  function checkFactorization() {
    const answers = {
      q31: "3(x+2)",
      q32: "4(y-2)",
      q33: "a(a+5)",
      q34: "3b(2-3b)",
      q35: "2x(x+2y)",
      q36: "3(4k+5)",
      q37: "m(m-n)",
      q38: "4p(2p+3q)",
      q39: "3(3-x)",
      q40: "5xy(x-2y)",
    };
    checkAnswers(answers, "factorization-feedback");
  }
  function checkEvaluation() {
    const answers = {
      q41: "5",
      q42: "6",
      q43: "2",
      q44: "-5",
      q45: "3",
      q46: "-12",
      q47: "10",
      q48: "-12",
      q49: "1",
      q50: "7",
    };
    checkAnswers(answers, "evaluation-feedback");
  }
  function checkAnswers(answers, feedbackId) {
    let correct = 0;
    for (const [id, ans] of Object.entries(answers)) {
      if (document.getElementById(id).value.replace(/\\s/g, "") === ans) {
        correct++;
        document.getElementById(id).className =
          "form-control d-inline-block w-50 border-success";
      } else {
        document.getElementById(id).className =
          "form-control d-inline-block w-50 border-danger";
      }
    }
    const percentage = (correct / Object.keys(answers).length) * 100;
    document.getElementById(feedbackId).innerHTML = `You got ${correct}/${
      Object.keys(answers).length
    } (${percentage}%) correct!`;
    document.getElementById(feedbackId).className =
      percentage >= 80
        ? "ml-2 text-success"
        : percentage >= 50
        ? "ml-2 text-warning"
        : "ml-2 text-danger";
  }

  function checkSet1() {
    const answers = {
      q1: "560",
      q2: "150",
      q3: "160",
      q4: "240",
      q5: "200",
      q6: "270",
      q7: "210",
      q8: "150",
      q9: "240",
      q10: "300",
      q11: "220",
      q12: "260",
      q13: "280",
      q14: "320",
      q15: "360",
      q16: "400",
      q17: "500",
      q18: "600",
      q19: "700",
      q20: "800",
    };
    checkAnswers(answers, "set1-feedback");
  }
  function checkSet2() {
    const answers = {
      q21: "480",
      q22: "600",
      q23: "540",
      q24: "600",
      q25: "750",
      q26: "900",
      q27: "1050",
      q28: "1200",
      q29: "1350",
      q30: "1500",
      q31: "550",
      q32: "650",
      q33: "680",
      q34: "760",
      q35: "920",
      q36: "1080",
      q37: "1160",
      q38: "1240",
      q39: "1320",
      q40: "1480",
    };
    checkAnswers(answers, "set2-feedback");
  }
  function checkSet3() {
    const answers = {
      q41: "1680",
      q42: "1800",
      q43: "1920",
      q44: "2080",
      q45: "2200",
      q46: "2400",
      q47: "2600",
      q48: "2800",
      q49: "3000",
      q50: "3200",
    };
    checkAnswers(answers, "set3-feedback");
  }
  function checkAnswers(answers, feedbackId) {
    let correct = 0;
    for (const [id, ans] of Object.entries(answers)) {
      if (document.getElementById(id).value.replace(/\\s/g, "") === ans) {
        correct++;
        document.getElementById(id).className =
          "form-control d-inline-block w-50 border-success";
      } else {
        document.getElementById(id).className =
          "form-control d-inline-block w-50 border-danger";
      }
    }
    const percentage = (correct / Object.keys(answers).length) * 100;
    document.getElementById(feedbackId).innerHTML = `You got ${correct}/${
      Object.keys(answers).length
    } (${percentage}%) correct!`;
    document.getElementById(feedbackId).className =
      percentage >= 80
        ? "ml-2 text-success"
        : percentage >= 50
        ? "ml-2 text-warning"
        : "ml-2 text-danger";
  }