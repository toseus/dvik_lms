/* ═══════════════════════════════════════════════════════════
   ДВИК СЭО — script.js
═══════════════════════════════════════════════════════════ */
'use strict';

const APP_NAME = 'ДВИК — СЭО';

/* ════════════════════════════════════
   ДЕМО-ПОЛЬЗОВАТЕЛИ
   role: 'student' | 'teacher' | 'admin'
════════════════════════════════════ */
const DEMO_USERS = [
  { login:'morozov',  password:'1234', name:'Морозов Сергей Александрович',  role:'student',  courseIds:['stcw','safety','navigation','radio'] },
  { login:'ivanova',  password:'1234', name:'Иванова Мария Петровна',         role:'student',  courseIds:['stcw','navigation'] },
  { login:'petrov',   password:'1234', name:'Петров Алексей Иванович',         role:'student',  courseIds:['safety','radio'] },
  { login:'sidorov',  password:'1234', name:'Сидоров Дмитрий Олегович',        role:'student',  courseIds:['stcw','safety','navigation'] },
  { login:'kozlova',  password:'1234', name:'Козлова Анна Викторовна',          role:'student',  courseIds:['radio','navigation'] },
  { login:'teacher',  password:'1234', name:'Никитин Владимир Сергеевич',       role:'teacher',  courseIds:['stcw','safety','navigation','radio'] },
  { login:'admin',    password:'1234', name:'Администратор системы',            role:'admin',    courseIds:[] },
];

const ROLE_LABELS = { student:'Слушатель', teacher:'Преподаватель', admin:'Администратор' };

/* ── Аутентификация ── */
function getUser()  { try{ return JSON.parse(sessionStorage.getItem('lms_user')||'null'); }catch{ return null; } }
function setUser(u) { sessionStorage.setItem('lms_user', JSON.stringify(u)); }
function logout()   { sessionStorage.clear(); window.location.href='login.html'; }
function requireAuth() { if(!getUser()) window.location.href='login.html'; }
function hasRole(r) { const u=getUser(); return u && u.role===r; }

/* ── Текущий курс ── */
function setActiveCourse(id) { sessionStorage.setItem('lms_active_course',id); }
function getActiveCourse()   { return sessionStorage.getItem('lms_active_course')||null; }

/* ════════════════════════════════════
   СОСТОЯНИЕ ПРОХОЖДЕНИЯ ШАГОВ
   Хранится отдельно для каждого логина:
   lms_state_<login> = { courseId: { stepIndex: true } }
════════════════════════════════════ */
function _sk(login) { return 'lms_state_'+(login||((getUser()||{}).login)||'anon'); }
function getLmsState(login)     { try{return JSON.parse(sessionStorage.getItem(_sk(login))||'{}');}catch{return{};} }
function saveLmsState(s,login)  { sessionStorage.setItem(_sk(login),JSON.stringify(s)); }

function isStepDone(courseId, stepIdx, login) {
  const s=getLmsState(login);
  return !!(s[courseId]&&s[courseId][stepIdx]);
}
function markStepDone(courseId, stepIdx, login) {
  const key=login||((getUser()||{}).login);
  const s=getLmsState(key);
  if(!s[courseId])s[courseId]={};
  s[courseId][stepIdx]=true;
  saveLmsState(s,key);
}

/* ════════════════════════════════════
   ЗАЧЁТЫ ПРАКТИЧЕСКИХ ЗАНЯТИЙ
   lms_practice = { "courseId_stepIdx_login": true }
════════════════════════════════════ */
function _pk() { return 'lms_practice'; }
function getPracticeState()   { try{return JSON.parse(sessionStorage.getItem(_pk())||'{}');}catch{return{};} }
function savePracticeState(s) { sessionStorage.setItem(_pk(),JSON.stringify(s)); }

function practiceKey(courseId,stepIdx,login) { return courseId+'__'+stepIdx+'__'+login; }

