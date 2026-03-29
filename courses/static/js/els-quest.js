/* ══════════════════════════════════════════════════
   ELS Quest — Django API Adapter
   STEP_PK, TIME_LIMIT, PASS_SCORE, RETURN_URL — from template
══════════════════════════════════════════════════ */
const LETTERS = ['А','Б','В','Г','Д','Е','Ж','З'];
let questions = [];

var QUIZ_STORAGE_KEY = 'quiz_progress_' + STEP_PK;

function saveQuizProgress() {
  try {
    var saved = { stepId: STEP_PK, currentQ: currentQ, state: state, timestamp: Date.now() };
    localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify(saved));
  } catch(e){}
}

function loadQuizProgress() {
  try {
    var raw = localStorage.getItem(QUIZ_STORAGE_KEY);
    if (!raw) return null;
    var p = JSON.parse(raw);
    if (String(p.stepId) === String(STEP_PK) && p.state && p.state.length) return p;
  } catch(e){}
  return null;
}

async function loadAndStart() {
  // Для final_exam — другой API endpoint
  var url = (typeof STEP_TYPE!=='undefined' && STEP_TYPE==='final_exam')
    ? '/api/final-exam/'+STEP_PK+'/questions/'
    : '/api/steps/'+STEP_PK+'/questions/';
  const r = await fetch(url);
  const d = await r.json();

  // final_exam API может вернуть pass_score и time_limit
  if (d.pass_score && typeof PASS_SCORE !== 'undefined') window.PASS_SCORE_FINAL = d.pass_score;

  questions = d.questions.map(q => ({
    id: q.id, text: q.text, type: q.type, points: q.points||1, weight: q.points||1,
    image: q.image_url||null, caption: null,
    description: q.explanation||null, answers: q.answers||[], correct: q.correct||[],
    terms: q.terms||null,
    instruction: q.type==='single'?'Выберите <strong>один правильный ответ</strong>.'
      :q.type==='multi'?'Выберите <strong>все правильные ответы</strong>.'
      :q.type==='order'?'Расставьте элементы в <strong>правильной последовательности</strong>.'
      :'Перетащите определения к понятиям.',
  }));

  // Попытка восстановить прогресс
  var saved = loadQuizProgress();
  if (saved && saved.state.length === questions.length) {
    state = saved.state;
    currentQ = saved.currentQ || 0;
  } else {
    // final_exam уже перемешан на сервере, quiz — перемешиваем тут
    if (typeof STEP_TYPE==='undefined' || STEP_TYPE!=='final_exam') {
      for(let i=questions.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[questions[i],questions[j]]=[questions[j],questions[i]];}
    }
    initQuizState();
  }
  renderAll();
  checkReturnBtn();
  // Кнопка "Пропустить" для суперадмина
  if (typeof USER_ROLE!=='undefined' && USER_ROLE==='superadmin') {
    var sb=document.getElementById('skipTestBtn'); if(sb) sb.style.display='inline-flex';
  }
  if (state.every(function(s){return s.confirmed;})) {
    setTimeout(showResultScreen, 500);
  }
}

function skipTest(){
  // Автоматически отвечаем на все вопросы (~80% правильных)
  var total=questions.length, target=Math.round(total*0.8);
  for(var i=0;i<total;i++){
    var q=questions[i], s=state[i];
    if(s.confirmed) continue;
    s.confirmed=true;
    if(i<target){
      // Правильный
      if(q.type==='single'||q.type==='multi'){s.selected=q.correct.slice();s.status='correct';}
      else if(q.type==='order'){s.order=q.correct.slice();s.status='correct';}
      else if(q.type==='match'){s.matchSlots=q.correct.slice();s.matchPool=[];s.status='correct';}
    } else {
      // Неправильный
      if(q.type==='single'||q.type==='multi'){var w=q.answers.findIndex(function(_,idx){return !q.correct.includes(idx);});s.selected=[w>=0?w:0];s.status='wrong';}
      else if(q.type==='order'){s.order=q.correct.slice().reverse();s.status='wrong';}
      else if(q.type==='match'){s.matchSlots=q.correct.slice().reverse();s.matchPool=[];s.status='wrong';}
    }
  }
  renderAll();
  saveQuizProgress();
  setTimeout(showResultScreen, 300);
}

// ══════════════════════════════════════
//  STATE (initialized after questions loaded)
// ══════════════════════════════════════
let currentQ = 0;
let state = [];

function initQuizState() {
state = questions.map(q => ({
  status:    'untouched',
  selected:  [],
  order:     q.type === 'order' ? shuffleArr(q.answers.map((_,i) => i)) : null,
  // match: for each term index → chosen answer index (-1 = empty)
  matchSlots: q.type === 'match' ? q.terms.map(() => -1) : null,
  // match: indices of answers still in the pool
  matchPool:  q.type === 'match' ? shuffleArr(q.answers.map((_,i) => i)) : null,
  confirmed: false,
}));
} // end initQuizState

// ══════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════
function ptLabel(n) { return n===1?'балл':n<5?'балла':'баллов'; }

function shuffleArr(arr) {
  const a = [...arr];
  for (let i = a.length-1; i>0; i--) {
    const j = Math.floor(Math.random()*(i+1));
    [a[i],a[j]] = [a[j],a[i]];
  }
  return a;
}

function getCounts() {
  return {
    correct:   state.filter(s=>s.status==='correct').length,
    partial:   state.filter(s=>s.status==='partial').length,
    wrong:     state.filter(s=>s.status==='wrong').length,
    untouched: state.filter(s=>s.status==='untouched').length,
  };
}

function getTotalPoints() {
  return state.reduce((sum,s,i) => {
    if (s.status==='correct') return sum + questions[i].points;
    if (s.status==='partial') return sum + Math.floor(questions[i].points/2);
    return sum;
  }, 0);
}

