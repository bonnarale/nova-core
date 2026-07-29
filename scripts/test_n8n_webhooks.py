import subprocess, json, time

N8N_BASE = "http://127.0.0.1:80"
N8N_AUTH = "admin:nova-core-n8n-admin-password"

def test_webhook(path, payload, label):
    """Test an n8n webhook endpoint."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"  Webhook: POST {N8N_BASE}/webhook/{path}")
    print(f"  Payload: {json.dumps(payload)}")
    print(f"{'='*60}")

    payload_str = json.dumps(payload)

    start = time.time()
    result = subprocess.run([
        'wsl', 'curl', '-s', '-w', '\n%{http_code}',
        '-X', 'POST',
        '-u', N8N_AUTH,
        '-H', 'Host:n8n.localhost',
        '-H', 'Content-Type: application/json',
        '-d', payload_str,
        f'{N8N_BASE}/webhook/{path}'
    ], capture_output=True, text=True, timeout=120)

    elapsed = time.time() - start
    lines = result.stdout.strip().split('\n')
    status_code = lines[-1] if lines else 'unknown'
    body = '\n'.join(lines[:-1]) if len(lines) > 1 else result.stdout

    print(f"  Status: {status_code}")
    print(f"  Time: {elapsed:.1f}s")
    try:
        data = json.loads(body)
        print(f"  Response: {json.dumps(data, indent=2)[:1000]}")
    except:
        print(f"  Raw: {body[:500]}")

    return status_code, body

# Test 1: Deep Research (express mode, no audit)
test_webhook('deep-research', {
    "topic": "microservices architecture",
    "mode": "express",
    "audit": False
}, "Deep Research - Express Mode (no audit)")

# Test 2: Audit Pipeline (standard depth)
test_webhook('audit-pipeline', {
    "target": "def calculate_total(items): return sum(item['price'] * item['qty'] for item in items)",
    "domain": "python",
    "depth": "standard"
}, "Audit Pipeline - Standard Depth")

# Test 3: Skill Incorporation (standard security)
test_webhook('skill-incorporation', {
    "source": "A simple logging decorator that wraps function calls with timing information",
    "skill_type": "skill",
    "security_level": "standard"
}, "Skill Incorporation - Standard Security")
