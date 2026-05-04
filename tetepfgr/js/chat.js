// ============================================
// CHAT MODE LOGIC - Полноэкранный чат как DeepSeek
// ============================================

// Глобальное состояние
let currentChatId = null;
// Используем isAIMode из admin.html, не создаём новую переменную
let chatHistory = [];

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadChatsFromStorage();
    setupChatEventListeners();
});

// Настройка обработчиков событий
function setupChatEventListeners() {
    // Обработчик ESC для выхода из чата
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isAIMode) {
            toggleChatMode();
        }
    });
}

// Переключение режима чата
function toggleChatMode() {
    isAIMode = !isAIMode;
    
    const contentWrapper = document.querySelector('.content-wrapper');
    const chatMode = document.getElementById('chat-mode-container');
    const tocNav = document.querySelector('.toc-nav');
    const searchContainer = document.querySelector('.search-container');
    const sidebarTitle = document.querySelector('.sidebar-title');
    const aiBtn = document.querySelector('.ai-toggle-btn');
    
    if (isAIMode) {
        // Включаем режим чата
        contentWrapper.style.display = 'none';
        chatMode.style.display = 'flex';
        
        // Меняем содержимое сайдбара на историю чатов
        tocNav.style.display = 'none';
        sidebarTitle.textContent = 'Чаты';
        
        // Добавляем кнопку "Новый чат" в sidebar
        if (!document.getElementById('new-chat-btn-container')) {
            const newChatBtn = document.createElement('button');
            newChatBtn.id = 'new-chat-btn-container';
            newChatBtn.className = 'new-chat-btn';
            newChatBtn.onclick = createNewChat;
            newChatBtn.textContent = '🆕 Новый чат';
            // Убираем inline стили - используем CSS класс
            searchContainer.after(newChatBtn);
        }
        
        // Добавляем контейнер истории чатов
        if (!document.getElementById('chat-history-list')) {
            const chatHistoryDiv = document.createElement('div');
            chatHistoryDiv.id = 'chat-history-list';
            chatHistoryDiv.className = 'chat-history';
            chatHistoryDiv.innerHTML = '<div class="history-group"><h3>Сегодня</h3></div>';
            tocNav.after(chatHistoryDiv);
        }
        
        // Добавляем кнопку очистки истории
        if (!document.getElementById('clear-history-btn')) {
            const clearBtn = document.createElement('button');
            clearBtn.id = 'clear-history-btn';
            clearBtn.className = 'clear-history-btn';
            clearBtn.onclick = clearAllHistory;
            clearBtn.textContent = '🗑️ Очистить историю';
            // Убираем inline стили - используем CSS класс
            document.getElementById('chat-history-list').after(clearBtn);
        }
        
        // Подсвечиваем кнопку AI (без галочки)
        if (aiBtn) {
            aiBtn.classList.add('active');
        }
        
        // Рендерим чат если есть активный
        if (currentChatId && chatHistory.find(c => c.id === currentChatId)) {
            renderCurrentChat();
        }
        
        // Фокус на поле ввода
        setTimeout(() => {
            const chatInput = document.getElementById('chat-input');
            if (chatInput) {
                chatInput.focus();
            }
        }, 100);
        
    } else {
        // Возвращаемся к документации
        contentWrapper.style.display = 'block';
        chatMode.style.display = 'none';
        
        // Восстанавливаем навигацию
        tocNav.style.display = 'block';
        sidebarTitle.textContent = 'Содержание';
        
        // Удаляем кнопку "Новый чат"
        const newChatBtn = document.getElementById('new-chat-btn-container');
        if (newChatBtn) {
            newChatBtn.remove();
        }
        
        // Удаляем контейнер истории чатов
        const chatHistoryDiv = document.getElementById('chat-history-list');
        if (chatHistoryDiv) {
            chatHistoryDiv.remove();
        }
        
        // Удаляем кнопку очистки истории
        const clearBtn = document.getElementById('clear-history-btn');
        if (clearBtn) {
            clearBtn.remove();
        }
        
        // Убираем подсветку кнопки AI
        if (aiBtn) {
            aiBtn.classList.remove('active');
        }
    }
}

// Создание нового чата
function createNewChat() {
    const chatId = 'chat_' + Date.now();
    const chat = {
        id: chatId,
        title: 'Новый чат',
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
        messages: []
    };
    
    chatHistory.push(chat);
    saveChatsToStorage();
    switchToChat(chatId);
    renderChatHistory();
}

// Переключение на конкретный чат
function switchToChat(chatId) {
    currentChatId = chatId;
    renderCurrentChat();
    renderChatHistory();
}

