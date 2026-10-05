"""Generate the six provisioned dashboards using Grafana's native panel system."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DS = {'type': 'prometheus', 'uid': 'prometheus'}
CPU = '100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval])))'
RAM = '100 * (1 - sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))'
DISK = '100 * (1 - min(node_filesystem_avail_bytes{mountpoint="/",fstype!="rootfs"} / node_filesystem_size_bytes{mountpoint="/",fstype!="rootfs"}))'
API = 'finops_http_requests_total'
UP = 'up{job="monitoring/finops-api"}'
RATE = f'sum(rate({API}[$__rate_interval]))'
# A quiet API has zero traffic only when its collector is still reachable.
ZERO = f'(0 * min({UP}))'
HTTP_RATE = f'({RATE}) or {ZERO}'
P95 = 'histogram_quantile(0.95, sum by (le) (rate(finops_http_request_duration_seconds_bucket[$__rate_interval])))'
PODCPU = 'sum by (pod) (rate(container_cpu_usage_seconds_total{container!="",container!="POD",namespace=~"$namespace",pod=~"$pod"}[$__rate_interval]))'
PODRAM = 'sum by (pod) (container_memory_working_set_bytes{container!="",container!="POD",namespace=~"$namespace",pod=~"$pod"})'


def variable(name, query):
    return {'name': name, 'label': {'namespace': 'Пространство имён', 'pod': 'Pod', 'service': 'Сервис'}[name], 'type': 'query', 'datasource': DS,
            'definition': query, 'query': {'query': query, 'refId': name},
            'refresh': 1, 'sort': 1, 'multi': True, 'includeAll': True, 'allValue': '.*',
            'current': {'text': 'All', 'value': '$__all'}}


def dashboard(slug, title, description, specs, variables=()):
    panels = [{'id': 1, 'type': 'text', 'title': '', 'transparent': True,
               'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 2},
               'options': {'mode': 'markdown', 'content': description}}]
    y, x = 2, 0
    for spec in specs:
        kind, name, unit, queries, width, *rest = spec
        extra = rest[0] if rest else {}
        height = 4 if kind == 'stat' else 8
        if x + width > 24:
            y += previous_height
            x = 0
        fields = {'unit': unit, 'min': 0, 'color': {'mode': 'palette-classic'},
                  'noValue': 'Нет измерений', 'thresholds': {'mode': 'absolute', 'steps': [{'color': 'blue', 'value': None}]}}
        if extra.get('negative'): fields.pop('min')
        if any('histogram_quantile' in q for q, _ in queries): fields['noValue'] = 'Нет трафика'
        if unit == 'percent': fields['max'] = 100
        if kind == 'stat' and unit == 'short': fields['decimals'] = 0
        if unit in ('percent', 'percentunit'): fields['decimals'] = 1
        if extra.get('health'):
            fields.update({'mappings': [{'type': 'value', 'options': {'0': {'text': 'Недоступно', 'color': 'red'}, '1': {'text': 'Работает', 'color': 'green'}}}],
                           'thresholds': {'mode': 'absolute', 'steps': [{'color': 'red', 'value': None}, {'color': 'green', 'value': 1}]}})
        if 'thresholds' in extra:
            fields['thresholds'] = {'mode': 'absolute', 'steps': [{'color': 'green', 'value': None}, {'color': 'orange', 'value': extra['thresholds'][0]}, {'color': 'red', 'value': extra['thresholds'][1]}]}
        options = {'tooltip': {'mode': 'multi', 'sort': 'desc'}, 'legend': {'displayMode': 'list', 'placement': 'bottom', 'calcs': []}}
        if kind == 'stat':
            fields['color'] = {'mode': 'thresholds'}
            options = {'reduceOptions': {'calcs': ['lastNotNull'], 'fields': '', 'values': False}, 'orientation': 'auto',
                       'textMode': 'auto', 'colorMode': 'value', 'graphMode': 'none', 'justifyMode': 'auto'}
        elif kind == 'timeseries':
            fields['custom'] = {'drawStyle': 'line', 'lineInterpolation': 'smooth', 'lineWidth': 2, 'fillOpacity': 8,
                                'showPoints': 'never', 'spanNulls': False, 'axisCenteredZero': False}
        else:
            options = {'showHeader': True, 'cellHeight': 'sm', 'sortBy': [{'displayName': 'Проблема', 'desc': False}]}
        hint = extra.get('description', '')
        if extra.get('health'):
            hint = 'Работает — метрика доступности равна 1. Недоступно — 0. При отсутствии измерений проверьте сборщик метрик и состояние Pod.'
        elif not hint and unit == 'reqps':
            hint = 'Среднее число запросов в секунду за выбранное окно. Ноль при работающем сборщике означает отсутствие запросов.'
        elif not hint and unit == 'cores':
            hint = 'Использование CPU в ядрах: 1 соответствует одному полностью занятому ядру. Сравнивайте с лимитом контейнера и ресурсами сервера.'
        elif not hint and 'histogram_quantile' in queries[0][0]:
            hint = 'p50 — медиана; p95 и p99 — время, быстрее которого завершились 95% и 99% запросов. Меньше — лучше. Без трафика задержка не вычисляется.'
        if 'thresholds' in extra:
            hint += f" Предупреждение от {extra['thresholds'][0]}, высокий уровень от {extra['thresholds'][1]}."
        panel = {'id': len(panels) + 1, 'title': name, 'type': kind, 'datasource': DS,
                 'description': hint.strip(), 'gridPos': {'x': x, 'y': y, 'w': width, 'h': height},
                 'fieldConfig': {'defaults': fields, 'overrides': []}, 'options': options,
                 'targets': [{'refId': chr(65+i), 'expr': q, 'legendFormat': legend, 'range': kind == 'timeseries', 'instant': kind != 'timeseries', 'format': 'table' if kind == 'table' else 'time_series', 'datasource': DS} for i, (q, legend) in enumerate(queries)]}
        if kind == 'table':
            panel['transformations'] = [{'id': 'organize', 'options': {'excludeByName': {'Time': True}, 'renameByName': {'alertname': 'Проблема', 'severity': 'Уровень', 'Value': 'Объектов'}}}]
        panels.append(panel)
        x += width
        previous_height = height
    result = {'uid': 'finops-' + slug, 'title': title, 'description': description, 'tags': ['finops', 'platform'],
              'timezone': 'browser', 'schemaVersion': 39, 'version': 1, 'editable': False, 'refresh': '30s',
              'time': {'from': 'now-1h', 'to': 'now'}, 'timepicker': {'refresh_intervals': ['30s', '1m', '5m']},
              'templating': {'list': list(variables)}, 'panels': panels,
              'links': [{'type': 'dashboards', 'title': 'FinOps Platform', 'tags': ['finops'], 'asDropdown': True, 'includeVars': True, 'keepTime': True}]}
    (ROOT / 'dashboards' / (slug + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


def stat(title, expr, unit='short', width=4, **kwargs):
    return ('stat', title, unit, [(expr, '')], width, kwargs)


def chart(title, unit, *queries, width=12, **kwargs):
    return ('timeseries', title, unit, queries, width, kwargs)


def main():
    (ROOT / 'dashboards').mkdir(exist_ok=True)
    dashboard('platform-overview', '01 Обзор платформы', 'Один сервер: доступность сервисов, запас ресурсов и поток запросов. Kafka с одной копией данных не обеспечивает отказоустойчивость.', [
        stat('Сервер доступен', 'min(kube_node_status_condition{condition="Ready",status="true"})', health=True),
        stat('CPU · загрузка', CPU, 'percent', thresholds=(80, 90)),
        stat('RAM · занято', RAM, 'percent', thresholds=(80, 90)),
        stat('Диск · занято', DISK, 'percent', thresholds=(80, 90)),
        stat('Работающие Pod', 'sum(kube_pod_status_phase{phase="Running"})'),
        stat('Перезапуски за час', 'sum(increase(kube_pod_container_status_restarts_total[1h]))', thresholds=(1, 5)),
        stat('Все экземпляры API доступны', f'min({UP})', health=True),
        stat('Kafka доступна', 'min(up{job="monitoring/kafka-broker"})', health=True),
        stat('PostgreSQL', 'min(pg_up)', health=True),
        stat('Pod не готовы', 'sum(kube_pod_status_ready{condition="false"} * on(namespace,pod,uid) (kube_pod_status_phase{phase=~"Pending|Running|Unknown"} == 1))', thresholds=(1, 3)),
        stat('Проблемы требуют внимания', 'count(ALERTS{alertstate="firing",severity=~"warning|critical"}) or vector(0)', thresholds=(1, 3)),
        stat('Соединения с базой', 'sum(pg_stat_database_numbackends)'),
        chart('API · запросы и ошибки', 'reqps', (HTTP_RATE, 'Все запросы'), (f'sum(rate({API}{{status=~"5.."}}[$__rate_interval])) or {ZERO}', '5xx')),
        chart('API · время ответа p95', 's', (P95, 'p95'), description='p95: 95% запросов выполнились быстрее этого времени. Меньше — лучше. Если запросов нет, задержка не вычисляется.'),
        chart('Кто использует RAM · топ-6', 'bytes', ('topk(6, sum by(namespace,pod) (container_memory_working_set_bytes{container!="",container!="POD",pod!=""}))', '{{namespace}} / {{pod}}')),
        chart('Kafka · отставание обработки', 'short', ('kafka_consumergroup_lag{topic="transactions",consumergroup="finops-analytics"} >= 0', 'Партиция {{partition}}'), description='Число ещё не обработанных сообщений в партициях с сохранённой позицией. Подробности и пустые партиции — на дашборде Kafka.'),
        chart('Кто использует CPU · топ-6', 'cores', ('topk(6, sum by(namespace,pod) (rate(container_cpu_usage_seconds_total{container!="",container!="POD",pod!=""}[$__rate_interval])))', '{{namespace}} / {{pod}}')),
        ('table', 'Что требует внимания', 'short', [('count by(alertname,severity) (ALERTS{alertstate="firing",severity=~"warning|critical"}) or label_replace(vector(0), "alertname", "Нет активных предупреждений и критических ошибок", "", "")', '')], 12),
    ])
    dashboard('kubernetes-node', '02 Сервер и Kubernetes', 'Ресурсы сервера и состояние приложений. Выберите пространство имён или Pod, чтобы сузить поиск проблемы.', [
        stat('CPU · загрузка', CPU, 'percent', thresholds=(80, 90)), stat('RAM · доступно', 'sum(node_memory_MemAvailable_bytes)', 'bytes'),
        stat('Диск · занято', DISK, 'percent', thresholds=(80, 90)), stat('Время работы сервера', 'time() - max(node_boot_time_seconds)', 's'),
        stat('Работающие Pod', 'sum(kube_pod_status_phase{phase="Running",namespace=~"$namespace"})'),
        stat('Пространства имён', 'count(kube_namespace_created)'),
        chart('CPU · загрузка', 'percent', (CPU, 'CPU')), chart('Очередь задач CPU · load average', 'short', ('node_load1', '1 минута'), ('node_load5', '5 минут'), ('node_load15', '15 минут')),
        chart('Память · использовано и доступно', 'bytes', ('node_memory_MemAvailable_bytes', 'Доступно'), ('node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes', 'Использовано')),
        chart('Диск · чтение и запись', 'Bps', ('sum(rate(node_disk_read_bytes_total{device!~"loop.*|ram.*"}[$__rate_interval]))', 'Чтение'), ('sum(rate(node_disk_written_bytes_total{device!~"loop.*|ram.*"}[$__rate_interval]))', 'Запись')),
        chart('Сеть · входящий и исходящий поток', 'Bps', ('sum(rate(node_network_receive_bytes_total{device=~"eth.*|en.*"}[$__rate_interval]))', 'Входящий'), ('sum(rate(node_network_transmit_bytes_total{device=~"eth.*|en.*"}[$__rate_interval]))', 'Исходящий')),
        chart('CPU по Pod · топ-8', 'cores', (f'topk(8, {PODCPU})', '{{pod}}')),
        chart('RAM по Pod · топ-8', 'bytes', (f'topk(8, {PODRAM})', '{{pod}}')),
        chart('Перезапуски за час', 'short', ('sum by(pod) (increase(kube_pod_container_status_restarts_total{namespace=~"$namespace",pod=~"$pod"}[1h]))', '{{pod}}')),
        chart('Состояния Pod', 'short', ('sum by(phase) (kube_pod_status_phase{namespace=~"$namespace",pod=~"$pod"})', '{{phase}}')),
        chart('Недоступные экземпляры приложений', 'short', ('kube_deployment_status_replicas_unavailable{namespace=~"$namespace"}', '{{namespace}} / {{deployment}}')),
    ], [variable('namespace', 'label_values(kube_pod_info, namespace)'), variable('pod', 'label_values(kube_pod_info{namespace=~"$namespace"}, pod)')])
    dashboard('finops-application', '03 Приложение FinOps', 'Реальные запросы API без проверок здоровья. Параметры URL и содержимое запросов не записываются. При отсутствии трафика время ответа не вычисляется.', [
        stat('Доступные экземпляры API', f'sum({UP})'), stat('Запросы в секунду', HTTP_RATE, 'reqps'),
        stat('Запросы в обработке', 'sum(finops_http_requests_in_flight)'),
        stat('Ошибки сервера · 5xx/с', f'sum(rate({API}{{status=~"5.."}}[$__rate_interval])) or {ZERO}', 'reqps'),
        stat('Отклонённые запросы · 4xx/с', f'sum(rate({API}{{status=~"4.."}}[$__rate_interval])) or {ZERO}', 'reqps'),
        stat('Перезапуски за час', 'sum(increase(kube_pod_container_status_restarts_total{namespace="finops",container="finops-api"}[1h]))'),
        chart('Какие методы API вызывают', 'reqps', (f'sum by(method,route) (rate({API}[$__rate_interval]))', '{{method}} {{route}}')),
        chart('Ответы API по HTTP-коду', 'reqps', (f'sum by(status) (rate({API}[$__rate_interval]))', '{{status}}')),
        chart('Время ответа · p50 / p95 / p99', 's', *[(f'histogram_quantile({q}, sum by(le) (rate(finops_http_request_duration_seconds_bucket[$__rate_interval])))', label) for q,label in [(0.5,'p50'),(0.95,'p95'),(0.99,'p99')]]),
        chart('Доля ошибок сервера · 5xx', 'percent', (f'100 * (sum(rate({API}{{status=~"5.."}}[$__rate_interval])) or {ZERO}) / clamp_min(({HTTP_RATE}), 0.001)', '5xx / all')),
        chart('CPU процесса API', 'cores', ('rate(process_cpu_seconds_total{job="monitoring/finops-api"}[$__rate_interval])', '{{pod}}')),
        chart('RAM процесса API', 'bytes', ('process_resident_memory_bytes{job="monitoring/finops-api"}', '{{pod}}')),
        chart('Создание транзакций · результат запроса', 'reqps', *[(f'sum(rate({API}{{method="POST",route=~"/transactions|/bot/transactions",status=~"{status}"}}[$__rate_interval])) or {ZERO}', label) for status,label in [('2..','Приняты'),('[45]..','Отклонены')]], description='Результат HTTP-запроса на создание транзакции. Успешный ответ API ещё не означает завершение обработки в Kafka.'),
        chart('Доступность каждого экземпляра API', 'short', (UP, '{{pod}}')),
    ])
    edge='traefik_service_requests_total{service=~"$service"}'
    dashboard('edge-web', '04 Веб-трафик и HTTPS', 'Весь внешний трафик проходит через Traefik. Выберите сервис, чтобы проверить его нагрузку, ошибки и время ответа.', [
        stat('Входной шлюз доступен', 'min(up{job="monitoring/traefik"})', health=True),
        stat('Веб-запросы в секунду', f'sum(rate({edge}[$__rate_interval]))', 'reqps'),
        stat('Открытые веб-соединения', 'sum(traefik_open_connections{entrypoint=~"web|websecure"})'),
        stat('До истечения HTTPS-сертификата', 'min(traefik_tls_certs_not_after) - time()', 's', description='Остаток срока самого раннего HTTPS-сертификата. cert-manager продлевает сертификаты автоматически; меньше 7 дней требует проверки.'),
        stat('Конфигурация шлюза загружена', 'min(traefik_config_last_reload_success)', health=True),
        stat('HTTPS-запросы в секунду', 'sum(rate(traefik_entrypoint_requests_total{entrypoint="websecure"}[$__rate_interval]))', 'reqps'),
        chart('Трафик по сервисам', 'reqps', (f'sum by(service) (rate({edge}[$__rate_interval]))', '{{service}}')),
        chart('Ответы сервисов по HTTP-коду', 'reqps', (f'sum by(code) (rate({edge}[$__rate_interval]))', '{{code}}')),
        chart('Время ответа сервисов · p95', 's', ('histogram_quantile(0.95, sum by(le,service) (rate(traefik_service_request_duration_seconds_bucket{service=~"$service"}[$__rate_interval])))', '{{service}}')),
        chart('Ошибки сервисов · 5xx', 'reqps', ('sum by(service) (rate(traefik_service_requests_total{service=~"$service",code=~"5.."}[$__rate_interval])) or (0 * sum by(service) (rate(traefik_service_requests_total{service=~"$service"}[$__rate_interval])))', '{{service}}')),
        chart('Объём входящего и исходящего трафика', 'Bps', ('sum(rate(traefik_entrypoint_requests_bytes_total{entrypoint=~"web|websecure"}[$__rate_interval]))', 'Входящий'), ('sum(rate(traefik_entrypoint_responses_bytes_total{entrypoint=~"web|websecure"}[$__rate_interval]))', 'Исходящий')),
        chart('Соединения по точке входа', 'short', ('sum by(entrypoint) (traefik_open_connections{entrypoint=~"web|websecure"})', '{{entrypoint}}')),
    ], [variable('service', 'label_values(traefik_service_requests_total, service)')])
    pg='{datname="finops"}'
    dashboard('postgresql', '05 База данных PostgreSQL', 'Состояние PostgreSQL: соединения, нагрузка и блокировки. Тексты SQL и финансовые данные в метрики не попадают.', [
        stat('База данных доступна', 'min(pg_up)', health=True), stat('Соединения · все базы', 'sum(pg_stat_database_numbackends)'),
        stat('Активные соединения · FinOps', 'sum(pg_stat_activity_count{datname="finops",state="active"})'), stat('Лимит соединений', 'max(pg_settings_max_connections)'),
        stat('Размер базы FinOps', 'pg_database_size_bytes{datname="finops"}', 'bytes'), stat('Самая долгая транзакция', 'max(pg_stat_activity_max_tx_duration{datname="finops"})', 's', thresholds=(60,300)),
        chart('Состояния соединений', 'short', (f'sum by(state) (pg_stat_activity_count{pg})', '{{state}}')),
        chart('Транзакции · фиксация и откат', 'ops', (f'rate(pg_stat_database_xact_commit{pg}[$__rate_interval])', 'Зафиксированы'), (f'rate(pg_stat_database_xact_rollback{pg}[$__rate_interval])', 'Отменены')),
        chart('Чтение из кеша · доля попаданий', 'percent', (f'100 * rate(pg_stat_database_blks_hit{pg}[$__rate_interval]) / clamp_min(rate(pg_stat_database_blks_hit{pg}[$__rate_interval]) + rate(pg_stat_database_blks_read{pg}[$__rate_interval]), 0.001)', 'Попадания в кеш')),
        chart('Строки · чтение и изменение', 'ops', *[(f'rate(pg_stat_database_tup_{suffix}{pg}[$__rate_interval])', label) for suffix,label in [('returned','Чтение'),('inserted','Добавлено'),('updated','Обновлено'),('deleted','Удалено')]]),
        chart('Блокировки по типу', 'short', (f'sum by(mode) (pg_locks_count{pg})', '{{mode}}')),
        chart('Взаимные блокировки за час', 'short', (f'increase(pg_stat_database_deadlocks{pg}[1h])', 'Взаимные блокировки')),
    ])
    group='{topic="transactions",consumergroup="finops-analytics"}'
    dashboard('kafka', '06 Очередь событий Kafka', 'Один брокер, одна копия данных. События transactions обрабатывает группа finops-analytics. Отказоустойчивого кластера пока нет.', [
        stat('Брокер Kafka доступен', 'min(up{job="monitoring/kafka-broker"})', health=True), stat('Топики · весь кластер', 'max(kafka_controller_kafkacontroller_globaltopiccount)'),
        stat('Партиции · transactions', 'kafka_topic_partitions{topic="transactions"}'), stat('Партиции с неполными копиями', 'sum(kafka_server_replicamanager_underreplicatedpartitions)', thresholds=(1,2)),
        stat('Недоступные партиции', 'sum(kafka_controller_kafkacontroller_offlinepartitionscount)', thresholds=(1,2)),
        stat('Партиции без сохранённой позиции', f'count(kafka_consumergroup_current_offset{group} < 0) or (0 * max(kafka_brokers))', description='У пустой партиции может ещё не быть сохранённой позиции. Это нормальное состояние, а не отрицательное отставание.'),
        chart('Поступление сообщений · все топики', 'ops', ('rate(kafka_server_brokertopicmetrics_messagesin_total{topic=""}[$__rate_interval])', 'Сообщения')),
        chart('Kafka · входящий и исходящий поток', 'Bps', ('rate(kafka_server_brokertopicmetrics_bytesin_total{topic=""}[$__rate_interval])', 'Входящий'), ('rate(kafka_server_brokertopicmetrics_bytesout_total{topic=""}[$__rate_interval])', 'Исходящий')),
        chart('Отставание обработчика · по партициям', 'short', (f'kafka_consumergroup_lag{group} >= 0', 'Партиция {{partition}}'), description='Показаны партиции с сохранённой позицией. Если их нет, проверьте график позиций ниже. Отсутствие данных не означает нулевое отставание.'),
        chart('Работающие обработчики FinOps', 'short', ('kafka_consumergroup_members{consumergroup="finops-analytics"}', 'finops-analytics')),
        chart('Сохранённая позиция обработчика', 'short', (f'kafka_consumergroup_current_offset{group}', 'Партиция {{partition}}'), negative=True, description='Значение -1: обработчик ещё не сохранил позицию в этой партиции. Обычно это пустая партиция.'),
        chart('Последняя позиция в журнале', 'short', ('kafka_topic_partition_current_offset{topic="transactions"}', 'Партиция {{partition}}')),
        chart('RAM брокера Kafka', 'bytes', ('container_memory_working_set_bytes{namespace="kafka",container="kafka",pod="finops-kafka-combined-0"}', 'Рабочая память')),
        chart('CPU брокера Kafka', 'cores', ('rate(container_cpu_usage_seconds_total{namespace="kafka",container="kafka",pod="finops-kafka-combined-0"}[$__rate_interval])', 'CPU')),
    ])


if __name__ == '__main__':
    main()
