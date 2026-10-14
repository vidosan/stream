"""HTML-страницы веб-интерфейса.

Шаблоны хранятся как обычные строки (не f-строки), поэтому фигурные скобки
в CSS и JavaScript не требуют экранирования. Подстановка — через replace.
"""

# =====================================================================
# Главная страница: сетка карточек мониторов
# =====================================================================
INDEX_HEAD = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Сетка мониторов</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            h1 { text-align: center; margin-bottom: 20px; }
            .hdr { max-width: 1600px; margin: 0 auto 16px; display: flex; align-items: center;
                   justify-content: center; gap: 14px; flex-wrap: wrap; }
            .mode-btn { padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px;
                        font-weight: bold; cursor: pointer; background: #e0e0e0; color: #333; }
            .mode-btn.on { background: #d32f2f; color: #fff; }
            .mode-btn:disabled { opacity: .5; cursor: not-allowed; }
            .hint { color: #666; font-size: 13px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; max-width: 1600px; margin: 0 auto; }
            .card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.25s ease; position: relative; z-index: 1; contain: layout style paint; user-select: none; }
            .card:hover { transform: scale(1.05) translateY(-4px); z-index: 10; box-shadow: 0 8px 20px rgba(0,0,0,0.25); }
            .card h3 { margin: 10px 0; padding: 0 10px; text-align: center; font-size: 16px; background-color: #ffffff; }
            .card img { width: 100%; height: 180px; object-fit: contain; background: #000; display: block; pointer-events: none; }
            .card.drag-over { opacity: 0.7; box-shadow: 0 0 0 3px #007bff, 0 8px 20px rgba(0,123,255,0.3); }
            .card.dragging { opacity: 0.3; transform: scale(0.95); }
            .drag-placeholder { border: 2px dashed #007bff; border-radius: 8px; background: rgba(0,123,255,0.1); min-height: 200px; opacity: 0.5; }
            /* Режим управления */
            body.control-mode .card:hover { transform: none; }
            body.control-mode .card { cursor: crosshair; }
            .card.focused { box-shadow: 0 0 0 4px #d32f2f, 0 8px 20px rgba(211,47,47,0.4); z-index: 10; }
            .card.focused h3 { background: #d32f2f; color: #fff; }
            .badge { position: absolute; top: 6px; right: 6px; background: #d32f2f; color: #fff;
                     font-size: 11px; padding: 2px 8px; border-radius: 10px; display: none; }
            .card.focused .badge { display: block; }
        </style>
    </head>
    <body>
        <div class="hdr">
            <button id="modeBtn" class="mode-btn">Режим: Просмотр</button>
            <span id="modeHint" class="hint">Нажмите, чтобы включить управление мышью и клавиатурой</span>
        </div>
        <div class="grid" id="monitorGrid">
    '''

INDEX_TAIL = '''
        </div>
        <script>
            const CONTROL_ENABLED = __CONTROL_ENABLED__;
            const PWD = new URLSearchParams(location.search).get('pwd') || '';
            let controlMode = false;
            let focusedCard = null;
            let ws = null;
            let queue = [];
            let flushTimer = null;
            let lastMove = { x: -1, y: -1 };

            // ---------- WebSocket ----------
            function connectWS() {
                if (!CONTROL_ENABLED) return;
                const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(proto + '//' + location.host + '/ws?pwd=' + encodeURIComponent(PWD));
                ws.onopen = () => { console.log('Управление: канал открыт'); };
                ws.onclose = () => { if (controlMode) setTimeout(connectWS, 1500); };
                ws.onmessage = (e) => {
                    try {
                        const m = JSON.parse(e.data);
                        if (m && m.error === 'control_disabled') {
                            alert('На сервере управление выключено (STREAM_CONTROL=1 не задан).');
                            setControlMode(false);
                        }
                    } catch (err) {}
                };
            }

            function send(ev) {
                if (!ws || ws.readyState !== WebSocket.OPEN) return;
                queue.push(ev);
                if (!flushTimer) flushTimer = setTimeout(flushQueue, 8);
            }

            function flushQueue() {
                flushTimer = null;
                if (!queue.length || !ws || ws.readyState !== WebSocket.OPEN) { queue = []; return; }
                const target = focusedCard ? (focusedCard.dataset.target || '') : '';
                ws.send(JSON.stringify({ events: queue, target: target, pwd: PWD }));
                queue = [];
            }

            function sendRelease() { send({ type: 'release' }); flushQueue(); }

            // ---------- Координаты ----------
            // Переводит позицию курсора в пиксели кадра монитора
            // (учитывает поля от object-fit: contain и масштаб).
            function toMonitorCoords(img, clientX, clientY) {
                const r = img.getBoundingClientRect();
                const nw = img.naturalWidth || 1, nh = img.naturalHeight || 1;
                const scale = Math.min(r.width / nw, r.height / nh);
                if (!scale) return null;
                const dw = nw * scale, dh = nh * scale;
                const offX = r.left + (r.width - dw) / 2;
                const offY = r.top + (r.height - dh) / 2;
                const x = Math.floor((clientX - offX) / scale);
                const y = Math.floor((clientY - offY) / scale);
                if (x < 0 || y < 0 || x >= nw || y >= nh) return null;
                return { x: x, y: y };
            }

            function eventCoords(card, e) {
                const img = card.querySelector('img');
                if (!img) return null;
                return toMonitorCoords(img, e.clientX, e.clientY);
            }

            function buttonName(b) {
                return b === 0 ? 'left' : (b === 2 ? 'right' : (b === 1 ? 'middle' : null));
            }

            // ---------- Фокус карточки ----------
            function setFocus(card) {
                if (focusedCard === card) return;
                sendRelease();
                if (focusedCard) focusedCard.classList.remove('focused');
                focusedCard = card;
                if (focusedCard) {
                    focusedCard.classList.add('focused');
                    focusedCard.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                }
                updateHint();
            }

            function updateHint() {
                const hint = document.getElementById('modeHint');
                if (!CONTROL_ENABLED) {
                    hint.textContent = 'Управление выключено на сервере (нужен STREAM_CONTROL=1)';
                    return;
                }
                if (!controlMode) {
                    hint.textContent = 'Нажмите, чтобы включить управление мышью и клавиатурой';
                } else if (!focusedCard) {
                    hint.textContent = 'Кликните по монитору, чтобы взять его под управление';
                } else {
                    hint.textContent = 'Управление активно: ' +
                        focusedCard.querySelector('h3').textContent +
                        '. Esc — снять фокус';
                }
            }

            function setControlMode(on) {
                if (on && !CONTROL_ENABLED) return;
                controlMode = on;
                document.body.classList.toggle('control-mode', on);
                const btn = document.getElementById('modeBtn');
                btn.textContent = on ? 'Режим: Управление' : 'Режим: Просмотр';
                btn.classList.toggle('on', on);
                document.querySelectorAll('.card').forEach(c => { c.draggable = !on; });
                if (on) { connectWS(); } else { sendRelease(); setFocus(null); }
                updateHint();
            }

            // ---------- Обработчики ввода ----------
            function bindCard(card) {
                card.addEventListener('mousedown', (e) => {
                    if (!controlMode) return;
                    e.preventDefault();
                    if (focusedCard !== card) { setFocus(card); return; }  // первый клик — только фокус
                    const c = eventCoords(card, e);
                    if (c) send({ type: 'mousemove', mon: +card.dataset.mon, x: c.x, y: c.y });
                    const b = buttonName(e.button);
                    if (b) send({ type: 'mousedown', button: b });
                });

                card.addEventListener('mousemove', (e) => {
                    if (!controlMode || focusedCard !== card) return;
                    const c = eventCoords(card, e);
                    if (!c) return;
                    if (c.x === lastMove.x && c.y === lastMove.y) return;
                    lastMove = c;
                    send({ type: 'mousemove', mon: +card.dataset.mon, x: c.x, y: c.y });
                });

                card.addEventListener('wheel', (e) => {
                    if (!controlMode || focusedCard !== card) return;
                    e.preventDefault();
                    send({ type: 'wheel', delta: e.deltaY > 0 ? -120 : 120 });
                }, { passive: false });

                card.addEventListener('contextmenu', (e) => {
                    if (!controlMode) return;
                    e.preventDefault();
                });
            }

            // Отпускание кнопки мыши может произойти вне карточки
            document.addEventListener('mouseup', (e) => {
                if (!controlMode || !focusedCard) return;
                const b = buttonName(e.button);
                if (b) { send({ type: 'mouseup', button: b }); flushQueue(); }
            });

            document.addEventListener('keydown', (e) => {
                if (!controlMode || !focusedCard) return;
                if (e.key === 'Escape') { setFocus(null); return; }
                e.preventDefault();
                send({ type: 'keydown', code: e.code, key: e.key });
                flushQueue();
            });

            document.addEventListener('keyup', (e) => {
                if (!controlMode || !focusedCard) return;
                e.preventDefault();
                send({ type: 'keyup', code: e.code, key: e.key });
                flushQueue();
            });

            // Защита от "залипания": сбрасываем клавиши при уходе со страницы
            window.addEventListener('blur', () => { if (controlMode) sendRelease(); });
            document.addEventListener('visibilitychange', () => {
                if (document.hidden && controlMode) sendRelease();
            });

            function openFS(card) {
                const mon = card.dataset.mon;
                const target = card.dataset.target || '';
                const q = '?mon=' + mon + '&target=' + encodeURIComponent(target) +
                          (PWD ? '&pwd=' + encodeURIComponent(PWD) : '');
                if (controlMode) {
                    window.open('/view' + q, '_blank', 'noopener,noreferrer');
                } else {
                    const pwdParam = PWD ? '?pwd=' + encodeURIComponent(PWD) : '';
                    const url = target ? ('/proxy/' + target + '/screen/' + mon + pwdParam)
                                       : ('/screen/' + mon + pwdParam);
                    window.open(url, '_blank', 'noopener,noreferrer');
                }
            }

            document.addEventListener('DOMContentLoaded', () => {
                const grid = document.getElementById('monitorGrid');
                let draggedItem = null, placeholder = null;
                const savedOrder = localStorage.getItem('monitorOrder');
                if (savedOrder) {
                    try {
                        const order = JSON.parse(savedOrder);
                        const cards = Array.from(grid.querySelectorAll('.card'));
                        order.forEach(cardId => { const card = cards.find(c => c.dataset.cardId === cardId); if (card) grid.appendChild(card); });
                    } catch (e) { console.error('Ошибка загрузки порядка:', e); }
                }
                function saveOrder() { const cards = grid.querySelectorAll('.card'); const order = Array.from(cards).map(c => c.dataset.cardId); localStorage.setItem('monitorOrder', JSON.stringify(order)); }
                function createPlaceholder(card) { const ph = document.createElement('div'); ph.className = 'drag-placeholder'; ph.style.height = card.offsetHeight + 'px'; return ph; }

                grid.querySelectorAll('.card').forEach(bindCard);
                const btn = document.getElementById('modeBtn');
                btn.disabled = !CONTROL_ENABLED;
                if (!CONTROL_ENABLED) btn.textContent = 'Режим: Просмотр (управление выключено)';
                btn.addEventListener('click', () => setControlMode(!controlMode));
                updateHint();

                grid.addEventListener('dragstart', (e) => { if (controlMode) { e.preventDefault(); return; } const card = e.target.closest('.card'); if (!card) return; draggedItem = card; placeholder = createPlaceholder(card); setTimeout(() => card.classList.add('dragging'), 0); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', ''); });
                grid.addEventListener('dragend', (e) => { if (!draggedItem) return; draggedItem.classList.remove('dragging'); if (placeholder && placeholder.parentNode) placeholder.parentNode.removeChild(placeholder); placeholder = null; draggedItem = null; saveOrder(); });
                grid.addEventListener('dragover', (e) => { if (controlMode) return; e.preventDefault(); e.dataTransfer.dropEffect = 'move'; const card = e.target.closest('.card'); if (!card || card === draggedItem) return; const rect = card.getBoundingClientRect(); const midY = rect.top + rect.height / 2; if (placeholder && placeholder.parentNode) placeholder.parentNode.removeChild(placeholder); placeholder = createPlaceholder(card); if (e.clientY < midY) card.parentNode.insertBefore(placeholder, card); else card.parentNode.insertBefore(placeholder, card.nextSibling); card.classList.add('drag-over'); setTimeout(() => card.classList.remove('drag-over'), 100); });
                grid.addEventListener('drop', (e) => { if (controlMode) return; e.preventDefault(); if (!draggedItem || !placeholder) return; const card = e.target.closest('.card'); if (card && card !== draggedItem) { const cardRect = card.getBoundingClientRect(); if (e.clientY < cardRect.top + cardRect.height / 2) grid.insertBefore(draggedItem, card); else grid.insertBefore(draggedItem, card.nextSibling); } else { if (placeholder.nextSibling) grid.insertBefore(draggedItem, placeholder.nextSibling); else grid.appendChild(draggedItem); } if (placeholder.parentNode) placeholder.parentNode.removeChild(placeholder); placeholder = null; saveOrder(); });
            });
        </script>
    </body>
    </html>
    '''

#: Карточка одного монитора (подставляется в сетку)
CARD_TEMPLATE = '''
                    <div class="card" draggable="true"
                         data-card-id="remote_{host}_{mon}"
                         data-mon="{mon}"
                         data-target="{target}"
                         ondblclick="openFS(this)">
                        <span class="badge">УПРАВЛЕНИЕ</span>
                        <h3>{name} - {mon}</h3>
                        <img src="/proxy/{host}:{port}/screen/{mon}{pwd_param}" alt="{name} - Монитор {mon}"
                             onerror="this.src='';this.alt='нет связи';this.style.background='#444';">
                    </div>
                '''


# =====================================================================
# Полноэкранная страница управления одним монитором
# =====================================================================
VIEW_TEMPLATE = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>__TITLE__</title>
        <style>
            html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
            #screen { width: 100vw; height: 100vh; object-fit: contain; display: block; cursor: crosshair; }
            #bar { position: fixed; top: 0; left: 0; right: 0; padding: 6px 12px; background: rgba(0,0,0,.6);
                   color: #fff; font: 13px Arial, sans-serif; display: flex; gap: 16px; align-items: center;
                   transition: opacity .3s; z-index: 10; }
            #bar.hidden { opacity: 0; }
            #state { color: #4caf50; font-weight: bold; }
            #state.off { color: #ff9800; }
        </style>
    </head>
    <body>
        <div id="bar">
            <span>__TITLE__</span>
            <span id="state">подключение...</span>
            <span>Esc — снять нажатия, F5 — обновить</span>
        </div>
        <img id="screen" src="__STREAM_URL__" alt="экран">
        <script>
            const CONTROL_ENABLED = __CONTROL_ENABLED__;
            const PWD = new URLSearchParams(location.search).get('pwd') || '';
            const MON = parseInt(new URLSearchParams(location.search).get('mon') || '1', 10);
            const TARGET = new URLSearchParams(location.search).get('target') || '';
            const img = document.getElementById('screen');
            const stateEl = document.getElementById('state');
            const bar = document.getElementById('bar');

            let ws = null, queue = [], flushTimer = null, active = false;
            let lastMove = { x: -1, y: -1 };

            function setState(text, off) {
                stateEl.textContent = text;
                stateEl.className = off ? 'off' : '';
            }

            function connectWS() {
                if (!CONTROL_ENABLED) { setState('управление выключено на сервере', true); return; }
                const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(proto + '//' + location.host + '/ws?pwd=' + encodeURIComponent(PWD));
                ws.onopen = () => setState('управление активно', false);
                ws.onclose = () => { setState('нет связи, переподключение...', true); setTimeout(connectWS, 1500); };
                ws.onerror = () => setState('ошибка канала', true);
                ws.onmessage = (e) => {
                    try {
                        const m = JSON.parse(e.data);
                        if (m && m.error === 'control_disabled') setState('управление выключено на сервере', true);
                    } catch (err) {}
                };
            }

            function send(ev) {
                if (!ws || ws.readyState !== WebSocket.OPEN) return;
                queue.push(ev);
                if (!flushTimer) flushTimer = setTimeout(flushQueue, 8);
            }

            function flushQueue() {
                flushTimer = null;
                if (!queue.length || !ws || ws.readyState !== WebSocket.OPEN) { queue = []; return; }
                ws.send(JSON.stringify({ events: queue, target: TARGET, pwd: PWD }));
                queue = [];
            }

            function sendRelease() { send({ type: 'release' }); flushQueue(); }

            // Позиция курсора -> пиксели кадра монитора (учёт object-fit: contain)
            function toMonitorCoords(clientX, clientY) {
                const r = img.getBoundingClientRect();
                const nw = img.naturalWidth || 1, nh = img.naturalHeight || 1;
                const scale = Math.min(r.width / nw, r.height / nh);
                if (!scale) return null;
                const dw = nw * scale, dh = nh * scale;
                const offX = r.left + (r.width - dw) / 2;
                const offY = r.top + (r.height - dh) / 2;
                const x = Math.floor((clientX - offX) / scale);
                const y = Math.floor((clientY - offY) / scale);
                if (x < 0 || y < 0 || x >= nw || y >= nh) return null;
                return { x: x, y: y };
            }

            function buttonName(b) {
                return b === 0 ? 'left' : (b === 2 ? 'right' : (b === 1 ? 'middle' : null));
            }

            img.addEventListener('mousemove', (e) => {
                if (!active) return;
                const c = toMonitorCoords(e.clientX, e.clientY);
                if (!c) return;
                if (c.x === lastMove.x && c.y === lastMove.y) return;
                lastMove = c;
                send({ type: 'mousemove', mon: MON, x: c.x, y: c.y });
            });

            img.addEventListener('mousedown', (e) => {
                if (!active) return;
                e.preventDefault();
                const c = toMonitorCoords(e.clientX, e.clientY);
                if (c) send({ type: 'mousemove', mon: MON, x: c.x, y: c.y });
                const b = buttonName(e.button);
                if (b) { send({ type: 'mousedown', button: b }); flushQueue(); }
            });

            document.addEventListener('mouseup', (e) => {
                if (!active) return;
                const b = buttonName(e.button);
                if (b) { send({ type: 'mouseup', button: b }); flushQueue(); }
            });

            img.addEventListener('wheel', (e) => {
                if (!active) return;
                e.preventDefault();
                send({ type: 'wheel', delta: e.deltaY > 0 ? -120 : 120 });
            }, { passive: false });

            img.addEventListener('contextmenu', (e) => e.preventDefault());

            document.addEventListener('keydown', (e) => {
                if (!active) return;
                if (e.key === 'Escape') { sendRelease(); return; }
                e.preventDefault();
                send({ type: 'keydown', code: e.code, key: e.key });
                flushQueue();
            });

            document.addEventListener('keyup', (e) => {
                if (!active) return;
                e.preventDefault();
                send({ type: 'keyup', code: e.code, key: e.key });
                flushQueue();
            });

            window.addEventListener('blur', () => { if (active) sendRelease(); });
            document.addEventListener('visibilitychange', () => { if (document.hidden && active) sendRelease(); });

            // Первый клик активирует управление, чтобы случайно ничего не нажать
            document.addEventListener('click', function activate() {
                if (active) return;
                active = true;
                lastMove = { x: -1, y: -1 };
                setState('управление активно', false);
            }, { once: true });

            // Прячем панель, чтобы не мешала
            let hideTimer = setTimeout(() => bar.classList.add('hidden'), 3000);
            document.addEventListener('mousemove', () => {
                bar.classList.remove('hidden');
                clearTimeout(hideTimer);
                hideTimer = setTimeout(() => bar.classList.add('hidden'), 3000);
            });

            connectWS();
        </script>
    </body>
    </html>
    '''


def render_index(remote_servers, password, control_enabled, is_local_host):
    """Собирает главную страницу — сетку карточек всех мониторов."""
    from ..logs import log

    parts = [INDEX_HEAD]
    for srv in remote_servers:
        try:
            for m in range(1, int(srv.get("monitors", 1)) + 1):
                # Для своей машины ввод применяем сразу, без пересылки по сети
                target = '' if is_local_host(srv['host']) else f"{srv['host']}:{srv['port']}"
                parts.append(CARD_TEMPLATE.format(
                    host=srv['host'],
                    port=srv['port'],
                    mon=m,
                    target=target,
                    name=srv.get("name", "Сервер"),
                    pwd_param=f"?pwd={password}" if password else "",
                ))
        except Exception as e:
            log.error(f"Конфигурация сервера: {e}")

    if not remote_servers:
        parts.append('<p style="text-align:center; color:#888;">Нет серверов для просмотра</p>')

    parts.append(INDEX_TAIL)
    html = ''.join(parts)
    return html.replace('__CONTROL_ENABLED__', 'true' if control_enabled else 'false')


def render_view(mon, target, pwd, control_enabled):
    """Собирает полноэкранную страницу управления одним монитором."""
    pwd_param = f"?pwd={pwd}" if pwd else ""
    if target:
        stream_url = f"/proxy/{target}/screen/{mon}{pwd_param}"
        title = f"{target} — монитор {mon}"
    else:
        stream_url = f"/screen/{mon}{pwd_param}"
        title = f"Монитор {mon}"

    html = VIEW_TEMPLATE.replace('__TITLE__', title).replace('__STREAM_URL__', stream_url)
    return html.replace('__CONTROL_ENABLED__', 'true' if control_enabled else 'false')
