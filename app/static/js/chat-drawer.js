/**
 * Chat Drawer Component
 * Resizable drawer for recommendation chat
 */

class ChatDrawer {
  constructor() {
    this.overlay = null;
    this.drawer = null;
    this.resizeHandle = null;
    this.isDragging = false;
    this.currentWidth = null;
    this.minWidth = 30; // 30% of viewport
    this.maxWidth = 70; // 70% of viewport
    this.defaultWidth = 40; // 40% of viewport
    this.recommendationId = null;
    this.scenario = 'recommendation';
    this.context = {};
    
    this.init();
  }
  
  init() {
    // Create drawer HTML
    this.createDrawer();
    
    // Load saved width from localStorage
    const savedWidth = localStorage.getItem('chat-drawer-width');
    if (savedWidth) {
      this.currentWidth = parseFloat(savedWidth);
    } else {
      this.currentWidth = this.defaultWidth;
    }
    
    this.updateDrawerWidth();
    
    // Bind event handlers
    this.bindEvents();
  }
  
  createDrawer() {
    // Create overlay
    this.overlay = document.createElement('div');
    this.overlay.className = 'chat-drawer-overlay';
    
    // Create drawer
    this.drawer = document.createElement('div');
    this.drawer.className = 'chat-drawer';
    this.drawer.innerHTML = `
      <div class="chat-drawer-resize-handle"></div>
      <div class="chat-drawer-header">
        <div>
          <div class="chat-drawer-title" id="chat-drawer-title">💬 FinOps консультант</div>
          <div class="chat-drawer-subtitle" id="chat-drawer-subtitle">
            Обсуждаем рекомендацию
          </div>
        </div>
        <button class="chat-drawer-close" aria-label="Закрыть чат">×</button>
      </div>
      <div class="chat-drawer-body" id="chat-drawer-body">
        <!-- Chat UI will be mounted here -->
      </div>
    `;
    
    // Append to body
    document.body.appendChild(this.overlay);
    document.body.appendChild(this.drawer);
    
    // Get references
    this.resizeHandle = this.drawer.querySelector('.chat-drawer-resize-handle');
    this.closeBtn = this.drawer.querySelector('.chat-drawer-close');
    this.body = this.drawer.querySelector('.chat-drawer-body');
    this.subtitle = this.drawer.querySelector('#chat-drawer-subtitle');
    this.titleEl = this.drawer.querySelector('#chat-drawer-title');
  }
  
  bindEvents() {
    // Close button
    this.closeBtn.addEventListener('click', () => this.close());
    
    // Overlay click (close)
    this.overlay.addEventListener('click', () => this.close());
    
    // ESC key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen()) {
        this.close();
      }
    });
    
    // Resize handle drag
    this.resizeHandle.addEventListener('mousedown', (e) => this.startDrag(e));
    document.addEventListener('mousemove', (e) => this.drag(e));
    document.addEventListener('mouseup', () => this.stopDrag());
    
    // Prevent text selection during drag
    this.resizeHandle.addEventListener('dragstart', (e) => e.preventDefault());
  }
  
  open(configOrId, recommendationTitle) {
    const options = typeof configOrId === 'object' && configOrId !== null
      ? configOrId
      : {
          scenario: 'recommendation',
          recommendationId: configOrId,
          title: '💬 FinOps консультант',
          subtitle: recommendationTitle,
          context: {}
        };

    this.scenario = options.scenario || 'recommendation';
    this.recommendationId = options.recommendationId || null;
    this.context = options.context || {};

    if (options.title) {
      this.titleEl.textContent = options.title;
    } else {
      this.titleEl.textContent = '💬 FinOps консультант';
    }

    const subtitleText = options.subtitle
      || (this.scenario === 'analytics' ? 'Анализируем показатели' : recommendationTitle || 'Обсуждаем рекомендацию');
    this.subtitle.textContent = subtitleText;
    
    // Show drawer
    this.overlay.classList.add('active');
    this.drawer.classList.add('active');
    
    // Dispatch custom event for chat UI to initialize
    document.dispatchEvent(new CustomEvent('chat-drawer-opened', {
      detail: {
        scenario: this.scenario,
        recommendationId: this.recommendationId,
        title: options.title,
        subtitle: subtitleText,
        context: this.context
      }
    }));
  }
  
  close() {
    this.overlay.classList.remove('active');
    this.drawer.classList.remove('active');
    
    // Dispatch custom event for chat UI to cleanup
    document.dispatchEvent(new CustomEvent('chat-drawer-closed'));
  }
  
  isOpen() {
    return this.drawer.classList.contains('active');
  }
  
  startDrag(e) {
    this.isDragging = true;
    this.resizeHandle.classList.add('dragging');
    document.body.classList.add('chat-drawer-resizing');
    e.preventDefault();
  }
  
  drag(e) {
    if (!this.isDragging) return;
    
    const viewportWidth = window.innerWidth;
    const mouseX = e.clientX;
    
    // Calculate new width as percentage
    const newWidthPx = viewportWidth - mouseX;
    const newWidthPercent = (newWidthPx / viewportWidth) * 100;
    
    // Clamp between min and max
    this.currentWidth = Math.max(this.minWidth, Math.min(this.maxWidth, newWidthPercent));
    
    this.updateDrawerWidth();
  }
  
  stopDrag() {
    if (!this.isDragging) return;
    
    this.isDragging = false;
    this.resizeHandle.classList.remove('dragging');
    document.body.classList.remove('chat-drawer-resizing');
    
    // Save to localStorage
    localStorage.setItem('chat-drawer-width', this.currentWidth.toString());
  }
  
  updateDrawerWidth() {
    this.drawer.style.width = `${this.currentWidth}vw`;
  }
  
  getBody() {
    return this.body;
  }
  
  getRecommendationId() {
    return this.recommendationId;
  }

  getScenario() {
    return this.scenario;
  }

  getContext() {
    return this.context;
  }
}

// Initialize drawer on page load
let chatDrawer = null;

document.addEventListener('DOMContentLoaded', () => {
  chatDrawer = new ChatDrawer();
});

// Export for use in other scripts
window.ChatDrawer = ChatDrawer;
window.getChatDrawer = () => chatDrawer;

