from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "atm_secret_key_2024"

# --- База данных пользователей (в реальном банке это было бы в БД) ---
USERS = {
    "1234": {"pin": "1111", "balance": 150000.00, "name": "Алишер Навоий", "history": []},
    "5678": {"pin": "2222", "balance": 75000.50, "name": "Малика Юсупова", "history": []},
    "9999": {"pin": "0000", "balance": 500000.00, "name": "Бобур Каримов", "history": []},
}

def get_user():
    card = session.get("card_number")
    if card and card in USERS:
        return USERS[card]
    return None

def add_history(card, action, amount, balance_after):
    entry = {
        "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "action": action,
        "amount": amount,
        "balance_after": balance_after
    }
    USERS[card]["history"].insert(0, entry)
    # Храним только последние 20 операций
    USERS[card]["history"] = USERS[card]["history"][:20]

# ── МАРШРУТЫ ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    session.clear()
    return render_template("index.html")

@app.route("/enter_pin", methods=["POST"])
def enter_pin():
    card = request.form.get("card_number", "").strip()
    if card not in USERS:
        return render_template("index.html", error="Карта не найдена. Попробуйте: 1234, 5678 или 9999")
    session["card_number"] = card
    session["attempts"] = 0
    return render_template("pin.html", card=card)

@app.route("/verify_pin", methods=["POST"])
def verify_pin():
    card = session.get("card_number")
    if not card:
        return redirect(url_for("index"))

    pin = request.form.get("pin", "").strip()
    attempts = session.get("attempts", 0)

    if USERS[card]["pin"] == pin:
        session["authenticated"] = True
        session["attempts"] = 0
        return redirect(url_for("menu"))
    else:
        attempts += 1
        session["attempts"] = attempts
        if attempts >= 3:
            session.clear()
            return render_template("index.html", error="❌ Карта заблокирована: слишком много попыток!")
        return render_template("pin.html", card=card,
                               error=f"Неверный PIN. Осталось попыток: {3 - attempts}")

@app.route("/menu")
def menu():
    if not session.get("authenticated"):
        return redirect(url_for("index"))
    user = get_user()
    return render_template("menu.html", user=user)

@app.route("/balance")
def balance():
    if not session.get("authenticated"):
        return redirect(url_for("index"))
    user = get_user()
    return render_template("balance.html", user=user)

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    if not session.get("authenticated"):
        return redirect(url_for("index"))
    card = session.get("card_number")
    user = get_user()

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
            if amount <= 0:
                return render_template("withdraw.html", user=user, error="Сумма должна быть больше нуля")
            if amount > user["balance"]:
                return render_template("withdraw.html", user=user, error="Недостаточно средств на счёте!")
            if amount % 1000 != 0:
                return render_template("withdraw.html", user=user, error="Сумма должна быть кратна 1000 сумов")
            USERS[card]["balance"] -= amount
            add_history(card, "Снятие наличных", -amount, USERS[card]["balance"])
            return render_template("success.html", user=user,
                                   message=f"Выдано: {amount:,.0f} сум",
                                   action="withdraw")
        except ValueError:
            return render_template("withdraw.html", user=user, error="Введите корректную сумму")

    return render_template("withdraw.html", user=user)

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if not session.get("authenticated"):
        return redirect(url_for("index"))
    card = session.get("card_number")
    user = get_user()

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
            if amount <= 0:
                return render_template("deposit.html", user=user, error="Сумма должна быть больше нуля")
            USERS[card]["balance"] += amount
            add_history(card, "Внесение наличных", +amount, USERS[card]["balance"])
            return render_template("success.html", user=user,
                                   message=f"Зачислено: {amount:,.0f} сум",
                                   action="deposit")
        except ValueError:
            return render_template("deposit.html", user=user, error="Введите корректную сумму")

    return render_template("deposit.html", user=user)

@app.route("/history")
def history():
    if not session.get("authenticated"):
        return redirect(url_for("index"))
    user = get_user()
    return render_template("history.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
