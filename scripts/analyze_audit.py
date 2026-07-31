import json

with open('workflows/audit_check.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

data = raw[0] if isinstance(raw, list) else raw

print('Workflow:', data.get('name'))
print('Active:', data.get('active'))
print()

# Check nodes
for n in data.get('nodes', []):
    name = n.get('name', '')
    ntype = n.get('type', '')
    params = n.get('parameters', {})
    
    if 'httpRequest' in ntype:
        print(f'HTTP: {name}')
        print(f'  specifyBody: {params.get("specifyBody")}')
        print(f'  jsonBody: {params.get("jsonBody", "")}')
        print(f'  url: {params.get("url", "")}')
    elif 'code' in ntype:
        js = params.get('jsCode', '')
        print(f'Code: {name}')
        print(f'  jsCode (first 200): {js[:200]}')
    elif 'webhook' in ntype:
        print(f'Webhook: {name} path={params.get("path")}')
    elif 'if' in ntype:
        print(f'IF: {name}')
        conds = params.get('conditions', {}).get('conditions', [])
        for c in conds:
            print(f'  condition: {c.get("leftValue")} {c.get("operator", {}).get("operation")} {c.get("rightValue")}')
    elif 'respond' in ntype:
        print(f'Respond: {name}')
    else:
        print(f'Other: {name} type={ntype}')
    print()

# Check connections
print('Connections:')
conns = data.get('connections', {})
for src, targets in conns.items():
    for main_list in targets.get('main', []):
        for conn in main_list:
            print(f'  {src} -> {conn["node"]}')
