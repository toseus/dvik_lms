/* person-card.js — Карточка слушателя */

// --- Данные из Django ---
const PROGS = JSON.parse(document.getElementById('programsData').textContent);
let apps = JSON.parse(document.getElementById('ordersData').textContent);
let docs = JSON.parse(document.getElementById('docsData').textContent);
let cenz = JSON.parse(document.getElementById('cenzData').textContent);
let msgs = JSON.parse(document.getElementById('msgsData').textContent);
const personData = JSON.parse(document.getElementById('personData').textContent);
const PROG_CATS = JSON.parse(document.getElementById('programCategoriesData').textContent);
let progTemplates = JSON.parse(document.getElementById('programTemplatesData')?.textContent || '[]');
let currentCat = '';

// --- CSRF ---
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie.split(';').find(c => c.trim().startsWith('csrftoken_lms='))?.split('=')[1] || '';
}

// --- Утилиты ---
const STAR = '<svg viewBox="0 0 20 20"><polygon points="10,2 12.5,7.5 18,8 14,12 15,18 10,15 5,18 6,12 2,8 7.5,7.5"/></svg>';
function sH(c, o) { return `<span class="star ${c}" onclick="${o}">${STAR}</span>`; }
const SC = ['#d4a017', '#c0392b', '#2980b9', '#8e44ad', '#27ae60'];
const SUBS = ['ПК', 'ОС', 'ГС', 'НТ', 'БЦ'];
function addDy(d, n) { const r = new Date(d); r.setDate(r.getDate() + n); return r.toISOString().slice(0, 10); }
function pF(p) { let v = p.price; if (p.dt === 'pct' && p.disc) v -= Math.round(v * p.disc / 100); if (p.dt === 'rub' && p.disc) v -= p.disc; return Math.max(0, v); }
function fS(s) { if (!s) return '\u2014'; const p = s.split('-'); return p[2] + '.' + p[1] + '.' + p[0].slice(2); }
function fD(s) { if (!s) return '\u2014'; const p = s.split('-'); return p[2] + '.' + p[1] + '.' + p[0]; }
function fDs(d) { return d.toLocaleDateString('ru', { day: 'numeric', month: 'short' }); }
function fM(n) { return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }

// --- Lock ---
let locked = true;
function toggleLock() {
    locked = !locked;
    document.getElementById('lockBtn').textContent = locked ? '\uD83D\uDD12' : '\uD83D\uDD13';
    ['fLnR', 'fLnL', 'fFnR', 'fFnL', 'fMid', 'fSnils'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.disabled = locked;
    });
    const dpInp = document.getElementById('dpBirthInp');
    if (dpInp) dpInp.disabled = locked;
}

// --- Datepicker ---
const DP_M = ['\u042F\u043D\u0432', '\u0424\u0435\u0432', '\u041C\u0430\u0440', '\u0410\u043F\u0440', '\u041C\u0430\u0439', '\u0418\u044E\u043D', '\u0418\u044E\u043B', '\u0410\u0432\u0433', '\u0421\u0435\u043D', '\u041E\u043A\u0442', '\u041D\u043E\u044F', '\u0414\u0435\u043A'];
const DP_D = ['\u041F\u043D', '\u0412\u0442', '\u0421\u0440', '\u0427\u0442', '\u041F\u0442', '\u0421\u0431', '\u0412\u0441'];
let dpBirth = personData.dob || '', dpCalY = 1990, dpCalM = 0;
if (dpBirth) { const d = new Date(dpBirth); dpCalY = d.getFullYear(); dpCalM = d.getMonth(); }

function dpMask(inp) {
    let v = inp.value.replace(/\D/g, '');
    if (v.length > 2) v = v.slice(0, 2) + '.' + v.slice(2);
    if (v.length > 5) v = v.slice(0, 5) + '.' + v.slice(5);
    inp.value = v.slice(0, 10);
}
function dpBlur() {
    const v = document.getElementById('dpBirthInp').value, m = v.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (m) dpBirth = `${m[3]}-${m[2]}-${m[1]}`;
}
function dpToggle() {
    const p = document.getElementById('dpBirthPopup');
    if (p.classList.contains('open')) { p.classList.remove('open'); return; }
    if (dpBirth) { const d = new Date(dpBirth); dpCalY = d.getFullYear(); dpCalM = d.getMonth(); }
    dpRender(); p.classList.add('open');
}
function dpRender() {
    const p = document.getElementById('dpBirthPopup'), sel = dpBirth ? new Date(dpBirth + 'T00:00:00') : null, today = new Date();
    today.setHours(0, 0, 0, 0);
    const dim = new Date(dpCalY, dpCalM + 1, 0).getDate(), pdim = new Date(dpCalY, dpCalM, 0).getDate();
    let dow = new Date(dpCalY, dpCalM, 1).getDay(); dow = dow === 0 ? 6 : dow - 1;
    const cells = [];
    for (let i = dow - 1; i >= 0; i--) cells.push({ d: pdim - i, c: 'other' });
    for (let d = 1; d <= dim; d++) {
        const dt = new Date(dpCalY, dpCalM, d), iso = dt.toISOString().slice(0, 10),
            s = sel && dt.getTime() === sel.getTime(), t = dt.getTime() === today.getTime();
        cells.push({ d, c: s ? 'selected' : t ? 'today' : '', iso });
    }
    let n = 1; while (cells.length % 7) cells.push({ d: n++, c: 'other' });
    const mO = DP_M.map((m, i) => `<option value="${i}"${i === dpCalM ? ' selected' : ''}>${m}</option>`).join('');
    p.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px"><button class="dp-cal-nav" onclick="event.stopPropagation();dpCalM--;if(dpCalM<0){dpCalM=11;dpCalY--}dpRender()">\u25C0</button><div style="display:flex;gap:4px;align-items:center"><select onchange="event.stopPropagation();dpCalM=+this.value;dpRender()" style="border:1px solid #ccc;border-radius:4px;padding:2px 4px;font-size:12px;font-weight:600">${mO}</select><input value="${dpCalY}" maxlength="4" style="width:48px;text-align:center;border:1px solid #ccc;border-radius:4px;padding:2px 4px;font-size:12px;font-weight:600" oninput="event.stopPropagation();const y=parseInt(this.value);if(y>1900&&y<2100){dpCalY=y;dpRender()}" onclick="event.stopPropagation()"></div><button class="dp-cal-nav" onclick="event.stopPropagation();dpCalM++;if(dpCalM>11){dpCalM=0;dpCalY++}dpRender()">\u25B6</button></div><div class="dp-grid">${DP_D.map(d => `<div class="dp-hdr">${d}</div>`).join('')}${cells.map(c => c.c === 'other' ? `<div class="dp-day other">${c.d}</div>` : `<div class="dp-day${c.c ? ' ' + c.c : ''}" onclick="event.stopPropagation();dpPick('${c.iso}')">${c.d}</div>`).join('')}</div><div class="dp-foot"><button onclick="event.stopPropagation();dpPick('${today.toISOString().slice(0, 10)}')">\u0421\u0435\u0433\u043E\u0434\u043D\u044F</button><button onclick="event.stopPropagation();document.getElementById('dpBirthPopup').classList.remove('open')">\u0417\u0430\u043A\u0440\u044B\u0442\u044C</button></div>`;
}
function dpPick(iso) {
    dpBirth = iso; const p = iso.split('-');
    document.getElementById('dpBirthInp').value = p[2] + '.' + p[1] + '.' + p[0];
    document.getElementById('dpBirthPopup').classList.remove('open');
}
document.addEventListener('click', e => { if (!e.target.closest('#dpBirthField')) document.getElementById('dpBirthPopup').classList.remove('open'); });

