
import httpx

NINE_ROUTER_URL = "http://localhost:20128/v1"
NINE_ROUTER_KEY = "sk-ad63867957b503e7-nrt4w0-b687b29d"

system_prompt = (
    "You are a strict technical recruiter evaluating candidate compatibility for an open job.\n"
    "Evaluate the candidates based on experience match, core technical skills, and language capabilities.\n"
    "You MUST output JSON adhering strictly to the JSON schema, under the 'evaluations' key. Do not output anything else."
)

user_prompt = (
    "JOB DETAILS:\nTitle: Software Engineer\n"
    + ("A" * 5000)
    + "\n\nCANDIDATES TO EVALUATE:\n"
    + ("Candidate Details\n" * 10)
)

payload = {
    "model": "gemini/gemini-3.1-flash-lite",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.2,
    "stream": False,
}
headers = {
    "Authorization": f"Bearer {NINE_ROUTER_KEY}",
    "Content-Type": "application/json",
}

try:
    resp = httpx.post(
        f"{NINE_ROUTER_URL}/chat/completions",
        json=payload,
        headers=headers,
        timeout=20.0,
    )
    print("STATUS CODE:", resp.status_code)
    print("BODY:")
    print(resp.text)
except Exception as e:
    print("ERROR:", e)
