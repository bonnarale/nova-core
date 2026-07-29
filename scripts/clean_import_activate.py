import subprocess, json, time

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def main():
    # Deactivate ALL workflows
    print("Deactivating all workflows...")
    output, _ = run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'list:workflow', '--onlyId'])
    ids = [l.strip() for l in output.split('\n') if l.strip()]
    print(f"  Found {len(ids)} workflows to deactivate")
    for wf_id in ids:
        run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'update:workflow', f'--id={wf_id}', '--active=false'])
    
    # Restart to apply
    print("Restarting n8n...")
    run_cmd(['docker', 'compose', 'restart', 'n8n'])
    time.sleep(15)
    
    # Verify clean state
    output, _ = run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'wget', '-qO-', 'http://127.0.0.1:5678/healthz'])
    print(f"Health: {output}")
    
    # Import fresh workflows
    print("\nImporting workflows...")
    workflows = []
    for f in ['n8n-deep-research.json', 'n8n-audit-pipeline.json', 'n8n-skill-incorporation.json']:
        with open(f'workflows/{f}', 'r', encoding='utf-8') as fh:
            wf = json.load(fh)
            for key in ['id', 'createdAt', 'updatedAt', 'versionId', 'meta', 'tags']:
                wf.pop(key, None)
            workflows.append(wf)
    
    with open('workflows/n8n-all-workflows.json', 'w', encoding='utf-8') as fh:
        json.dump(workflows, fh, indent=2)
    
    subprocess.run(['docker', 'cp', 'workflows/n8n-all-workflows.json', 'nova-core-n8n-1:/tmp/n8n-all-workflows.json'], check=True)
    output, rc = run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'import:workflow', '--input=/tmp/n8n-all-workflows.json'])
    print(output)
    
    # Get new IDs and activate
    output, _ = run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'list:workflow'])
    print(f"\nAll workflows after import:")
    new_ids = []
    for line in output.split('\n'):
        if '|' in line:
            print(f"  {line.strip()}")
            wf_id = line.split('|')[0].strip()
            new_ids.append(wf_id)
    
    print(f"\nActivating {len(new_ids)} workflows...")
    for wf_id in new_ids:
        run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'update:workflow', f'--id={wf_id}', '--active=true'])
    
    # Final restart
    print("Final restart...")
    run_cmd(['docker', 'compose', 'restart', 'n8n'])
    time.sleep(15)
    
    output, _ = run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'wget', '-qO-', 'http://127.0.0.1:5678/healthz'])
    print(f"Health: {output}")
    
    # List active
    output, _ = run_cmd(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'list:workflow', '--active=true'])
    print(f"\nActive workflows:")
    for line in output.split('\n'):
        if '|' in line:
            print(f"  {line.strip()}")

if __name__ == "__main__":
    main()