// --- Gender ---
let genderVal = personData.gender || '';
function toggleGender() {
    if (genderVal === '') genderVal = '\u041C';
    else if (genderVal === '\u041C') genderVal = '\u0416';
    else genderVal = '';
    const e = document.getElementById('genderTog');
    e.className = 'gender-tog ' + (genderVal === '' ? 'empty' : genderVal === '\u041C' ? 'm' : 'f');
    e.textContent = genderVal === '' ? '' : genderVal === '\u041C' ? '\u041C' : '\u0416';
}

// --- Accordion ---
function toggleAcc(e, el) { if (e.target.closest('.acc-body')) return; el.classList.toggle('open'); }

// --- Masks ---
function maskSnils(el) {
    let v = el.value.replace(/\D/g, '').slice(0, 11), f = '';
    for (let i = 0; i < v.length; i++) { if (i === 3 || i === 6) f += '-'; if (i === 9) f += ' '; f += v[i]; }
    el.value = f;
}
function maskPhone(el) {
    let v = el.value.replace(/\D/g, '').slice(0, 11), f = '';
    if (v.length > 0) f = '+' + v[0];
    if (v.length > 1) f += '(' + v.slice(1, 4);
    if (v.length > 4) f += ')' + v.slice(4, 7);
    if (v.length > 7) f += '-' + v.slice(7, 9);
    if (v.length > 9) f += '-' + v.slice(9, 11);
    el.value = f;
}

// --- Orders ---
let selIds = new Set();
let selProgs = {};
let mSel = [];
let casesOpen = false;
let docSelIds = new Set();

function calcT(a) { return a.programs.reduce((s, p) => s + pF(p), 0); }
function getSelApps() { return apps.filter(a => selIds.has(a.id)); }
function toggleApp(id) { selIds.has(id) ? selIds.delete(id) : selIds.add(id); render(); }
function selAllApps() { selIds.size === apps.length ? selIds.clear() : apps.forEach(a => selIds.add(a.id)); render(); }

