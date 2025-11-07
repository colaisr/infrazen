/**
 * Chat Integration
 * Manages chat drawer wiring for different scenarios (recommendations, analytics, ...)
 */

(function() {
  let chatUI = null;
  let wsClient = null;
  let currentConfig = null;

  const _dbg = (...args) => {
    if (window.INFRAZEN_DATA?.debugAgent) {
      // eslint-disable-next-line no-console
      console.log(...args);
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('chat-drawer-opened', (event) => {
      const detail = event.detail || {};
      currentConfig = {
        scenario: detail.scenario || 'recommendation',
        recommendationId: detail.recommendationId,
        context: detail.context || {},
        title: detail.title,
        subtitle: detail.subtitle
      };

      initializeChat(currentConfig);
    });

    document.addEventListener('chat-drawer-closed', () => {
      cleanupChat();
    });

    wireRecommendationButtons();
  });

  function wireRecommendationButtons() {
    document.addEventListener('click', (event) => {
      const button = event.target.closest('.chat-with-finops-btn');
      if (!button) return;

      event.preventDefault();
      event.stopPropagation();

      const recCard = button.closest('.rec-card');
      if (!recCard) return;

      const recId = recCard.dataset.id;
      const recTitle = recCard.querySelector('.rec-title')?.textContent || 'Рекомендация';

      openChat({
        scenario: 'recommendation',
        recommendationId: recId,
        subtitle: recTitle
      });
    });
  }

  function openChat(config) {
    const drawer = window.getChatDrawer();
    if (!drawer) return;
    drawer.open(config);
  }

  function initializeChat(config) {
    const drawer = window.getChatDrawer();
    if (!drawer) return;

    const drawerBody = drawer.getBody();
    chatUI = new window.ChatUI(drawerBody);

    if (config.scenario === 'analytics') {
      const emptyText = drawerBody.querySelector('.chat-empty-text');
      if (emptyText) {
        emptyText.innerHTML = 'Задайте вопрос об аналитике<br>Помогу разобрать тренды, KPI и аномалии';
      }
      const input = drawerBody.querySelector('#chat-input');
      if (input) {
        input.setAttribute('placeholder', 'Спросите про расходы, тренды и аномалии...');
      }
    }

    const enableAgent = window.INFRAZEN_DATA?.enableAgentChat ?? window.INFRAZEN_DATA?.enableAIRecommendations;

    if (enableAgent) {
      wsClient = new window.RealWebSocketClient(config);
      wsClient.setChatUI(chatUI);
      chatUI.setWebSocketClient(wsClient);

      wsClient.connect().then(() => {
        _dbg('Real chat connected:', config);
      }).catch(() => {
        initializeMockChat(config);
      });
    } else {
      initializeMockChat(config);
    }
  }

  function initializeMockChat(config) {
    const drawer = window.getChatDrawer();
    const drawerBody = drawer.getBody();

    chatUI = new window.ChatUI(drawerBody);
    wsClient = new window.MockWebSocketClient(config?.recommendationId);
    wsClient.setChatUI(chatUI);
    chatUI.setWebSocketClient(wsClient);

    wsClient.connect().then(() => {
      _dbg('Mock chat connected:', config);
    });
  }

  function cleanupChat() {
    if (wsClient) {
      wsClient.disconnect();
      wsClient = null;
    }

    chatUI = null;
    currentConfig = null;
  }

  window.chatDebug = {
    getChatUI: () => chatUI,
    getWSClient: () => wsClient,
    getCurrentConfig: () => currentConfig
  };
})();

