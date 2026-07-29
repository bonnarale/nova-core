import re

with open("docker-compose.yml", "r", encoding="utf-8") as f:
    content = f.read()

# Find n8n basic auth config
basic_auth = re.search(r"N8N_BASIC_AUTH_ACTIVE.*?=.*?(\w+)", content)
basic_user = re.search(r"N8N_BASIC_AUTH_USER.*?=.*?(\w+)", content)
basic_pass = re.search(r"N8N_BASIC_AUTH_PASSWORD.*?=.*?(\w+)", content)

print("n8n basic auth active:", basic_auth.group(1) if basic_auth else "NOT FOUND")
print("n8n basic auth user:", basic_user.group(1) if basic_user else "NOT FOUND")
print("n8n basic auth password:", basic_pass.group(1) if basic_pass else "NOT FOUND")

# Find n8n port mapping
port_match = re.search(r'"(\d+):5678"', content)
print("n8n external port:", port_match.group(1) if port_match else "NOT FOUND")
