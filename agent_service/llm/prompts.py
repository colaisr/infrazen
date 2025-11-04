"""
Prompt templates for different scenarios
"""

FINOPS_SYSTEM_PROMPT = """Ты — опытный FinOps-консультант с 10+ летним опытом и глубоким пониманием системного администрирования. 

Твоя задача — помогать компаниям оптимизировать облачные расходы, балансируя экономию, усилия и риски.

Ключевые принципы:
- Конкретность: указывай точные цифры, провайдеров, SKU
- Честность: упоминай реальные усилия и риски, не только экономию
- Практичность: давай actionable рекомендации
- Контекст: учитывай тип ресурса (prod/dev/test), критичность
- Язык: пиши на русском, профессионально но понятно

Форматирование:
- Используй HTML для выделения: <strong>, <span class="provider-name">, <span class="text-success">
- Числа выделяй: <strong>2,336 ₽</strong>
- Провайдеры: <span class="provider-name">Selectel</span>
- НЕ используй списки (ul/ol) - только inline текст
"""


def build_recommendation_prompt(data: dict) -> str:
    """
    Build prompt for recommendation text generation
    
    Args:
        data: Dict with recommendation, resource, provider, and pricing info
    """
    rec = data.get('recommendation', {})
    resource = data.get('resource', {})
    current_provider = data.get('current_provider', {})
    
    # Parse insights and metrics first
    insights = rec.get('insights', {})
    metrics = rec.get('metrics', {})
    
    # Extract key data
    resource_name = resource.get('name', 'ресурс')
    resource_type = resource.get('resource_type', 'resource')
    
    # Get current cost from metrics (more accurate) or fallback to resource
    current_cost = round(metrics.get('current_monthly', 0) if metrics else resource.get('monthly_cost', 0))
    
    current_provider_name = current_provider.get('provider_type', 'текущий провайдер')
    
    target_provider = rec.get('target_provider', 'другой провайдер')
    target_sku = rec.get('target_sku', '')
    target_region = rec.get('target_region', '')
    estimated_savings = round(rec.get('estimated_monthly_savings', 0))
    
    # Get target monthly from either metrics or insights
    target_monthly = 0
    if metrics and metrics.get('target_monthly'):
        target_monthly = round(metrics.get('target_monthly'))
    elif insights and insights.get('top2') and len(insights['top2']) > 0:
        target_monthly = round(insights['top2'][0].get('monthly', 0))
    
    similarity = round(metrics.get('similarity', 0) * 100) if metrics else 0
    
    # Get resource specs
    cpu = resource.get('cpu_cores', 'N/A')
    ram = resource.get('ram_gb', 'N/A')
    storage = resource.get('storage_gb', 'N/A')
    
    prompt = f"""Сгенерируй два описания для рекомендации по оптимизации облачного ресурса.

КОНТЕКСТ:
Текущий ресурс: {resource_name} (тип: {resource_type})
ТЕКУЩИЙ провайдер: {current_provider_name}
ТЕКУЩАЯ стоимость: {current_cost} ₽/мес
Конфигурация: {cpu} vCPU, {ram} GB RAM, {storage} GB хранилище

РЕКОМЕНДАЦИЯ: мигрировать С {current_provider_name} НА {target_provider}
ЦЕЛЕВОЙ провайдер: {target_provider}
Целевой SKU: {target_sku}
Целевой регион: {target_region}
НОВАЯ стоимость: {target_monthly:,} ₽/мес (у {target_provider})
Экономия: {estimated_savings:,} ₽/мес
Сопоставимость конфигурации: {similarity}%

ЗАДАЧА:
Верни JSON с двумя полями:

1. "short_description_html" — краткое описание (1 предложение, ~60-80 символов):
   - Для свернутой карточки рекомендации
   - Формат: "[ЦЕЛЕВОЙ провайдер] предлагает аналог за [НОВАЯ цена: {target_monthly} ₽] вместо текущих [ТЕКУЩАЯ цена: {current_cost} ₽]"
   - ВАЖНО: ЦЕЛЕВОЙ провайдер = {target_provider}, НОВАЯ цена = {target_monthly} ₽/мес
   - Используй HTML: <strong> для цен, <span class="provider-name"> для провайдера
   - Пример: "<span class='provider-name'>{target_provider}</span> предлагает аналог за <strong>{target_monthly} ₽/мес</strong> вместо текущих <strong>{current_cost} ₽/мес</strong>"

2. "detailed_description_html" — детальное описание (максимум 3 строки, ~200-250 символов):
   - Заменит секции "Пояснения" и "Метрики"
   - Включи: имя ресурса ({resource_name}), конфигурацию, целевой провайдер ({target_provider}) + регион ({target_region}) + SKU ({target_sku}), экономию ({estimated_savings} ₽/мес)
   - Если конфигурация неизвестна (cpu/ram = None) — НЕ упоминай её
   - Упомяни усилия и риски ТОЛЬКО если они значимые (например, для production-ресурсов)
   - Используй HTML для выделения ключевой информации
   - Пример: "Ресурс <strong>{resource_name}</strong> можно мигрировать на <span class='provider-highlight'>{target_provider} {target_region}</span> (SKU: {target_sku}). Экономия <strong class='text-success'>{estimated_savings} ₽/мес</strong> при сопоставимой конфигурации."

ВАЖНО:
- НЕ используй списки (ul/ol), только inline текст
- НЕ добавляй лишний fluff - только факты
- Цифры точные, из данных выше
- Если риски незначительные — не упоминай
- Формат: чистый JSON без markdown блоков

Ответ (только JSON):"""
    
    return prompt


RECOMMENDATION_FALLBACK = {
    "short_description_html": "Доступен более дешёвый аналог у другого провайдера",
    "detailed_description_html": "Найдено сопоставимое предложение с потенциальной экономией. Подробности смотрите в метриках."
}

