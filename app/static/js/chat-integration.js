/**
 * Chat Integration
 * Wires chat drawer with recommendations page
 */

(function() {
  let chatUI = null;
  let wsClient = null;
  let currentRecommendationId = null;
  
  // Wait for DOM and drawer to be ready
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize chat when drawer opens
    document.addEventListener('chat-drawer-opened', (e) => {
      const { recommendationId } = e.detail;
      currentRecommendationId = recommendationId;
      
      initializeChat(recommendationId);
    });
    
    // Cleanup when drawer closes
    document.addEventListener('chat-drawer-closed', () => {
      cleanupChat();
    });
    
    // Wire "Обсудить с FinOps" buttons
    wireRecommendationButtons();
  });
  
  function wireRecommendationButtons() {
    // Use event delegation for dynamically added buttons
    document.addEventListener('click', (e) => {
      // Check if clicked element is the chat button
      const button = e.target.closest('.chat-with-finops-btn');
      
      if (button) {
        e.preventDefault();
        e.stopPropagation();
        
        // Extract recommendation ID from the button's context
        const recCard = button.closest('.rec-card');
        if (recCard) {
          const recId = recCard.dataset.id;
          const recTitle = recCard.querySelector('.rec-title')?.textContent || 'Рекомендация';
          
          openChat(recId, recTitle);
        }
      }
    });
  }
  
  function openChat(recommendationId, recommendationTitle) {
    const drawer = window.getChatDrawer();
    if (drawer) {
      drawer.open(recommendationId, recommendationTitle);
    }
  }
  
  function initializeChat(recommendationId) {
    const drawer = window.getChatDrawer();
    if (!drawer) return;
    
    const drawerBody = drawer.getBody();
    
    // Initialize chat UI
    chatUI = new window.ChatUI(drawerBody);
    
    // Initialize WebSocket client (mock for now)
    wsClient = new window.MockWebSocketClient(recommendationId);
    wsClient.setChatUI(chatUI);
    
    // Wire chat UI with WebSocket
    chatUI.setWebSocketClient(wsClient);
    
    // Connect
    wsClient.connect().then(() => {
      console.log('Chat connected for recommendation:', recommendationId);
    });
  }
  
  function cleanupChat() {
    if (wsClient) {
      wsClient.disconnect();
      wsClient = null;
    }
    
    chatUI = null;
    currentRecommendationId = null;
  }
  
  // Export for debugging
  window.chatDebug = {
    getChatUI: () => chatUI,
    getWSClient: () => wsClient,
    getCurrentRecId: () => currentRecommendationId
  };
})();

