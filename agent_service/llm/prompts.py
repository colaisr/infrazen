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


def build_cleanup_prompt(data: dict) -> str:
    """
    Build prompt for cleanup recommendation text generation
    
    Args:
        data: Dict with recommendation, resource, provider, and pricing info
    """
    rec = data.get('recommendation', {})
    resource = data.get('resource', {})
    
    insights = rec.get('insights', {})
    metrics = rec.get('metrics', {})
    rec_type = rec.get('type', '')
    
    resource_name = resource.get('name', 'ресурс')
    resource_type = resource.get('resource_type', 'resource')
    estimated_savings = round(rec.get('estimated_monthly_savings', 0))
    current_cost = round(resource.get('monthly_cost', 0))
    
    # Map resource types to Russian names
    resource_type_names = {
        'server': 'сервер',
        'snapshot': 'снапшот',
        'volume': 'диск',
        'storage': 'хранилище',
        'ip': 'IP-адрес',
        'reserved_ip': 'IP-адрес',
        'image': 'образ',
    }
    
    resource_type_ru = resource_type_names.get(resource_type.lower(), 'ресурс')
    
    # Get age/size info from insights
    age_days = insights.get('age_days', 0) if insights else 0
    size_gb = insights.get('size_gb', 0) if insights else 0
    
    # For stopped servers, we don't know when they were stopped, only when created
    # So don't use age_days for cleanup_stopped
    is_stopped_server = (rec_type == 'cleanup_stopped')
    
    # Calculate wasted amount (money already spent) - only if we have reliable age_days
    wasted_amount = 0
    if age_days > 0 and estimated_savings > 0 and not is_stopped_server:
        wasted_amount = round((estimated_savings * age_days) / 30)
    
    prompt = f"""Сгенерируй два описания для рекомендации по УДАЛЕНИЮ неиспользуемого ресурса.
Это НЕ миграция, это CLEANUP - удаление ресурса для экономии!

ДАННЫЕ:
- Ресурс: {resource_name} ({resource_type_ru})
- Текущая стоимость: {current_cost:,} ₽/мес
- Экономия при удалении: {estimated_savings:,} ₽/мес
- Тип рекомендации: {'ОСТАНОВЛЕННЫЙ СЕРВЕР' if is_stopped_server else 'НЕИСПОЛЬЗУЕМЫЙ РЕСУРС'}
{f'- Возраст ресурса: {age_days} дней (~{round(age_days/30)} мес)' if age_days > 0 and not is_stopped_server else ''}
{f'- Размер: {size_gb} GB' if size_gb > 0 else ''}
{f'- УЖЕ ПОТРАЧЕНО на этот ресурс: {wasted_amount:,} ₽ (за {age_days} дней)' if wasted_amount > 0 else ''}

ЗАДАЧА:
Верни JSON с двумя полями:

1. "short_description_html" (1 предложение, ~60-80 символов):
   Формат: "Экономия {estimated_savings:,} ₽/мес при удалении неиспользуемого {resource_type_ru}"
   - Выдели экономию: <strong>{estimated_savings:,} ₽/мес</strong>
   - НЕ упоминай провайдеров или аналоги - это УДАЛЕНИЕ!
   
2. "detailed_description_html" (2-3 предложения, ~250-300 символов):
   Пиши по-человечески, естественно и конкретно, КАК ОПЫТНЫЙ FINOPS-КОНСУЛЬТАНТ.
   ФОКУС НА ЭКОНОМИИ от удаления! Деликатно упомяни потраченные средства (если они есть в ДАННЫХ).
   
   СТИЛЬ ДЛЯ НЕИСПОЛЬЗУЕМЫХ РЕСУРСОВ (снапшоты, IP, и т.д.) - с возрастом и потраченными средствами:
   
   Для снапшотов:
   "Экономия <strong>1,709 ₽/мес</strong> при удалении снапшота <strong>gitdisk-1740816592565</strong>. Снапшот не используется уже 248 дней (размер 507 GB), за это время на него уже было потрачено <strong>14,119 ₽</strong>."
   
   Для IP-адресов:
   "Экономия <strong>241 ₽/мес</strong> при удалении IP-адреса <strong>gitlab_new</strong>. IP не используется уже 547 дней, за это время на него уже было потрачено <strong>4,394 ₽</strong>."
   
   СТИЛЬ ДЛЯ ОСТАНОВЛЕННЫХ СЕРВЕРОВ (без возраста и потраченных средств):
   "Экономия <strong>1,289 ₽/мес</strong> при удалении остановленного сервера <strong>punch-dev-monitoring-1</strong>. Сервер находится в статусе STOPPED и продолжает потреблять средства на хранение."
   
   ПЛОХОЙ СТИЛЬ (НЕ делай так):
   ❌ "Ресурс не используется уже 764 дня" - для снапшота пиши "Снапшот", не "Ресурс"!
   ❌ "Ресурс существует уже 547 дней" - пиши "не используется", не "существует"!
   ❌ "за это время на него уже было потрачено 4,394 ₽" - забыл <strong> для суммы!
   ❌ "Удаление полностью исключит эти расходы" - redundant fluff, убери!
   ❌ "освободит средства для более нужных задач" - лишний fluff, не добавляй!
   ❌ "при удалении неиспользуемого ресурса gitlab_new" - пиши тип! "IP-адреса gitlab_new"
   ❌ "при переносе снапшота" - НЕТ переноса, только удаление!
   ❌ "аналог за 0 ₽/мес" - НЕТ аналога, только удаление!
   ❌ "ВЫ ПОТРАТИЛИ ВПУСТУЮ!!!" - слишком агрессивно!
   
   ПРАВИЛА:
   - НАЧИНАЙ С ЭКОНОМИИ: "Экономия {estimated_savings:,} ₽/мес при удалении..."
   - Выделяй экономию: <strong>{estimated_savings:,} ₽/мес</strong>
   - Название ресурса: <strong>{resource_name}</strong>
   
   ДЛЯ ОСТАНОВЛЕННЫХ СЕРВЕРОВ (тип: ОСТАНОВЛЕННЫЙ СЕРВЕР):
   - НЕ упоминай возраст и потраченные средства (эти данные недоступны!)
   - Упомяни, что сервер в статусе STOPPED
   - Объясни, что он продолжает потреблять средства на хранение дисков
   - Пример: "Сервер находится в статусе STOPPED и продолжает потреблять средства на хранение"
   
   ДЛЯ ДРУГИХ РЕСУРСОВ (снапшоты, IP, и т.д.):
   - Используй корректный тип ресурса из ДАННЫХ: "снапшота", "IP-адреса", "диска" и т.д.
   - В первом предложении: "при удалении {resource_type_ru} <strong>{resource_name}</strong>"
   - Во втором предложении используй краткое конкретное название:
     * Для IP-адреса → "IP"
     * Для снапшота → "Снапшот" (НЕ "Ресурс"!)
     * Для диска → "Диск"
   - Пиши "не используется уже X дней" (НЕ "существует" - это другое!)
   - Упомяни размер (если есть в ДАННЫХ): "(размер 507 GB)"
   - ОБЯЗАТЕЛЬНО выдели потраченную сумму: "<strong>4,394 ₽</strong>"
   - Формула: "[Тип ресурса] не используется уже X дней (размер Y GB), за это время на него уже было потрачено <strong>Z ₽</strong>."
   - Где [Тип ресурса] = "IP", "Снапшот", "Диск" и т.д.
   - НЕ пиши "потрачено впустую" - слишком грубо! Пиши "уже было потрачено"
   - Заканчивай на потраченной сумме - точка! НЕ добавляй "Удаление полностью исключит эти расходы" - это очевидно и redundant!
   
   ОБЩИЕ ПРАВИЛА:
   - НЕ используй слова: миграция, перенос, аналог, провайдер, конфигурация
   - НЕ используй списки (ul/ol)
   - НЕ добавляй fluff типа "Удаление полностью исключит эти расходы" - redundant!
   - НЕ добавляй fluff типа "освободит средства для более нужных задач" - redundant!
   - Тон: профессиональный, деликатный, но убедительный, без лишних слов
   - Это CLEANUP, не миграция!
   - НЕ упоминай возраст "0 дней" и "потрачено 0 ₽" - если данных нет, просто не упоминай!

Ответ (только чистый JSON, без markdown):"""
    
    return prompt


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
    
    # Check recommendation type
    rec_type = rec.get('type', '')
    
    # For cleanup recommendations, use different prompt
    if rec_type in ['cleanup_unused_ip', 'cleanup_stopped', 'cleanup_unused_volume', 'cleanup_old_snapshot']:
        return build_cleanup_prompt(data)
    
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
    
    # Map resource types to Russian names
    resource_type_names = {
        'server': 'сервер',
        'vm': 'виртуальная машина',
        'instance': 'инстанс',
        'volume': 'диск',
        'storage': 'хранилище',
        'database': 'база данных',
        'cluster': 'кластер',
        'kubernetes': 'K8s кластер',
        'snapshot': 'снапшот',
        'ip': 'IP-адрес',
        'reserved_ip': 'зарезервированный IP',
    }
    
    resource_type_ru = resource_type_names.get(resource_type.lower(), 'ресурс')
    
    # Build specs string naturally
    specs_parts = []
    if cpu and cpu != 'N/A':
        specs_parts.append(f"{cpu} CPU")
    if ram and ram != 'N/A':
        specs_parts.append(f"{ram} GB RAM")
    if storage and storage != 'N/A':
        specs_parts.append(f"{storage} GB HD")
    
    specs_str = ', '.join(specs_parts) if specs_parts else ''
    
    prompt = f"""Сгенерируй два описания для рекомендации по оптимизации облачного ресурса.
Пиши естественно, как опытный FinOps-консультант общается с клиентом, а не как робот по шаблону.

ДАННЫЕ:
- Ресурс: {resource_name} ({resource_type_ru})
- Текущий провайдер: {current_provider_name}
- Текущая стоимость: {current_cost:,} ₽/мес
- Конфигурация: {specs_str if specs_str else 'не указана'}
- Альтернативный провайдер: {target_provider}
- Альтернативный SKU: {target_sku}
- Альтернативная стоимость: {target_monthly:,} ₽/мес
- Экономия: {estimated_savings:,} ₽/мес

ЗАДАЧА:
Верни JSON с двумя полями:

1. "short_description_html" (1 предложение, ~60-80 символов):
   Формат: "{target_provider} предлагает аналог за {target_monthly:,} ₽/мес вместо текущих {current_cost:,} ₽/мес"
   - Выдели провайдера: <span class='provider-name'>{target_provider}</span>
   - Выдели цены: <strong>{target_monthly:,} ₽/мес</strong>
   
2. "detailed_description_html" (2-3 предложения, ~200-250 символов):
   Пиши по-человечески, естественно и конкретно.
   ФОКУС НА ЭКОНОМИИ - это главное для FinOps!
   
   ХОРОШИЙ СТИЛЬ (конкретный пример):
   "Экономия <strong>6,809 ₽/мес</strong> при переносе сервера <strong>punch-dev-backend-1</strong> в <span class='provider-name'>beget</span>. Схожая конфигурация (4 CPU, 7 GB RAM, 105 GB HD) там стоит <strong>6,570 ₽/мес</strong>"
   
   Если конфигурация НЕ указана:
   "Экономия <strong>6,809 ₽/мес</strong> при переносе сервера <strong>punch-dev-backend-1</strong> в <span class='provider-name'>beget</span>. Схожая конфигурация там стоит <strong>6,570 ₽/мес</strong>"
   
   ПЛОХОЙ СТИЛЬ (НЕ делай так):
   ❌ "Схожая конфигурация (CPU/RAM/HD)" - НЕ используй плейсхолдеры!
   ❌ "Возможна экономия..." - слишком мягко
   ❌ "Ресурс можно мигрировать на..." - фокус не на экономии
   
   ПРАВИЛА:
   - НАЧИНАЙ С ЭКОНОМИИ: "Экономия {estimated_savings:,} ₽/мес при..."
   - Выделяй экономию: <strong>{estimated_savings:,} ₽/мес</strong>
   - Название ресурса: <strong>{resource_name}</strong>
   - Провайдер: <span class='provider-name'>{target_provider}</span>
   - ВАЖНО: Если в ДАННЫХ указана "Конфигурация" (не "не указана"), то напиши РЕАЛЬНЫЕ значения в скобках: (4 CPU, 7 GB RAM, 105 GB HD)
   - Если конфигурация "не указана", просто пиши "Схожая конфигурация" БЕЗ скобок
   - НЕ используй плейсхолдеры типа (CPU/RAM/HD) — только реальные цифры или ничего!
   - Говори "там стоит" вместо "должен стоить около"
   - НЕ используй списки (ul/ol)
   - НЕ добавляй лишний контекст - только экономия и факты

Ответ (только чистый JSON, без markdown):"""
    
    return prompt


RECOMMENDATION_FALLBACK = {
    "short_description_html": "Доступен более дешёвый аналог у другого провайдера",
    "detailed_description_html": "Найдено сопоставимое предложение с потенциальной экономией. Подробности смотрите в метриках."
}

