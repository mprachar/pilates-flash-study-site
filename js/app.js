(function () {
  'use strict';

  // ── STATE ──
  const state = {
    questions: [],
    sections: [],
    selectedSections: new Set(),
    studyMode: 'new', // 'new', 'all', 'missed'
    format: 'quiz', // 'quiz' or 'flash'
    queue: [],
    currentIndex: 0,
    answered: false,
    flashFlipped: false,
    multiSelected: new Set(),
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
  const flashScreen = $('flashScreen');
  const flashCard = $('flashCard');
  const flashProgress = $('flashProgress');
  const flashSection = $('flashSection');
  const flashProgressFill = $('flashProgressFill');
  const flashImage = $('flashImage');
  const flashImg = $('flashImg');
  const flashQuestion = $('flashQuestion');
  const flashBackImage = $('flashBackImage');
  const flashBackImg = $('flashBackImg');
  const flashBackQuestion = $('flashBackQuestion');
  const flashAnswer = $('flashAnswer');
  const flashBtnBack = $('flashBtnBack');
  const flashBtnPrev = $('flashBtnPrev');
  const flashBtnNext = $('flashBtnNext');
  const flashCounterText = $('flashCounterText');
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
    [homeScreen, quizScreen, resultsScreen, flashScreen].forEach((s) => s.classList.add('hidden'));
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
    const isFlash = state.format === 'flash';
    if (count === 0) {
      btnStartQuiz.disabled = true;
      btnStartQuiz.textContent = isFlash ? 'Select sections for flash cards' : 'Select sections to start';
    } else {
      btnStartQuiz.disabled = false;
      const qCount = isFlash ? getAllSectionQuestions().length : getFilteredQuestions().length;
      const label = isFlash ? 'Start Flash Cards' : 'Start Quiz';
      btnStartQuiz.textContent = `${label} (${qCount} card${qCount !== 1 ? 's' : ''})`;
    }
  }

  function getAllSectionQuestions() {
    return state.questions.filter((q) => state.selectedSections.has(q.section));
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
    if (!questions) {
      questions = state.format === 'flash' ? getAllSectionQuestions() : getFilteredQuestions();
    }
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
    state.flashFlipped = false;
    state.session = { correct: 0, total: 0, missed: [], bySection: {} };

    if (state.format === 'flash') {
      showScreen(flashScreen);
      renderFlashcard();
    } else {
      showScreen(quizScreen);
      renderQuestion();
    }
  }

  // ── RENDER QUESTION ──
  function renderQuestion() {
    const q = state.queue[state.currentIndex];
    state.answered = false;
    state.multiSelected = new Set();

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
    const isMulti = q.type === 'multi' && q.correctAnswers.length > 1;
    const questionLabel = isMulti ? q.question + (q.question.includes('Select all') ? '' : ' (Select all that apply)') : q.question;
    questionText.textContent = questionLabel;

    // Answers: shuffle correct + wrong
    const correctSet = new Set(q.correctAnswers.map((a) => a.toLowerCase().trim()));
    const allAnswers = shuffle([
      ...q.correctAnswers.map((a) => ({ text: a, isCorrect: true })),
      ...q.wrongAnswers.map((w) => ({ text: w, isCorrect: false })),
    ]);

    const letters = 'ABCDEFGH'.split('');
    answersContainer.innerHTML = allAnswers
      .map(
        (a, i) => `
      <button class="answer-btn${isMulti ? ' multi-select' : ''}" data-correct="${a.isCorrect}" data-text="${escapeAttr(a.text)}">
        <span class="answer-letter">${letters[i] || ''}</span>
        <span>${escapeHtml(a.text)}</span>
      </button>`
      )
      .join('');

    // Show submit button for multi-select, or direct click for single
    if (isMulti) {
      // Multi-select: toggle selection on click, submit with dedicated button
      answersContainer.querySelectorAll('.answer-btn').forEach((btn) => {
        btn.addEventListener('click', () => toggleMultiSelect(btn));
      });
      btnNext.classList.remove('hidden');
      btnNext.textContent = 'Check Answers';
      btnNext.onclick = () => submitMultiAnswer();
    } else {
      answersContainer.querySelectorAll('.answer-btn').forEach((btn) => {
        btn.addEventListener('click', () => handleAnswer(btn));
      });
      btnNext.classList.add('hidden');
      btnNext.onclick = () => nextQuestion();
    }

    // Hide explanation
    explanation.classList.add('hidden');

    window.scrollTo(0, 0);
  }

  function toggleMultiSelect(btn) {
    if (state.answered) return;
    btn.classList.toggle('selected');
    const text = btn.dataset.text;
    if (state.multiSelected.has(text)) {
      state.multiSelected.delete(text);
    } else {
      state.multiSelected.add(text);
    }
  }

  function submitMultiAnswer() {
    if (state.answered) {
      nextQuestion();
      return;
    }
    state.answered = true;

    const q = state.queue[state.currentIndex];
    const correctSet = new Set(q.correctAnswers.map((a) => a.toLowerCase().trim()));
    const selectedSet = new Set([...state.multiSelected].map((a) => a.toLowerCase().trim()));

    // Check if selection matches exactly
    const allCorrectSelected = q.correctAnswers.every((a) => selectedSet.has(a.toLowerCase().trim()));
    const noWrongSelected = [...state.multiSelected].every((a) => correctSet.has(a.toLowerCase().trim()));
    const isCorrect = allCorrectSelected && noWrongSelected;

    // Mark all buttons
    answersContainer.querySelectorAll('.answer-btn').forEach((b) => {
      b.classList.add('answered');
      if (b.dataset.correct === 'true') b.classList.add('correct');
      // Mark selected wrong ones as incorrect
      if (b.classList.contains('selected') && b.dataset.correct !== 'true') {
        b.classList.add('incorrect');
      }
      b.classList.remove('selected');
    });

    // Session tracking
    state.session.total++;
    if (isCorrect) state.session.correct++;
    else state.session.missed.push(q);

    if (!state.session.bySection[q.section]) {
      state.session.bySection[q.section] = { correct: 0, total: 0 };
    }
    state.session.bySection[q.section].total++;
    if (isCorrect) state.session.bySection[q.section].correct++;

    recordAnswer(q, isCorrect);

    // Show explanation
    const correctList = q.correctAnswers.join(', ');
    explanation.innerHTML = (isCorrect ? '<strong>Correct!</strong> ' : '<strong>Incorrect.</strong> ') + 'The correct answers are: ' + escapeHtml(correctList);
    explanation.classList.remove('hidden');

    // Change button to Next
    btnNext.textContent = state.currentIndex < state.queue.length - 1 ? 'Next Question' : 'See Results';
    btnNext.onclick = () => nextQuestion();

    explanation.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
    const correctText = q.correctAnswers.join(', ');
    explanation.innerHTML = (isCorrect ? '<strong>Correct!</strong> ' : '<strong>Incorrect.</strong> ') + 'The correct answer is: ' + escapeHtml(correctText);
    explanation.classList.remove('hidden');

    // Show next
    btnNext.classList.remove('hidden');
    btnNext.textContent = state.currentIndex < state.queue.length - 1 ? 'Next Question' : 'See Results';
    btnNext.onclick = () => nextQuestion();

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

  // ── FLASHCARD MODE ──
  function renderFlashcard() {
    const q = state.queue[state.currentIndex];
    state.flashFlipped = false;
    flashCard.classList.remove('flipped');

    // Progress
    flashProgress.textContent = `${state.currentIndex + 1} / ${state.queue.length}`;
    flashSection.textContent = sectionName(q.section);
    flashProgressFill.style.width = `${((state.currentIndex + 1) / state.queue.length) * 100}%`;

    // Front: question + image
    if (q.image) {
      flashImg.src = 'images/' + q.image;
      flashImg.alt = 'Diagram for: ' + q.question;
      flashImage.style.display = '';
      flashBackImg.src = 'images/' + q.image;
      flashBackImg.alt = flashImg.alt;
      flashBackImage.style.display = '';
    } else {
      flashImage.style.display = 'none';
      flashBackImage.style.display = 'none';
    }

    flashQuestion.textContent = q.question;

    // Back: question (smaller) + answer
    flashBackQuestion.textContent = q.question;
    flashAnswer.textContent = q.correctAnswers.join(', ');

    // Nav state
    flashBtnPrev.disabled = state.currentIndex === 0;
    flashCounterText.textContent = `Card ${state.currentIndex + 1} of ${state.queue.length}`;

    window.scrollTo(0, 0);
  }

  function flipFlashcard() {
    state.flashFlipped = !state.flashFlipped;
    flashCard.classList.toggle('flipped');
  }

  function flashNext() {
    if (state.currentIndex < state.queue.length - 1) {
      state.currentIndex++;
      renderFlashcard();
    } else {
      renderHome();
    }
  }

  function flashPrev() {
    if (state.currentIndex > 0) {
      state.currentIndex--;
      renderFlashcard();
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

  // Format toggle (Quiz vs Flash Cards)
  const modeToggle = document.querySelector('.mode-toggle');
  document.querySelectorAll('.format-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.format-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.format = btn.id === 'btnFormatFlash' ? 'flash' : 'quiz';
      // Hide mode filter for flash cards (always shows all)
      if (state.format === 'flash') {
        modeToggle.classList.add('hidden');
      } else {
        modeToggle.classList.remove('hidden');
      }
      updateStartButton();
    });
  });

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

  btnNext.addEventListener('click', () => { if (btnNext.onclick) btnNext.onclick(); });

  btnStudyMissedResults.addEventListener('click', () => startQuiz(state.session.missed));
  btnStudyAgain.addEventListener('click', () => startQuiz());
  btnBackHome.addEventListener('click', renderHome);

  // Flashcard events
  flashCard.addEventListener('click', (e) => {
    // Don't flip if tapping an image (let lightbox handle it)
    if (e.target.tagName === 'IMG') return;
    flipFlashcard();
  });
  flashBtnBack.addEventListener('click', () => {
    if (confirm('Leave this session?')) renderHome();
  });
  flashBtnNext.addEventListener('click', flashNext);
  flashBtnPrev.addEventListener('click', flashPrev);
  flashImg.addEventListener('click', (e) => {
    e.stopPropagation();
    openLightbox(flashImg.src, flashImg.alt);
  });
  flashBackImg.addEventListener('click', (e) => {
    e.stopPropagation();
    openLightbox(flashBackImg.src, flashBackImg.alt);
  });

  // Lightbox
  questionImg.addEventListener('click', () => openLightbox(questionImg.src, questionImg.alt));
  lightbox.addEventListener('click', closeLightbox);

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Flashcard mode
    if (!flashScreen.classList.contains('hidden')) {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        flipFlashcard();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        flashNext();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        flashPrev();
      }
      return;
    }

    // Quiz mode
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
      if (btnNext.onclick) btnNext.onclick();
    }
  });

  init();
})();
