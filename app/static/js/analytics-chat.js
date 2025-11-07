/**
 * Analytics chat trigger wiring
 */

(function() {
  document.addEventListener('DOMContentLoaded', () => {
    const trigger = document.getElementById('analyticsChatTrigger');
    if (!trigger) return;

    trigger.addEventListener('click', () => {
      const drawer = window.getChatDrawer();
      if (!drawer) {
        // eslint-disable-next-line no-console
        console.warn('Chat drawer is not initialized');
        return;
      }

      const rangeSelector = document.querySelector('.analytics-main-chart-section .analytics-time-selector');
      const selectedRange = parseInt(rangeSelector?.value || '30', 10);
      const timeRangeDays = Number.isNaN(selectedRange) ? 30 : selectedRange;

      drawer.open({
        scenario: 'analytics',
        title: '💬 FinOps консультант',
        subtitle: `Расходы за последние ${timeRangeDays} дней`,
        context: {
          time_range_days: timeRangeDays
        }
      });
    });
  });
})();