async function addApp() {
    const resp = await fetch(`/api/persons/${personData.id}/orders/create/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    });
    const data = await resp.json();
    if (data.success) {
        apps.push(data.order);
        selIds.add(data.order.id);
        render();
    }
}

function delApp(id, e) {
    e.stopPropagation();
    if (!confirm('\u0423\u0434\u0430\u043B\u0438\u0442\u044C?')) return;
    apps = apps.filter(x => x.id !== id);
    selIds.delete(id);
    render();
}

function render() { renderApps(); renderDet(); renderCenz(); renderDocs(); renderArch(); }

function renderApps() {
    const sorted = [...apps].sort((a, b) => b.id - a.id);
    document.getElementById('appsList').innerHTML = sorted.map(a => {
        const t = calcT(a), on = selIds.has(a.id);
        const bc = a.status === 'draft' ? 'ai-badge-d' : a.status === 'active' ? 'ai-badge-a' : 'ai-badge-c';
        const bt = a.status === 'draft' ? '\u0427\u0435\u0440\u043D\u043E\u0432\u0438\u043A' : a.status === 'active' ? '\u0410\u043A\u0442\u0438\u0432\u043D\u0430' : '\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u0430';
        let dH = '';
        if (a.paid) dH = '<div class="ai-money-debt paid">\u041E\u043F\u043B\u0430\u0447\u0435\u043D\u043E</div>';
        else if (a.debt > 0) dH = `<div class="ai-money-debt unpaid">\u0414\u043E\u043B\u0433 ${fM(a.debt)} \u20BD</div>`;
        return `<div class="ai ${on ? 'sel' : ''}" onclick="toggleApp(${a.id})"><button class="ai-del" onclick="delApp(${a.id},event)">\u2715</button><div><div class="ai-row1"><div class="ai-head"><b>\u2116 ${a.num}</b> | ${fD(a.date)} <span style="color:var(--t3);font-size:9px">${a.programs.length} \u043F\u0440\u043E\u0433\u0440.</span></div><span class="ai-badge ${bc}">${bt}</span></div><div class="ai-row2"><div class="ai-payer">${a.payer || '\u2014'}</div><div class="ai-money"><div class="ai-money-sum">${fM(t)} \u20BD</div>${a.bonus ? `<div class="ai-money-bonus">\u0411\u043E\u043D\u0443\u0441 ${fM(a.bonus)} \u20BD</div>` : ''}${dH}</div></div><div class="ai-row3"><div class="ai-author">${a.author}</div></div></div></div>`;
    }).join('');
}

function getPS(a) { if (!selProgs[a]) selProgs[a] = new Set(); return selProgs[a]; }
function togProg(a, i) { const s = getPS(a); s.has(i) ? s.delete(i) : s.add(i); renderDet(); }
function togAllP(a) { const ap = apps.find(x => x.id === a); if (!ap) return; const s = getPS(a); s.size === ap.programs.length ? s.clear() : ap.programs.forEach((_, i) => s.add(i)); renderDet(); }
async function delSelP(a) { const s = getPS(a); if (!s.size || !confirm('\u0423\u0434\u0430\u043B\u0438\u0442\u044C ' + s.size + '?')) return; const ap = apps.find(x => x.id === a); const ids = [...s].map(i => ap.programs[i].id); await fetch(`/api/orders/${a}/remove-programs/`, { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }, body: JSON.stringify({ ids }) }); ap.programs = ap.programs.filter((_, i) => !s.has(i)); s.clear(); render(); }

function renderDet() {
    const el = document.getElementById('detContent'), sa = getSelApps();
    if (!sa.length) { el.innerHTML = '<div class="empty">\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u0437\u0430\u044F\u0432\u043A\u0438</div>'; return; }
    let html = '';
    sa.forEach(a => {
        const ps = getPS(a.id), tot = calcT(a);
        const hs = !a.programs.length ? 'empty' : ps.size === 0 ? 'empty' : ps.size === a.programs.length ? 'full' : 'partial';
        let rows = a.programs.map((p, i) => {
            const sc = SC[SUBS.indexOf(p.sub)] || '#888', fi = pF(p);
            let dH = '';
            if (p.dt === 'pct' && p.disc) dH = `<span class="disc-cell pct">${p.disc}%</span>`;
            else if (p.dt === 'rub' && p.disc) dH = `<span class="disc-cell rub">${fM(p.disc)} \u20BD</span>`;
            let iss;
            if (p.issuedDate) { iss = `<span class="issue-date">${fS(p.issuedDate)}</span>`; }
            else if (a.payerType === 'ul' && p.grade) { iss = `<span class="issue-ready">\u041D\u0430 \u0432\u044B\u0434\u0430\u0447\u0443</span>`; }
            else if (a.payerType === 'fl' && p.paymentDate && p.grade) { iss = `<span class="issue-ready">\u041D\u0430 \u0432\u044B\u0434\u0430\u0447\u0443</span>`; }
            else { iss = `<span class="issue-no">\u041D\u0435 \u0432\u044B\u0434\u0430\u0432\u0430\u0442\u044C!</span>`; }
            const pC = a.paid ? 'cell-paid' : (a.debt > 0 && fi > 0 ? 'cell-debt' : '');
            const ms = p.moduleStatus;
            const modCell = ms ? `<span title="\u0412\u044B\u0434\u0430\u043D\u043E ${ms.total}, \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u043E ${ms.completed}">${ms.completed}/${ms.total}</span>` : '\u2014';
            const gradeVal = p.manualGrade || '';
            const gradeOpts = ['','5 (\u043E\u0442\u043B.)','4 (\u0445\u043E\u0440.)','3 (\u0443\u0434\u043E\u0432\u043B.)','\u0437\u0430\u0447\u0451\u0442','\u043D\u0435 \u0441\u0434\u0430\u043B'].map(v => `<option value="${v}" ${gradeVal===v?'selected':''}>${v||'\u2014'}</option>`).join('');
            return `<tr class="${ps.has(i) ? 'p-sel' : ''}"><td class="star-cell">${sH(ps.has(i) ? 'star-full' : 'star-empty', 'togProg(' + a.id + ',' + i + ')')}</td><td class="col-sub"><span class="cdot" style="background:${sc}"></span>${p.sub}</td><td class="col-name" title="${p.name}">${p.name}</td><td class="col-df">${fS(p.dateFrom)}</td><td class="col-dt">${fS(p.dateTo)}</td><td class="col-disc">${dH}</td><td class="col-pay r ${pC}">${fi ? fM(fi) + ' \u20BD' : '0 \u20BD'}</td><td class="col-mod">${modCell}</td><td class="col-grade"><select class="grade-sel" onchange="setGrade(${a.id},${i},this.value)">${gradeOpts}</select></td><td class="col-doc">${p.docNum || '\u2014'}</td><td class="col-reg">${p.regNum || '\u2014'}</td><td class="col-iss">${iss}</td></tr>`;
        }).join('');
        const moduleBtn = ps.size === 1 ? `<button class="b" onclick="openModuleAssign(${a.id},${[...ps][0]})">Модули</button>` : '';
        const impBtn = (typeof userRole !== 'undefined' && userRole === 'superadmin' && ps.size === 1) ? `<button class="b" onclick="impersonateAndOpen()">&#128065; Войти как слушатель</button>` : '';
        html += `<div class="ag"><div>\u2116 ${a.num} \u00B7 ${fD(a.date)}<span class="agr">${a.payer}</span></div><div style="display:flex;gap:4px">${ps.size ? `<button class="berr b" onclick="delSelP(${a.id})">\u0423\u0434\u0430\u043B\u0438\u0442\u044C (${ps.size})</button>` : ''}${moduleBtn}${impBtn}<button class="b" onclick="openModal(${a.id})">+ \u041F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0430</button></div></div>`;
        if (a.programs.length) html += `<div style="overflow-x:auto"><table class="pt"><thead><tr><th class="star-cell">${sH('star-' + hs, 'togAllP(' + a.id + ')')}</th><th class="col-sub">\u041F\u043E\u0434\u0440.</th><th class="col-name">\u041F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0430</th><th class="col-df">\u0421</th><th class="col-dt">\u041F\u043E</th><th class="col-disc">\u0421\u043A\u0438\u0434\u043A\u0430</th><th class="col-pay r">\u041A \u043E\u043F\u043B\u0430\u0442\u0435</th><th class="col-mod">\u041C\u043E\u0434\u0443\u043B\u0438</th><th class="col-grade">\u041E\u0446\u0435\u043D\u043A\u0430</th><th class="col-doc">\u2116 \u0441\u0435\u0440\u0442.</th><th class="col-reg">\u0420\u0435\u0433 \u2116</th><th class="col-iss">\u0412\u044B\u0434\u0430\u043D\u043E</th></tr></thead><tbody>${rows}</tbody></table></div>`;
        else html += '<div class="empty" style="padding:8px">\u041D\u0435\u0442 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C</div>';
        html += `<div class="pt-f"><span class="pt-f-t">\u0418\u0442\u043E\u0433\u043E: ${fM(tot)} \u20BD</span></div>`;
    });
    el.innerHTML = html;
}


