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
    return {'name': name, 'label': name.capitalize(), 'type': 'query', 'datasource': DS,
            'definition': query, 'query': {'query': query, 'refId': name},
            'refresh': 1, 'sort': 1, 'multi': True, 'includeAll': True, 'allValue': '.*',
            'current': {'text': 'All', 'value': '$__all'}}


def dashboard(slug, title, description, specs, variables=()):
    panels, y, x = [], 0, 0
    for spec in specs:
        kind, name, unit, queries, width, *rest = spec
        extra = rest[0] if rest else {}
        height = 4 if kind == 'stat' else 8
        if x + width > 24:
            y += previous_height
            x = 0
        fields = {'unit': unit, 'min': 0, 'color': {'mode': 'palette-classic'},
                  'noValue': 'No samples', 'thresholds': {'mode': 'absolute', 'steps': [{'color': 'blue', 'value': None}]}}
        if extra.get('negative'): fields.pop('min')
        if any('histogram_quantile' in q for q, _ in queries): fields['noValue'] = 'No traffic'
        if unit == 'percent': fields['max'] = 100
        if extra.get('health'):
            fields.update({'mappings': [{'type': 'value', 'options': {'0': {'text': 'DOWN', 'color': 'red'}, '1': {'text': 'UP', 'color': 'green'}}}],
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
            options = {'showHeader': True, 'cellHeight': 'sm', 'sortBy': [{'displayName': 'Alert', 'desc': False}]}
        panel = {'id': len(panels) + 1, 'title': name, 'type': kind, 'datasource': DS,
                 'description': extra.get('description', ''), 'gridPos': {'x': x, 'y': y, 'w': width, 'h': height},
                 'fieldConfig': {'defaults': fields, 'overrides': []}, 'options': options,
                 'targets': [{'refId': chr(65+i), 'expr': q, 'legendFormat': legend, 'range': kind == 'timeseries', 'instant': kind != 'timeseries', 'format': 'table' if kind == 'table' else 'time_series', 'datasource': DS} for i, (q, legend) in enumerate(queries)]}
        if kind == 'table':
            panel['transformations'] = [{'id': 'organize', 'options': {'excludeByName': {'Time': True}, 'renameByName': {'alertname': 'Alert', 'severity': 'Severity', 'Value': 'Instances'}}}]
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
    dashboard('platform-overview', '01 Platform Overview', 'Single-node homelab · availability, capacity and traffic. Kafka RF=1 is not high availability.', [
        stat('Node ready', 'min(kube_node_status_condition{condition="Ready",status="true"})', health=True),
        stat('CPU used', CPU, 'percent', thresholds=(80, 90)),
        stat('Memory used', RAM, 'percent', thresholds=(80, 90)),
        stat('Root disk used', DISK, 'percent', thresholds=(80, 90)),
        stat('Running pods', 'sum(kube_pod_status_phase{phase="Running"})'),
        stat('Restarts · last hour', 'sum(increase(kube_pod_container_status_restarts_total[1h]))', thresholds=(1, 5)),
        stat('All API replicas reachable', f'min({UP})', health=True),
        stat('Kafka broker', 'min(up{job="monitoring/kafka-broker"})', health=True),
        stat('PostgreSQL', 'min(pg_up)', health=True),
        stat('Pods not ready', 'sum(kube_pod_status_ready{condition="false"} * on(namespace,pod,uid) (kube_pod_status_phase{phase=~"Pending|Running|Unknown"} == 1))', thresholds=(1, 3)),
        stat('Firing alerts', 'count(ALERTS{alertstate="firing",severity=~"warning|critical"}) or vector(0)', thresholds=(1, 3)),
        stat('Database connections', 'sum(pg_stat_database_numbackends)'),
        chart('API traffic & server errors', 'reqps', (HTTP_RATE, 'All requests'), (f'sum(rate({API}{{status=~"5.."}}[$__rate_interval])) or {ZERO}', '5xx')),
        chart('API response time · p95', 's', (P95, 'p95'), description='No samples means no completed requests in the rate window, not zero latency.'),
        chart('Memory by workload · top 6', 'bytes', ('topk(6, sum by(namespace,pod) (container_memory_working_set_bytes{container!="",container!="POD",pod!=""}))', '{{namespace}} / {{pod}}')),
        chart('Kafka lag · transactions', 'short', ('kafka_consumergroup_lag{topic="transactions",consumergroup="finops-analytics"} >= 0', 'Partition {{partition}}'), description='Only committed partitions. -1 means there is no committed offset; see Kafka dashboard.'),
        chart('CPU by workload · top 6', 'cores', ('topk(6, sum by(namespace,pod) (rate(container_cpu_usage_seconds_total{container!="",container!="POD",pod!=""}[$__rate_interval])))', '{{namespace}} / {{pod}}')),
        ('table', 'Alerts requiring attention', 'short', [('count by(alertname,severity) (ALERTS{alertstate="firing",severity=~"warning|critical"}) or label_replace(vector(0), "alertname", "No firing warning or critical alerts", "", "")', '')], 12),
    ])
    dashboard('kubernetes-node', '02 Kubernetes & Node', 'Node capacity, workload health and resource consumers.', [
        stat('CPU used', CPU, 'percent', thresholds=(80, 90)), stat('Memory available', 'sum(node_memory_MemAvailable_bytes)', 'bytes'),
        stat('Root disk used', DISK, 'percent', thresholds=(80, 90)), stat('Uptime', 'time() - max(node_boot_time_seconds)', 's'),
        stat('Running pods', 'sum(kube_pod_status_phase{phase="Running",namespace=~"$namespace"})'),
        stat('Namespaces', 'count(kube_namespace_created)'),
        chart('CPU used', 'percent', (CPU, 'CPU')), chart('Load average', 'short', ('node_load1', '1 minute'), ('node_load5', '5 minutes'), ('node_load15', '15 minutes')),
        chart('Memory capacity', 'bytes', ('node_memory_MemAvailable_bytes', 'Available'), ('node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes', 'Used')),
        chart('Disk throughput', 'Bps', ('sum(rate(node_disk_read_bytes_total{device!~"loop.*|ram.*"}[$__rate_interval]))', 'Read'), ('sum(rate(node_disk_written_bytes_total{device!~"loop.*|ram.*"}[$__rate_interval]))', 'Write')),
        chart('Network · physical interface', 'Bps', ('sum(rate(node_network_receive_bytes_total{device=~"eth.*|en.*"}[$__rate_interval]))', 'Receive'), ('sum(rate(node_network_transmit_bytes_total{device=~"eth.*|en.*"}[$__rate_interval]))', 'Transmit')),
        chart('Pod CPU · top 8', 'cores', (f'topk(8, {PODCPU})', '{{pod}}')),
        chart('Pod memory · top 8', 'bytes', (f'topk(8, {PODRAM})', '{{pod}}')),
        chart('Restarts · last hour', 'short', ('sum by(pod) (increase(kube_pod_container_status_restarts_total{namespace=~"$namespace",pod=~"$pod"}[1h]))', '{{pod}}')),
        chart('Pod phases', 'short', ('sum by(phase) (kube_pod_status_phase{namespace=~"$namespace",pod=~"$pod"})', '{{phase}}')),
        chart('Deployment replicas unavailable', 'short', ('kube_deployment_status_replicas_unavailable{namespace=~"$namespace"}', '{{namespace}} / {{deployment}}')),
    ], [variable('namespace', 'label_values(kube_pod_info, namespace)'), variable('pod', 'label_values(kube_pod_info{namespace=~"$namespace"}, pod)')])
    dashboard('finops-application', '03 FinOps Application', 'HTTP instrumentation excludes health probes. No URL parameters, identities or payloads are recorded. Idle latency has no samples.', [
        stat('Replicas reachable', f'sum({UP})'), stat('Requests / second', HTTP_RATE, 'reqps'),
        stat('In-flight requests', 'sum(finops_http_requests_in_flight)'),
        stat('5xx / second', f'sum(rate({API}{{status=~"5.."}}[$__rate_interval])) or {ZERO}', 'reqps'),
        stat('4xx / second', f'sum(rate({API}{{status=~"4.."}}[$__rate_interval])) or {ZERO}', 'reqps'),
        stat('Restarts · last hour', 'sum(increase(kube_pod_container_status_restarts_total{namespace="finops",container="finops-api"}[1h]))'),
        chart('Traffic by endpoint', 'reqps', (f'sum by(method,route) (rate({API}[$__rate_interval]))', '{{method}} {{route}}')),
        chart('HTTP status codes', 'reqps', (f'sum by(status) (rate({API}[$__rate_interval]))', '{{status}}')),
        chart('Response time', 's', *[(f'histogram_quantile({q}, sum by(le) (rate(finops_http_request_duration_seconds_bucket[$__rate_interval])))', label) for q,label in [(0.5,'p50'),(0.95,'p95'),(0.99,'p99')]]),
        chart('Server error ratio', 'percent', (f'100 * (sum(rate({API}{{status=~"5.."}}[$__rate_interval])) or {ZERO}) / clamp_min(({HTTP_RATE}), 0.001)', '5xx / all')),
        chart('Process CPU', 'cores', ('rate(process_cpu_seconds_total{job="monitoring/finops-api"}[$__rate_interval])', '{{pod}}')),
        chart('Process memory', 'bytes', ('process_resident_memory_bytes{job="monitoring/finops-api"}', '{{pod}}')),
        chart('Transaction submissions', 'reqps', *[(f'sum(rate({API}{{method="POST",route=~"/transactions|/bot/transactions",status=~"{status}"}}[$__rate_interval])) or {ZERO}', label) for status,label in [('2..','Accepted'),('[45]..','Rejected')]], description='HTTP submission outcomes; not an assertion that downstream Kafka processing has completed.'),
        chart('API replica availability', 'short', (UP, '{{pod}}')),
    ])
    edge='traefik_service_requests_total{service=~"$service"}'
    dashboard('edge-web', '04 Edge & Web Traffic', 'Traefik ingress metrics cover web and API traffic. No extra Nginx exporter is needed.', [
        stat('Ingress reachable', 'min(up{job="monitoring/traefik"})', health=True),
        stat('Service requests / second', f'sum(rate({edge}[$__rate_interval]))', 'reqps'),
        stat('Open web connections', 'sum(traefik_open_connections{entrypoint=~"web|websecure"})'),
        stat('TLS expiry · earliest', 'min(traefik_tls_certs_not_after) - time()', 's', description='Remaining lifetime of the earliest certificate served by Traefik.'),
        stat('Config reload successful', 'min(traefik_config_last_reload_success)', health=True),
        stat('HTTPS requests / second', 'sum(rate(traefik_entrypoint_requests_total{entrypoint="websecure"}[$__rate_interval]))', 'reqps'),
        chart('Traffic by service', 'reqps', (f'sum by(service) (rate({edge}[$__rate_interval]))', '{{service}}')),
        chart('Status codes', 'reqps', (f'sum by(code) (rate({edge}[$__rate_interval]))', '{{code}}')),
        chart('Upstream response time · p95', 's', ('histogram_quantile(0.95, sum by(le,service) (rate(traefik_service_request_duration_seconds_bucket{service=~"$service"}[$__rate_interval])))', '{{service}}')),
        chart('Upstream 5xx', 'reqps', ('sum by(service) (rate(traefik_service_requests_total{service=~"$service",code=~"5.."}[$__rate_interval])) or (0 * sum by(service) (rate(traefik_service_requests_total{service=~"$service"}[$__rate_interval])))', '{{service}}')),
        chart('Ingress bandwidth', 'Bps', ('sum(rate(traefik_entrypoint_requests_bytes_total{entrypoint=~"web|websecure"}[$__rate_interval]))', 'Incoming'), ('sum(rate(traefik_entrypoint_responses_bytes_total{entrypoint=~"web|websecure"}[$__rate_interval]))', 'Outgoing')),
        chart('Open connections', 'short', ('sum by(entrypoint) (traefik_open_connections{entrypoint=~"web|websecure"})', '{{entrypoint}}')),
    ], [variable('service', 'label_values(traefik_service_requests_total, service)')])
    pg='{datname="finops"}'
    dashboard('postgresql', '05 PostgreSQL', 'Read-only pg_monitor collector. Query text and application data are never exported.', [
        stat('PostgreSQL reachable', 'min(pg_up)', health=True), stat('Connections · all databases', 'sum(pg_stat_database_numbackends)'),
        stat('Active · finops', 'sum(pg_stat_activity_count{datname="finops",state="active"})'), stat('Connection limit', 'max(pg_settings_max_connections)'),
        stat('Database size', 'pg_database_size_bytes{datname="finops"}', 'bytes'), stat('Long-running transactions', 'sum(pg_long_running_transactions)', thresholds=(1,3)),
        chart('Connections by state', 'short', (f'sum by(state) (pg_stat_activity_count{pg})', '{{state}}')),
        chart('Transactions', 'ops', (f'rate(pg_stat_database_xact_commit{pg}[$__rate_interval])', 'Commits'), (f'rate(pg_stat_database_xact_rollback{pg}[$__rate_interval])', 'Rollbacks')),
        chart('Cache hit ratio', 'percent', (f'100 * rate(pg_stat_database_blks_hit{pg}[$__rate_interval]) / clamp_min(rate(pg_stat_database_blks_hit{pg}[$__rate_interval]) + rate(pg_stat_database_blks_read{pg}[$__rate_interval]), 0.001)', 'Hit ratio')),
        chart('Rows read / written', 'ops', *[(f'rate(pg_stat_database_tup_{suffix}{pg}[$__rate_interval])', label) for suffix,label in [('returned','Read'),('inserted','Inserted'),('updated','Updated'),('deleted','Deleted')]]),
        chart('Locks by mode', 'short', (f'sum by(mode) (pg_locks_count{pg})', '{{mode}}')),
        chart('Deadlocks · last hour', 'short', (f'increase(pg_stat_database_deadlocks{pg}[1h])', 'Deadlocks')),
    ])
    group='{topic="transactions",consumergroup="finops-analytics"}'
    dashboard('kafka', '06 Kafka', 'Single combined broker/controller · replication factor 1 · transactions / finops-analytics. No high availability.', [
        stat('Broker reachable', 'min(up{job="monitoring/kafka-broker"})', health=True), stat('Topics · cluster', 'max(kafka_controller_kafkacontroller_globaltopiccount)'),
        stat('Partitions · transactions', 'kafka_topic_partitions{topic="transactions"}'), stat('Under-replicated partitions', 'sum(kafka_server_replicamanager_underreplicatedpartitions)', thresholds=(1,2)),
        stat('Offline partitions', 'sum(kafka_controller_kafkacontroller_offlinepartitionscount)', thresholds=(1,2)),
        stat('Partitions without a commit', f'count(kafka_consumergroup_current_offset{group} < 0) or (0 * max(kafka_brokers))', description='An empty partition can legitimately have no committed consumer offset. It is not negative lag.'),
        chart('Broker message rate · all topics', 'ops', ('rate(kafka_server_brokertopicmetrics_messagesin_total{topic=""}[$__rate_interval])', 'Messages')),
        chart('Broker throughput · all topics', 'Bps', ('rate(kafka_server_brokertopicmetrics_bytesin_total{topic=""}[$__rate_interval])', 'In'), ('rate(kafka_server_brokertopicmetrics_bytesout_total{topic=""}[$__rate_interval])', 'Out')),
        chart('Consumer lag · committed partitions', 'short', (f'kafka_consumergroup_lag{group} >= 0', 'Partition {{partition}}'), description='No samples means no committed partition. Inspect the offset panels and the uncommitted partition count; do not interpret it as zero lag.'),
        chart('Consumer group members', 'short', ('kafka_consumergroup_members{consumergroup="finops-analytics"}', 'finops-analytics')),
        chart('Committed offsets', 'short', (f'kafka_consumergroup_current_offset{group}', 'Partition {{partition}}'), negative=True, description='-1 means no committed offset yet.'),
        chart('Log-end offsets', 'short', ('kafka_topic_partition_current_offset{topic="transactions"}', 'Partition {{partition}}')),
        chart('Broker memory', 'bytes', ('container_memory_working_set_bytes{namespace="kafka",container="kafka",pod="finops-kafka-combined-0"}', 'Working set')),
        chart('Broker CPU', 'cores', ('rate(container_cpu_usage_seconds_total{namespace="kafka",container="kafka",pod="finops-kafka-combined-0"}[$__rate_interval])', 'CPU')),
    ])


if __name__ == '__main__':
    main()