// Отображение текущего чата
function renderCurrentChat() {
    const chat = chatHistory.find(c => c.id === currentChatId);
    if (!chat) return;
    
    const messagesContainer = document.getElementById('messages-container');
    
    if (chat.messages.length === 0) {
        // Показываем минимальное приветствие
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <h2 class="welcome-title">НАВИГАТОР.ПГР</h2>
                <p class="welcome-subtitle">Справочная система АСУ ПГР</p>
            </div>
        `;
    } else {
        // Отображаем все сообщения
        messagesContainer.innerHTML = '';
        chat.messages.forEach(msg => {
            addMessageToUI(msg.role, msg.content, msg.metadata);
        });
    }
    
    // Прокрутка вниз
    scrollToBottom();
}

// Добавление сообщения в UI
function addMessageToUI(role, content, metadata = {}) {
    const messagesContainer = document.getElementById('messages-container');
    
    // Убираем welcome message если есть
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    // Рендерим Markdown для ответов бота, экранируем для пользователя
    let contentHTML;
    if (role === 'assistant') {
        // Для бота рендерим Markdown
        contentHTML = `<div class="message-content markdown-body">${marked.parse(content)}</div>`;
    } else {
        // Для пользователя просто экранируем HTML
        contentHTML = `<div class="message-content">${escapeHtml(content)}</div>`;
    }
    
    // Добавляем метаданные для сообщений бота
    if (role === 'assistant' && metadata) {
        let metadataHTML = '<div class="message-metadata">';
        
        // Уверенность в виде прогресс-бара
        if (metadata.confidence !== undefined && metadata.confidence !== null) {
            const confidenceValue = metadata.confidence;
            const confidenceColor = confidenceValue >= 90 ? '#22c55e' : 
                                   confidenceValue >= 70 ? '#eab308' : '#ef4444';
            
            metadataHTML += `
                <div class="confidence-bar-container">
                    <span class="confidence-bar-label">Уверенность: ${confidenceValue}%</span>
                    <div class="confidence-bar-track">
                        <div class="confidence-bar-fill" style="width: ${confidenceValue}%; background-color: ${confidenceColor};"></div>
                    </div>
                </div>
            `;
        }
        
        // Источники
        if (metadata.sources && metadata.sources.length > 0) {
            metadataHTML += `
                <details class="message-sources">
                    <summary>Источники (${metadata.sources.length})</summary>
                    <ul>
                        ${metadata.sources.map(src => {
                            if (typeof src === 'object') {
                                return `<li>${src.file || 'Неизвестный файл'}${src.line ? `, строка ${src.line}` : ''}</li>`;
                            }
                            return `<li>${escapeHtml(src)}</li>`;
                        }).join('')}
                    </ul>
                </details>
            `;
        }
        
        // Кнопки действий
        metadataHTML += `
            <div class="message-actions">
                <button class="action-btn" onclick="rateMessage('${currentChatId}', 'positive')" title="Хороший ответ">👍</button>
                <button class="action-btn" onclick="rateMessage('${currentChatId}', 'negative')" title="Плохой ответ">👎</button>
                <button class="action-btn" onclick="copyMessage('${escapeHtml(content)}')" title="Копировать">📋</button>
            </div>
        `;
        
        metadataHTML += '</div>';
        contentHTML += metadataHTML;
    }
    
    messageDiv.innerHTML = contentHTML;
    messagesContainer.appendChild(messageDiv);
    
    // Прокрутка вниз
    scrollToBottom();
}

// Отправка сообщения
async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const question = chatInput.value.trim();
    
    if (!question) return;
    
    // Если нет активного чата - создаём новый
    if (!currentChatId) {
        createNewChat();
    }
    
    // Очищаем поле ввода
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;
    
    // Добавляем сообщение пользователя
    addMessageToUI('user', question);
    saveMessageToChat(currentChatId, 'user', question);
    
    // Обновляем название чата (если первый вопрос)
    const chat = chatHistory.find(c => c.id === currentChatId);
    if (chat && chat.messages.length === 1) {
        chat.title = question.substring(0, 30) + (question.length > 30 ? '...' : '');
        saveChatsToStorage();
        renderChatHistory();
    }
    
    // Показываем typing indicator
    showTypingIndicator();
    
    try {
        // Получаем историю чата (последние 5 сообщений)
        const history = getCurrentChatHistory(5);
        
        // Отправляем запрос к API
        const response = await fetch('http://localhost:8000/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'change-me-in-production'
            },
            body: JSON.stringify({
                question: question,
                session_id: getSessionId(),
                chat_id: currentChatId,
                history: history
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Убираем typing indicator
        hideTypingIndicator();
        
        // Добавляем ответ бота
        addMessageToUI('assistant', data.answer, {
            sources: data.sources,
            confidence: data.confidence
        });
        
        // Сохраняем ответ
        saveMessageToChat(currentChatId, 'assistant', data.answer, {
            sources: data.sources,
            confidence: data.confidence
        });
        
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        addMessageToUI('assistant', 'Произошла ошибка при обработке вопроса. Попробуйте ещё раз.');
    }
}

// Показать typing indicator
function showTypingIndicator() {
    const messagesContainer = document.getElementById('messages-container');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    messagesContainer.appendChild(typingDiv);
    scrollToBottom();
}

// Скрыть typing indicator
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Получить историю чата (последние N сообщений)
function getCurrentChatHistory(limit = 5) {
    const chat = chatHistory.find(c => c.id === currentChatId);
    if (!chat || !chat.messages) return [];
    
    return chat.messages.slice(-limit).map(msg => ({
        role: msg.role,
        content: msg.content
    }));
}

// Сохранить сообщение в чат
function saveMessageToChat(chatId, role, content, metadata = {}) {
    const chat = chatHistory.find(c => c.id === chatId);
    if (!chat) return;
    
    chat.messages.push({
        role: role,
        content: content,
        metadata: metadata,
        timestamp: new Date().toISOString()
    });
    
    chat.updated = new Date().toISOString();
    saveChatsToStorage();
}

// Отображение истории чатов
function renderChatHistory() {
    const historyList = document.getElementById('chat-history-list');
    if (!historyList) return;
    
    // Группируем чаты по времени
    const grouped = groupChatsByTime(chatHistory);
    
    let html = '';
    
    for (const [groupName, chats] of Object.entries(grouped)) {
        if (chats.length === 0) continue;
        
        html += `<div class="history-group"><h3>${groupName}</h3>`;
        
        chats.forEach(chat => {
            const isActive = chat.id === currentChatId ? 'active' : '';
            html += `
                <div class="chat-item ${isActive}" onclick="switchToChat('${chat.id}')">
                    <span>${escapeHtml(chat.title)}</span>
                    <button class="delete-chat" onclick="event.stopPropagation(); deleteChat('${chat.id}')" title="Удалить чат">🗑️</button>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    historyList.innerHTML = html;
}

// Группировка чатов по времени
function groupChatsByTime(chats) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    
    const groups = {
        'Сегодня': [],
        'Вчера': [],
        'Последние 7 дней': [],
        'Ранее': []
    };
    
    chats.forEach(chat => {
        const chatDate = new Date(chat.updated || chat.created);
        
        if (chatDate >= today) {
            groups['Сегодня'].push(chat);
        } else if (chatDate >= yesterday) {
            groups['Вчера'].push(chat);
        } else if (chatDate >= weekAgo) {
            groups['Последние 7 дней'].push(chat);
        } else {
            groups['Ранее'].push(chat);
        }
    });
    
    return groups;
}