// --- Docs ---
function togDocSel(id) { docSelIds.has(id) ? docSelIds.delete(id) : docSelIds.add(id); renderDocs(); }
function togAllDocs() { const act = docs.filter(d => !d.archived); if (docSelIds.size === act.length) docSelIds.clear(); else act.forEach(d => docSelIds.add(d.id)); renderDocs(); }

async function archSelDocs() {
    if (!docSelIds.size) return;
    if (!confirm('\u0412 \u0430\u0440\u0445\u0438\u0432: ' + docSelIds.size + ' \u0434\u043E\u043A.?')) return;
    const ids = [...docSelIds];
    const resp = await fetch(`/api/persons/${personData.id}/documents/archive/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_ids: ids })
    });
    const data = await resp.json();
    if (data.success) {
        docs.forEach(d => { if (ids.includes(d.id)) d.archived = true; });
        docSelIds.clear();
        renderDocs(); renderArch();
    }
}

function renderDocs() {
    const act = docs.filter(d => !d.archived);
    const allSel = act.length > 0 && docSelIds.size === act.length;
    const someSel = docSelIds.size > 0 && !allSel;
    const hsCls = allSel ? 'star-full' : someSel ? 'star-partial' : 'star-empty';
    document.getElementById('docSelInfo').textContent = docSelIds.size ? `\u0412\u044B\u0431\u0440\u0430\u043D\u043E: ${docSelIds.size}` : '';
    document.getElementById('docArchBtn').style.display = docSelIds.size ? '' : 'none';
    let h = `<table class="doc-table"><thead><tr><th class="star-cell">${sH(hsCls, 'togAllDocs()')}</th><th>\u0414\u0430\u0442\u0430</th><th>\u0414\u043E\u043A\u0443\u043C\u0435\u043D\u0442</th><th>\u0410\u0432\u0442\u043E\u0440</th></tr></thead><tbody>`;
    act.forEach(d => {
        const sel = docSelIds.has(d.id);
        h += `<tr class="${sel ? 'd-sel' : ''}"><td class="star-cell">${sH(sel ? 'star-full' : 'star-empty', 'togDocSel(' + d.id + ')')}</td><td>${fD(d.date)}</td><td>${d.fileUrl ? `<span class="doc-name-link" onclick="previewDoc(${d.id})">${d.name}</span>` : d.name}</td><td>${d.author}</td></tr>`;
    });
    h += '</tbody></table>';
    if (!act.length) h = '<div class="empty">\u041D\u0435\u0442 \u0434\u043E\u043A\u0443\u043C\u0435\u043D\u0442\u043E\u0432</div>';
    document.getElementById('docsListWrap').innerHTML = h;
}

function previewDoc(id) {
    const d = docs.find(x => x.id === id);
    if (!d || !d.fileUrl) return;
    document.getElementById('previewImg').src = d.fileUrl;
    document.getElementById('previewOv').classList.add('show');
}

async function restDoc(id) {
    const resp = await fetch(`/api/documents/${id}/restore/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    });
    const data = await resp.json();
    if (data.success) {
        const d = docs.find(x => x.id === id);
        if (d) d.archived = false;
        renderDocs(); renderArch();
    }
}

function renderArch() {
    const ar = docs.filter(d => d.archived);
    let h = '<table class="doc-table"><thead><tr><th>\u0414\u0430\u0442\u0430</th><th>\u0414\u043E\u043A\u0443\u043C\u0435\u043D\u0442</th><th>\u0410\u0432\u0442\u043E\u0440</th><th></th></tr></thead><tbody>';
    ar.forEach(d => { h += `<tr><td>${fD(d.date)}</td><td>${d.name}</td><td>${d.author}</td><td><button class="b" style="font-size:9px;padding:1px 4px" onclick="restDoc(${d.id})">\u0412\u0435\u0440\u043D\u0443\u0442\u044C</button></td></tr>`; });
    h += '</tbody></table>';
    if (!ar.length) h = '<div class="empty">\u0410\u0440\u0445\u0438\u0432 \u043F\u0443\u0441\u0442</div>';
    document.getElementById('archContent').innerHTML = h;
}

