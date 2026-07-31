import subprocess, json

def run_n8n_cmd(args):
    """Run n8n CLI command and return output."""
    cmd = ['docker', 'exec', 'nova-core-n8n-1', 'n8n'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def get_all_workflows():
    """Get all workflow IDs and names."""
    output, _ = run_n8n_cmd(['list:workflow', '--onlyId'])
    lines = [l.strip() for l in output.split('\n') if l.strip() and '|' in l]
    workflows = []
    for line in lines:
        if '|' in line:
            wf_id, wf_name = line.split('|', 1)
            workflows.append((wf_id.strip(), wf_name.strip()))
    return workflows

def main():
    print("=== Cleaning up n8n workflows ===\n")
    
    # Get all workflows
    workflows = get_all_workflows()
    print(f"Found {len(workflows)} workflows:")
    for wf_id, wf_name in workflows:
        print(f"  {wf_name} (id: {wf_id})")
    
    # Deactivate all workflows
    print("\nDeactivating all workflows...")
    for wf_id, wf_name in workflows:
        output, rc = run_n8n_cmd(['update:workflow', f'--id={wf_id}', '--active=false'])
        status = "OK" if rc == 0 else "FAILED"
        print(f"  {wf_name}: {status}")
    
    # Restart n8n to apply deactivation
    print("\nRestarting n8n...")
    subprocess.run(['docker', 'compose', 'restart', 'n8n'], capture_output=True, text=True)
    
    import time
    time.sleep(10)
    
    # Check health
    result = subprocess.run(['docker', 'exec', 'nova-core-n8n-1', 'wget', '-qO-', 'http://127.0.0.1:5678/healthz'], capture_output=True, text=True)
    print(f"n8n health: {result.stdout.strip()}")
    
    # Import fresh workflows
    print("\nImporting fresh workflows...")
    workflows_data = []
    for f in ['n8n-deep-research.json', 'n8n-audit-pipeline.json', 'n8n-skill-incorporation.json']:
        with open(f'workflows/{f}', 'r', encoding='utf-8') as fh:
            wf = json.load(fh)
            for key in ['id', 'createdAt', 'updatedAt', 'versionId', 'meta', 'tags']:
                wf.pop(key, None)
            workflows_data.append(wf)
    
    with open('workflows/n8n-all-workflows.json', 'w', encoding='utf-8') as fh:
        json.dump(workflows_data, fh, indent=2)
    
    subprocess.run(['docker', 'cp', 'workflows/n8n-all-workflows.json', 'nova-core-n8n-1:/tmp/n8n-all-workflows.json'], check=True)
    
    output, rc = run_n8n_cmd(['import:workflow', '--input=/tmp/n8n-all-workflows.json'])
    print(output)
    
    # Get new workflow IDs
    new_workflows = get_all_workflows()
    print(f"\nNew workflows: {len(new_workflows)}")
    
    # Activate new workflows
    print("\nActivating new workflows...")
    for wf_id, wf_name in new_workflows:
        output, rc = run_n8n_cmd(['update:workflow', f'--id={wf_id}', '--active=true'])
        status = "OK" if rc == 0 else "FAILED"
        print(f"  {wf_name}: {status}")
    
    # Final restart
    print("\nFinal restart...")
    subprocess.run(['docker', 'compose', 'restart', 'n8n'], capture_output=True, text=True)
    time.sleep(10)
    
    result = subprocess.run(['docker', 'exec', 'nova-core-n8n-1', 'wget', '-qO-', 'http://127.0.0.1:5678/healthz'], capture_output=True, text=True)
    print(f"n8n health: {result.stdout.strip()}")
    
    # List active workflows
    print("\nActive workflows:")
    output, _ = run_n8n_cmd(['list:workflow', '--active=true'])
    for line in output.split('\n'):
        if '|' in line:
            print(f"  {line.strip()}")

if __name__ == "__main__":
    main()