// ══════════════════════════════════════
//  RENDER — NAV / SCORES
// ══════════════════════════════════════
function renderNavGrid() {
  const grid = document.getElementById('navGrid');
  grid.innerHTML = '';
  const done = state.filter(s=>s.confirmed).length;
  const pct  = done/questions.length*100;
  document.getElementById('navProgressFill').style.width = pct+'%';
  document.getElementById('navProgressText').textContent = `${done} из ${questions.length}`;
  document.getElementById('panelCount').textContent = `${done} / ${questions.length}`;
  document.getElementById('mobileTotalQ').textContent = questions.length;
  questions.forEach((_,i) => {
    const cls = i===currentQ ? 'current' : state[i].status;
    const dot = document.createElement('div');
    dot.className = `nav-dot ${cls}`;
    dot.textContent = i+1;
    dot.title = `Вопрос ${i+1}`;
    dot.onclick = () => goToQ(i);
    grid.appendChild(dot);
  });
}

function renderMobileNav() {
  const strip = document.getElementById('mobileDotsStrip');
  strip.innerHTML = '';
  questions.forEach((_,i) => {
    const cls = i===currentQ ? 'current' : state[i].status;
    const dot = document.createElement('div');
    dot.className = `m-dot ${cls}`;
    dot.textContent = i+1;
    dot.onclick = () => goToQ(i);
    strip.appendChild(dot);
  });
  setTimeout(() => {
    const dots = strip.querySelectorAll('.m-dot');
    if (dots[currentQ]) dots[currentQ].scrollIntoView({inline:'center',block:'nearest',behavior:'smooth'});
  }, 50);
  document.getElementById('mobileQNum').textContent = currentQ+1;
  const c = getCounts();
  document.getElementById('mChipsRow').innerHTML =
    `<span class="m-chip green">✓ ${c.correct}</span>
     <span class="m-chip yellow">~ ${c.partial}</span>
     <span class="m-chip red">✗ ${c.wrong}</span>
     <span class="m-chip gray">○ ${c.untouched}</span>`;
}

function renderScores() {
  const c = getCounts();
  document.getElementById('sCorrect').textContent = c.correct;
  document.getElementById('sPartial').textContent = c.partial;
  document.getElementById('sWrong').textContent   = c.wrong;
  document.getElementById('sLeft').textContent    = c.untouched;
  document.getElementById('totalPts').textContent = getTotalPoints();
  updateResultPanel();
}

function updateResultPanel() {
  const answeredIdx = state.map((s,i)=>s.confirmed?i:-1).filter(i=>i!==-1);
  const answeredCount = answeredIdx.length;

  let wEarned = 0, wMax = 0;
  answeredIdx.forEach(i => {
    const w = questions[i].weight ?? 1;
    const ratio = state[i].status==='correct' ? 1 : state[i].status==='partial' ? 0.5 : 0;
    wEarned += ratio * w;
    wMax    += w;
  });

  const pct = wMax > 0 ? Math.round(wEarned/wMax*100) : null;
  const color = pct===null ? 'var(--text-muted)' : pct>=80 ? 'var(--status-green)' : pct>=50 ? '#c87800' : 'var(--status-red)';
  const barColor = pct===null ? '' : pct>=80 ? 'var(--status-green)' : pct>=50 ? '#f0c040' : 'var(--status-red)';

  // Desktop sidebar
  const pctEl  = document.getElementById('gaugePct');
  const noteEl = document.getElementById('gaugeNote');
  const barEl  = document.getElementById('resultBar');
  const answEl = document.getElementById('resultAnswered');
  if (answEl) answEl.textContent = `${answeredCount} из ${questions.length}`;
  pctEl.textContent  = pct===null ? '—' : pct+'%';
  pctEl.style.color  = color;
  noteEl.textContent = pct===null ? 'нет пройденных вопросов' : `по ${answeredCount} отвеченным вопросам`;
  if (barEl) { barEl.style.width = (pct||0)+'%'; if (barColor) barEl.style.background = barColor; }

  // Mobile strip
  const mPct  = document.getElementById('mobileResultPct');
  const mBar  = document.getElementById('mobileResultBar');
  const mNote = document.getElementById('mobileResultNote');
  if (mPct)  { mPct.textContent = pct===null ? '—' : pct+'%'; mPct.style.color = color; }
  if (mBar)  { mBar.style.width = (pct||0)+'%'; if (barColor) mBar.style.background = barColor; }
  if (mNote) mNote.textContent = pct===null ? 'нет ответов' : `${answeredCount} из ${questions.length}`;
}

// ══════════════════════════════════════
//  RENDER — QUESTION
// ══════════════════════════════════════
function renderQuestion() {
  const q = questions[currentQ];
  const s = state[currentQ];

  const card = document.getElementById('questionCard');
  card.classList.remove('anim'); void card.offsetWidth; card.classList.add('anim');

  document.getElementById('qNum').textContent  = `Вопрос ${currentQ+1}`;
  document.getElementById('qType').textContent =
    q.type==='single' ? 'Один ответ' : q.type==='multi' ? 'Несколько ответов' :
    q.type==='order'  ? 'Последовательность' : 'Сопоставление';
  document.getElementById('qPoints').textContent = `${q.points} ${ptLabel(q.points)}`;
  document.getElementById('qText').textContent   = q.text;
  document.getElementById('navCounter').textContent = `Вопрос ${currentQ+1} из ${questions.length}`;
  document.getElementById('instructionText').innerHTML = `<strong>Инструкция:</strong> ${q.instruction}`;

  const iw = document.getElementById('qImageWrap');
  if (q.image) {
    iw.style.display = '';
    document.getElementById('qImage').src = q.image;
    const cap = document.getElementById('qCaption');
    cap.textContent = q.caption||''; cap.style.display = q.caption?'':'none';
  } else { iw.style.display = 'none'; }

  const desc = document.getElementById('qDesc');
  var showDesc = q.description && !(typeof STEP_TYPE!=='undefined' && STEP_TYPE==='final_exam' && s.confirmed);
  if (showDesc) { desc.style.display=''; desc.textContent=q.description; }
  else { desc.style.display='none'; }

  // Labels
  const noCount = q.type==='order' || q.type==='match';
  document.getElementById('selMaxWrap').style.display = noCount ? 'none' : '';
  document.getElementById('answersLabel').textContent =
    q.type==='order' ? 'Расставьте в правильном порядке' :
    q.type==='match' ? 'Перетащите определения к понятиям' :
    q.type==='single' ? 'Выберите один ответ' : `Выберите ${q.correct.length} верных ответа`;

  const list = document.getElementById('answersList');
  list.innerHTML = '';

  if      (q.type==='order') renderOrderQ(q, s, list);
  else if (q.type==='match') renderMatchQ(q, s, list);
  else                       renderChoiceQ(q, s, list);

  // Confirm button
  const btn = document.getElementById('confirmBtn');
  const selCount = s.selected.length;
  document.getElementById('selCount').textContent = noCount ? '—' : selCount;

  if (s.confirmed) {
    btn.disabled = true;
    const lbl = s.status==='correct'?'Верно ✓':s.status==='partial'?'Частично верно':'Неверно ✗';
    btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 8l4 4 6-7" stroke-linecap="round" stroke-linejoin="round"/></svg>${lbl}`;
    btn.style.background = s.status==='correct'?'var(--status-green)':s.status==='partial'?'#c87800':'var(--status-red)';
  } else {
    let ready = false;
    if      (q.type==='single'||q.type==='multi') ready = selCount > 0;
    else if (q.type==='order') ready = true;
    else if (q.type==='match') ready = s.matchSlots.every(v=>v!==-1);
    btn.disabled = !ready;
    btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 8l4 4 6-7" stroke-linecap="round" stroke-linejoin="round"/></svg>Подтвердить ответ`;
    btn.style.background = '';
  }
}

