document.addEventListener('DOMContentLoaded', function () {
    const countSlider = document.getElementById('count');
    const rangeSlider = document.getElementById('num-range');
    const fillSlider = document.getElementById('fill-percent');
    const countValue = document.getElementById('count-value');
    const rangeValue = document.getElementById('range-value');
    const fillValue = document.getElementById('fill-value');

    let currentData = null;
    let answersVisible = false;
    let lastGenerateTime = 0;
    var GENERATE_COOLDOWN = 3000;

    countSlider.addEventListener('input', function () {
        countValue.textContent = countSlider.value;
    });
    rangeSlider.addEventListener('input', function () {
        rangeValue.textContent = rangeSlider.value;
    });
    fillSlider.addEventListener('input', function () {
        fillValue.textContent = fillSlider.value + '%';
    });

    document.getElementById('generate-btn').addEventListener('click', generateCrossword);
    document.getElementById('answer-btn').addEventListener('click', toggleAnswers);
    document.getElementById('pdf-btn').addEventListener('click', downloadPDF);
    document.getElementById('print-btn').addEventListener('click', function () {
        window.print();
    });

    function startCooldown() {
        var btn = document.getElementById('generate-btn');
        var status = document.getElementById('status');
        btn.disabled = true;
        var secondsLeft = Math.ceil(GENERATE_COOLDOWN / 1000);
        status.textContent = 'Подождите ' + secondsLeft + ' сек...';
        var timer = setInterval(function () {
            secondsLeft--;
            if (secondsLeft <= 0) {
                clearInterval(timer);
                btn.disabled = false;
                status.textContent = '';
            } else {
                status.textContent = 'Подождите ' + secondsLeft + ' сек...';
            }
        }, 1000);
    }

    async function generateCrossword() {
        const btn = document.getElementById('generate-btn');
        const status = document.getElementById('status');
        btn.disabled = true;
        status.textContent = 'Генерация кроссворда...';
        answersVisible = false;
        document.querySelectorAll('.cell-hidden').forEach(function (el) {
            el.classList.remove('show-answers');
            el.textContent = '';
        });
        document.getElementById('answer-key').style.display = 'none';
        document.getElementById('answer-btn').textContent = 'Показать ответы';

        const operations = [];
        if (document.getElementById('op-add').checked) operations.push('+');
        if (document.getElementById('op-sub').checked) operations.push('-');
        if (document.getElementById('op-mul').checked) operations.push('*');

        if (operations.length === 0) {
            status.textContent = 'Выберите хотя бы одну операцию!';
            btn.disabled = false;
            return;
        }

        const payload = {
            count: parseInt(countSlider.value),
            num_range: parseInt(rangeSlider.value),
            operations: operations,
            fill_percent: parseInt(fillSlider.value),
        };

        try {
            const resp = await fetch('generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (resp.status === 429) {
                var errData = await resp.json();
                var hours = Math.ceil(errData.resets_in / 3600);
                var quotaMsg = document.getElementById('quota-message');
                if (!errData.is_authenticated) {
                    quotaMsg.innerHTML =
                        'Лимит ' + errData.limit + ' генераций исчерпан. ' +
                        '<a href="/register">Зарегистрируйтесь</a> для 50 генераций в день. ' +
                        'Или попробуйте через ' + hours + ' ч.';
                } else {
                    quotaMsg.textContent = 'Дневной лимит исчерпан. Попробуйте через ' + hours + ' ч.';
                }
                quotaMsg.classList.remove('hidden');
                document.getElementById('quota-remaining').classList.add('hidden');
                status.textContent = '';
                startCooldown();
                return;
            }

            currentData = await resp.json();
            renderCrossword(currentData, false);
            status.textContent = 'Создано уравнений: ' + currentData.total_equations + '. Сетка: ' + currentData.bounds.rows + '\u00d7' + currentData.bounds.cols;
            document.getElementById('answer-btn').classList.remove('hidden');
            document.getElementById('pdf-btn').classList.remove('hidden');
            document.getElementById('quota-message').classList.add('hidden');

            var remainingEl = document.getElementById('quota-remaining');
            if (currentData.remaining >= 0) {
                remainingEl.textContent = 'Осталось генераций: ' + currentData.remaining;
                remainingEl.classList.remove('hidden');
            } else {
                remainingEl.classList.add('hidden');
            }
        } catch (err) {
            status.textContent = 'Ошибка: ' + err.message;
        } finally {
            startCooldown();
        }
    }

    function toggleAnswers() {
        answersVisible = !answersVisible;
        const btn = document.getElementById('answer-btn');
        btn.textContent = answersVisible ? 'Скрыть ответы' : 'Показать ответы';

        document.querySelectorAll('.cell-hidden').forEach(function (el) {
            el.classList.toggle('show-answers', answersVisible);
            el.textContent = answersVisible ? el.dataset.answer : '';
        });

        var answerKey = document.getElementById('answer-key');
        answerKey.style.display = answersVisible ? 'block' : 'none';
    }

    async function downloadPDF() {
        const btn = document.getElementById('pdf-btn');
        const status = document.getElementById('status');
        btn.disabled = true;
        btn.textContent = 'Генерация PDF...';
        status.textContent = '';

        const jsPDFCtor = (window.jspdf && window.jspdf.jsPDF) || window.jsPDF;
        if (typeof domtoimage === 'undefined' || !jsPDFCtor) {
            status.textContent = 'Ошибка: библиотеки не загружены.';
            btn.disabled = false;
            btn.textContent = 'Скачать PDF';
            return;
        }

        const element = document.getElementById('crossword-container');

        const saved = {
            width:        element.style.width,
            overflow:     element.style.overflow,
            borderRadius: element.style.borderRadius,
            boxShadow:    element.style.boxShadow,
        };
        element.style.width        = '718px';
        element.style.overflow     = 'visible';
        element.style.borderRadius = '0';
        element.style.boxShadow    = 'none';

        try {
            const dataUrl = await domtoimage.toJpeg(element, {
                quality: 0.95,
                bgcolor: '#ffffff',
            });

            const img = new Image();
            await new Promise(function (resolve) { img.onload = resolve; img.src = dataUrl; });

            const pdf = new jsPDFCtor({ unit: 'mm', format: 'a4', orientation: 'portrait' });
            const margin = 10;
            const pageW  = 190;
            const pageH  = 277;

            var imgW = pageW;
            var imgH = (img.naturalHeight / img.naturalWidth) * imgW;
            if (imgH > pageH) {
                imgH = pageH;
                imgW = (img.naturalWidth / img.naturalHeight) * imgH;
            }

            const now = new Date();
            const pad = function (n) { return String(n).padStart(2, '0'); };
            const date = now.getFullYear() + '-' + pad(now.getMonth()+1) + '-' + pad(now.getDate());
            const time = pad(now.getHours()) + '-' + pad(now.getMinutes()) + '-' + pad(now.getSeconds());

            pdf.addImage(dataUrl, 'JPEG', margin, margin, imgW, imgH);
            pdf.save('кроссворд_' + date + '_' + time + '.pdf');
            status.textContent = 'PDF сохранён.';
        } catch (err) {
            status.textContent = 'Ошибка при создании PDF: ' + err.message;
            console.error(err);
        } finally {
            element.style.width        = saved.width;
            element.style.overflow     = saved.overflow;
            element.style.borderRadius = saved.borderRadius;
            element.style.boxShadow    = saved.boxShadow;
            btn.disabled = false;
            btn.textContent = 'Скачать PDF';
        }
    }

    function renderCrossword(data, showAnswers) {
        const wrapper = document.getElementById('crossword-wrapper');
        const grid = document.getElementById('crossword-grid');
        const info = document.getElementById('crossword-info');

        wrapper.style.display = 'block';
        grid.innerHTML = '';

        const rows = data.bounds.rows;
        const cols = data.bounds.cols;

        const maxGridWidth = 678;
        const maxGridHeight = 940;
        const cellByWidth = Math.floor(maxGridWidth / cols);
        const cellByHeight = Math.floor(maxGridHeight / rows);
        const cellSize = Math.max(24, Math.min(48, Math.min(cellByWidth, cellByHeight)));

        grid.style.gridTemplateColumns = 'repeat(' + cols + ', ' + cellSize + 'px)';
        grid.style.gridTemplateRows = 'repeat(' + rows + ', ' + cellSize + 'px)';

        const cellMap = {};
        for (var i = 0; i < data.cells.length; i++) {
            var cell = data.cells[i];
            cellMap[cell.row + ',' + cell.col] = cell;
        }

        const baseFontSize = Math.max(11, cellSize - 18);

        for (var r = 0; r < rows; r++) {
            for (var c = 0; c < cols; c++) {
                const div = document.createElement('div');
                div.style.width = cellSize + 'px';
                div.style.height = cellSize + 'px';

                const key = r + ',' + c;
                const cellData = cellMap[key];

                if (!cellData) {
                    div.className = 'cell cell-empty';
                } else if (cellData.is_hidden) {
                    div.className = 'cell cell-hidden';
                    div.dataset.answer = cellData.value;
                    if (showAnswers) {
                        div.classList.add('show-answers');
                        div.textContent = cellData.value;
                    }
                    var len = cellData.value.length;
                    div.style.fontSize = (len > 2 ? baseFontSize - 4 : len > 1 ? baseFontSize - 2 : baseFontSize) + 'px';
                } else if (!cellData.is_number) {
                    div.className = 'cell cell-operator';
                    div.style.fontSize = (baseFontSize + 6) + 'px';
                    div.textContent = cellData.value === '*' ? '\u00d7' : cellData.value;
                } else {
                    div.className = 'cell';
                    var len2 = cellData.value.length;
                    div.style.fontSize = (len2 > 2 ? baseFontSize - 4 : len2 > 1 ? baseFontSize - 2 : baseFontSize) + 'px';
                    div.textContent = cellData.value;
                }

                grid.appendChild(div);
            }
        }

        info.textContent = 'Уравнений: ' + data.total_equations + ' | Размер сетки: ' + rows + '\u00d7' + cols;

        const eqList = document.getElementById('equations-list');
        eqList.innerHTML = '';
        if (data.equations) {
            data.equations.forEach(function (eq, i) {
                const span = document.createElement('div');
                var text = eq.equation.replace(/\*/g, '\u00d7');
                span.textContent = (i + 1) + '. ' + text;
                eqList.appendChild(span);
            });
        }
    }
});