// --- Doc upload modal ---
let pendingBlobUrl = null, pendingDocType = 'spravka', docRotation = 0;
function openDocModal(input) {
    if (!input.files.length) return;
    const file = input.files[0];
    pendingBlobUrl = URL.createObjectURL(file);
    docRotation = 0;
    document.getElementById('docPreview').innerHTML = `<button class="rotate-btn" onclick="rotatePreview()">\u21BB</button><img src="${pendingBlobUrl}" id="docPreviewImg">`;
    const fname = file.name.toLowerCase();
    let gt = 'other', gn = file.name.replace(/\.[^.]+$/, '');
    if (/справк|spravk|certificate|стаж/i.test(fname)) { gt = 'spravka'; gn = '\u0421\u043F\u0440\u0430\u0432\u043A\u0430 \u043E \u043F\u043B\u0430\u0432\u0430\u043D\u0438\u0438'; }
    else if (/диплом|diplom|пднв|stcw/i.test(fname)) { gt = 'diploma'; gn = '\u0414\u0438\u043F\u043B\u043E\u043C'; }
    document.getElementById('dcName').value = gn;
    pendingDocType = gt;
    document.querySelectorAll('.doc-type-tab').forEach(t => t.classList.remove('on'));
    document.querySelector(`.doc-type-tab[data-type="${gt}"]`)?.classList.add('on');
    document.getElementById('cenzFields').classList.toggle('show', gt === 'spravka');
    ['dcVessel', 'dcFrom', 'dcTo', 'dcTon', 'dcPow'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    document.getElementById('dcAddCenz').checked = true;
    document.getElementById('docModal').classList.add('show');
    input.value = '';
}

function rotatePreview() {
    docRotation = (docRotation + 90) % 360;
    const img = document.getElementById('docPreviewImg');
    if (img) img.style.transform = `rotate(${docRotation}deg)`;
}

function setDocType(type, el) {
    pendingDocType = type;
    document.querySelectorAll('.doc-type-tab').forEach(t => t.classList.remove('on'));
    el.classList.add('on');
    document.getElementById('cenzFields').classList.toggle('show', type === 'spravka');
    const cur = document.getElementById('dcName').value;
    if (!cur || '\u0421\u043F\u0440\u0430\u0432\u043A\u0430 \u043E \u043F\u043B\u0430\u0432\u0430\u043D\u0438\u0438\u0414\u0438\u043F\u043B\u043E\u043C\u0414\u043E\u043A\u0443\u043C\u0435\u043D\u0442'.includes(cur))
        document.getElementById('dcName').value = type === 'spravka' ? '\u0421\u043F\u0440\u0430\u0432\u043A\u0430 \u043E \u043F\u043B\u0430\u0432\u0430\u043D\u0438\u0438' : type === 'diploma' ? '\u0414\u0438\u043F\u043B\u043E\u043C' : '\u0414\u043E\u043A\u0443\u043C\u0435\u043D\u0442';
}

async function confirmDoc() {
    const fileInput = document.getElementById('docFileInput');
    const formData = new FormData();
    // File from blob - need to get from the original input; re-use pending blob
    const blobResp = await fetch(pendingBlobUrl);
    const blob = await blobResp.blob();
    const name = document.getElementById('dcName').value || '\u0414\u043E\u043A\u0443\u043C\u0435\u043D\u0442';
    formData.append('file', blob, name);
    formData.append('title', name);
    formData.append('doc_type', pendingDocType);
    formData.append('rotation', docRotation);
    if (pendingDocType === 'spravka' && document.getElementById('dcAddCenz').checked) {
        formData.append('vessel', document.getElementById('dcVessel').value);
        formData.append('date_from', document.getElementById('dcFrom').value);
        formData.append('date_to', document.getElementById('dcTo').value);
        formData.append('tonnage', document.getElementById('dcTon').value);
        formData.append('power', document.getElementById('dcPow').value);
    }
    const resp = await fetch(`/api/persons/${personData.id}/documents/upload/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: formData
    });
    const data = await resp.json();
    if (data.success) {
        docs.push(data.document);
        if (data.sea_service) cenz.push(data.sea_service);
        document.getElementById('docModal').classList.remove('show');
        if (pendingBlobUrl) URL.revokeObjectURL(pendingBlobUrl);
        pendingBlobUrl = null;
        renderDocs(); renderCenz();
    }
}

function cancelDoc() {
    if (pendingBlobUrl) URL.revokeObjectURL(pendingBlobUrl);
    pendingBlobUrl = null;
    document.getElementById('docModal').classList.remove('show');
}

// --- Cenz ---
let czSel = new Set();
function cDays(f, t) { return Math.max(0, Math.round((new Date(t) - new Date(f)) / 864e5)); }
function dMD(d) { return Math.floor(d / 30) + ' \u043C\u0435\u0441. ' + (d % 30) + ' \u0434\u043D.'; }
function toggleCz(id) { czSel.has(id) ? czSel.delete(id) : czSel.add(id); renderCenz(); }

async function delCz(id) {
    if (!confirm('\u0423\u0434\u0430\u043B\u0438\u0442\u044C?')) return;
    const resp = await fetch(`/api/sea-service/${id}/delete/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCsrfToken() }
    });
    const data = await resp.json();
    if (data.success) {
        cenz = cenz.filter(c => c.id !== id);
        czSel.delete(id);
        renderCenz();
    }
}

function renderCenz() {
    let h = '<div style="padding:4px 8px;display:flex;justify-content:flex-end"><button class="b bp" onclick="openCM()">+ \u0417\u0430\u043F\u0438\u0441\u044C</button></div><table class="cenz-table"><thead><tr><th class="ck"></th><th>\u0421</th><th>\u041F\u043E</th><th>\u0421\u0443\u0434\u043D\u043E</th><th>\u0422\u043E\u043D\u043D\u0430\u0436</th><th>\u041C\u043E\u0449\u043D\u043E\u0441\u0442\u044C</th><th>\u0421\u0440\u043E\u043A</th><th></th></tr></thead><tbody>';
    cenz.forEach(c => {
        const d = cDays(c.dateFrom, c.dateTo);
        h += `<tr class="${czSel.has(c.id) ? 'cz-sel' : ''}"><td class="ck"><input type="checkbox" ${czSel.has(c.id) ? 'checked' : ''} onclick="toggleCz(${c.id})"></td><td>${fS(c.dateFrom)}</td><td>${fS(c.dateTo)}</td><td>${c.vessel}</td><td>${fM(c.tonnage)}</td><td>${fM(c.power)} \u043A\u0412\u0442</td><td>${dMD(d)}</td><td><button class="cenz-del" onclick="delCz(${c.id})">\u2715</button></td></tr>`;
    });
    h += '</tbody></table>';
    if (czSel.size) {
        const td = cenz.filter(c => czSel.has(c.id)).reduce((s, c) => s + cDays(c.dateFrom, c.dateTo), 0);
        h += `<div class="cenz-sum"><span>\u0412\u044B\u0431\u0440\u0430\u043D\u043E (${czSel.size})</span><span>${dMD(td)}</span></div>`;
    }
    const ta = cenz.reduce((s, c) => s + cDays(c.dateFrom, c.dateTo), 0);
    h += `<div class="cenz-sum" style="background:#f0f3f8;color:var(--t2);font-weight:600"><span>\u041E\u0431\u0449\u0438\u0439 \u0446\u0435\u043D\u0437</span><span>${dMD(ta)}</span></div>`;
    document.getElementById('cenzContent').innerHTML = h;
}

