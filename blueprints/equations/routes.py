from flask import Blueprint, request, jsonify, session
from flask_login import login_required
import sympy
from models import get_db_connection
from sympy import symbols, Eq, solve, simplify
from flask import current_app as app

equations_bp = Blueprint('equations', __name__)


@app.route('/api/solve-equation', methods=['POST'])
def api_solve_equation():
    data = request.get_json()
    expr = data.get('expression', '')

    try:
        # Use SymPy for more advanced solving
        x = symbols('x')

        if '=' in expr:
            # Handle equations
            parts = expr.split('=')
            lhs = sympy.sympify(parts[0])
            rhs = sympy.sympify(parts[1])
            equation = Eq(lhs, rhs)
            solutions = solve(equation, x)

            # Format solutions
            solution_text = []
            for sol in solutions:
                if sol.is_real:
                    solution_text.append(f"x = {sol.evalf(3)}")
                else:
                    solution_text.append(
                        f"x = {sol.as_real_imag()[0].evalf(3)} + {sol.as_real_imag()[1].evalf(3)}i")

            return jsonify({
                'solution': ', '.join(solution_text),
                'steps': [str(step) for step in sympy.solveset(equation, x, domain=sympy.S.Reals).args]
            })
        else:
            # Handle expressions
            simplified = simplify(expr)
            return jsonify({
                'solution': str(simplified),
                'steps': [f"Simplified: {simplified}"]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/save-equation', methods=['POST'])
@login_required
def api_save_equation():
    data = request.get_json()
    equation = data.get('equation', '')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO saved_equations (user_id, equation) VALUES (%s, %s)',
            (session['user_id'], equation)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-saved-equations', methods=['GET'])
@login_required
def api_get_saved_equations():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT id, equation FROM saved_equations WHERE user_id = %s ORDER BY created_at DESC',
            (session['user_id'],)
        )
        equations = cur.fetchall()
        cur.close()
        conn.close()
        # Convert to list of dicts
        return jsonify([{'id': eq[0], 'equation': eq[1]} for eq in equations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-equation/<int:eq_id>', methods=['DELETE'])
@login_required
def api_delete_equation(eq_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'DELETE FROM saved_equations WHERE id = %s AND user_id = %s',
            (eq_id, session['user_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
