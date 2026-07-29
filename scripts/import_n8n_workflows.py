import subprocess, json, os

N8N_BASE = "http://127.0.0.1:80"
N8N_AUTH = "admin:nova-core-n8n-admin-password"
HOST_HEADER = "n8n.localhost"

WORKFLOW_FILES = [
    "workflows/n8n-deep-research.json",
    "workflows/n8n-audit-pipeline.json",
    "workflows/n8n-skill-incorporation.json",
]

def import_workflow(filepath):
    """Import a workflow into n8n via API."""
    with open(filepath, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)

    # Remove fields that n8n auto-generates
    for key in ['id', 'createdAt', 'updatedAt']:
        workflow_data.pop(key, None)

    # Ensure active is false (don't auto-activate)
    workflow_data['active'] = False

    payload = json.dumps(workflow_data)

    # Write payload to temp file to avoid shell escaping issues
    tmp_file = f"/tmp/n8n_import_{os.path.basename(filepath)}.json"
    wsl_tmp = f"/tmp/n8n_import_{os.path.basename(filepath)}.json"

    # Write to WSL tmp
    subprocess.run(['wsl', 'bash', '-c', f"cat > {wsl_tmp}"], input=payload, capture_output=True, text=True)

    # Import via curl
    result = subprocess.run([
        'wsl', 'curl', '-s', '-X', 'POST',
        '-u', N8N_AUTH,
        '-H', 'Host:n8n.localhost',
        '-H', 'Content-Type: application/json',
        '-d', f'@{wsl_tmp}',
        f'{N8N_BASE}/api/v1/workflows'
    ], capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)
        wf_id = data.get('id', '?')
        wf_name = data.get('name', '?')
        print(f'  OK: {wf_name} (id: {wf_id})')
        print(f'  Response keys: {list(data.keys())}')
        return data
    except Exception as e:
        print(f'  ERROR: {e}')
        print(f'  Raw: {result.stdout[:500]}')
        return None

def main():
    print("Importing n8n workflows...")
    print()

    imported = []
    for wf_file in WORKFLOW_FILES:
        print(f"Importing {wf_file}...")
        result = import_workflow(wf_file)
        if result:
            imported.append(result)
        print()

    print(f"Imported {len(imported)}/{len(WORKFLOW_FILES)} workflows")

    # List all workflows
    print("\nAll n8n workflows:")
    result = subprocess.run([
        'wsl', 'curl', '-s',
        '-u', N8N_AUTH,
        '-H', f'Host:{HOST_HEADER}',
        f'{N8N_BASE}/api/v1/workflows'
    ], capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)
        workflows = data.get('data', data) if isinstance(data, dict) else data
        if isinstance(workflows, list):
            for wf in workflows:
                status = "ACTIVE" if wf.get('active') else "inactive"
                print(f"  [{status}] {wf.get('name')} (id: {wf.get('id')})")
        else:
            print(f"  Response: {json.dumps(data)[:500]}")
    except:
        print(f"  Error listing: {result.stdout[:500]}")

if __name__ == "__main__":
    main()
