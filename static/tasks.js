function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const cookie = c.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function urlize(text) {
  if (!text) return '';
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return text.replace(urlRegex, url => {
    const safeUrlText = escapeHtml(url);
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${safeUrlText}</a>`;
  });
}

const csrfToken = getCookie('csrf_token');

function updateTaskInfo(item, state) {
  const infoPanel = document.getElementById('currentTaskInfo');
  const content = document.getElementById('taskInfoContent');
  if (!infoPanel || !content) return;
  if (item) {
    let info = '';
    if (item.itemType === 'lab') {
      info = `
        <div class="mb-2"><strong>Тип:</strong> ${item.type}</div>
        <div class="mb-2"><strong>Сложность:</strong>
          <span class="badge bg-${item.difficulty === 'Легко' ? 'success' : item.difficulty === 'Средне' ? 'warning' : 'danger'}">
            ${item.difficulty}
          </span>
        </div>
        <div class="mb-2"><strong>Статус:</strong>
          ${item.is_solved ? '<span class="text-success">✅ Решена</span>' : '<span class="text-warning">⏳ В процессе</span>'}
        </div>`;
    } else {
      info = `
        <div class="mb-2"><strong>Тип:</strong> ${item.type}</div>
        <div class="mb-2"><strong>Статус:</strong>
          ${item.status === 'approved' ? '<span class="text-success">✅ Решена</span>' :
            item.status === 'pending' ? '<span class="text-warning">⏳ На проверке</span>' :
            '<span class="text-muted">📝 Не решена</span>'}
        </div>`;
    }
    content.innerHTML = info;
    infoPanel.style.display = 'block';
  } else {
    infoPanel.style.display = 'none';
  }
}

function updateButtonState(task) {
  const checkBtn = document.getElementById('checkBtn');
  const checkBtnText = document.getElementById('checkBtnText');
  const btnIcon = document.getElementById('btnIcon');
  const answerInput = document.getElementById('answerInput');
  const clearBtn = document.getElementById('clearBtn');
  const submissionStatus = document.getElementById('submissionStatus');
  if (!checkBtn || !checkBtnText || !btnIcon) return;
  if (task && task.status === 'approved') {
    checkBtn.disabled = true;
    checkBtn.className = 'btn btn-success btn-lg flex-fill custom-submit-btn';
    btnIcon.className = 'fas fa-check';
    checkBtnText.innerHTML = 'Задача решена<br><small class="btn-sub-text">Ответ принят</small>';
    if (answerInput) {
      answerInput.disabled = true;
      answerInput.value = task.approved_answer || '';
    }
    if (clearBtn) clearBtn.disabled = true;
    if (submissionStatus) {
      submissionStatus.className = 'submission-status-wrapper approved';
      submissionStatus.innerHTML = `
        <div class="d-flex align-items-center">
          <i class="fas fa-check-circle me-3 fa-2x"></i>
          <div>
            <strong class="fs-5">Ответ принят</strong><br>
            <span>Ваш ответ был одобрен куратором</span>
          </div>
        </div>`;
      submissionStatus.style.display = 'block';
    }
  } else if (task && task.status === 'pending') {
    checkBtn.disabled = true;
    checkBtn.className = 'btn btn-warning btn-lg flex-fill custom-submit-btn submitted';
    btnIcon.className = 'fas fa-hourglass-half';
    checkBtnText.innerHTML = 'На проверке<br><small class="btn-sub-text">Ожидаем ответа</small>';
    if (answerInput) answerInput.disabled = true;
    if (clearBtn) clearBtn.disabled = true;
    if (submissionStatus) {
      submissionStatus.className = 'submission-status-wrapper pending';
      submissionStatus.innerHTML = `
        <div class="d-flex align-items-center">
          <i class="fas fa-hourglass-half me-3 fa-2x"></i>
          <div>
            <strong class="fs-5">Ответ на проверке</strong><br>
            <span>Куратор рассмотрит ваш ответ в ближайшее время</span>
          </div>
        </div>`;
      submissionStatus.style.display = 'block';
    }
  } else {
    checkBtn.disabled = false;
    checkBtn.className = 'btn btn-primary btn-lg flex-fill custom-submit-btn';
    btnIcon.className = 'fas fa-send';
    checkBtnText.innerHTML = 'Отправить решение<br><small class="btn-sub-text">На проверку куратору</small>';
    if (answerInput) answerInput.disabled = false;
    if (clearBtn) clearBtn.disabled = false;
    if (submissionStatus) submissionStatus.style.display = 'none';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const elements = {
    tasksList: document.getElementById('tasksList'),
    taskContent: document.getElementById('taskContent'),
    noTaskMessage: document.getElementById('noTaskMessage'),
    taskTitle: document.getElementById('taskTitle'),
    taskDescription: document.getElementById('taskDescription'),
    taskType: document.getElementById('taskType'),
    taskStatus: document.getElementById('taskStatus'),
    answerInput: document.getElementById('answerInput'),
    checkBtn: document.getElementById('checkBtn'),
    clearBtn: document.getElementById('clearBtn'),
    btnIcon: document.getElementById('btnIcon'),
    checkBtnText: document.getElementById('checkBtnText'),
    result: document.getElementById('result'),
    btnPractice: document.getElementById('btnPractice'),
    btnTheory: document.getElementById('btnTheory'),
    regularTaskFields: document.getElementById('regularTaskFields'),
    labSpecificContent: document.getElementById('labSpecificContent'),
    charCount: document.getElementById('charCount'),
    submissionStatus: document.getElementById('submissionStatus')
  };

  const missingElements = Object.entries(elements).filter(([key, el]) => !el);
  if (missingElements.length > 0) {
    console.log('Отсутствующие элементы DOM:', missingElements.map(([key]) => key));
  }

  let state = {
    currentTaskId: null,
    currentTaskType: null,
    currentType: 'Теория',
    shouldAutoSelectNext: true,
    loading: false,
    allTasks: [],
    allLabs: [],
    filteredItems: []
  };

  const STATUS_CONFIG = {
    approved: { class: 'status-solved', icon: '✅', text: '✓ ', bgClass: 'solved' },
    pending: { class: 'status-pending', icon: '🟡', text: '⏳ ', bgClass: 'pending' },
    rejected: { class: 'status-rejected', icon: '❌', text: '❌ ', bgClass: 'rejected' },
    not_answered: { class: 'status-not-answered', icon: '⚪', text: '', bgClass: 'not-solved' }
  };

  const DIFFICULTY_CONFIG = {
    'Легко': { class: 'difficulty-easy', badge: 'success' },
    'Средне': { class: 'difficulty-medium', badge: 'warning' },
    'Сложно': { class: 'difficulty-hard', badge: 'danger' }
  };

  if (elements.answerInput && elements.charCount) {
    elements.answerInput.addEventListener('input', function() {
      elements.charCount.textContent = this.value.length;
    });
  }

  if (elements.clearBtn && elements.answerInput) {
    elements.clearBtn.addEventListener('click', function() {
      if (elements.checkBtn && elements.checkBtn.disabled) {
        if (typeof Swal !== 'undefined') {
          Swal.fire({
            title: 'Внимание!',
            text: 'Ответ уже отправлен на проверку. Очистить поле?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Да, очистить',
            cancelButtonText: 'Отмена'
          }).then((result) => {
            if (result.isConfirmed) {
              resetForm();
            }
          });
        } else {
          resetForm();
        }
      } else {
        elements.answerInput.value = '';
        if (elements.charCount) elements.charCount.textContent = '0';
        elements.answerInput.focus();
      }
    });
  }

  function resetForm() {
    if (elements.answerInput) elements.answerInput.value = '';
    if (elements.charCount) elements.charCount.textContent = '0';
    if (elements.checkBtn) elements.checkBtn.disabled = false;
    if (elements.clearBtn) elements.clearBtn.disabled = false;
    if (elements.submissionStatus) elements.submissionStatus.style.display = 'none';
  }

  function showContent(isTask = true) {
    if (elements.taskContent) elements.taskContent.style.display = isTask ? 'block' : 'none';
    if (elements.noTaskMessage) elements.noTaskMessage.style.display = isTask ? 'none' : 'block';
  }

  function clearTaskContent() {
    if (elements.taskTitle) elements.taskTitle.textContent = '';
    if (elements.taskDescription) elements.taskDescription.innerHTML = '';
    if (elements.regularTaskFields) elements.regularTaskFields.style.display = 'none';
    if (elements.labSpecificContent) {
      elements.labSpecificContent.style.display = 'none';
      elements.labSpecificContent.innerHTML = '';
    }
    if (elements.result) elements.result.innerHTML = '';
    if (elements.answerInput) {
      elements.answerInput.value = '';
      elements.answerInput.disabled = false;
    }
    if (elements.checkBtn) elements.checkBtn.disabled = false;
    const checkBtnText = document.getElementById('checkBtnText');
    if (checkBtnText) {
      checkBtnText.innerHTML = 'Отправить решение<br><small class="btn-sub-text">На проверку куратору</small>';
    }
    const answerDiv = document.getElementById('correctAnswer');
    if (answerDiv) answerDiv.style.display = 'none';
  }

  function getStatusInfo(item) {
    const status = item.status || (item.is_solved ? 'approved' : 'not_answered');
    return STATUS_CONFIG[status] || STATUS_CONFIG.not_answered;
  }

  function createTaskButton(item) {
    const btn = document.createElement('button');
    const statusInfo = getStatusInfo(item);
    btn.className = `list-group-item list-group-item-action text-truncate ${statusInfo.class}`;
    btn.dataset.id = item.id;
    btn.dataset.type = item.itemType || 'task';
    if (item.itemType === 'lab') {
      const diffConfig = DIFFICULTY_CONFIG[item.difficulty] || DIFFICULTY_CONFIG['Сложно'];
      btn.classList.add('lab-item', diffConfig.class);
      btn.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
          <div class="d-flex align-items-center">
            <span class="status-icon ${statusInfo.bgClass}">${statusInfo.icon}</span>
            <span class="me-2">🧪</span>
            <div>
              <div class="fw-bold lab-title">${escapeHtml(item.title)}</div>
              <small class="lab-type-badge">${escapeHtml(item.type || 'SQL Injection')}</small>
            </div>
          </div>
          <div>
            <span class="badge bg-${diffConfig.badge}">${item.difficulty}</span>
            ${item.is_solved ? '<span class="badge bg-success ms-1">🏁</span>' : ''}
          </div>
        </div>`;
    } else {
      btn.innerHTML = `
        <div class="d-flex align-items-center">
          <span class="status-icon ${statusInfo.bgClass}">${statusInfo.icon}</span>
          <span class="ms-2">${statusInfo.text}${escapeHtml(item.title)}</span>
        </div>`;
    }
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      state.shouldAutoSelectNext = false;
      if (item.itemType === 'lab') {
        selectLab(item.id);
      } else {
        selectTask(item.id);
      }
    });
    return btn;
  }

  function renderItems() {
    if (!elements.tasksList) {
      console.log('TasksList element not found, skipping render');
      return;
    }

    elements.tasksList.innerHTML = '';
    if (state.currentType === 'Теория') {
      state.filteredItems = state.allTasks.filter(t => t.type === 'Теория');
    } else if (state.currentType === 'Практика') {
      const practicalTasks = state.allTasks.filter(t => t.type === 'Практика');
      const labs = state.allLabs.map(lab => ({
        ...lab,
        itemType: 'lab',
        status: lab.is_solved ? 'approved' : 'not_answered'
      }));
      state.filteredItems = [...practicalTasks, ...labs];
    }

    if (!state.filteredItems.length) {
      showContent(false);
      return;
    }

    const fragment = document.createDocumentFragment();
    let nextItemId = null;
    let currentItemStillExists = false;
    if (state.shouldAutoSelectNext) {
      const nextItem = state.filteredItems.find(item =>
        getStatusInfo(item).bgClass !== 'solved'
      );
      nextItemId = nextItem?.id;
    } else if (state.currentTaskId) {
      currentItemStillExists = state.filteredItems.some(item => item.id === state.currentTaskId);
    }

    state.filteredItems.forEach(item => {
      fragment.appendChild(createTaskButton(item));
    });
    elements.tasksList.appendChild(fragment);

    if (state.shouldAutoSelectNext && nextItemId) {
      const item = state.filteredItems.find(i => i.id === nextItemId);
      if (item?.itemType === 'lab') {
        selectLab(nextItemId);
      } else {
        selectTask(nextItemId);
      }
    } else if (!state.shouldAutoSelectNext && currentItemStillExists) {
      if (state.currentTaskType === 'lab') {
        selectLab(state.currentTaskId);
      } else {
        selectTask(state.currentTaskId);
      }
    } else if (state.filteredItems.length) {
      const firstItem = state.filteredItems[0];
      if (firstItem.itemType === 'lab') {
        selectLab(firstItem.id);
      } else {
        selectTask(firstItem.id);
      }
    } else {
      showContent(false);
    }
  }

  function updateAnswerDisplay(task) {
    let answerDiv = document.getElementById('correctAnswer');
    if (!answerDiv && elements.taskDescription && elements.taskDescription.parentNode) {
      answerDiv = document.createElement('div');
      answerDiv.id = 'correctAnswer';
      answerDiv.className = 'alert mt-3';
      elements.taskDescription.parentNode.insertBefore(answerDiv, elements.taskDescription.nextSibling);
    }
    const statusHandlers = {
      approved: () => {
        if (answerDiv) {
        }
      },
      pending: () => {
        if (answerDiv) {
        }
      },
      rejected: () => {
        if (answerDiv) {
          answerDiv.textContent = 'Ответ отклонён куратором. Попробуйте отправить новый ответ.';
          answerDiv.className = 'alert alert-danger mt-3';
        }
      }
    };
    if (statusHandlers[task.status] && answerDiv) {
      statusHandlers[task.status]();
      answerDiv.style.display = 'block';
    } else if (answerDiv) {
      answerDiv.style.display = 'none';
    }
    if (elements.answerInput) elements.answerInput.value = '';
    if (elements.result) elements.result.innerHTML = '';
    updateButtonState(task);
  }

  function selectTask(id) {
    const task = state.allTasks.find(t => t.id === id);
    if (!task) {
      showContent(false);
      return;
    }
    state.currentTaskId = id;
    state.currentTaskType = 'task';
    showContent(true);
    if (elements.taskTitle) elements.taskTitle.textContent = task.title;
    if (elements.taskDescription) elements.taskDescription.innerHTML = urlize(task.description);
    if (elements.taskType) elements.taskType.textContent = task.type;
    if (elements.taskStatus) {
      const statusText = task.status === 'approved' ? 'Решена' :
                        task.status === 'pending' ? 'На проверке' : 'Не решена';
      elements.taskStatus.textContent = statusText;
    }
    if (elements.regularTaskFields) elements.regularTaskFields.style.display = 'block';
    if (elements.labSpecificContent) elements.labSpecificContent.style.display = 'none';
    updateAnswerDisplay(task);
    updateActiveButton();
    updateTaskInfo(task, state);
  }

  function selectLab(id) {
    const lab = state.allLabs.find(l => l.id === id);
    if (!lab) {
      showContent(false);
      return;
    }
    state.currentTaskId = id;
    state.currentTaskType = 'lab';
    showContent(true);
    const diffConfig = DIFFICULTY_CONFIG[lab.difficulty] || DIFFICULTY_CONFIG['Сложно'];
    if (elements.taskTitle) {
      elements.taskTitle.innerHTML = `🧪 ${lab.title} <span class="badge bg-${diffConfig.badge}">${lab.difficulty}</span>`;
    }
    if (elements.taskType) elements.taskType.textContent = lab.type || 'Лабораторная';
    if (elements.taskStatus) {
      elements.taskStatus.textContent = lab.is_solved ? 'Решена' : 'Не решена';
    }
    if (elements.regularTaskFields) elements.regularTaskFields.style.display = 'none';
    if (elements.labSpecificContent) {
      elements.labSpecificContent.style.display = 'block';
      let content = `
        <div class="lab-description">${urlize(lab.description)}</div>
        <div class="lab-actions">
          <div class="d-flex flex-wrap gap-2 mb-3">
            <a href="${lab.endpoint}" class="btn btn-danger btn-lg lab-endpoint-btn" target="_blank">
              🚀 Открыть лабораторию
            </a>
          </div>
        </div>`;
      if (lab.is_solved) {
        content += `
          <div class="alert alert-success solved-lab">
            <i class="fas fa-check-circle me-2"></i>
            <strong>Лабораторная работа решена!</strong> Вы успешно получили флаг.
          </div>`;
      } else {
        content += `
          <div class="flag-input-group">
            <h5 class="mb-3">🏁 Отправить флаг</h5>
            <div class="row">
              <div class="col-md-8 mb-2">
                <input type="text" class="form-control" id="labFlagInput" placeholder="FLAG{...}" />
              </div>
              <div class="col-md-4">
                <button class="btn btn-success w-100" id="submitLabFlag">Проверить флаг</button>
              </div>
            </div>
            <small class="text-muted mt-2 d-block">
              Флаг имеет формат FLAG{текст}. Скопируйте его точно как найдете в лаборатории.
            </small>
          </div>`;
      }
      elements.labSpecificContent.innerHTML = content;
      if (!lab.is_solved) {
        const submitBtn = document.getElementById('submitLabFlag');
        const flagInput = document.getElementById('labFlagInput');
        if (submitBtn && flagInput) {
          const submitHandler = () => submitLabFlag(id, flagInput.value.trim());
          submitBtn.addEventListener('click', submitHandler);
          flagInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') submitHandler();
          });
        }
      }
    }
    updateActiveButton();
    updateTaskInfo({...lab, itemType: 'lab'}, state);
    if (elements.result) elements.result.innerHTML = '';
    const answerDiv = document.getElementById('correctAnswer');
    if (answerDiv) answerDiv.style.display = 'none';
  }

  async function showNotification(title, message, type = 'info') {
    if (typeof Swal !== 'undefined') {
      const config = {
        title,
        text: message,
        icon: type,
        confirmButtonText: 'ОК'
      };
      if (type === 'success') config.confirmButtonText = 'Отлично!';
      await Swal.fire(config);
    } else {
      console.log(`${title}: ${message}`);
    }
  }

  async function submitLabFlag(labId, flag) {
    if (!flag) {
      showNotification('Ошибка', 'Введите флаг!', 'error');
      return;
    }
    const submitBtn = document.getElementById('submitLabFlag');
    const originalText = submitBtn?.textContent;
    try {
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Проверяем...';
      }
      const response = await fetch(`/lab/${labId}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrfToken,
        },
        body: `flag=${encodeURIComponent(flag)}`,
      });
      const data = await response.json();
      if (data.success) {
        if (elements.result) {
          elements.result.innerHTML = `
            <div class="alert alert-success">
              <i class="fas fa-trophy me-2"></i> ${data.message}
            </div>`;
        }
        showNotification('Поздравляем! 🎉', 'Лабораторная работа успешно решена!', 'success');
        await loadLabs();
        state.shouldAutoSelectNext = false;
        renderItems();
      } else {
        if (elements.result) {
          elements.result.innerHTML = `
            <div class="alert alert-danger">
              <i class="fas fa-times me-2"></i> ${data.message}
            </div>`;
        }
        showNotification('Неверный флаг', data.message, 'error');
      }
    } catch (error) {
      console.error('Error submitting flag:', error);
      if (elements.result) {
        elements.result.innerHTML = `
          <div class="alert alert-danger">
            Ошибка при отправке флага: ${error.message}
          </div>`;
      }
      showNotification('Ошибка', 'Не удалось отправить флаг. Попробуйте позже.', 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText || 'Проверить флаг';
      }
    }
  }

  function updateActiveButton() {
    if (!elements.tasksList) return;
    const buttons = elements.tasksList.querySelectorAll('button');
    buttons.forEach(btn => {
      const btnId = parseInt(btn.dataset.id);
      const btnType = btn.dataset.type;
      const isActive = btnId === state.currentTaskId &&
                      ((state.currentTaskType === 'task' && btnType === 'task') ||
                       (state.currentTaskType === 'lab' && btnType === 'lab'));
      btn.classList.toggle('active', isActive);
    });
  }

  async function fetchData(url, errorMessage) {
    try {
      console.log(`Запрос к: ${url}`);
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error(`Ожидался JSON, но получен: ${text.substring(0, 100)}...`);
        throw new Error('Сервер вернул HTML вместо JSON. Возможно, проблемы с аутентификацией.');
      }

      return await response.json();
    } catch (error) {
      console.error(errorMessage, error);
      throw error;
    }
  }

  async function loadTasks() {
    try {
      console.log('Загрузка задач...');
      const data = await fetchData('/api/tasks', 'Не удалось загрузить задачи');
      state.allTasks = data.tasks || data || [];
      console.log(`Загружено задач: ${state.allTasks.length}`);
    } catch (error) {
      console.log('Ошибка загрузки задач, используется пустой массив');
      state.allTasks = [];
    }
  }

  async function loadLabs() {
    try {
      console.log('Загрузка лабораторий...');
      const data = await fetchData('/api/labs', 'Не удалось загрузить лабораторные');

      if (!data.success) {
        throw new Error(data.message || 'API error');
      }
      state.allLabs = data.labs || [];
      console.log(`Загружено лабораторий: ${state.allLabs.length}`);

      if (state.currentType === 'Практика') {
        renderItems();
      }
    } catch (e) {
      console.log('Ошибка загрузки лабораторий, используется пустой массив');
      state.allLabs = [];
      if (state.currentType === 'Практика') {
        renderItems();
      }
    }
  }

  function switchType(newType, activeBtn, inactiveBtn) {
    if (state.currentType === newType) return;
    state.currentType = newType;
    state.shouldAutoSelectNext = true;
    if (activeBtn) activeBtn.classList.add('active');
    if (inactiveBtn) inactiveBtn.classList.remove('active');
    clearTaskContent();
    renderItems();
  }

  if (elements.btnPractice) {
    elements.btnPractice.addEventListener('click', () =>
      switchType('Практика', elements.btnPractice, elements.btnTheory)
    );
  }
  if (elements.btnTheory) {
    elements.btnTheory.addEventListener('click', () =>
      switchType('Теория', elements.btnTheory, elements.btnPractice)
    );
  }

  if (elements.checkBtn) {
    elements.checkBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      if (!state.currentTaskId || state.currentTaskType !== 'task') {
        showNotification('Ошибка', 'Выберите задачу', 'error');
        return;
      }
      const userAnswer = elements.answerInput.value.trim();
      if (!userAnswer) {
        showNotification('Ошибка', 'Введите ответ', 'error');
        return;
      }

      if (elements.checkBtn) {
        elements.checkBtn.disabled = true;
        elements.checkBtn.classList.add('loading');
      }
      if (elements.btnIcon) elements.btnIcon.className = 'fas fa-spinner';
      if (elements.checkBtnText) elements.checkBtnText.textContent = 'Отправляем...';
      if (elements.result) elements.result.innerHTML = 'Отправляем ответ на проверку...';

      try {
        const response = await fetch(`/task/solve/${state.currentTaskId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({ answer: userAnswer }),
        });

        if (response.ok) {
          const data = await response.json();

          if (elements.checkBtn) {
            elements.checkBtn.classList.remove('loading');
            elements.checkBtn.classList.add('submitted');
          }
          if (elements.btnIcon) elements.btnIcon.className = 'fas fa-hourglass-half';
          if (elements.checkBtnText) {
            elements.checkBtnText.innerHTML = 'На проверке<br><small class="btn-sub-text">Ожидаем ответа</small>';
          }
          if (elements.answerInput) elements.answerInput.disabled = true;
          if (elements.clearBtn) elements.clearBtn.disabled = true;

          if (elements.submissionStatus) {
            elements.submissionStatus.className = 'submission-status-wrapper pending';
            elements.submissionStatus.innerHTML = `
              <div class="d-flex align-items-center">
                <i class="fas fa-hourglass-half me-3 fa-2x"></i>
                <div>
                  <strong class="fs-5">Ответ на проверке</strong><br>
                  <span>Куратор рассмотрит ваш ответ в ближайшее время</span>
                </div>
              </div>`;
            elements.submissionStatus.style.display = 'block';
          }
          if (elements.result) {
            elements.result.innerHTML = `<p class="text-info">${data.message || 'Ответ отправлен на проверку.'}</p>`;
          }
          showNotification('Ответ отправлен!', 'Ваш ответ отправлен на проверку. Результат появится после проверки куратором.', 'success');
          await loadTasks();
          state.shouldAutoSelectNext = false;
          renderItems();
        } else {
          const errorData = await response.json();
          if (elements.result) {
            elements.result.innerHTML = `<p class="text-danger">Ошибка: ${errorData.error || 'неизвестная'}</p>`;
          }

          if (elements.checkBtn) {
            elements.checkBtn.disabled = false;
            elements.checkBtn.classList.remove('loading');
          }
          if (elements.btnIcon) elements.btnIcon.className = 'fas fa-send';
          if (elements.checkBtnText) {
            elements.checkBtnText.innerHTML = 'Отправить решение<br><small class="btn-sub-text">На проверку куратору</small>';
          }
        }
      } catch (err) {
        console.error('Submit error:', err);
        if (elements.result) {
          elements.result.innerHTML = `<p class="text-danger">Ошибка сети: ${err.message}</p>`;
        }

        if (elements.checkBtn) {
          elements.checkBtn.disabled = false;
          elements.checkBtn.classList.remove('loading');
        }
        if (elements.btnIcon) elements.btnIcon.className = 'fas fa-send';
        if (elements.checkBtnText) {
          elements.checkBtnText.innerHTML = 'Отправить решение<br><small class="btn-sub-text">На проверку куратору</small>';
        }
        showNotification('Ошибка', 'Произошла ошибка при отправке ответа. Проверьте соединение и попробуйте еще раз.', 'error');
      }
    });
  }

  window.switchToTheory = () => {
    if (elements.btnTheory) elements.btnTheory.click();
  };
  window.switchToPractice = () => {
    if (elements.btnPractice) elements.btnPractice.click();
  };

  window.updateTaskSubmissionState = function(taskId, taskData) {
    state.currentTaskId = taskId;
    updateButtonState(taskData);
  };

  window.showLabHints = function(labId) {
    const lab = state.allLabs.find(l => l.id === labId);
    if (!lab) return;
    const hints = getLabHints(lab);
    const hintsContent = document.getElementById('labHintsContent');
    if (!hintsContent) {
      showNotification('Подсказки', hints.join('\n\n'), 'info');
      return;
    }
    hintsContent.innerHTML = `
      <h6>Лаборатория: ${escapeHtml(lab.title)}</h6>
      <div class="hints-body">
        ${hints.map(hint => `<div class="hint-item">${escapeHtml(hint)}</div>`).join('')}
      </div>
      <hr>
      <small class="text-muted">
        <strong>Помните:</strong> это обучающая среда. В реальности SQL-инъекции могут причинить серьезный вред!
      </small>`;
    try {
      const modal = new bootstrap.Modal(document.getElementById('labHintsModal'));
      modal.show();
    } catch (e) {
      showNotification('Подсказки', hints.join('\n\n'), 'info');
    }
  };

  function getLabHints(lab) {
    const hintMap = {
      login: [
        "Попробуйте ввести символ ' в поле логина",
        "Используйте SQL комментарии: -- или /**/",
        "Сделайте условие WHERE всегда истинным",
        "Пример: admin' OR '1'='1' --",
        "Попробуйте различные вариации: ' OR 1=1#, admin'--"
      ],
      union: [
        "Определите количество колонок ORDER BY",
        "Используйте UNION SELECT для объединения",
        "Исследуйте таблицы: flags, vulnerable_users",
        "Пример: ' UNION SELECT flag_value, 'desc', 0 FROM flags--"
      ],
      blind: [
        "Используйте условные запросы",
        "Функции SUBSTR(), ASCII(), LENGTH()",
        "Извлекайте флаги посимвольно",
        "Пример: 1 AND SUBSTR((SELECT flag_value FROM flags),1,1)='F'"
      ]
    };
    const endpoint = lab.endpoint.toLowerCase();
    if (endpoint.includes('login') || endpoint.includes('auth')) return hintMap.login;
    if (endpoint.includes('search') || endpoint.includes('union')) return hintMap.union;
    if (endpoint.includes('blind') || endpoint.includes('check')) return hintMap.blind;
    return [
      "Изучите возможные SQL инъекции",
      "Попробуйте различные payload'ы",
      "Обратитесь к куратору за подсказками"
    ];
  }

  async function initialize() {
    try {
      console.log('Инициализация приложения...');
      if (elements.tasksList) {
        await Promise.all([loadTasks(), loadLabs()]);
        renderItems();
      } else {
        console.log('Основные элементы DOM не найдены, пропускаем инициализацию');
      }
    } catch (error) {
      console.error('Ошибка инициализации:', error);
      showContent(false);
    }
  }

  initialize();
});