function isPracticeGraded(courseId,stepIdx,login) {
  return !!getPracticeState()[practiceKey(courseId,stepIdx,login)];
}
function gradePractice(courseId,stepIdx,login) {
  const s=getPracticeState();
  s[practiceKey(courseId,stepIdx,login)]=true;
  savePracticeState(s);
  markStepDone(courseId,stepIdx,login);
}
function ungradePractice(courseId,stepIdx,login) {
  const s=getPracticeState();
  delete s[practiceKey(courseId,stepIdx,login)];
  savePracticeState(s);
  const st=getLmsState(login);
  if(st[courseId]){delete st[courseId][stepIdx];saveLmsState(st,login);}
}

/* ════════════════════════════════════
   БАЗА ДАННЫХ КУРСОВ
   Типы шагов: 'online' | 'pdf' | 'test' | 'practice'
   Порядок: обычные → practice → test (последним)
════════════════════════════════════ */
const COURSES = [
  {
    id:'stcw', short:'ПДНВ',
    title:'Подготовка, оценка компетентности и дипломирование моряков',
    author:'Кафедра морского права и менеджмента',
    description:'В соответствии с требованиями правила I/6 Конвенции ПДНВ лица, ответственные за подготовку и оценку компетентности моряков, должны иметь надлежащую квалификацию.',
    assignedDate:'05.02.2026',
    coverColor:'#0f62ae', coverEmoji:'⚓',
    coverBg:'linear-gradient(135deg,#0f62ae 0%,#1a3a6e 100%)',
    steps:[
      {type:'online',  title:'Общие положения и введение в курс',               role:'Экзаменатор', url:'https://example.com/stcw/1'},
      {type:'online',  title:'Пересмотренная конвенция ПДНВ, 1995 год',         role:'Экзаменатор', url:'https://example.com/stcw/2'},
      {type:'online',  title:'Требования к подготовке и дипломированию',        role:'Экзаменатор', url:'https://example.com/stcw/3'},
      {type:'online',  title:'Международные обязательства государств',           role:'Экзаменатор', url:'https://example.com/stcw/4'},
      {type:'online',  title:'Полномочия государств и организаций',              role:'Экзаменатор', url:'https://example.com/stcw/5'},
      {type:'online',  title:'Система качества подготовки',                     role:'Экзаменатор', url:'https://example.com/stcw/6'},
      {type:'online',  title:'Профессиональные дипломы и документы',             role:'Экзаменатор', url:'https://example.com/stcw/7'},
      {type:'online',  title:'Стандарты компетентности',                        role:'Экзаменатор', url:'https://example.com/stcw/8'},
      {type:'pdf',     title:'Методические материалы по оценке компетентности',  role:'Инструктор',  url:'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'},
      {type:'online',  title:'Нормативно-правовое регулирование',               role:'Экзаменатор', url:'https://example.com/stcw/10'},
      {type:'online',  title:'Организация процесса подготовки',                 role:'Экзаменатор', url:'https://example.com/stcw/11'},
      {type:'online',  title:'Документирование результатов оценки',             role:'Экзаменатор', url:'https://example.com/stcw/12'},
      {type:'pdf',     title:'Образцы документов для заполнения',                role:'Инструктор',  url:'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'},
      {type:'online',  title:'Медицинское обеспечение и фитнес-стандарты',      role:'Экзаменатор', url:'https://example.com/stcw/14'},
      {type:'practice',title:'Практическое занятие: оценка компетентности',     role:'Практика',    date:'18.03.2026'},
      {type:'practice',title:'Практическое занятие: оформление документации',   role:'Практика',    date:'25.03.2026'},
      {type:'test',    title:'Итоговая аттестация',                              role:'Тестирование', url:'quest.html'},
    ]
  },
  {
    id:'safety', short:'ОТ и ПБ',
    title:'Охрана труда и безопасность на производстве',
    author:'Кафедра морской безопасности',
    description:'Программа охватывает нормативную базу, организацию рабочих мест, процедуры аварийного реагирования и требования международных стандартов безопасности.',
    assignedDate:'10.02.2026',
    coverColor:'#107c10', coverEmoji:'🛡️',
    coverBg:'linear-gradient(135deg,#107c10 0%,#0a4d0a 100%)',
    steps:[
      {type:'online',  title:'Введение в охрану труда',                         role:'Инструктор', url:'https://example.com/safety/1'},
      {type:'online',  title:'Нормативно-правовая база',                        role:'Инструктор', url:'https://example.com/safety/2'},
      {type:'pdf',     title:'Инструкция по охране труда',                      role:'Инструктор', url:'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'},
      {type:'online',  title:'Аварийное реагирование',                          role:'Инструктор', url:'https://example.com/safety/4'},
      {type:'practice',title:'Практическое занятие: действия при аварии',       role:'Практика',   date:'20.03.2026'},
      {type:'test',    title:'Итоговая аттестация по ОТ и ПБ',                  role:'Тестирование', url:'quest.html'},
    ]
  },
  {
    id:'navigation', short:'Навигация',
    title:'Навигация и управление судном',
    author:'Кафедра судовождения',
    description:'Курс охватывает принципы безопасного судовождения, использование навигационных систем и международные правила предупреждения столкновений.',
    assignedDate:'15.02.2026',
    coverColor:'#a4262c', coverEmoji:'🧭',
    coverBg:'linear-gradient(135deg,#a4262c 0%,#6b1418 100%)',
    steps:[
      {type:'online',  title:'Основы навигации',                                role:'Экзаменатор', url:'https://example.com/nav/1'},
      {type:'online',  title:'МППСС-72',                                        role:'Экзаменатор', url:'https://example.com/nav/2'},
      {type:'pdf',     title:'Навигационные таблицы и карты',                   role:'Инструктор',  url:'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'},
      {type:'practice',title:'Практическое занятие: прокладка курса',           role:'Практика',    date:'22.03.2026'},
      {type:'test',    title:'Итоговая аттестация по навигации',                role:'Тестирование', url:'quest.html'},
    ]
  },
  {
    id:'radio', short:'ГМССБ',
    title:'Глобальная морская система связи при бедствии (ГМССБ)',
    author:'Кафедра связи и навигации',
    description:'Программа включает изучение ГМССБ: оборудование, процедуры, частоты и порядок действий в аварийных ситуациях.',
    assignedDate:'20.02.2026',
    coverColor:'#9a6300', coverEmoji:'📡',
    coverBg:'linear-gradient(135deg,#9a6300 0%,#5c3c00 100%)',
    steps:[
      {type:'online',  title:'Введение в ГМССБ',                                role:'Экзаменатор', url:'https://example.com/gmdss/1'},
      {type:'online',  title:'Оборудование ГМССБ',                              role:'Экзаменатор', url:'https://example.com/gmdss/2'},
      {type:'online',  title:'Процедуры аварийной связи',                       role:'Экзаменатор', url:'https://example.com/gmdss/3'},
      {type:'pdf',     title:'Справочник ГМССБ',                                role:'Инструктор',  url:'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'},
      {type:'practice',title:'Практическое занятие: работа с оборудованием',    role:'Практика',    date:'28.03.2026'},
      {type:'test',    title:'Итоговая аттестация ГМССБ',                       role:'Тестирование', url:'quest.html'},
    ]
  }
];