// ── Single / Multi
function renderChoiceQ(q, s, list) {
  list.className = 'answers-list';
  q.answers.forEach((text, idx) => {
    const isSel = s.selected.includes(idx);
    const isCorrect = q.correct.includes(idx);
    const label = document.createElement('label');
    label.className = 'answer-option' + (q.type==='multi'?' checkbox':'');
    if (!s.confirmed && isSel) label.classList.add('selected');
    if (s.confirmed) {
      label.classList.add('locked');
      if (isSel && isCorrect)  label.classList.add('res-correct');
      else if (isSel)          label.classList.add('res-wrong');
      else if (isCorrect)      label.classList.add('res-missed');
      else                     label.classList.add('res-neutral');
    }
    const svg = q.type==='single'
      ? `<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="5" cy="5" r="2.5" fill="white" stroke="none"/></svg>`
      : `<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M2 5l2.5 2.5 3.5-4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    label.innerHTML = `
      <input type="${q.type==='single'?'radio':'checkbox'}" name="q${currentQ}" value="${idx}" ${isSel?'checked':''}>
      <div class="answer-indicator">${svg}</div>
      <span class="answer-letter">${LETTERS[idx]}</span>
      <span class="answer-text">${text}</span>`;
    if (!s.confirmed) label.querySelector('input').addEventListener('change', () => toggleAnswer(idx));
    list.appendChild(label);
  });
}

// ── Order — physics drag
function renderOrderQ(q, s, list) {
  list.className = 'order-list';
  const arr = s.order;

  arr.forEach((ansIdx, pos) => {
    const item = document.createElement('div');
    item.className = 'order-item';
    item.dataset.pos = pos;

    if (s.confirmed) {
      item.classList.add('locked');
      item.classList.add(ansIdx === q.correct[pos] ? 'res-correct' : 'res-wrong');
    }

    let note = '';
    if (s.confirmed && ansIdx !== q.correct[pos]) {
      note = `<span class="order-correct-note">→ позиция ${q.correct.indexOf(ansIdx)+1}</span>`;
    }
    item.innerHTML = `
      <div class="drag-handle"><span></span><span></span><span></span><span></span><span></span><span></span></div>
      <div class="order-pos">${pos+1}</div>
      <span class="order-item-text">${q.answers[ansIdx]}${note}</span>
      <div class="order-arrows">
        <button class="order-arrow-btn" data-dir="up"   ${pos===0?'disabled':''}>▲</button>
        <button class="order-arrow-btn" data-dir="down" ${pos===arr.length-1?'disabled':''}>▼</button>
      </div>`;

    if (!s.confirmed) {
      item.querySelectorAll('.order-arrow-btn').forEach(btn => {
        btn.addEventListener('click', e => {
          e.stopPropagation();
          const cur  = parseInt(item.dataset.pos);
          const swap = btn.dataset.dir==='up' ? cur-1 : cur+1;
          if (swap<0||swap>=arr.length) return;
          [s.order[cur], s.order[swap]] = [s.order[swap], s.order[cur]];
          renderQuestion();
        });
      });
      attachOrderDrag(item, list, s);
    }
    list.appendChild(item);
  });
}

// ── Physics drag for order list
let orderDragSrc = null;
let orderGhost   = null;
let orderOffX    = 0, orderOffY = 0;
let orderHoverIdx = null;

function attachOrderDrag(item, list, s) {
  // Mouse
  item.addEventListener('mousedown', e => {
    if (e.target.closest('.order-arrow-btn')) return;
    e.preventDefault();
    startOrderDrag(item, list, s, e.clientX, e.clientY);
  });
  // Touch: on mobile screens use arrow buttons only (no drag ghost to avoid scroll conflict)
  item.addEventListener('touchstart', e => {
    if (e.target.closest('.order-arrow-btn')) return;
    // On touch-primary devices (mobile), skip ghost drag — use arrow buttons instead
    if (isTouchDevice()) return;
    const t = e.touches[0];
    startOrderDrag(item, list, s, t.clientX, t.clientY);
  }, {passive:true});
}

function startOrderDrag(item, list, s, cx, cy) {
  orderDragSrc = item;
  const rect = item.getBoundingClientRect();
  orderOffX = cx - rect.left;
  orderOffY = cy - rect.top;

  // Create ghost
  orderGhost = item.cloneNode(true);
  orderGhost.style.cssText = `position:fixed;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;pointer-events:none;z-index:9000;transition:none;`;
  orderGhost.classList.add('is-dragging');
  document.body.appendChild(orderGhost);

  // Store original height for shift calculation
  list.querySelectorAll('.order-item').forEach(el => {
    el.style.setProperty('--item-h', el.offsetHeight+'px');
  });

  item.classList.add('is-dragging');
  item.style.opacity = '0.25';

  const moveHandler = e => {
    const x = e.clientX ?? e.touches?.[0]?.clientX;
    const y = e.clientY ?? e.touches?.[0]?.clientY;
    if (x==null) return;
    orderGhost.style.left = (x - orderOffX) + 'px';
    orderGhost.style.top  = (y - orderOffY) + 'px';
    updateOrderShifts(list, s, x, y);
  };
  const upHandler = e => {
    const x = e.clientX ?? e.changedTouches?.[0]?.clientX;
    const y = e.clientY ?? e.changedTouches?.[0]?.clientY;
    endOrderDrag(list, s, x, y);
    document.removeEventListener('mousemove', moveHandler);
    document.removeEventListener('mouseup',   upHandler);
    document.removeEventListener('touchmove', moveHandler);
    document.removeEventListener('touchend',  upHandler);
  };
  document.addEventListener('mousemove', moveHandler);
  document.addEventListener('mouseup',   upHandler);
  document.addEventListener('touchmove', moveHandler, {passive:true});
  document.addEventListener('touchend',  upHandler);
}

function updateOrderShifts(list, s, cx, cy) {
  const items = [...list.querySelectorAll('.order-item')];
  const srcPos = parseInt(orderDragSrc.dataset.pos);
  let targetPos = srcPos;
  items.forEach((el, i) => {
    if (el === orderDragSrc) return;
    const r = el.getBoundingClientRect();
    const mid = r.top + r.height/2;
    if (cy > mid) targetPos = Math.max(targetPos, parseInt(el.dataset.pos));
    if (cy < mid && i < srcPos) targetPos = Math.min(targetPos, parseInt(el.dataset.pos));
  });
  // Calculate target from Y among all items
  let best = -1, bestDist = Infinity;
  items.forEach(el => {
    const r = el.getBoundingClientRect();
    const mid = r.top + r.height/2;
    const d = Math.abs(cy - mid);
    if (d < bestDist) { bestDist = d; best = parseInt(el.dataset.pos); }
  });
  if (best !== -1) targetPos = best;
  orderHoverIdx = targetPos;

  items.forEach(el => el.classList.remove('shift-down','shift-up'));
  if (targetPos === srcPos) return;
  items.forEach(el => {
    const p = parseInt(el.dataset.pos);
    if (el === orderDragSrc) return;
    if (targetPos > srcPos && p > srcPos && p <= targetPos) el.classList.add('shift-up');
    if (targetPos < srcPos && p >= targetPos && p < srcPos)  el.classList.add('shift-down');
  });
}

function endOrderDrag(list, s, cx, cy) {
  if (orderGhost) { orderGhost.remove(); orderGhost = null; }
  const items = [...list.querySelectorAll('.order-item')];
  items.forEach(el => { el.classList.remove('shift-down','shift-up'); });

  const srcPos = parseInt(orderDragSrc.dataset.pos);
  orderDragSrc.classList.remove('is-dragging');
  orderDragSrc.style.opacity = '';
  orderDragSrc = null;

  if (orderHoverIdx !== null && orderHoverIdx !== srcPos) {
    const [moved] = s.order.splice(srcPos, 1);
    s.order.splice(orderHoverIdx, 0, moved);
  }
  orderHoverIdx = null;
  renderQuestion();
}

// ══════════════════════════════════════
//  MATCH — helpers
// ══════════════════════════════════════

// Detect touch-primary device (mobile)
const isTouchDevice = () => window.matchMedia('(max-width: 880px)').matches || ('ontouchstart' in window && !window.matchMedia('(hover: hover)').matches);

// Tap-mode state (shared across renders)
let matchTapSelected = null;   // { ansIdx, fromTermIdx } | null

// Drag state (desktop only)
let matchDragAnsIdx   = null;
let matchDragFromSlot = null;
let matchGhostEl      = null;
let matchOffX = 0, matchOffY = 0;
let matchEvictTimer   = null;

function renderMatchQ(q, s, list) {
  list.className = 'answers-list';
  list.style.display = '';

  const touchMode = isTouchDevice();
  const area = document.createElement('div');
  area.className = 'match-area';

  // ── Tap mode hint
  if (touchMode && !s.confirmed) {
    const hint = document.createElement('div');
    hint.className = 'match-tap-hint';
    hint.id = 'matchTapHint';
    if (matchTapSelected !== null) {
      hint.textContent = `Выбран: «${q.answers[matchTapSelected.ansIdx]}» — нажмите на понятие чтобы прикрепить`;
    } else {
      hint.textContent = 'Нажмите на ответ чтобы выбрать, затем нажмите на понятие';
    }
    area.appendChild(hint);
  }

  // ── Pool
  const poolDiv = document.createElement('div');
  poolDiv.className = 'match-pool';
  // In tap mode: pool is also a drop target when chip is selected (to de-select)
  if (touchMode && !s.confirmed && matchTapSelected !== null) {
    poolDiv.classList.add('pool-active-target');
    poolDiv.title = 'Нажмите чтобы снять выделение';
    poolDiv.addEventListener('click', e => {
      if (!e.target.closest('.match-chip')) {
        matchTapSelected = null;
        renderQuestion();
      }
    });
  }

  const poolLabel = document.createElement('div');
  poolLabel.className = 'match-pool-label';
  poolLabel.textContent = touchMode
    ? 'Ответы — нажмите чтобы выбрать'
    : 'Ответы — перетащите к понятию';
  poolDiv.appendChild(poolLabel);

  s.matchPool.forEach(ansIdx => {
    const chip = makeMatchChip(ansIdx, q, s, null, touchMode);
    poolDiv.appendChild(chip);
  });

  // ── Slots
  const slotsDiv = document.createElement('div');
  slotsDiv.className = 'match-slots';

  q.terms.forEach((term, termIdx) => {
    const row = document.createElement('div');
    row.className = 'match-row';

    const termEl = document.createElement('div');
    termEl.className = 'match-term';
    termEl.innerHTML = `<span class="match-term-letter">${LETTERS[termIdx]||termIdx+1}</span><span>${term}</span>`;

    const slot = document.createElement('div');
    slot.className = 'match-slot';
    slot.dataset.termIdx = termIdx;

    const occupied = s.matchSlots[termIdx];

    if (s.confirmed) {
      const isRight = occupied === q.correct[termIdx];
      slot.classList.add(isRight ? 'confirmed-correct' : 'confirmed-wrong');
      if (occupied !== -1) {
        const chip = document.createElement('div');
        chip.className = 'match-chip';
        chip.textContent = q.answers[occupied];
        slot.appendChild(chip);
      }
      row.appendChild(termEl);
      row.appendChild(slot);
      slotsDiv.appendChild(row);
      if (!isRight && occupied !== -1) {
        const hintWrap = document.createElement('div');
        hintWrap.style.cssText = 'padding:2px 0 4px calc(50% + 5px);';
        const hint = document.createElement('div');
        hint.className = 'match-correct-hint';
        hint.textContent = '✓ ' + q.answers[q.correct[termIdx]];
        hintWrap.appendChild(hint);
        slotsDiv.appendChild(hintWrap);
      }
      return;
    }

    // Occupied chip inside slot
    if (occupied !== -1) {
      slot.appendChild(makeMatchChip(occupied, q, s, termIdx, touchMode));
    } else {
      const ph = document.createElement('span');
      ph.style.cssText = 'font-size:18px;color:var(--text-muted);pointer-events:none;';
      ph.textContent = '…';
      slot.appendChild(ph);
    }

    // ── Tap mode: slot is click target when chip selected
    if (touchMode) {
      if (matchTapSelected !== null) {
        slot.classList.add('tap-target');
        if (occupied !== -1) slot.classList.add('slot-occupied');
        slot.addEventListener('click', () => {
          const { ansIdx } = matchTapSelected;
          // Evict current if occupied
          if (occupied !== -1) evictSlot(termIdx, s);
          // Remove from pool (might already be removed if coming from another slot)
          s.matchPool = s.matchPool.filter(i => i !== ansIdx);
          // Remove from previous slot if it came from one
          if (matchTapSelected.fromTermIdx !== null) {
            s.matchSlots[matchTapSelected.fromTermIdx] = -1;
            if (!s.matchPool.includes(matchTapSelected.fromTermIdx)) {
              // was from slot, already handled above
            }
          }
          s.matchSlots[termIdx] = ansIdx;
          matchTapSelected = null;
          renderQuestion();
        });
      }
    } else {
      // ── Desktop drag: slot is drop target
      slot.addEventListener('dragover', e => { e.preventDefault(); slot.classList.add('drag-over-slot'); });
      slot.addEventListener('dragleave', () => slot.classList.remove('drag-over-slot'));
      slot.addEventListener('drop', e => { e.preventDefault(); slot.classList.remove('drag-over-slot'); });
      slot.addEventListener('pointerenter', () => {
        if (matchDragAnsIdx === null) return;
        slot.classList.add('drag-over-slot');
        if (occupied !== -1) {
          clearTimeout(matchEvictTimer);
          matchEvictTimer = setTimeout(() => {
            evictSlot(termIdx, s);
            slot.classList.remove('drag-over-slot');
            renderQuestion();
          }, 1000);
        }
      });
      slot.addEventListener('pointerleave', () => {
        slot.classList.remove('drag-over-slot');
        clearTimeout(matchEvictTimer);
      });
      slot.addEventListener('pointerup', () => {
        if (matchDragAnsIdx === null) return;
        dropChipIntoSlot(termIdx, s);
      });
    }

    row.appendChild(termEl);
    row.appendChild(slot);
    slotsDiv.appendChild(row);
  });

  area.appendChild(poolDiv);
  area.appendChild(slotsDiv);
  list.appendChild(area);
}

function makeMatchChip(ansIdx, q, s, fromTermIdx, touchMode) {
  const chip = document.createElement('div');
  chip.className = 'match-chip';
  chip.dataset.ansIdx = ansIdx;

  const label = document.createElement('span');
  label.textContent = q.answers[ansIdx];
  chip.appendChild(label);

  if (s.confirmed) return chip;

  if (touchMode) {
    // ── TAP MODE
    const isSelected = matchTapSelected !== null && matchTapSelected.ansIdx === ansIdx;
    if (isSelected) chip.classList.add('chip-selected');

    chip.style.cursor = 'pointer';
    chip.addEventListener('click', e => {
      e.stopPropagation();
      if (matchTapSelected !== null && matchTapSelected.ansIdx === ansIdx) {
        // De-select
        matchTapSelected = null;
      } else {
        // Select this chip (from pool or from a slot)
        // If it's currently in a slot, mark that slot as source
        matchTapSelected = { ansIdx, fromTermIdx };
      }
      renderQuestion();
    });

    // Remove button only when chip is in a slot
    if (fromTermIdx !== null) {
      const rm = document.createElement('button');
      rm.className = 'chip-remove';
      rm.innerHTML = '×';
      rm.addEventListener('click', e => {
        e.stopPropagation();
        if (matchTapSelected && matchTapSelected.ansIdx === ansIdx) matchTapSelected = null;
        evictSlot(fromTermIdx, s);
        renderQuestion();
      });
      chip.appendChild(rm);
    }
  } else {
    // ── DRAG MODE (desktop)
    chip.addEventListener('pointerdown', e => {
      if (e.target.closest('.chip-remove')) return;
      e.preventDefault();
      startMatchDrag(chip, ansIdx, fromTermIdx, s, e.clientX, e.clientY);
    });

    // Remove button in slot
    if (fromTermIdx !== null) {
      const rm = document.createElement('button');
      rm.className = 'chip-remove';
      rm.innerHTML = '×';
      rm.addEventListener('click', e => {
        e.stopPropagation();
        evictSlot(fromTermIdx, s);
        renderQuestion();
      });
      chip.appendChild(rm);
    }
  }

  return chip;
}

// ── Desktop drag
function startMatchDrag(chip, ansIdx, fromTermIdx, s, cx, cy) {
  matchDragAnsIdx   = ansIdx;
  matchDragFromSlot = fromTermIdx;

  const rect = chip.getBoundingClientRect();
  matchOffX = cx - rect.left;
  matchOffY = cy - rect.top;

  if (fromTermIdx !== null) {
    s.matchSlots[fromTermIdx] = -1;
    if (!s.matchPool.includes(ansIdx)) s.matchPool.push(ansIdx);
  }

  matchGhostEl = chip.cloneNode(true);
  matchGhostEl.querySelector?.('.chip-remove')?.remove();
  matchGhostEl.className = 'match-chip ghost';
  matchGhostEl.style.left  = (cx - matchOffX) + 'px';
  matchGhostEl.style.top   = (cy - matchOffY) + 'px';
  matchGhostEl.style.width = rect.width + 'px';
  document.body.appendChild(matchGhostEl);

  chip.classList.add('dragging-chip');

  const move = e => {
    matchGhostEl.style.left = (e.clientX - matchOffX) + 'px';
    matchGhostEl.style.top  = (e.clientY - matchOffY) + 'px';
  };
  const up = () => {
    endMatchDrag(s);
    document.removeEventListener('pointermove', move);
    document.removeEventListener('pointerup',   up);
  };
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup',   up);
  renderQuestion();
}

function dropChipIntoSlot(termIdx, s) {
  if (matchDragAnsIdx === null) return;
  if (s.matchSlots[termIdx] !== -1) evictSlot(termIdx, s);
  s.matchSlots[termIdx] = matchDragAnsIdx;
  s.matchPool = s.matchPool.filter(i => i !== matchDragAnsIdx);
  clearTimeout(matchEvictTimer);
  matchDragAnsIdx = null; matchDragFromSlot = null;
  if (matchGhostEl) { matchGhostEl.remove(); matchGhostEl = null; }
  renderQuestion();
}

function evictSlot(termIdx, s) {
  const ev = s.matchSlots[termIdx];
  if (ev === -1) return;
  s.matchSlots[termIdx] = -1;
  if (!s.matchPool.includes(ev)) s.matchPool.push(ev);
}

function endMatchDrag(s) {
  clearTimeout(matchEvictTimer);
  if (matchGhostEl) { matchGhostEl.remove(); matchGhostEl = null; }
  if (matchDragAnsIdx !== null) {
    if (!s.matchPool.includes(matchDragAnsIdx)) s.matchPool.push(matchDragAnsIdx);
    matchDragAnsIdx = null; matchDragFromSlot = null;
    renderQuestion();
  }
}

// ══════════════════════════════════════
//  INTERACTIONS — CHOICE
// ══════════════════════════════════════
function toggleAnswer(idx) {
  const q = questions[currentQ];
  const s = state[currentQ];
  if (s.confirmed) return;
  if (q.type==='single') {
    s.selected = [idx];
  } else {
    s.selected = s.selected.includes(idx) ? s.selected.filter(i=>i!==idx) : [...s.selected, idx];
  }
  const selCount = s.selected.length;
  document.getElementById('selCount').textContent = selCount;
  document.getElementById('confirmBtn').disabled = selCount===0;
  document.querySelectorAll('.answer-option').forEach((el,i) => el.classList.toggle('selected', s.selected.includes(i)));
}

// ══════════════════════════════════════
//  CONFIRM
// ══════════════════════════════════════
function confirmAnswer() {
  const q = questions[currentQ];
  const s = state[currentQ];
  if (s.confirmed) return;

  s.confirmed = true;

  if (q.type==='order') {
    let correct = 0;
    s.order.forEach((ansIdx, pos) => { if (ansIdx===q.correct[pos]) correct++; });
    s.status = correct===q.answers.length ? 'correct' : correct>=Math.ceil(q.answers.length/2) ? 'partial' : 'wrong';

  } else if (q.type==='match') {
    if (s.matchSlots.some(v=>v===-1)) { s.confirmed=false; return; }
    let correct = 0;
    s.matchSlots.forEach((chosen, i) => { if (chosen===q.correct[i]) correct++; });
    s.status = correct===q.terms.length ? 'correct' : correct>=Math.ceil(q.terms.length/2) ? 'partial' : 'wrong';

  } else {
    if (s.selected.length===0) { s.confirmed=false; return; }
    const hits  = s.selected.filter(i=>q.correct.includes(i)).length;
    const wrong = s.selected.filter(i=>!q.correct.includes(i)).length;
    s.status = (hits===q.correct.length && wrong===0) ? 'correct' : (hits>0&&wrong===0) ? 'partial' : 'wrong';
  }

  renderAll();
  saveQuizProgress();
  checkAllDone();
  if (currentQ < questions.length-1) setTimeout(()=>{ currentQ++; renderAll(); saveQuizProgress(); }, 950);
}

// ══════════════════════════════════════
//  NAVIGATION
// ══════════════════════════════════════
function renderNavButtons() {
  document.getElementById('btnPrev').disabled = currentQ===0;
  document.getElementById('btnNext').disabled = currentQ===questions.length-1;
}

function renderAll() {
  renderNavGrid();
  renderMobileNav();
  renderScores();
  renderQuestion();
  renderNavButtons();
}

function navigateQ(dir) {
  const next = currentQ + dir;
  if (next<0||next>=questions.length) return;
  goToQ(next);
}

function goToQ(idx) {
  currentQ = idx;
  matchTapSelected = null; // reset tap selection on navigation
  renderAll();
  document.getElementById('mobileExpanded').classList.remove('open');
  document.getElementById('mobileBarToggle').classList.remove('open');
  window.scrollTo({top:0, behavior:'smooth'});
}

function toggleMobileExpanded() {
  document.getElementById('mobileExpanded').classList.toggle('open');
  document.getElementById('mobileBarToggle').classList.toggle('open');
}

// ══════════════════════════════════════
//  RETURN TO LEARN MODULE
// ══════════════════════════════════════
function returnToLearn() {
  const raw = sessionStorage.getItem('questReturn');
  if (raw) {
    try {
      const obj = JSON.parse(raw);
      // Mark all confirmed questions as test completed
      const allConfirmed = state.every(s => s.confirmed);
      if (allConfirmed) obj.completed = true;
      sessionStorage.setItem('questReturn', JSON.stringify(obj));
    } catch {}
  }
  if(typeof RETURN_URL!=='undefined'&&RETURN_URL)window.location.href=RETURN_URL;else window.close();
}

function checkReturnBtn() {
  const raw = sessionStorage.getItem('questReturn');
  const btn = document.getElementById('btnBackLearn');
  if (raw && btn) btn.style.display = 'inline-flex';
}

// After all questions confirmed — show result screen
function checkAllDone() {
  const allConfirmed = state.every(s => s.confirmed);
  if (!allConfirmed) return;
  const raw = sessionStorage.getItem('questReturn');
  if (raw) {
    try {
      const obj = JSON.parse(raw);
      obj.completed = true;
      sessionStorage.setItem('questReturn', JSON.stringify(obj));
    } catch {}
  }
  const btn = document.getElementById('btnBackLearn');
  if (btn) btn.style.display = 'inline-flex';
  // Show result screen after brief delay
  setTimeout(showResultScreen, 1200);
}

function getCSRF(){const m=document.cookie.match(/(?:^|;\s*)csrftoken_lms=([^;]*)/);return m?decodeURIComponent(m[1]):'';}

function showResultScreen() {
  var totalPts = questions.reduce(function(s,q){return s+q.points;}, 0);
  var earnedPts = getTotalPoints();
  var pct = totalPts > 0 ? Math.round(earnedPts/totalPts*100) : 0;
  var ps = (typeof PASS_SCORE_FINAL!=='undefined') ? PASS_SCORE_FINAL : PASS_SCORE;
  var passed = ps > 0 ? pct >= ps : true;
  var c = getCounts();
  var isFinal = (typeof STEP_TYPE!=='undefined' && STEP_TYPE==='final_exam');
  var isPreview = (typeof IS_PREVIEW!=='undefined' && IS_PREVIEW);

  window._quizResult = {pct:pct, correct:c.correct, totalQ:questions.length, earnedPts:earnedPts, totalPts:totalPts, passed:passed};

  // API calls
  if (isFinal) {
    // Собираем детали
    var details = questions.map(function(q,i){
      return {question_id:q.id||null, question_text:q.text, type:q.type, answers:q.answers, correct:q.correct,
        selected:state[i]?state[i].selected:[], is_correct:state[i]?state[i].status==='correct':false,
        points:q.points, earned:(state[i]&&state[i].status==='correct')?q.points:(state[i]&&state[i].status==='partial')?Math.floor(q.points/2):0};
    });
    var quizScores = {};
    try { quizScores = JSON.parse(localStorage.getItem('module_scores_'+MODULE_ID)||'{}'); } catch(e){}
    fetch('/api/final-exam/'+STEP_PK+'/submit/', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()},
      body:JSON.stringify({score:pct, passed:passed, quiz_scores:quizScores, details:details, is_preview:isPreview})
    }).catch(function(){});
  } else {
    fetch('/api/progress/quiz/'+STEP_PK+'/complete/', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()},
      body:JSON.stringify({score:earnedPts, max_score:totalPts, answers:{}})
    }).catch(function(){});
  }
  fetch('/api/progress/step/'+STEP_PK+'/complete/', {
    method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()}
  }).catch(function(){});

  // Рендер экрана результата
  var color = passed ? 'var(--status-green,#107c10)' : 'var(--status-red,#d32f2f)';
  var icon, title, statusLine, buttonsHtml;

  if (isFinal && isPreview) {
    icon = passed ? '\ud83c\udf93' : '\ud83d\udcdd';
    title = passed ? '\u0418\u0442\u043e\u0433\u043e\u0432\u0430\u044f \u043f\u0440\u043e\u0439\u0434\u0435\u043d\u0430!' : '\u0418\u0442\u043e\u0433\u043e\u0432\u0430\u044f \u043d\u0435 \u0441\u0434\u0430\u043d\u0430';
    statusLine = '\u0420\u0435\u0436\u0438\u043c \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438. \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442: '+pct+'% (\u043f\u043e\u0440\u043e\u0433: '+ps+'%)';
    buttonsHtml = '<button onclick="resetAndGoEdit()" style="padding:12px 28px;font-size:14px;font-weight:700;background:var(--accent,#0f62ae);color:#fff;border:none;border-radius:8px;cursor:pointer;">\u0421\u0431\u0440\u043e\u0441\u0438\u0442\u044c \u0438 \u0432 \u043a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u043e\u0440</button>' +
      '<button onclick="goEditNoReset()" style="padding:12px 28px;font-size:14px;font-weight:700;background:#f0f0f0;color:var(--text-secondary,#3d5269);border:none;border-radius:8px;cursor:pointer;">\u0412 \u043a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u043e\u0440 (\u0431\u0435\u0437 \u0441\u0431\u0440\u043e\u0441\u0430)</button>';
  } else if (isFinal && !passed) {
    icon = '\ud83d\udcdd';
    title = '\u0418\u0442\u043e\u0433\u043e\u0432\u0430\u044f \u043d\u0435 \u0441\u0434\u0430\u043d\u0430';
    statusLine = '\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442: '+pct+'% (\u043d\u0443\u0436\u043d\u043e: '+ps+'%)';
    buttonsHtml = '<button onclick="retryExam()" style="padding:12px 28px;font-size:15px;font-weight:700;background:var(--accent,#0f62ae);color:#fff;border:none;border-radius:8px;cursor:pointer;margin-right:8px;">\u041f\u0435\u0440\u0435\u0441\u0434\u0430\u0442\u044c</button>' +
      '<button onclick="finishQuiz()" style="padding:12px 28px;font-size:15px;font-weight:700;background:#f0f0f0;color:var(--text-secondary);border:none;border-radius:8px;cursor:pointer;">\u0412\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f \u043a \u043c\u043e\u0434\u0443\u043b\u044e</button>';
  } else if (isFinal && passed) {
    icon = '\ud83c\udfc6';
    title = '\u041c\u043e\u0434\u0443\u043b\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d!';
    statusLine = '\u041f\u043e\u0437\u0434\u0440\u0430\u0432\u043b\u044f\u0435\u043c! \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442: '+pct+'%';
    buttonsHtml = '<button onclick="finishQuiz()" style="padding:12px 32px;font-size:16px;font-weight:700;background:var(--accent,#0f62ae);color:#fff;border:none;border-radius:8px;cursor:pointer;">\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c</button>';
  } else if (!isFinal && isPreview) {
    // Quiz в режиме проверки
    icon = '\ud83c\udf93';
    title = '\u0422\u0435\u0441\u0442 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d!';
    var stp = ps>0 ? (passed?'\u0417\u0430\u0447\u0442\u0435\u043d\u043e':'\u041d\u0435 \u0437\u0430\u0447\u0442\u0435\u043d\u043e (\u043f\u043e\u0440\u043e\u0433: '+ps+'%)') : '\u0422\u0435\u0441\u0442 \u043f\u0440\u043e\u0439\u0434\u0435\u043d';
    statusLine = '\u0420\u0435\u0436\u0438\u043c \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438. '+stp;
    buttonsHtml = '<button onclick="finishQuiz()" style="padding:12px 28px;font-size:14px;font-weight:700;background:var(--accent,#0f62ae);color:#fff;border:none;border-radius:8px;cursor:pointer;">\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u043c\u043e\u0434\u0443\u043b\u044c</button>' +
      '<button onclick="goEditNoReset()" style="padding:12px 28px;font-size:14px;font-weight:700;background:#f0f0f0;color:var(--text-secondary,#3d5269);border:none;border-radius:8px;cursor:pointer;">\u0412 \u043a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u043e\u0440</button>';
  } else {
    // Quiz обычный
    icon = '\ud83c\udf93';
    title = '\u0422\u0435\u0441\u0442 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d!';
    var st = ps>0 ? (passed?'\u0417\u0430\u0447\u0442\u0435\u043d\u043e':'\u041d\u0435 \u0437\u0430\u0447\u0442\u0435\u043d\u043e (\u043f\u043e\u0440\u043e\u0433: '+ps+'%)') : '\u0422\u0435\u0441\u0442 \u043f\u0440\u043e\u0439\u0434\u0435\u043d';
    statusLine = st;
    buttonsHtml = '<button onclick="finishQuiz()" style="padding:12px 32px;font-size:16px;font-weight:700;background:var(--accent,#0f62ae);color:#fff;border:none;border-radius:8px;cursor:pointer;">\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c</button>';
  }

  var screen = document.getElementById('resultScreen');
  var content = document.getElementById('resultContent');
  content.innerHTML =
    '<div style="text-align:center;padding:40px 20px;background:#fff;border-radius:12px;box-shadow:0 2px 16px rgba(0,0,0,0.08);">' +
      '<div style="font-size:64px;margin-bottom:20px;">'+icon+'</div>' +
      '<h2 style="font-size:26px;font-weight:900;margin-bottom:12px;color:var(--text-primary,#1a2b4a);">'+title+'</h2>' +
      '<div style="font-size:56px;font-weight:900;color:'+color+';margin:20px 0;">'+pct+'%</div>' +
      '<div style="font-size:15px;color:var(--text-muted,#7a93ad);margin-bottom:8px;">\u041f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0445: '+c.correct+' \u0438\u0437 '+questions.length+(ps>0?' \u00b7 \u041f\u043e\u0440\u043e\u0433: '+ps+'%':'')+'</div>' +
      '<div style="font-size:16px;color:'+color+';font-weight:700;margin-bottom:32px;">'+statusLine+'</div>' +
      '<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">'+buttonsHtml+'</div>' +
    '</div>';
  screen.style.display = 'block';
  var navRow = document.querySelector('.nav-row');
  var navPanel = document.querySelector('.nav-panel');
  if (navRow) navRow.style.display = 'none';
  if (navPanel) navPanel.style.display = 'none';
}

function finishQuiz() {
  var res = window._quizResult || {};
  try {
    localStorage.setItem('quizReturn', JSON.stringify({
      stepId: STEP_PK, moduleId: typeof MODULE_ID!=='undefined'?MODULE_ID:null,
      completed: true, score: res.pct||0, correctCount: res.correct||0, totalCount: res.totalQ||0,
    }));
  } catch(e){}
  localStorage.removeItem(QUIZ_STORAGE_KEY);
  window.location.href = RETURN_URL;
}

function retryExam() {
  localStorage.removeItem(QUIZ_STORAGE_KEY);
  window.location.reload();
}

function resetAndGoEdit() {
  localStorage.removeItem('module_progress_'+MODULE_ID);
  localStorage.removeItem('module_scores_'+MODULE_ID);
  localStorage.removeItem(QUIZ_STORAGE_KEY);
  window.location.href = typeof EDIT_URL!=='undefined' ? EDIT_URL : '/modules/'+MODULE_ID+'/edit/';
}

function goEditNoReset() {
  localStorage.removeItem(QUIZ_STORAGE_KEY);
  window.location.href = typeof EDIT_URL!=='undefined' ? EDIT_URL : '/modules/'+MODULE_ID+'/edit/';
}

// ══════════════════════════════════════
//  TIMER
// ══════════════════════════════════════
let timerSec = (typeof TIME_LIMIT!=="undefined"&&TIME_LIMIT>0)?TIME_LIMIT*60:20*60;
setInterval(() => {
  timerSec = Math.max(0, timerSec-1);
  const m = String(Math.floor(timerSec/60)).padStart(2,'0');
  const s = String(timerSec%60).padStart(2,'0');
  const timerEl = document.getElementById('timerDisplay');
  const timerWrap = document.getElementById('headerTimer');
  if (timerEl) timerEl.textContent = `${m}:${s}`;
  if (timerWrap && timerSec<=300) timerWrap.style.background = 'rgba(220,53,69,0.3)';
}, 1000);

// ── Global safety cleanup for stuck ghost elements (mobile Safari etc.)
function cleanupAllGhosts() {
  if (orderGhost)   { orderGhost.remove();   orderGhost   = null; }
  if (matchGhostEl) { matchGhostEl.remove(); matchGhostEl = null; }
  if (orderDragSrc) {
    orderDragSrc.classList.remove('is-dragging');
    orderDragSrc.style.opacity = '';
    document.querySelectorAll('.order-item').forEach(el => el.classList.remove('shift-down','shift-up'));
    orderDragSrc = null;
    orderHoverIdx = null;
  }
  if (matchDragAnsIdx !== null) {
    const s = state[currentQ];
    if (s && !s.matchPool.includes(matchDragAnsIdx)) s.matchPool.push(matchDragAnsIdx);
    matchDragAnsIdx = null;
    matchDragFromSlot = null;
  }
  clearTimeout(matchEvictTimer);
}
document.addEventListener('pointercancel',    cleanupAllGhosts);
document.addEventListener('touchcancel',      cleanupAllGhosts);
document.addEventListener('visibilitychange', () => { if (document.hidden) cleanupAllGhosts(); });
window.addEventListener('blur',               cleanupAllGhosts);
window.addEventListener('scroll',             () => { if (orderGhost || matchGhostEl) cleanupAllGhosts(); }, {passive: true});
loadAndStart();
