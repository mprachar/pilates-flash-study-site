(function () {
  'use strict';

  // ── STATE ──
  const state = {
    questions: [],
    sections: [],
    selectedSections: new Set(),
    studyMode: 'new', // 'new', 'all', 'missed'
    queue: [],
    currentIndex: 0,
    answered: false,
    session: { correct: 0, total: 0, missed: [], bySection: {} },
  };

  const STORAGE_KEY = 'pilates-study-progress';

  // ── DOM REFS ──
  const $ = (id) => document.getElementById(id);
  const homeScreen = $('homeScreen');
  const quizScreen = $('quizScreen');
  const resultsScreen = $('resultsScreen');
  const sectionList = $('sectionList');
  const btnStartQuiz = $('btnStartQuiz');
  const btnSelectAll = $('btnSelectAll');
  const btnResetProgress = $('btnResetProgress');
  const btnBack = $('btnBack');
  const btnNext = $('btnNext');
  const quizProgress = $('quizProgress');
  const quizSection = $('quizSection');
  const progressFill = $('progressFill');
  const questionImage = $('questionImage');
  const questionImg = $('questionImg');
  const questionText = $('questionText');
  const answersContainer = $('answersContainer');
  const explanation = $('explanation');
  const resultsPercent = $('resultsPercent');
  const resultsCount = $('resultsCount');
  const resultsBySection = $('resultsBySection');
  const btnStudyMissedResults = $('btnStudyMissedResults');
  const btnStudyAgain = $('btnStudyAgain');
  const btnBackHome = $('btnBackHome');
  const lightbox = $('lightbox');
  const lightboxImg = $('lightboxImg');

  // ── PROGRESS STORAGE ──
  function loadProgress() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : { sections: {} };
    } catch { return { sections: {} }; }
  }

  function saveProgress(progress) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); } catch {}
  }

  function resetProgress() {
    if (confirm('Reset all progress? This cannot be undone.')) {
      localStorage.removeItem(STORAGE_KEY);
      renderHome();
    }
  }

  function recordAnswer(question, isCorrect) {
    const progress = loadProgress();
    if (!progress.sections[question.section]) {
      progress.sections[question.section] = { attempted: 0, correct: 0, answeredIds: [], missedIds: [] };
    }
    const sec = progress.sections[question.section];
    if (!sec.answeredIds.includes(question.id)) {
      sec.attempted++;
      sec.answeredIds.push(question.id);
      if (isCorrect) {
        sec.correct++;
      } else {
        if (!sec.missedIds) sec.missedIds = [];
        sec.missedIds.push(question.id);
      }
    } else {
      // Re-answering: update correctness
      const wasMissed = sec.missedIds && sec.missedIds.includes(question.id);
      if (isCorrect && wasMissed) {
        sec.correct++;
        sec.missedIds = sec.missedIds.filter((id) => id !== question.id);
      } else if (!isCorrect && !wasMissed) {
        sec.correct = Math.max(0, sec.correct - 1);
        if (!sec.missedIds) sec.missedIds = [];
        sec.missedIds.push(question.id);
      }
    }
    saveProgress(progress);
  }

  // ── SHUFFLE ──
  function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // ── SECTION NAME LOOKUP ──
  function sectionName(id) {
    const s = state.sections.find((s) => s.id === id);
    return s ? s.name : id;
  }

  // ── SCREENS ──
  function showScreen(screen) {
    [homeScreen, quizScreen, resultsScreen].forEach((s) => s.classList.add('hidden'));
    screen.classList.remove('hidden');
    window.scrollTo(0, 0);
  }

  // ── RENDER HOME ──
  function renderHome() {
    showScreen(homeScreen);
    const progress = loadProgress();

    sectionList.innerHTML = state.sections
      .map((sec) => {
        const p = progress.sections[sec.id] || { attempted: 0, correct: 0, answeredIds: [], missedIds: [] };
        const pct = sec.questionCount > 0 ? Math.round((p.attempted / sec.questionCount) * 100) : 0;
        const selected = state.selectedSections.has(sec.id) ? 'selected' : '';
        const missedCount = (p.missedIds || []).length;
        const metaParts = [`${sec.questionCount} questions`];
        if (p.attempted > 0) metaParts.push(`${p.correct}/${p.attempted} correct`);
        if (missedCount > 0) metaParts.push(`${missedCount} missed`);

        return `
        <div class="section-card ${selected}" data-section="${sec.id}">
          <div class="section-checkbox">${selected ? '&#10003;' : ''}</div>
          <div class="section-info">
            <div class="section-name">${sec.name}</div>
            <div class="section-meta">${metaParts.join(' &middot; ')}</div>
          </div>
          <div class="section-progress">
            <div class="section-score">${pct}%</div>
            <div class="section-bar"><div class="section-bar-fill" style="width:${pct}%"></div></div>
          </div>
        </div>`;
      })
      .join('');

    // Section click handlers
    sectionList.querySelectorAll('.section-card').forEach((card) => {
      card.addEventListener('click', () => {
        const id = card.dataset.section;
        if (state.selectedSections.has(id)) {
          state.selectedSections.delete(id);
        } else {
          state.selectedSections.add(id);
        }
        renderHome();
      });
    });

    updateStartButton();
  }

  function updateStartButton() {
    const count = state.selectedSections.size;
    if (count === 0) {
      btnStartQuiz.disabled = true;
      btnStartQuiz.textContent = 'Select sections to start';
    } else {
      btnStartQuiz.disabled = false;
      const qCount = getFilteredQuestions().length;
      btnStartQuiz.textContent = `Start (${qCount} question${qCount !== 1 ? 's' : ''})`;
    }
  }

  function getFilteredQuestions() {
    const progress = loadProgress();
    let questions = state.questions.filter((q) => state.selectedSections.has(q.section));

    if (state.studyMode === 'new') {
      questions = questions.filter((q) => {
        const sec = progress.sections[q.section];
        return !sec || !sec.answeredIds || !sec.answeredIds.includes(q.id);
      });
    } else if (state.studyMode === 'missed') {
      questions = questions.filter((q) => {
        const sec = progress.sections[q.section];
        return sec && sec.missedIds && sec.missedIds.includes(q.id);
      });
    }

    return questions;
  }

  // ── START QUIZ ──
  function startQuiz(questions) {
    if (!questions) questions = getFilteredQuestions();
    if (questions.length === 0) {
      alert(
        state.studyMode === 'new'
          ? 'No new questions in selected sections. Try "All Questions" or "Missed Only" mode.'
          : state.studyMode === 'missed'
            ? 'No missed questions in selected sections.'
            : 'No questions found.'
      );
      return;
    }

    state.queue = shuffle(questions);
    state.currentIndex = 0;
    state.answered = false;
    state.session = { correct: 0, total: 0, missed: [], bySection: {} };

    showScreen(quizScreen);
    renderQuestion();
  }

  // ── RENDER QUESTION ──
  function renderQuestion() {
    const q = state.queue[state.currentIndex];
    state.answered = false;

    // Progress
    quizProgress.textContent = `${state.currentIndex + 1} / ${state.queue.length}`;
    quizSection.textContent = sectionName(q.section);
    progressFill.style.width = `${((state.currentIndex + 1) / state.queue.length) * 100}%`;

    // Image
    if (q.image) {
      questionImg.src = 'images/' + q.image;
      questionImg.alt = 'Diagram for: ' + q.question;
      questionImage.style.display = '';
    } else {
      questionImage.style.display = 'none';
    }

    // Question text
    questionText.textContent = q.question;

    // Answers: shuffle correct + wrong
    const allAnswers = shuffle([
      { text: q.correctAnswer, isCorrect: true },
      ...q.wrongAnswers.map((w) => ({ text: w, isCorrect: false })),
    ]);

    const letters = ['A', 'B', 'C', 'D'];
    answersContainer.innerHTML = allAnswers
      .map(
        (a, i) => `
      <button class="answer-btn" data-correct="${a.isCorrect}" data-text="${escapeAttr(a.text)}">
        <span class="answer-letter">${letters[i]}</span>
        <span>${escapeHtml(a.text)}</span>
      </button>`
      )
      .join('');

    // Answer click handlers
    answersContainer.querySelectorAll('.answer-btn').forEach((btn) => {
      btn.addEventListener('click', () => handleAnswer(btn));
    });

    // Hide explanation and next button
    explanation.classList.add('hidden');
    btnNext.classList.add('hidden');

    window.scrollTo(0, 0);
  }

  function handleAnswer(btn) {
    if (state.answered) return;
    state.answered = true;

    const q = state.queue[state.currentIndex];
    const isCorrect = btn.dataset.correct === 'true';

    // Mark all buttons
    answersContainer.querySelectorAll('.answer-btn').forEach((b) => {
      b.classList.add('answered');
      if (b.dataset.correct === 'true') b.classList.add('correct');
    });

    if (!isCorrect) {
      btn.classList.add('incorrect');
    }

    // Session tracking
    state.session.total++;
    if (isCorrect) state.session.correct++;
    else state.session.missed.push(q);

    if (!state.session.bySection[q.section]) {
      state.session.bySection[q.section] = { correct: 0, total: 0 };
    }
    state.session.bySection[q.section].total++;
    if (isCorrect) state.session.bySection[q.section].correct++;

    // Persist
    recordAnswer(q, isCorrect);

    // Show explanation
    if (q.explanation) {
      explanation.innerHTML = (isCorrect ? '<strong>Correct!</strong> ' : '<strong>Incorrect.</strong> ') + escapeHtml(q.explanation);
      explanation.classList.remove('hidden');
    } else {
      explanation.innerHTML = isCorrect ? '<strong>Correct!</strong>' : '<strong>Incorrect.</strong> The answer is: ' + escapeHtml(q.correctAnswer);
      explanation.classList.remove('hidden');
    }

    // Show next
    btnNext.classList.remove('hidden');
    btnNext.textContent = state.currentIndex < state.queue.length - 1 ? 'Next Question' : 'See Results';

    // Scroll to see explanation
    explanation.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function nextQuestion() {
    state.currentIndex++;
    if (state.currentIndex < state.queue.length) {
      renderQuestion();
    } else {
      showResults();
    }
  }

  // ── RESULTS ──
  function showResults() {
    showScreen(resultsScreen);

    const pct = state.session.total > 0 ? Math.round((state.session.correct / state.session.total) * 100) : 0;
    resultsPercent.textContent = pct + '%';
    resultsCount.textContent = `${state.session.correct} of ${state.session.total} correct`;

    // Per-section breakdown
    const sectionIds = Object.keys(state.session.bySection);
    if (sectionIds.length > 1) {
      resultsBySection.innerHTML = sectionIds
        .map((id) => {
          const s = state.session.bySection[id];
          const sp = Math.round((s.correct / s.total) * 100);
          const cls = sp === 100 ? 'perfect' : '';
          return `<div class="result-section-row">
          <span>${sectionName(id)}</span>
          <span class="result-section-score ${cls}">${s.correct}/${s.total} (${sp}%)</span>
        </div>`;
        })
        .join('');
    } else {
      resultsBySection.innerHTML = '';
    }

    // Study missed button
    if (state.session.missed.length > 0) {
      btnStudyMissedResults.classList.remove('hidden');
      btnStudyMissedResults.textContent = `Study ${state.session.missed.length} Missed Question${state.session.missed.length !== 1 ? 's' : ''}`;
    } else {
      btnStudyMissedResults.classList.add('hidden');
    }
  }

  // ── LIGHTBOX ──
  function openLightbox(src, alt) {
    lightboxImg.src = src;
    lightboxImg.alt = alt;
    lightbox.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    lightbox.classList.add('hidden');
    document.body.style.overflow = '';
  }

  // ── HELPERS ──
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── INIT ──
  async function init() {
    try {
      const resp = await fetch('data/questions.json');
      const data = await resp.json();
      state.questions = data.questions;
      state.sections = data.sections;
      renderHome();
    } catch (err) {
      document.body.innerHTML = '<div style="padding:32px;text-align:center;"><h2>Failed to load questions</h2><p>' + err.message + '</p></div>';
    }
  }

  // ── EVENT LISTENERS ──
  btnStartQuiz.addEventListener('click', () => startQuiz());

  btnSelectAll.addEventListener('click', () => {
    if (state.selectedSections.size === state.sections.length) {
      state.selectedSections.clear();
    } else {
      state.sections.forEach((s) => state.selectedSections.add(s.id));
    }
    renderHome();
  });

  btnResetProgress.addEventListener('click', resetProgress);

  // Mode toggle
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.studyMode = btn.id === 'btnStudyNew' ? 'new' : btn.id === 'btnStudyAll' ? 'all' : 'missed';
      updateStartButton();
    });
  });

  btnBack.addEventListener('click', () => {
    if (state.answered || state.currentIndex === 0) {
      if (confirm('Leave this quiz session?')) renderHome();
    } else {
      renderHome();
    }
  });

  btnNext.addEventListener('click', nextQuestion);

  btnStudyMissedResults.addEventListener('click', () => startQuiz(state.session.missed));
  btnStudyAgain.addEventListener('click', () => startQuiz());
  btnBackHome.addEventListener('click', renderHome);

  // Lightbox
  questionImg.addEventListener('click', () => openLightbox(questionImg.src, questionImg.alt));
  lightbox.addEventListener('click', closeLightbox);

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (quizScreen.classList.contains('hidden')) return;

    if (!state.answered) {
      const keyMap = { '1': 0, '2': 1, '3': 2, '4': 3, a: 0, b: 1, c: 2, d: 3 };
      const idx = keyMap[e.key.toLowerCase()];
      if (idx !== undefined) {
        const btns = answersContainer.querySelectorAll('.answer-btn');
        if (btns[idx]) btns[idx].click();
      }
    } else if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowRight') {
      e.preventDefault();
      btnNext.click();
    }
  });

  init();
})();
