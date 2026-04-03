from flask import Flask, render_template, request, jsonify
from crossword import CrosswordGenerator
from quota import consume_quota

app = Flask(__name__)

APP_SLUG = "math-crossword"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    # Проверить и списать квоту
    try:
        allowed, quota = consume_quota(request, APP_SLUG, "generate")
    except Exception:
        # Платформа недоступна (локальная разработка) — пропустить
        allowed, quota = True, {"remaining": -1, "limit": 0, "is_authenticated": False, "resets_in": 0}

    if not allowed:
        return jsonify({
            "error": "limit_exceeded",
            "remaining": 0,
            "limit": quota["limit"],
            "is_authenticated": quota["is_authenticated"],
            "resets_in": quota["resets_in"],
        }), 429

    data = request.get_json()
    target_count = int(data.get('count', 15))
    num_range = int(data.get('num_range', 20))
    operations = data.get('operations', ['+', '-'])

    fill_percent = int(data.get('fill_percent', 50))

    target_count = max(5, min(50, target_count))
    num_range = max(1, min(100, num_range))
    fill_percent = max(10, min(80, fill_percent))

    valid_ops = {'+', '-', '*'}
    operations = [op for op in operations if op in valid_ops]
    if not operations:
        operations = ['+']

    generator = CrosswordGenerator()
    result = generator.build(
        target_count=target_count,
        num_range=num_range,
        operations=operations,
        fill_percent=fill_percent,
        max_attempts=30,
    )

    result["remaining"] = quota.get("remaining", -1)
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
