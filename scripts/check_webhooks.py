import subprocess

result = subprocess.run(
    ['docker', 'exec', 'nova-core-postgres-1', 'psql', '-U', 'n8n', '-d', 'n8n', '-c',
     'SELECT "webhookPath", "workflowId", "node" FROM webhook_entity;'],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print('ERROR:', result.stderr)
