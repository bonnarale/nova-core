import json

with open('workflows/audit_export.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

# Handle both list and dict formats
data = raw[0] if isinstance(raw, list) else raw

print('Name:', data.get('name'))
print('Active:', data.get('active'))
print('Nodes:', len(data.get('nodes', [])))

for n in data.get('nodes', []):
    ntype = n.get('type', '')
    name = n.get('name', '')
    params = n.get('parameters', {})
    
    if 'httpRequest' in ntype:
        sb = params.get('specifyBody', 'N/A')
        jb = params.get('jsonBody', 'N/A')[:80]
        print(f'  HTTP: {name} specifyBody={sb} jsonBody={jb}')
    elif 'code' in ntype:
        js = params.get('jsCode', '')[:80]
        print(f'  Code: {name} jsCode={js}')
    elif 'webhook' in ntype:
        path = params.get('path', 'N/A')
        print(f'  Webhook: {name} path={path}')
    elif 'if' in ntype:
        print(f'  IF: {name}')
    elif 'respond' in ntype:
        print(f'  Respond: {name}')
    else:
        print(f'  Other: {name} type={ntype}')
