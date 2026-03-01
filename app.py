from flask import Flask, render_template, request, jsonify
from crossword import CrosswordGenerator

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
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

    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
