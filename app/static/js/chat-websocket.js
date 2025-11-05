/**
 * Real WebSocket Client for Chat
 * Connects to agent service for live chat
 */

class RealWebSocketClient {
  constructor(recommendationId) {
    this.recommendationId = recommendationId;
    this.chatUI = null;
    this.ws = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000; // 2 seconds
    this.token = null;
  }
  
  async connect() {
    try {
      this.chatUI?.showStatus('connecting', 'Подключение...');
      
      // Get JWT token from Flask backend
      const tokenResponse = await fetch('/api/chat/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          recommendation_id: this.recommendationId
        })
      });
      
      if (!tokenResponse.ok) {
        throw new Error(`Failed to get token: ${tokenResponse.statusText}`);
      }
      
      const tokenData = await tokenResponse.json();
      this.token = tokenData.token;
      
      // Get agent service URL from config
      const agentUrl = window.INFRAZEN_DATA?.agentServiceUrl || 'http://127.0.0.1:8001';
      
      // Connect to WebSocket (convert http to ws)
      const wsUrl = agentUrl.replace(/^http/, 'ws');
      const wsEndpoint = `${wsUrl}/v1/chat/rec/${this.recommendationId}?token=${this.token}`;
      
      console.log('Connecting to WebSocket:', wsEndpoint);
      
      this.ws = new WebSocket(wsEndpoint);
      
      // WebSocket event handlers
      this.ws.onopen = () => this.handleOpen();
      this.ws.onmessage = (event) => this.handleMessage(event);
      this.ws.onerror = (error) => this.handleError(error);
      this.ws.onclose = () => this.handleClose();
      
    } catch (error) {
      console.error('Connection error:', error);
      this.chatUI?.showStatus('error', `Ошибка подключения: ${error.message}`);
      this.handleReconnect();
    }
  }
  
  handleOpen() {
    console.log('WebSocket connected');
    this.connected = true;
    this.reconnectAttempts = 0;
    this.chatUI?.showStatus('connected', 'Подключено к FinOps');
  }
  
  handleMessage(event) {
    try {
      const data = JSON.parse(event.data);
      console.log('Received message:', data);
      
      if (data.type === 'system') {
        this.chatUI?.addSystemMessage(data.content);
      } else if (data.type === 'assistant') {
        this.chatUI?.receiveMessage(data.content);
      } else if (data.type === 'user') {
        // Skip user messages (we already show them)
      } else if (data.type === 'typing') {
        // Agent is typing - show indicator
        this.chatUI?.showTyping();
      } else {
        console.warn('Unknown message type:', data.type);
      }
    } catch (error) {
      console.error('Error parsing message:', error);
    }
  }
  
  handleError(error) {
    console.error('WebSocket error:', error);
    this.chatUI?.showStatus('error', 'Ошибка соединения');
  }
  
  handleClose() {
    console.log('WebSocket closed');
    this.connected = false;
    
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.handleReconnect();
    } else {
      this.chatUI?.showStatus('error', 'Соединение потеряно. Обновите страницу.');
    }
  }
  
  handleReconnect() {
    this.reconnectAttempts++;
    this.chatUI?.showStatus('connecting', `Переподключение (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(() => {
      if (!this.connected && this.reconnectAttempts <= this.maxReconnectAttempts) {
        this.connect();
      }
    }, this.reconnectDelay * this.reconnectAttempts);
  }
  
  send(message) {
    if (!this.connected || !this.ws) {
      console.warn('WebSocket not connected');
      this.chatUI?.showStatus('error', 'Нет соединения');
      return;
    }
    
    try {
      const payload = {
        content: message
      };
      
      this.ws.send(JSON.stringify(payload));
      console.log('Sent message:', payload);
    } catch (error) {
      console.error('Error sending message:', error);
      this.chatUI?.showStatus('error', 'Ошибка отправки');
    }
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
  }
  
  setChatUI(chatUI) {
    this.chatUI = chatUI;
  }
}

// Export for use in other scripts
window.RealWebSocketClient = RealWebSocketClient;