function getCourseById(id) { return COURSES.find(c=>c.id===id)||null; }

/* ── Список слушателей для курса ── */
function getStudentsForCourse(courseId) {
  return DEMO_USERS.filter(u=>u.role==='student' && u.courseIds.includes(courseId));
}

/* ── Все слушатели ── */
function getAllStudents() {
  return DEMO_USERS.filter(u=>u.role==='student');
}

/* ── Прогресс курса для конкретного слушателя ── */
function getCourseProgressFor(courseId, login) {
  const course=getCourseById(courseId);
  if(!course) return {done:0,total:0,pct:0};
  const total=course.steps.length;
  const s=getLmsState(login);
  const done=s[courseId]?Object.keys(s[courseId]).length:0;
  return {done,total,pct:total?Math.round(done/total*100):0};
}

/* ── Заполнить шапку ── */
function fillHeader() {
  const u=getUser();
  if(!u) return;
  const el=document.getElementById('headerUserName');
  const av=document.getElementById('headerUserAvatar');
  const rl=document.getElementById('headerUserRole');
  if(el) el.textContent=u.name;
  if(av){ const p=u.name.split(' '); av.textContent=p.map(x=>x[0]).join('').slice(0,2).toUpperCase(); }
  if(rl) rl.textContent=ROLE_LABELS[u.role]||u.role;
}
