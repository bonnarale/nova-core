path = "/home/aalej/nova-core/tests/backend/test_reasoning.py"

with open(path, "r") as f:
    content = f.read()

content = content.replace(
    'assert len(IntentType) == 13',
    'assert len(IntentType) == 14'
)

with open(path, "w") as f:
    f.write(content)

print("Done")