// Удаление чата
function deleteChat(chatId) {
    if (!confirm('Удалить этот чат?')) return;
    
    chatHistory = chatHistory.filter(c => c.id !== chatId);
    saveChatsToStorage();
    
    if (currentChatId === chatId) {
        // Если удалили текущий чат - переключаемся на последний или очищаем
        if (chatHistory.length > 0) {
            currentChatId = chatHistory[chatHistory.length - 1].id;
            renderCurrentChat();
        } else {
            currentChatId = null;
            const messagesContainer = document.getElementById('messages-container');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
            }
        }
        renderChatHistory();
    } else {
        renderChatHistory();
    }
}

// Очистка всей истории
function clearAllHistory() {
    if (!confirm('Удалить ВСЕ чаты? Это действие нельзя отменить.')) return;
    
    chatHistory = [];
    currentChatId = null;
    saveChatsToStorage();
    
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        messagesContainer.innerHTML = '';
    }
    
    renderChatHistory();
}

// Сохранение чатов в LocalStorage
function saveChatsToStorage() {
    localStorage.setItem('ai_chats', JSON.stringify(chatHistory));
}

// Загрузка чатов из LocalStorage
function loadChatsFromStorage() {
    const stored = localStorage.getItem('ai_chats');
    if (stored) {
        try {
            chatHistory = JSON.parse(stored);
            // Удаляем пустые чаты при загрузке
            chatHistory = chatHistory.filter(chat => chat.messages && chat.messages.length > 0);
            if (chatHistory.length > 0) {
                currentChatId = chatHistory[chatHistory.length - 1].id;
            }
            saveChatsToStorage();
        } catch (e) {
            console.error('Error loading chats:', e);
            chatHistory = [];
            currentChatId = null;
        }
    } else {
        chatHistory = [];
        currentChatId = null;
    }
}

// Получить или создать session_id
function getSessionId() {
    let sessionId = localStorage.getItem('session_id');
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('session_id', sessionId);
    }
    return sessionId;
}

// Автоизменение высоты textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    
    // Активация/деактивация кнопки отправки
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.disabled = !textarea.value.trim();
    }
}

// Обработка нажатий клавиш в поле ввода
function handleChatInputKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

// Прокрутка вниз
function scrollToBottom() {
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Копирование сообщения
function copyMessage(content) {
    navigator.clipboard.writeText(content).then(() => {
        // Можно добавить уведомление
        console.log('Сообщение скопировано');
    }).catch(err => {
        console.error('Ошибка копирования:', err);
    });
}

// Оценка сообщения
function rateMessage(chatId, rating) {
    console.log(`Rating: ${rating} for chat ${chatId}`);
    // Здесь можно отправить фидбек на сервер
    // fetch('/api/feedback', { ... })
}

// Экранирование HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

