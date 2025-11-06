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
    this.uploadedImages = []; // Track uploaded images for this session
    
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
          <div id="chat-image-preview" class="chat-image-preview" style="display: none;">
            <img id="chat-preview-img" alt="Preview">
            <button class="chat-preview-remove" id="chat-remove-image">✕</button>
            <div class="chat-preview-name" id="chat-preview-name"></div>
          </div>
          <div class="chat-input-wrapper">
            <button class="chat-attach-btn" id="chat-attach-btn" title="Прикрепить изображение">
              📎
            </button>
            <input 
              type="file" 
              id="chat-file-input" 
              accept="image/jpeg,image/jpg,image/png,image/webp,image/gif" 
              style="display: none;"
            >
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
    this.attachBtn = document.getElementById('chat-attach-btn');
    this.fileInput = document.getElementById('chat-file-input');
    this.imagePreview = document.getElementById('chat-image-preview');
    this.previewImg = document.getElementById('chat-preview-img');
    this.previewName = document.getElementById('chat-preview-name');
    this.removeImageBtn = document.getElementById('chat-remove-image');
    
    // Current image state
    this.currentImage = null;
    
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
      this.sendBtn.disabled = !this.input.value.trim() && !this.currentImage;
    });
    
    // Attach button click
    this.attachBtn.addEventListener('click', () => {
      this.fileInput.click();
    });
    
    // File input change
    this.fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        this.handleFileSelect(file);
      }
    });
    
    // Remove image button
    this.removeImageBtn.addEventListener('click', () => {
      this.clearImage();
    });
    
    // Paste event for clipboard images (like Cursor chat)
    this.input.addEventListener('paste', (e) => {
      this.handlePaste(e);
    });
  }
  
  setWebSocketClient(wsClient) {
    this.wsClient = wsClient;
  }
  
  async sendMessage() {
    const text = this.input.value.trim();
    const hasImage = this.currentImage !== null;
    
    if (!text && !hasImage) return;
    
    // If there's an image, upload it first
    if (hasImage) {
      try {
        const imageId = await this.uploadImage(this.currentImage.file);
        
        // Add image reference to message
        const messageText = text || 'Проанализируй это изображение';
        const messageWithImage = `[image:${imageId}] ${messageText}`;
        
        // Add user message with image preview to UI
        this.addMessage({
          role: 'user',
          content: messageText,
          timestamp: new Date(),
          image: this.currentImage.dataUrl,
          imageId: imageId
        });
        
        // Send via WebSocket
        if (this.wsClient) {
          this.wsClient.send(messageWithImage);
        }
        
        // Clear image
        this.clearImage();
      } catch (error) {
        console.error('Failed to upload image:', error);
        this.addSystemMessage(`Ошибка загрузки изображения: ${error.message}`);
        return;
      }
    } else {
      // Text-only message
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
    }
    
    // Clear input
    this.input.value = '';
    this.input.style.height = 'auto';
    this.sendBtn.disabled = true;
    
    // Show typing indicator
    this.showTyping();
  }
  
  async handleFileSelect(file) {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'];
    if (!validTypes.includes(file.type)) {
      this.addSystemMessage('Неподдерживаемый формат изображения. Используйте JPG, PNG, WEBP или GIF.');
      return;
    }
    
    // Validate file size (5MB max)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      this.addSystemMessage('Изображение слишком большое. Максимальный размер: 5MB.');
      return;
    }
    
    // Generate friendly name for pasted images (if no name or generic blob name)
    let fileName = file.name;
    if (!fileName || fileName === 'image.png' || fileName === 'blob') {
      const ext = file.type.split('/')[1] || 'png';
      const timestamp = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
      fileName = `Скриншот ${timestamp}.${ext}`;
    }
    
    // Read file as data URL for preview
    const reader = new FileReader();
    reader.onload = (e) => {
      this.currentImage = {
        file: file,
        dataUrl: e.target.result,
        name: fileName
      };
      
      // Show preview
      this.showImagePreview();
      
      // Enable send button
      this.sendBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }
  
  showImagePreview() {
    if (!this.currentImage) return;
    
    this.previewImg.src = this.currentImage.dataUrl;
    this.previewName.textContent = this.currentImage.name;
    this.imagePreview.style.display = 'flex';
  }
  
  clearImage() {
    this.currentImage = null;
    this.imagePreview.style.display = 'none';
    this.fileInput.value = '';
    this.sendBtn.disabled = !this.input.value.trim();
  }
  
  async uploadImage(file) {
    const agentUrl = window.INFRAZEN_DATA?.agentServiceUrl || 'http://127.0.0.1:8001';
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${agentUrl}/v1/chat/upload`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Failed to upload image');
    }
    
    const data = await response.json();
    return data.image_id;
  }
  
  handlePaste(e) {
    // Check if clipboard contains image data
    const items = e.clipboardData?.items;
    if (!items) return;
    
    // Look for image in clipboard
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      
      // Check if item is an image
      if (item.type.indexOf('image') !== -1) {
        // Prevent default paste behavior for images
        e.preventDefault();
        
        // Get image file from clipboard
        const file = item.getAsFile();
        if (file) {
          console.log('Image pasted from clipboard:', file.type, file.size);
          this.handleFileSelect(file);
        }
        
        // Only handle first image
        break;
      }
    }
    // If no image found, allow default paste behavior (text)
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
    
    // Format content based on role
    const formattedContent = message.role === 'assistant' 
      ? this.formatMarkdown(message.content)
      : this.escapeHtml(message.content);
    
    // Build message HTML
    let messageHTML = '';
    
    // Add image if present (for user messages with uploads)
    if (message.image) {
      messageHTML += `
        <div class="chat-message-image">
          <img src="${message.image}" alt="Uploaded image" onclick="window.open(this.src, '_blank')">
        </div>
      `;
    }
    
    messageHTML += `<div class="chat-message-content">${formattedContent}</div>`;
    messageHTML += `<div class="chat-message-timestamp">${timestamp}</div>`;
    
    messageEl.innerHTML = messageHTML;
    
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
  
  formatMarkdown(text) {
    // Escape HTML first
    let html = this.escapeHtml(text);
    
    // Convert markdown to HTML
    // Bold: **text** -> <strong>text</strong>
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Numbered lists: preserve line breaks before numbers
    html = html.replace(/\n(\d+)\./g, '\n\n$1.');
    
    // Line breaks: \n -> <br>
    html = html.replace(/\n/g, '<br>');
    
    // Add spacing after list items for readability
    html = html.replace(/(\d+\.\s.+?)<br>/g, '$1<br><br>');
    
    return html;
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

