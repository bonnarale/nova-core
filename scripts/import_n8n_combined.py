import json, subprocess

# Read all 3 workflow files and wrap in array
workflows = []
for f in ['n8n-deep-research.json', 'n8n-audit-pipeline.json', 'n8n-skill-incorporation.json']:
    with open(f'workflows/{f}', 'r', encoding='utf-8') as fh:
        wf = json.load(fh)
        # Remove ALL auto-generated/identity fields to avoid conflicts
        for key in ['id', 'createdAt', 'updatedAt', 'versionId', 'meta', 'tags']:
            wf.pop(key, None)
        workflows.append(wf)

# Write combined array
with open('workflows/n8n-all-workflows.json', 'w', encoding='utf-8') as fh:
    json.dump(workflows, fh, indent=2)

print(f'Created combined file with {len(workflows)} workflows')
print('Workflow names:', [w.get('name') for w in workflows])

# Copy to container
subprocess.run(['docker', 'cp', 'workflows/n8n-all-workflows.json', 'nova-core-n8n-1:/tmp/n8n-all-workflows.json'], check=True)
print('Copied to container')

# Import
result = subprocess.run(['docker', 'exec', 'nova-core-n8n-1', 'n8n', 'import:workflow', '--input=/tmp/n8n-all-workflows.json'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr[:500])
