/**
 * Chat UI Component
 * Handles message rendering, input, and user interactions
 */

class ChatUI {
  constructor(container) {
    this.container = container;
    this.messages = [];
    this.isTyping = false;
    this.wsClient = null;
    
    this.init();
  }
  
  init() {
    // Create chat UI HTML
    this.container.innerHTML = `
      <div class="chat-container">
        <div class="chat-status" id="chat-status" style="display: none;">
          <span class="chat-status-dot"></span>
          <span id="chat-status-text">Подключение...</span>
        </div>
        <div class="chat-messages" id="chat-messages">
          <div class="chat-empty">
            <div class="chat-empty-icon">💬</div>
            <div class="chat-empty-text">
              Задайте вопрос о рекомендации<br>
              Я помогу разобраться в деталях и рисках
            </div>
          </div>
        </div>
        <div class="chat-input-area">
          <div class="chat-input-wrapper">
            <textarea 
              class="chat-input" 
              id="chat-input" 
              placeholder="Напишите сообщение..."
              rows="1"
            ></textarea>
            <button class="chat-send-btn" id="chat-send-btn" disabled>
              Отправить
            </button>
          </div>
          <div class="chat-input-hint">
            Нажмите Enter для отправки, Shift+Enter для новой строки
          </div>
        </div>
      </div>
    `;
    
    // Get references
    this.messagesContainer = document.getElementById('chat-messages');
    this.input = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('chat-send-btn');
    this.statusBar = document.getElementById('chat-status');
    this.statusText = document.getElementById('chat-status-text');
    
    // Bind events
    this.bindEvents();
  }
  
  bindEvents() {
    // Send button click
    this.sendBtn.addEventListener('click', () => this.sendMessage());
    
    // Enter key to send
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
    
    // Auto-resize textarea
    this.input.addEventListener('input', () => {
      this.input.style.height = 'auto';
      this.input.style.height = this.input.scrollHeight + 'px';
      
      // Enable/disable send button
      this.sendBtn.disabled = !this.input.value.trim();
    });
  }
  
  setWebSocketClient(wsClient) {
    this.wsClient = wsClient;
  }
  
  sendMessage() {
    const text = this.input.value.trim();
    if (!text) return;
    
    // Add user message to UI
    this.addMessage({
      role: 'user',
      content: text,
      timestamp: new Date()
    });
    
    // Send via WebSocket
    if (this.wsClient) {
      this.wsClient.send(text);
    }
    
    // Clear input
    this.input.value = '';
    this.input.style.height = 'auto';
    this.sendBtn.disabled = true;
    
    // Show typing indicator
    this.showTyping();
  }
  
  addMessage(message) {
    // Remove empty state
    const emptyState = this.messagesContainer.querySelector('.chat-empty');
    if (emptyState) {
      emptyState.remove();
    }
    
    this.messages.push(message);
    
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${message.role}`;
    
    const timestamp = this.formatTimestamp(message.timestamp);
    
    messageEl.innerHTML = `
      <div class="chat-message-content">${this.escapeHtml(message.content)}</div>
      <div class="chat-message-timestamp">${timestamp}</div>
    `;
    
    this.messagesContainer.appendChild(messageEl);
    this.scrollToBottom();
  }
  
  showTyping() {
    if (this.isTyping) return;
    
    this.isTyping = true;
    
    const typingEl = document.createElement('div');
    typingEl.className = 'chat-typing';
    typingEl.id = 'chat-typing-indicator';
    typingEl.innerHTML = `
      <div class="chat-typing-dots">
        <span class="chat-typing-dot"></span>
        <span class="chat-typing-dot"></span>
        <span class="chat-typing-dot"></span>
      </div>
      <span class="chat-typing-text">FinOps думает...</span>
    `;
    
    this.messagesContainer.appendChild(typingEl);
    this.scrollToBottom();
  }
  
  hideTyping() {
    const typingEl = document.getElementById('chat-typing-indicator');
    if (typingEl) {
      typingEl.remove();
    }
    this.isTyping = false;
  }
  
  receiveMessage(text) {
    this.hideTyping();
    
    this.addMessage({
      role: 'assistant',
      content: text,
      timestamp: new Date()
    });
  }
  
  addSystemMessage(text) {
    const messageEl = document.createElement('div');
    messageEl.className = 'chat-message system';
    messageEl.innerHTML = `
      <div class="chat-message-content">${this.escapeHtml(text)}</div>
    `;
    
    this.messagesContainer.appendChild(messageEl);
    this.scrollToBottom();
  }
  
  showStatus(status, text) {
    this.statusBar.style.display = 'flex';
    this.statusBar.className = `chat-status ${status}`;
    this.statusText.textContent = text;
    
    // Hide after 3 seconds if connected
    if (status === 'connected') {
      setTimeout(() => {
        this.statusBar.style.display = 'none';
      }, 3000);
    }
  }
  
  hideStatus() {
    this.statusBar.style.display = 'none';
  }
  
  scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    });
  }
  
  formatTimestamp(date) {
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds
    
    if (diff < 60) return 'только что';
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
    
    // Format as time
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  clear() {
    this.messages = [];
    this.messagesContainer.innerHTML = `
      <div class="chat-empty">
        <div class="chat-empty-icon">💬</div>
        <div class="chat-empty-text">
          Задайте вопрос о рекомендации<br>
          Я помогу разобраться в деталях и рисках
        </div>
      </div>
    `;
    this.hideTyping();
  }
  
  loadHistory(messages) {
    this.clear();
    
    messages.forEach(msg => {
      this.addMessage(msg);
    });
  }
}

// Export for use in other scripts
window.ChatUI = ChatUI;

