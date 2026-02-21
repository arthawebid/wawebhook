import requests

N8N_URL = "https://n8n.app.bkr/webhook-test/message"
CA_CERT = "/home/dev/.local/share/mkcert/rootCA.pem"

payload = {
    "from": "wa-gateway",
    "message": "Test dari Python ke n8n LAN"
}

response = requests.post(
    N8N_URL,
    json=payload,
    verify=CA_CERT
)

print("Status:", response.status_code)
print("Response:", response.text)