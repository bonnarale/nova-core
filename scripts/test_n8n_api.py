import subprocess, json

# Test n8n API
result = subprocess.run(
    ['wsl', 'curl', '-s', '-u', 'admin:nova-core-n8n-admin-password',
     '-H', 'Host: n8n.localhost', 'http://127.0.0.1:80/api/v1/workflows'],
    capture_output=True, text=True
)

try:
    data = json.loads(result.stdout)
    workflows = data.get('data', [])
    print(f'Workflows: {len(workflows)}')
    for wf in workflows:
        print(f'  - {wf.get("name", "unknown")} (id: {wf.get("id", "?")})')
except Exception as e:
    print(f'Error: {e}')
    print(f'Raw output: {result.stdout[:500]}')