function openCM() {
    document.getElementById('cmBody').innerHTML = `<div class="fg"><label>\u0414\u0430\u0442\u0430 \u0441</label><input type="date" id="czF"></div><div class="fg"><label>\u0414\u0430\u0442\u0430 \u043F\u043E</label><input type="date" id="czT"></div><div class="fg"><label>\u0421\u0443\u0434\u043D\u043E</label><input id="czV"></div><div class="fg"><label>\u0422\u043E\u043D\u043D\u0430\u0436</label><input type="number" id="czTn"></div><div class="fg"><label>\u041C\u043E\u0449\u043D\u043E\u0441\u0442\u044C (\u043A\u0412\u0442)</label><input type="number" id="czPw"></div>`;
    document.getElementById('cenzModal').classList.add('show');
}
function closeCM() { document.getElementById('cenzModal').classList.remove('show'); }

async function confirmCM() {
    const f = document.getElementById('czF').value, t = document.getElementById('czT').value, v = document.getElementById('czV').value;
    if (!f || !t || !v) { alert('\u0417\u0430\u043F\u043E\u043B\u043D\u0438\u0442\u0435'); return; }
    const resp = await fetch(`/api/persons/${personData.id}/sea-service/create/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
            vessel_name: v, date_from: f, date_to: t,
            tonnage: +document.getElementById('czTn').value || 0,
            power: +document.getElementById('czPw').value || 0
        })
    });
    const data = await resp.json();
    if (data.success) {
        cenz.push(data.sea_service);
        closeCM(); renderCenz();
    }
}

// --- Tabs ---
function dtSw(el) {
    document.querySelectorAll('.dt').forEach(t => t.classList.remove('on'));
    el.classList.add('on');
    document.querySelectorAll('.dtc').forEach(c => c.classList.remove('on'));
    document.getElementById('dt-' + el.dataset.dt).classList.add('on');
    const tab = el.dataset.dt;
    if (tab === 'gantt') renderG();
    if (tab === 'cenz') renderCenz();
    if (tab === 'docs') renderDocs();
    if (tab === 'arch') renderArch();
}

// --- Gantt ---
function renderG() {
    const w = document.getElementById('ganttW'); const sa = getSelApps(); const all = [];
    const cols = ['#d4a017', '#c0392b', '#2980b9', '#8e44ad', '#27ae60'];
    sa.forEach((a, ai) => {
        a.programs.forEach(p => {
            if (!p.dateFrom || !p.dateTo) return;
            const st = new Date(p.dateFrom), en = new Date(p.dateTo), d = Math.max(1, Math.round((en - st) / 864e5));
            all.push({ label: `${a.num}: ${p.name}`, start: st, end: en, days: d, color: cols[ai % 5] });
        });
    });
    if (!all.length) { w.innerHTML = '<div class="g-empty">\u041D\u0435\u0442 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C</div>'; return; }
    const ad = all.flatMap(p => [p.start, p.end]);
    let mn = new Date(Math.min(...ad)), mx = new Date(Math.max(...ad));
    const dw = mn.getDay(); mn.setDate(mn.getDate() - (dw === 0 ? 6 : dw - 1));
    const dw2 = mx.getDay(); mx.setDate(mx.getDate() + (dw2 === 0 ? 0 : 7 - dw2));
    const td = (mx - mn) / 864e5, wks = Math.ceil(td / 7);
    const wL = [];
    for (let i = 0; i < wks; i++) { const d = new Date(mn); d.setDate(d.getDate() + i * 7); wL.push(d.toLocaleDateString('ru', { day: 'numeric', month: 'short' })); }
    const today = new Date(), tOff = ((today - mn) / 864e5) / td * 100;
    let h = '<div class="gantt"><div class="g-hdr">' + wL.map(x => `<div class="g-wk">${x}</div>`).join('') + '</div>';
    all.forEach(p => {
        const sO = (p.start - mn) / 864e5, l = (sO / td) * 100, wd = (p.days / td) * 100;
        h += `<div class="g-row"><div class="g-lbl" title="${p.label}">${p.label}</div><div class="g-bars">${tOff >= 0 && tOff <= 100 ? `<div class="g-today" style="left:${tOff}%"></div>` : ''}<div class="g-bar" style="left:${l}%;width:${Math.max(wd, 1.2)}%;background:${p.color}">${fDs(p.start)}\u2013${fDs(p.end)}</div></div></div>`;
    });
    w.innerHTML = h + '</div>';
}

// --- Programs modal ---
let modalAid = null;
function openModal(a) {
    modalAid = a; mSel = []; currentCat = '';
    document.getElementById('pSearch').value = '';
    document.getElementById('addToApp').innerHTML = getSelApps().map(x => `<option value="${x.id}" ${x.id === a ? 'selected' : ''}>\u2116 ${x.num}</option>`).join('');
    initCatPanel();
    renderTemplates();
    renderModal();
    document.getElementById('pModal').classList.add('show');
}
function closeModal() { document.getElementById('pModal').classList.remove('show'); }

function initCatPanel() {
    const panel = document.getElementById('catPanel');
    const catCounts = {};
    PROGS.forEach(p => { const c = p.cat || ''; catCounts[c] = (catCounts[c] || 0) + 1; });
    let html = `<div class="cat-item on" data-cat="" onclick="filterByCat('',this)"><span class="cat-name">\u0412\u0441\u0435 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u044B</span><span class="cat-count">${PROGS.length}</span></div>`;
    PROG_CATS.forEach(cat => {
        const cnt = catCounts[cat] || 0;
        html += `<div class="cat-item" data-cat="${cat}" onclick="filterByCat('${cat.replace(/'/g,"\\'")}',this)"><span class="cat-name">${cat}</span><span class="cat-count">${cnt}</span></div>`;
    });
    panel.innerHTML = html;
}

function filterByCat(cat, el) {
    currentCat = cat;
    document.querySelectorAll('#catPanel .cat-item').forEach(c => c.classList.remove('on'));
    if (el) el.classList.add('on');
    renderModal();
}

