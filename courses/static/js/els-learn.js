/* ══════════════════════════════════════════════════
   ELS Learn — Логика прохождения модуля (preview)
══════════════════════════════════════════════════ */

function getCSRF(){var m=document.cookie.match(/(?:^|;\s*)csrftoken_lms=([^;]*)/);return m?decodeURIComponent(m[1]):'';}

/* ── Иконки SVG ── */
var ICO = {
  online:   '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="8" cy="8" r="6.5"/><path d="M8 4v4l3 2" stroke-linecap="round"/></svg>',
  pdf:      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke-linejoin="round"/><path d="M9 1v4h4M5.5 9h5M5.5 11.5h3" stroke-linecap="round"/></svg>',
  test:     '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="1.5" y="1.5" width="13" height="13" rx="1.5"/><path d="M5 8l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  practice: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="8" cy="6" r="3"/><path d="M3 14c0-2.8 2.2-4.5 5-4.5s5 1.7 5 4.5" stroke-linecap="round"/></svg>',
  upload:   '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8 10V2M5 5l3-3 3 3" stroke-linecap="round" stroke-linejoin="round"/><path d="M1 11v2a1 1 0 001 1h12a1 1 0 001-1v-2" stroke-linecap="round"/></svg>',
  slide:    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="1.5" y="2.5" width="13" height="10" rx="1.5"/><path d="M5.5 7l2.5 2 2.5-2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  done:     '<svg viewBox="0 0 16 16" fill="none" stroke="#107c10" stroke-width="2.2"><path d="M3 8l4 4 6-7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  current:  '<svg viewBox="0 0 16 16" fill="none" stroke="#0f62ae" stroke-width="2"><circle cx="8" cy="8" r="5"/><path d="M8 5v4" stroke-linecap="round"/><circle cx="8" cy="11" r=".5" fill="#0f62ae"/></svg>',
  locked:   '<svg viewBox="0 0 16 16" fill="none" stroke="#7a93ad" stroke-width="1.8"><rect x="4" y="7" width="8" height="7" rx="1"/><path d="M5.5 7V5a2.5 2.5 0 015 0v2" stroke-linecap="round"/></svg>',
  clock:    '<svg viewBox="0 0 16 16" fill="none" stroke="#9a6300" stroke-width="1.8"><circle cx="8" cy="8" r="6.5"/><path d="M8 5v4l2.5 1.5" stroke-linecap="round"/></svg>',
  repeat:   '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 8A7 7 0 1013.5 4M13.5 1v3h-3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
var ICO_OPEN = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 3h7a1 1 0 011 1v7a1 1 0 01-1 1H5" stroke-linecap="round"/><path d="M10 8H1M7 5l3 3-3 3" stroke-linecap="round" stroke-linejoin="round"/></svg>';

var TYPE_MAP = {material:'online',practice:'practice',upload:'upload',quiz:'test',final_exam:'test',slide:'slide'};
var TYPE_LABELS = {material:'\u041e\u041d\u041b\u0410\u0419\u041d',practice:'\u041f\u0420\u0410\u041a\u0422\u0418\u041a\u0410',upload:'\u0417\u0410\u0413\u0420\u0423\u0417\u041a\u0410',quiz:'\u0422\u0415\u0421\u0422',final_exam:'\u0410\u0422\u0422\u0415\u0421\u0422\u0410\u0426\u0418\u042f',slide:'\u0421\u041b\u0410\u0419\u0414'};

/* ══════════════════════════════════════
   Состояние + localStorage
══════════════════════════════════════ */
var allSteps = [];
var doneSet = new Set();

function saveDone() {
  var ids = [];
  doneSet.forEach(function(idx){ if(allSteps[idx]&&allSteps[idx].id) ids.push(allSteps[idx].id); });
  try { localStorage.setItem('module_progress_'+MODULE_PK, JSON.stringify(ids)); } catch(e){}
}
function loadDone() {
  try {
    var raw = localStorage.getItem('module_progress_'+MODULE_PK);
    if(!raw) return;
    JSON.parse(raw).forEach(function(id){
      var idx = allSteps.findIndex(function(s){return s.id===id;});
      if(idx!==-1) doneSet.add(idx);
    });
  } catch(e){}
}
function isStepDone(idx) { return doneSet.has(idx); }
function markStepDone(idx) {
  doneSet.add(idx); saveDone();
  var step = allSteps[idx];
  if(step&&step.id) fetch('/api/progress/step/'+step.id+'/complete/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()}}).catch(function(){});
  renderPage();
}

/* ── Проверка результата теста (из localStorage, после возврата) ── */
function checkQuizReturn() {
  var raw = localStorage.getItem('quizReturn');
  if(!raw) return;
  try {
    var r = JSON.parse(raw);
    if(String(r.moduleId)===String(MODULE_PK)) {
      var idx = allSteps.findIndex(function(s){return s.id===r.stepId;});
      if(idx!==-1) { doneSet.add(idx); saveDone(); }
      try {
        var sc = JSON.parse(localStorage.getItem('module_scores_'+MODULE_PK)||'{}');
        sc[r.stepId] = {score:r.score,correct:r.correctCount,total:r.totalCount};
        localStorage.setItem('module_scores_'+MODULE_PK, JSON.stringify(sc));
      } catch(e2){}
    }
  } catch(e){}
  localStorage.removeItem('quizReturn');
}

/* ── Группировка ── */
function getMainSteps(){return allSteps.map(function(s,i){return Object.assign({},s,{idx:i});}).filter(function(s){return ['practice','upload','final_exam'].indexOf(s.type)===-1;});}
function getPracticeSteps(){return allSteps.map(function(s,i){return Object.assign({},s,{idx:i});}).filter(function(s){return s.type==='practice'||s.type==='upload';});}
function getFinalSteps(){return allSteps.map(function(s,i){return Object.assign({},s,{idx:i});}).filter(function(s){return s.type==='final_exam';});}

function getMainStepStatus(step){
  if(isStepDone(step.idx)) return 'done';
  var mains=getMainSteps();
  for(var k=0;k<mains.length;k++){if(mains[k].idx>=step.idx) break; if(!isStepDone(mains[k].idx)) return 'locked';}
  return 'current';
}
function getFinalStepStatus(step){
  if(isStepDone(step.idx)) return 'done';
  if(getMainSteps().every(function(s){return isStepDone(s.idx);})&&(getPracticeSteps().length===0||getPracticeSteps().every(function(s){return isStepDone(s.idx);}))) return 'current';
  return 'locked';
}

function getScoreText(stepId) {
  try { var sc=JSON.parse(localStorage.getItem('module_scores_'+MODULE_PK)||'{}'); var q=sc[stepId]; if(q) return ' \u00b7 <span style="color:'+(q.score>=70?'var(--status-green)':'var(--status-red)')+';font-weight:700">'+q.score+'%</span> ('+q.correct+' \u0438\u0437 '+q.total+')'; } catch(e){}
  return '';
}

/* ── Открыть шаг ── */
function openStep(idx) {
  var step = allSteps[idx];
  if(!step) return;
  // slide — новая вкладка + confirm
  if(step.type==='slide') {
    if(step.id) window.open('/modules/step/'+step.id+'/slides/','_blank');
    var el=document.getElementById('confirm-'+idx); if(el) el.classList.add('visible');
    return;
  }
  // quiz/final_exam — В ТЕКУЩЕЙ ВКЛАДКЕ (прогресс в localStorage)
  if(step.type==='quiz'||step.type==='final_exam') {
    if(step.id) { localStorage.removeItem('quiz_progress_'+step.id); window.location.href='/modules/step/'+step.id+'/quiz/preview/'; }
    return;
  }
  // material — новая вкладка + confirm
  if(step.url) window.open(step.url,'_blank');
  var el2=document.getElementById('confirm-'+idx); if(el2) el2.classList.add('visible');
}

function confirmStep(idx) { markStepDone(idx); var el=document.getElementById('confirm-'+idx); if(el) el.classList.remove('visible'); }

function finishCourse() {
  document.getElementById('modalText').innerHTML='\u0412\u044b \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043b\u0438 \u043c\u043e\u0434\u0443\u043b\u044c<br><strong>\u00ab'+MODULE_TITLE+'\u00bb</strong>.<br>\u041f\u043e\u0437\u0434\u0440\u0430\u0432\u043b\u044f\u0435\u043c!';
  document.getElementById('finishModal').classList.add('visible');
}

/* ── Карточка шага ── */
function buildStepCard(step,cardClass,typeLabel,subtitleHtml,actionHtml,extraHtml,stepNum){
  var mt=TYPE_MAP[step.type]||'online';
  return '<div class="step-card '+cardClass+'" id="step-'+step.idx+'"><div class="step-card-inner"><div class="step-top-row"><div class="step-type-badge '+mt+'">'+(ICO[mt]||'')+' '+typeLabel+'</div><div class="step-author-num"><span class="step-num">\u0428\u0430\u0433 '+stepNum+'</span></div></div><div class="step-title">'+step.title+'</div><div class="step-bottom-row">'+subtitleHtml+'<div class="step-actions">'+actionHtml+'</div></div></div>'+extraHtml+'</div>';
}

/* ══════════════════════════════════════
   Рендер страницы
══════════════════════════════════════ */
function renderPage(){
  var mainSteps=getMainSteps(), practiceSteps=getPracticeSteps(), finalSteps=getFinalSteps();
  var total=allSteps.length, doneCount=doneSet.size, pct=total?Math.round(doneCount/total*100):0;
  var allMainDone=mainSteps.every(function(s){return isStepDone(s.idx);});
  var allPracticeDone=practiceSteps.length===0||practiceSteps.every(function(s){return isStepDone(s.idx);});
  var allFinalDone=finalSteps.length===0||finalSteps.every(function(s){return isStepDone(s.idx);});
  var allDone=allMainDone&&allPracticeDone&&allFinalDone;
  document.getElementById('footerCourseName').textContent=MODULE_TITLE;
  document.getElementById('footerProgress').textContent=doneCount+' / '+total+' \u0448\u0430\u0433\u043e\u0432';

  var stepNum=0;
  var mainHtml=mainSteps.map(function(step){
    stepNum++;
    var st=getMainStepStatus(step), tl=TYPE_LABELS[step.type]||step.type.toUpperCase();
    var cls,sub,act,ext='';
    if(st==='done'){
      cls='done';
      var dt='\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e';
      if(step.type==='quiz') dt='\u041f\u0440\u043e\u0439\u0434\u0435\u043d\u043e'+getScoreText(step.id);
      sub='<div class="step-subtitle">'+ICO.done+' '+dt+'</div>';
      act='<button class="btn-step repeat" onclick="openStep('+step.idx+')">'+ICO.repeat+' \u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c</button>';
    } else if(st==='current'){
      cls='current';
      if(step.type==='slide') sub='<div class="step-subtitle">'+ICO.current+' \u0418\u043d\u0442\u0435\u0440\u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u0441\u043b\u0430\u0439\u0434</div>';
      else if(step.type==='quiz') sub='<div class="step-subtitle">'+ICO.current+' \u041f\u0440\u043e\u043c\u0435\u0436\u0443\u0442\u043e\u0447\u043d\u044b\u0439 \u0442\u0435\u0441\u0442</div>';
      else sub='<div class="step-subtitle">'+ICO.current+' \u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u044d\u0442\u0430\u043f</div>';
      act='<button class="btn-step open" onclick="openStep('+step.idx+')">'+ICO_OPEN+' \u041e\u0442\u043a\u0440\u044b\u0442\u044c</button>';
      // confirm для slide и material, НЕ для quiz
      if(step.type!=='quiz'){
        ext='<div class="step-confirm" id="confirm-'+step.idx+'"><div class="step-confirm-text">\u0412\u044b \u0438\u0437\u0443\u0447\u0438\u043b\u0438 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b <strong>\u00ab'+step.title+'\u00bb</strong>?</div><button class="btn-mark-done" onclick="confirmStep('+step.idx+')">'+ICO.done+' \u041e\u0442\u043c\u0435\u0442\u0438\u0442\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u043c</button></div>';
      }
    } else {
      cls='locked'; sub='<div class="step-subtitle">'+ICO.locked+' \u0417\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u043e</div>';
      act='<button class="btn-step locked-btn" disabled>'+ICO.locked+' \u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e</button>';
    }
    return buildStepCard(step,cls,tl,sub,act,ext,stepNum);
  }).join('');

  var practiceHtml='';
  if(practiceSteps.length>0){
    var pC=practiceSteps.map(function(step){
      stepNum++; var done=isStepDone(step.idx),cls,sub,act;
      if(done){cls='practice-done';sub='<div class="step-subtitle">'+ICO.done+' \u0417\u0430\u0447\u0442\u0435\u043d\u043e</div>';act='<span class="btn-step practice-wait" style="background:var(--status-green-bg);color:var(--status-green);border-color:#8fcb8f">'+ICO.done+' \u0417\u0430\u0447\u0442\u0435\u043d\u043e</span>';}
      else{cls='practice-pending';if(step.type==='upload'){sub='<div class="step-subtitle">'+ICO.upload+' \u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u0444\u0430\u0439\u043b</div>';act='<button class="btn-step open" style="background:#5c3fb0" onclick="markStepDone('+step.idx+')">'+ICO.upload+' \u0418\u043c\u0438\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c</button>';}else{sub='<div class="step-subtitle">'+ICO.clock+' \u041e\u0436\u0438\u0434\u0430\u0435\u0442 \u0437\u0430\u0447\u0451\u0442\u0430</div>';act='<button class="btn-step open" style="background:var(--status-green)" onclick="markStepDone('+step.idx+')">'+ICO.done+' \u0418\u043c\u0438\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c</button>';}}
      return buildStepCard(step,cls,TYPE_LABELS[step.type]||'\u041f\u0420\u0410\u041a\u0422\u0418\u041a\u0410',sub,act,'',stepNum);
    }).join('');
    practiceHtml='<div class="practice-divider"><div class="practice-divider-line"></div><div class="practice-divider-label">\ud83d\udccb \u041f\u0440\u0430\u043a\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u0437\u0430\u043d\u044f\u0442\u0438\u044f</div><div class="practice-divider-line"></div></div><div class="steps-list">'+pC+'</div>';
  }

  var finalHtml='';
  if(finalSteps.length>0){
    var fC=finalSteps.map(function(step){
      stepNum++; var st=getFinalStepStatus(step),cls,sub,act;
      if(st==='done'){cls='done';sub='<div class="step-subtitle">'+ICO.done+' \u041f\u0440\u043e\u0439\u0434\u0435\u043d\u043e'+getScoreText(step.id)+'</div>';act='<button class="btn-step repeat" onclick="openStep('+step.idx+')">'+ICO.repeat+' \u041f\u0440\u043e\u0439\u0442\u0438 \u0441\u043d\u043e\u0432\u0430</button>';}
      else if(st==='current'){cls='current';sub='<div class="step-subtitle">'+ICO.current+' \u0418\u0442\u043e\u0433\u043e\u0432\u0430\u044f \u0430\u0442\u0442\u0435\u0441\u0442\u0430\u0446\u0438\u044f \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430</div>';act='<button class="btn-step open" onclick="openStep('+step.idx+')">'+ICO_OPEN+' \u041d\u0430\u0447\u0430\u0442\u044c \u0442\u0435\u0441\u0442</button>';}
      else{var w=!allMainDone?'\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0435 \u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u044d\u0442\u0430\u043f\u044b':'\u041e\u0436\u0438\u0434\u0430\u0435\u0442 \u0437\u0430\u0447\u0451\u0442\u0430 \u043f\u0440\u0430\u043a\u0442\u0438\u043a\u0438';cls='locked';sub='<div class="step-subtitle">'+ICO.locked+' '+w+'</div>';act='<button class="btn-step locked-btn" disabled>'+ICO.locked+' \u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e</button>';}
      return buildStepCard(step,cls,TYPE_LABELS[step.type]||'\u0410\u0422\u0422\u0415\u0421\u0422\u0410\u0426\u0418\u042f',sub,act,'',stepNum);
    }).join('');
    finalHtml='<div class="practice-divider"><div class="practice-divider-line"></div><div class="practice-divider-label">\ud83c\udf93 \u0418\u0442\u043e\u0433\u043e\u0432\u0430\u044f \u0430\u0442\u0442\u0435\u0441\u0442\u0430\u0446\u0438\u044f</div><div class="practice-divider-line"></div></div><div class="steps-list">'+fC+'</div>';
  }

  var fin='<div class="finish-card'+(allDone?' ready':'')+'" id="finishCard"><div class="finish-emoji">'+(allDone?'\ud83c\udfc6':'\ud83c\udfaf')+'</div><div class="finish-title">'+(allDone?'\u0412\u0441\u0435 \u044d\u0442\u0430\u043f\u044b \u043f\u0440\u043e\u0439\u0434\u0435\u043d\u044b!':'\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0435 \u0432\u0441\u0435 \u044d\u0442\u0430\u043f\u044b')+'</div><div class="finish-desc">'+(allDone?'\u0412\u044b \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u043f\u0440\u043e\u0448\u043b\u0438 \u0432\u0441\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b.':'\u041f\u0440\u043e\u0439\u0434\u0438\u0442\u0435 \u0432\u0441\u0435 \u0448\u0430\u0433\u0438.')+'</div><button class="btn-finish"'+(allDone?'':' disabled')+' onclick="finishCourse()"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8l4 4 6-7" stroke-linecap="round" stroke-linejoin="round"/></svg> \u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c</button></div>';

  document.getElementById('pageContent').innerHTML=
  '<div style="max-width:800px;margin:0 auto;padding:20px 20px 0;">'+
    '<a href="/modules/" style="color:var(--accent);font-size:13px;display:inline-flex;align-items:center;gap:5px;margin-bottom:16px;text-decoration:none;"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M10 3L5 8l5 5" stroke-linecap="round" stroke-linejoin="round"/></svg> \u041d\u0430\u0437\u0430\u0434 \u043a \u043c\u043e\u0434\u0443\u043b\u044f\u043c</a>'+
    '<div style="background:var(--card-bg,#fff);border:1px solid var(--border,#e0eaf5);border-radius:8px;box-shadow:0 2px 12px rgba(15,98,174,0.08);padding:20px;margin-bottom:20px;">'+
      '<div style="display:flex;justify-content:flex-end;gap:12px;margin-bottom:14px;"><span style="font-size:13px;color:var(--text-muted);">'+doneCount+' \u0438\u0437 '+total+' \u044d\u0442\u0430\u043f\u043e\u0432</span><div style="flex:1;max-width:200px;height:6px;background:var(--border,#e0eaf5);border-radius:3px;overflow:hidden;align-self:center;"><div style="height:100%;width:'+pct+'%;background:var(--status-green,#107c10);border-radius:3px;transition:width .5s;"></div></div></div>'+
      '<div style="font-size:22px;font-weight:900;color:var(--text-primary,#1a2433);margin-bottom:6px;">'+MODULE_TITLE+'</div>'+
      '<div style="font-size:14px;color:var(--accent,#0f62ae);font-weight:600;margin-bottom:8px;">'+PROGRAM_TITLE+'</div>'+
      (MODULE_DESC?'<div style="font-size:14px;color:var(--text-secondary,#3d5269);line-height:1.6;">'+MODULE_DESC+'</div>':'')+
    '</div></div>'+
  '<div style="max-width:800px;margin:0 auto;padding:0 20px 40px;">'+
    '<div class="steps-section"><div class="steps-heading">\u041e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u044d\u0442\u0430\u043f\u044b</div><div class="steps-list">'+mainHtml+'</div>'+practiceHtml+finalHtml+'</div>'+
    '<div class="finish-section">'+fin+'</div></div>';
}

/* ══════════════════════════════════════ */
async function initLearn(){
  var r=await fetch('/api/modules/'+MODULE_PK+'/steps/');
  var d=await r.json();
  allSteps=d.steps.filter(function(s){return s.is_active;});
  loadDone();
  checkQuizReturn();
  try{var pr=await fetch('/api/progress/module/'+MODULE_PK+'/');if(pr.ok){var pd=await pr.json();if(pd.steps)Object.entries(pd.steps).forEach(function(e){var id=parseInt(e[0]),info=e[1];if(info.status==='completed'||info.status==='graded'){var idx=allSteps.findIndex(function(s){return s.id===id;});if(idx!==-1)doneSet.add(idx);}});}}catch(e){}
  saveDone(); renderPage();
}
initLearn();
