import subprocess, json

# Get workflow IDs
result = subprocess.run(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'list:workflow'], capture_output=True, text=True)
lines = [l.strip() for l in result.stdout.strip().split('\n') if '|' in l]

workflow_ids = []
for line in lines:
    wf_id, wf_name = line.split('|', 1)
    workflow_ids.append((wf_id, wf_name))
    print(f'Found: {wf_name} (id: {wf_id})')

# Activate each workflow
for wf_id, wf_name in workflow_ids:
    print(f'\nActivating {wf_name}...')
    result = subprocess.run(
        ['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'update:workflow', f'--id={wf_id}', '--active=true'],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        print(f'Error: {result.stderr[:200]}')

# Verify
print('\n--- Verification ---')
result2 = subprocess.run(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'list:workflow'], capture_output=True, text=True)
print(result2.stdout.strip())