function renderModal() {
    const q = (document.getElementById('pSearch').value || '').toLowerCase();
    const a = apps.find(x => x.id === (parseInt(document.getElementById('addToApp').value) || modalAid));
    const have = a ? a.programs.map(p => p.catId) : [];
    let list = PROGS.filter(p =>
        (p.code.toLowerCase().includes(q) || p.name.toLowerCase().includes(q)) &&
        !have.includes(p.id) &&
        (!currentCat || p.cat === currentCat)
    );
    list.sort((a, b) => {
        const aS = mSel.includes(a.id) ? 0 : 1;
        const bS = mSel.includes(b.id) ? 0 : 1;
        return aS - bS;
    });
    document.getElementById('pList').innerHTML = list.length
        ? list.map(p => {
            const sel = mSel.includes(p.id);
            return `<div class="si ${sel ? 'on' : ''}" onclick="togM(${p.id})"><div class="si-left"><span class="si-id">[${p.id}]</span><span class="si-code">${p.code || p.name}</span></div><div class="si-right"><span class="si-hours">${p.h} \u0447.</span><span class="si-price">${fM(p.p)} \u20BD</span></div></div>`;
        }).join('')
        : '<div class="empty">\u041D\u0435\u0442 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C</div>';
    const countEl = document.getElementById('pSelCount');
    if (countEl) countEl.textContent = mSel.length ? `\u0412\u044B\u0431\u0440\u0430\u043D\u043E: ${mSel.length}` : '';
    const clearBtn = document.getElementById('pClearBtn');
    if (clearBtn) clearBtn.style.display = mSel.length ? '' : 'none';
}

// --- Шаблоны программ ---
function renderTemplates() {
    const panel = document.getElementById('tplPanel');
    let html = '<div style="padding:4px 2px;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--lbl);letter-spacing:.3px;margin-bottom:4px;">\u0428\u0430\u0431\u043B\u043E\u043D\u044B</div>';
    progTemplates.forEach(t => {
        html += `<div class="tpl-item" onclick="applyTemplate(${t.id})"><button class="tpl-del" onclick="event.stopPropagation();delTemplate(${t.id})">\u2715</button><div class="tpl-name">${t.name}</div><div class="tpl-count">${t.count} \u043F\u0440\u043E\u0433\u0440.</div></div>`;
    });
    html += `<div class="tpl-create"><input id="tplName" placeholder="\u0418\u043C\u044F \u0448\u0430\u0431\u043B\u043E\u043D\u0430..."><button class="b bp" style="width:100%;font-size:10px" onclick="saveTemplate()">\u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C \u0432\u044B\u0431\u0440\u0430\u043D\u043D\u044B\u0435</button></div>`;
    panel.innerHTML = html;
}

function applyTemplate(id) {
    const tpl = progTemplates.find(t => t.id === id);
    if (!tpl || !tpl.programs) return;
    const a = apps.find(x => x.id === (parseInt(document.getElementById('addToApp')?.value) || modalAid));
    const have = a ? a.programs.map(p => Number(p.catId)) : [];
    tpl.programs.forEach(pid => {
        pid = Number(pid);
        if (!PROGS.find(p => Number(p.id) === pid)) return;
        if (mSel.includes(pid)) return;
        if (have.includes(pid)) return;
        mSel.push(pid);
    });
    renderModal();
}

async function saveTemplate() {
    const name = document.getElementById('tplName').value.trim();
    if (!name) { alert('\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0438\u043C\u044F \u0448\u0430\u0431\u043B\u043E\u043D\u0430'); return; }
    if (!mSel.length) { alert('\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u044B'); return; }
    const resp = await fetch('/api/program-templates/create/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, program_ids: mSel })
    });
    const data = await resp.json();
    if (data.success) {
        progTemplates.push(data.template);
        document.getElementById('tplName').value = '';
        renderTemplates();
    }
}

async function delTemplate(id) {
    if (!confirm('\u0423\u0434\u0430\u043B\u0438\u0442\u044C \u0448\u0430\u0431\u043B\u043E\u043D?')) return;
    const resp = await fetch(`/api/program-templates/${id}/delete/`, {
        method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() }
    });
    if (resp.ok) {
        progTemplates = progTemplates.filter(t => t.id !== id);
        renderTemplates();
    }
}
function togM(id) { const i = mSel.indexOf(id); i >= 0 ? mSel.splice(i, 1) : mSel.push(id); renderModal(); }
function clearSelection() { mSel = []; renderModal(); }

