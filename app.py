from flask import Flask, render_template, request, jsonify, session
import random
import string
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-change-this")


def load_word_list():
    with open("word_list.txt", "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


WORD_LIST = load_word_list()


def get_daily_word():
    """Get a consistent word for today based on date"""
    today = datetime.now().date()
    # Use date as seed for consistent daily word
    seed = int(today.strftime("%Y%m%d"))
    random.seed(seed)
    return random.choice(WORD_LIST)


def check_word_validity(word):
    """Check if a word is valid (5 letters, alphabetic)"""
    return len(word) == 5 and word.isalpha() and word.upper() in WORD_LIST


def evaluate_guess(guess, target):
    """Evaluate a guess against the target word"""
    guess = guess.upper()
    target = target.upper()
    result = []

    # Count letter frequencies in target
    target_counts = {}
    for letter in target:
        target_counts[letter] = target_counts.get(letter, 0) + 1

    # First pass: mark correct positions
    for i in range(5):
        if guess[i] == target[i]:
            result.append("correct")
            target_counts[guess[i]] -= 1
        else:
            result.append("pending")

    # Second pass: mark present/absent
    for i in range(5):
        if result[i] == "pending":
            if guess[i] in target_counts and target_counts[guess[i]] > 0:
                result[i] = "present"
                target_counts[guess[i]] -= 1
            else:
                result[i] = "absent"

    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start-game", methods=["POST"])
def start_game():
    """Start a new game"""
    target_word = get_daily_word()
    session["target_word"] = target_word
    session["guesses"] = []
    session["game_over"] = False
    session["won"] = False

    return jsonify({"success": True, "message": "Game started!", "max_guesses": 6})


@app.route("/api/guess", methods=["POST"])
def make_guess():
    """Submit a guess"""
    data = request.get_json()
    guess = data.get("guess", "").strip().upper()

    # Validate session
    if "target_word" not in session:
        return jsonify({"error": "No active game. Please start a new game."}), 400

    # Check if game is already over
    if session.get("game_over", False):
        return jsonify({"error": "Game is already over."}), 400

    # Validate guess
    if not check_word_validity(guess):
        return (
            jsonify({"error": "Invalid word. Please enter a valid 5-letter word."}),
            400,
        )

    # Check if already guessed
    if guess in [g["word"] for g in session.get("guesses", [])]:
        return jsonify({"error": "You already guessed that word."}), 400

    # Evaluate guess
    target_word = session["target_word"]
    result = evaluate_guess(guess, target_word)

    # Store guess
    guess_data = {"word": guess, "result": result}

    if "guesses" not in session:
        session["guesses"] = []
    session["guesses"].append(guess_data)

    # Check win condition
    won = guess.upper() == target_word.upper()
    game_over = won or len(session["guesses"]) >= 6

    session["won"] = won
    session["game_over"] = game_over

    response_data = {
        "result": result,
        "won": won,
        "game_over": game_over,
        "guesses_remaining": 6 - len(session["guesses"]),
    }

    if game_over and not won:
        response_data["target_word"] = target_word

    return jsonify(response_data)


@app.route("/api/game-state", methods=["GET"])
def get_game_state():
    """Get current game state"""
    return jsonify(
        {
            "has_active_game": "target_word" in session,
            "guesses": session.get("guesses", []),
            "game_over": session.get("game_over", False),
            "won": session.get("won", False),
            "target_word": (
                session.get("target_word") if session.get("game_over") else None
            ),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
