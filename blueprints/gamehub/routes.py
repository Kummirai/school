from flask import Blueprint, render_template, url_for, request, jsonify, redirect, abort
import json
import os
from flask_login import login_required
from flask import current_app as app
from .utils import get_random_question

# Create a Blueprint for the grades routes
gamehub_bp = Blueprint('gamehub', __name__,
                       template_folder='templates', static_folder='static')


@gamehub_bp.route('/games')
def game_hub():
    return render_template('game_hub.html')


@gamehub_bp.route('/math-game')
def math_game():
    grade = request.args.get('grade', default=7, type=int)
    players = request.args.get('players', default=1, type=int)
    player_names = [request.args.get(
        f'player{i+1}', f'Player {i+1}') for i in range(players)]

    # Determine which math game to serve based on grade level
    math_games = {
        7: 'math_game_7.html',
        8: 'math_game_8.html',
        # ... up to grade 12
    }

    return render_template(math_games.get(grade, 'math_game_7.html'),
                           grade=grade,
                           players=players,
                           player_names=player_names)


@gamehub_bp.route('/english-game')
def english_game():
    grade = request.args.get('grade', default=7, type=int)
    players = request.args.get('players', default=1, type=int)
    player_names = [request.args.get(
        f'player{i+1}', f'Player {i+1}') for i in range(players)]

    # Determine which English game to serve based on grade level
    english_games = {
        7: 'english_game_7.html',
        8: 'english_game_8.html',
        # ... up to grade 12
    }

    return render_template(english_games.get(grade, 'english_game_7.html'),
                           grade=grade,
                           players=players,
                           player_names=player_names)

# Add similar routes for science and history games


@gamehub_bp.route('/science-game')
def science_game():
    grade = request.args.get('grade', default=7, type=int)
    players = request.args.get('players', default=1, type=int)
    player_names = [request.args.get(
        f'player{i+1}', f'Player {i+1}') for i in range(players)]

    # Determine which English game to serve based on grade level
    english_games = {
        7: 'science_game_7.html',
        8: 'science_game_8.html',
        # ... up to grade 12
    }

    return render_template(english_games.get(grade, 'science_game_7.html'),
                           grade=grade,
                           players=players,
                           player_names=player_names)


@gamehub_bp.route('/history-game')
def history_game():
    grade = request.args.get('grade', default=7, type=int)
    players = request.args.get('players', default=1, type=int)
    player_names = [request.args.get(
        f'player{i+1}', f'Player {i+1}') for i in range(players)]

    # Determine which English game to serve based on grade level
    english_games = {
        7: 'history_game_7.html',
        8: 'history_game_8.html',
        # ... up to grade 12
    }

    return render_template(english_games.get(grade, 'history_game_7.html'),
                           grade=grade,
                           players=players,
                           player_names=player_names)


@gamehub_bp.route('/snake-and-ladder-game')
def snake_and_ladder_game():
    grade = request.args.get('grade', default=7, type=int)
    players = request.args.get('players', default=1, type=int)
    player_names = [request.args.get(
        f'player{i+1}', f'Player {i+1}') for i in range(players)]
    return render_template('snake_and_ladder_game.html',
                           grade=grade,
                           players=players,
                           player_names=player_names)


@gamehub_bp.route('/api/get_question')
def get_question():
    grade = request.args.get('grade', type=int)
    if not grade:
        return jsonify({'error': 'Grade parameter is required'}), 400

    question_data = get_random_question(grade)
    if question_data:
        # Convert DictRow to a regular dictionary for JSON serialization
        question_dict = dict(question_data)
        return jsonify(question_dict)
    else:
        return jsonify({'error': 'No questions found for this grade or an error occurred'}), 404