async function confirmP() {
    const targetId = parseInt(document.getElementById('addToApp').value) || modalAid;
    const a = apps.find(x => x.id === targetId);
    if (!a || !mSel.length) return;
    const resp = await fetch(`/api/orders/${targetId}/add-program/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ program_ids: mSel })
    });
    const data = await resp.json();
    if (data.success && data.programs) {
        data.programs.forEach(p => a.programs.push(p));
        closeModal(); render();
    }
}

// --- Messages ---
function renderMsgs() {
    document.getElementById('msgList').innerHTML = msgs.filter(m => !m.pinned).map(m => `<div class="msg ${m.own ? 'own' : ''}"><div class="msg-av c${m.c}">${m.ini}</div><div class="msg-bd"><div class="msg-nm">${m.who}</div><div class="msg-tx">${m.text}</div><div class="msg-tm">${m.time}</div></div><button class="msg-pin" onclick="pinMsg(${m.id})">\uD83D\uDCCC</button></div>`).join('');
    document.getElementById('msgList').scrollTop = 9999;
    renderCases();
}

async function pinMsg(id) {
    const resp = await fetch(`/api/messages/${id}/pin/`, { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() } });
    const data = await resp.json();
    if (data.success) { const m = msgs.find(x => x.id === id); if (m) { m.pinned = true; m.cs = 'active'; } renderMsgs(); }
}

async function unpinMsg(id) {
    const resp = await fetch(`/api/messages/${id}/unpin/`, { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() } });
    const data = await resp.json();
    if (data.success) { const m = msgs.find(x => x.id === id); if (m) { m.pinned = false; m.cs = ''; } renderMsgs(); }
}

async function togCS(id) {
    const resp = await fetch(`/api/messages/${id}/toggle-case-status/`, {
        method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() }
    });
    if (resp.ok) {
        const data = await resp.json();
        const m = msgs.find(x => x.id === id);
        if (m) m.cs = data.status;
        renderCases();
    }
}

function renderCases() {
    const p = msgs.filter(m => m.pinned);
    document.getElementById('caseCount').textContent = p.length;
    const w = document.getElementById('casesWrap');
    if (!p.length) { w.style.display = 'none'; return; }
    w.style.display = '';
    document.getElementById('casesBody').innerHTML = p.map(m => `<div class="case-item"><span class="ca">${m.who}</span><span class="ct">${m.time}</span><span class="case-status ${m.cs === 'archive' ? 'archive' : 'active'}" onclick="togCS(${m.id})">${m.cs === 'archive' ? '\u0410\u0440\u0445\u0438\u0432' : '\u0412 \u0440\u0430\u0431\u043E\u0442\u0435'}</span><button class="cu" onclick="unpinMsg(${m.id})">\u2715</button><div style="margin-top:2px">${m.text}</div></div>`).join('');
}

function toggleCases() {
    casesOpen = !casesOpen;
    document.getElementById('casesBody').classList.toggle('open', casesOpen);
    document.getElementById('casesArrow').textContent = casesOpen ? '\u25BE' : '\u25B8';
}

async function sendMsg() {
    const inp = document.getElementById('msgIn');
    const t = inp.value.trim();
    if (!t) return;
    const resp = await fetch(`/api/persons/${personData.id}/messages/send/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: t })
    });
    const data = await resp.json();
    if (data.success) {
        msgs.push(data.message);
        inp.value = '';
        renderMsgs();
    }
}

// --- Save all ---
async function saveAll() {
    const fields = {};
    document.querySelectorAll('[data-field]').forEach(el => {
        if (el.tagName === 'SELECT') fields[el.dataset.field] = el.value;
        else if (el.tagName === 'TEXTAREA') fields[el.dataset.field] = el.value;
        else fields[el.dataset.field] = el.value;
    });
    fields.dob = dpBirth;
    fields.gender = genderVal;
    const resp = await fetch(`/persons/${personData.id}/save/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(fields)
    });
    const data = await resp.json();
    if (data.ok) {
        const btn = document.querySelector('.hdr .b');
        if (btn) { btn.textContent = '\u2705 \u0421\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u043E'; setTimeout(() => { btn.textContent = '\uD83D\uDCBE \u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C'; }, 1500); }
    }
}

// --- Module Assignment ---
let moduleSelIds = [];
let assignCtx = {};

function openModuleAssign(orderId, progIndex) {
    const a = apps.find(x => x.id === orderId);
    if (!a) return;
    const p = a.programs[progIndex];
    if (!p || !p.catId) return;
    assignCtx = { personId: personData.id, programId: p.catId, programLineId: p.id, orderId: orderId };
    moduleSelIds = [];
    fetch(`/api/training-programs/${p.catId}/modules/`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(data => {
        document.getElementById('moduleModalTitle').textContent = `\u0412\u044B\u0434\u0430\u0442\u044C \u043C\u043E\u0434\u0443\u043B\u0438 \u2014 ${data.program_title || ''}`;
        if (!data.modules.length) {
            document.getElementById('moduleModalBody').innerHTML = '<div class="empty">\u041D\u0435\u0442 \u043C\u043E\u0434\u0443\u043B\u0435\u0439 \u0434\u043B\u044F \u044D\u0442\u043E\u0439 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u044B</div>';
        } else {
            document.getElementById('moduleModalBody').innerHTML = data.modules.map(m =>
                `<div class="si" data-mid="${m.id}" onclick="togModSel(${m.id})"><div class="si-left">${m.cover_image ? `<img src="${m.cover_image}" style="width:36px;height:48px;object-fit:cover;border-radius:3px;margin-right:8px;">` : ''}<div><div class="si-code">${m.title}</div><div style="font-size:9px;color:var(--t3)">${m.steps_count} \u044D\u0442\u0430\u043F\u043E\u0432</div></div></div></div>`
            ).join('');
        }
        document.getElementById('moduleSelCount').textContent = '';
        document.getElementById('moduleModal').classList.add('show');
    }).catch(e => { console.error('Ошибка загрузки модулей:', e); });
}
function togModSel(id) {
    const i = moduleSelIds.indexOf(id); i >= 0 ? moduleSelIds.splice(i, 1) : moduleSelIds.push(id);
    document.querySelectorAll('#moduleModalBody .si').forEach(el => {
        el.classList.toggle('on', moduleSelIds.includes(Number(el.dataset.mid)));
    });
    document.getElementById('moduleSelCount').textContent = moduleSelIds.length ? `\u0412\u044B\u0431\u0440\u0430\u043D\u043E: ${moduleSelIds.length}` : '';
}
function closeModuleModal() { document.getElementById('moduleModal').classList.remove('show'); }
async function confirmAssignModules() {
    if (!moduleSelIds.length) return;
    const resp = await fetch(`/api/persons/${assignCtx.personId}/assign-modules/`, {
        method: 'POST', headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ module_ids: moduleSelIds, program_line_id: assignCtx.programLineId, order_id: assignCtx.orderId })
    });
    const data = await resp.json();
    if (data.success) { closeModuleModal(); render(); }
}

// --- Grade ---
async function setGrade(orderId, progIndex, value) {
    const a = apps.find(x => x.id === orderId);
    if (!a) return;
    const p = a.programs[progIndex];
    if (!p || !p.id) return;
    const resp = await fetch(`/api/program-lines/${p.id}/set-grade/`, {
        method: 'POST', headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ grade: value })
    });
    if (resp.ok) { p.manualGrade = value; p.grade = value; }
}

// --- Impersonation ---
async function impersonateAndOpen() {
    const resp = await fetch(`/api/impersonate/${personData.id}/`, {
        method: 'POST', headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    });
    const data = await resp.json();
    if (data.success) {
        window.open('/learning/', '_blank');
    }
}

// --- Init ---
render();
renderMsgs();
