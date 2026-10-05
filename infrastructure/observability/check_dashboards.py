"""Validate every provisioned PromQL query against a live Prometheus.

Run: python3 infrastructure/observability/check_dashboards.py http://PROMETHEUS:9090
This performs read-only queries. Idle HTTP latency is explicitly reported.
"""
import json
import math
from pathlib import Path
import sys
import urllib.parse
import urllib.request

base = sys.argv[1].rstrip('/')
failures = []
count = 0
for path in sorted((Path(__file__).parent / 'dashboards').glob('*.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['uid'] and len({p['id'] for p in data['panels']}) == len(data['panels'])
    for panel in data['panels']:
        for target in panel.get('targets', []):
            expr = target['expr'].replace('$__rate_interval', '5m')
            for name in ('namespace', 'pod', 'service'):
                expr = expr.replace('$' + name, '.*')
            count += 1
            try:
                url = base + '/api/v1/query?' + urllib.parse.urlencode({'query': expr})
                response = json.load(urllib.request.urlopen(url, timeout=15))
                assert response['status'] == 'success', response
                rows = response['data']['result']
                finite = [r for r in rows if math.isfinite(float(r['value'][1]))]
                if not finite:
                    # Lazy HTTP label creation means idle/newly deployed APIs
                    # have no endpoint series; never fabricate request traffic.
                    if 'finops_http_' in expr or ('histogram_quantile' in expr and rows):
                        print('IDLE HTTP:', path.stem, panel['title'])
                    elif 'kafka_consumergroup_lag' in expr:
                        print('NO COMMITTED PARTITION:', path.stem, panel['title'])
                    else:
                        failures.append((path.stem, panel['title'], 'No finite samples'))
            except Exception as exc:
                failures.append((path.stem, panel['title'], str(exc)))
print(f'Checked {count} PromQL queries; failures: {len(failures)}')
for failure in failures:
    print(*failure, sep=': ')
sys.exit(bool(failures))
