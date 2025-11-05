/**
 * Mock WebSocket Client
 * For testing chat UI without backend
 */

class MockWebSocketClient {
  constructor(recommendationId) {
    this.recommendationId = recommendationId;
    this.chatUI = null;
    this.connected = false;
    
    // Mock responses database
    this.responses = {
      'сколько': 'По моим расчётам, экономия составит **6,809 ₽/мес**. Текущая цена в selectel: 13,379 ₽/мес, на beget аналог: 6,570 ₽/мес с похожей конфигурацией (4 CPU, 7 GB RAM, 105 GB HD).',
      
      'риск': 'Основные риски миграции:\n\n1. **Downtime** 15-30 минут при переносе\n2. Нужно переконфигурировать DNS\n3. Проверить совместимость приложений\n4. Возможная потеря данных если не сделать бэкап\n\nРекомендую делать миграцию в нерабочее время.',
      
      'как': 'План миграции:\n\n1. Создать снапшот текущего сервера\n2. Развернуть новый сервер на beget\n3. Настроить конфигурацию и окружение\n4. Перенести данные\n5. Протестировать работу\n6. Переключить DNS\n7. Мониторинг 24 часа\n\nПри правильной подготовке процесс займёт 2-3 часа.',
      
      'стоит': 'Да, экономия **81,708 ₽ в год** при схожей конфигурации — это хороший результат. Beget — надёжный провайдер с хорошей репутацией.\n\nОсновные плюсы:\n- Стабильный аптайм\n- Техподдержка на русском\n- Прозрачное ценообразование',
      
      'конфиг': 'Текущая конфигурация в selectel:\n- **CPU:** 4 cores\n- **RAM:** 7 GB\n- **Storage:** 105 GB HD\n- **Цена:** 13,379 ₽/мес\n\nАналог на beget:\n- **CPU:** 4 cores\n- **RAM:** 8 GB (чуть больше)\n- **Storage:** 100 GB SSD (быстрее)\n- **Цена:** 6,570 ₽/мес\n\nСхожесть конфигурации: **95%**',
      
      'альтернатив': 'Кроме beget, есть ещё варианты:\n\n**Yandex Cloud:**\n- Цена: ~8,500 ₽/мес\n- Экономия: 4,879 ₽/мес\n- Плюс: российский облак, интеграция с другими сервисами\n\n**Timeweb:**\n- Цена: ~7,200 ₽/мес\n- Экономия: 6,179 ₽/мес\n- Плюс: гибкие тарифы\n\nBeget остаётся лучшим вариантом по соотношению цена/качество.',
      
      'помощь': 'Могу помочь вам:\n\n- Рассчитать точную экономию\n- Оценить риски миграции\n- Составить план переноса\n- Сравнить альтернативных провайдеров\n- Проверить совместимость конфигураций\n- Ответить на вопросы о ценообразовании\n\nЧто вас интересует больше всего?',
      
      'default': 'Понял ваш вопрос. Дайте мне секунду, чтобы проанализировать данные по этой рекомендации...\n\nПо рекомендации #{REC_ID} у меня есть следующая информация:\n- Тип: миграция на более дешёвого провайдера\n- Экономия: 6,809 ₽/мес\n- Ресурс: сервер\n\nЧто конкретно вас интересует?'
    };
  }
  
  connect() {
    return new Promise((resolve) => {
      this.chatUI?.showStatus('connecting', 'Подключение...');
      
      // Simulate connection delay
      setTimeout(() => {
        this.connected = true;
        this.chatUI?.showStatus('connected', 'Подключено к FinOps');
        this.chatUI?.addSystemMessage('Чат-сессия начата. Задавайте вопросы о рекомендации.');
        resolve();
      }, 800);
    });
  }
  
  disconnect() {
    this.connected = false;
    this.chatUI?.showStatus('', 'Отключено');
  }
  
  send(message) {
    if (!this.connected) {
      console.warn('Not connected');
      return;
    }
    
    // Simulate network delay and response
    setTimeout(() => {
      const response = this.getMockResponse(message);
      this.chatUI?.receiveMessage(response);
    }, 1200 + Math.random() * 800); // 1.2-2s delay
  }
  
  getMockResponse(message) {
    const lowerMessage = message.toLowerCase();
    
    // Try to match keywords
    for (const [keyword, response] of Object.entries(this.responses)) {
      if (keyword === 'default') continue;
      
      if (lowerMessage.includes(keyword)) {
        return response.replace('#{REC_ID}', this.recommendationId);
      }
    }
    
    // Default response
    return this.responses.default.replace('#{REC_ID}', this.recommendationId);
  }
  
  setChatUI(chatUI) {
    this.chatUI = chatUI;
  }
  
  simulateError() {
    this.chatUI?.showStatus('error', 'Ошибка подключения. Попробуйте позже.');
  }
  
  simulateReconnect() {
    this.chatUI?.showStatus('connecting', 'Переподключение...');
    setTimeout(() => {
      this.connected = true;
      this.chatUI?.showStatus('connected', 'Снова на связи');
    }, 1500);
  }
}

// Export for use in other scripts
window.MockWebSocketClient = MockWebSocketClient;

