from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os, json, re

load_dotenv()
app = Flask(__name__)
CORS(app)
client = OpenAI()

VEA_SYSTEM = (
    "You are VEA, the Virtual Extension Assistant for Alcorn State University's Extension Program. "
    "Your job is to help students and community members with internships, workshops/trainings, scholarships, "
    "how to start research, and who to contact. Be concise and friendly. Prefer step-by-step guidance and clear "
    "next actions. If a fact (date, deadline, dollar amounts) isn’t certain, say you’re not sure and point them "
    "to the Extension Office (email/phone/website). Never invent official details. Offer to connect them to the "
    "office if needed.\n\n"
    "Greeting rule: If the user says something casual like 'hi', 'hello', 'hey', or small talk, respond with a "
    "brief, warm greeting and one-line prompt such as 'I can help with internships, workshops, scholarships, "
    "research, or who to contact—what do you need?' Do NOT include office contact details unless they ask "
    "for specifics or you need to escalate."
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FAQ_PATH = os.path.join(DATA_DIR, "faqs.json")
CONTACTS_PATH = os.path.join(DATA_DIR, "contacts.json")

def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

FAQS = _load(FAQ_PATH, {})
CONTACTS = _load(CONTACTS_PATH, {
    "office_email": "extension@alcorn.edu",
    "office_phone": "601-877-6128",
    "office_hours": "Mon–Fri 9:00am–4:00pm",
    "site": "https://www.alcorn.edu/extension"
})

def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", s.lower()).strip()

def kb_lookup(user_text: str) -> str | None:
    u = normalize(user_text)
    best_ans, best_len = None, 0
    for k, ans in FAQS.items():
        key = normalize(k)
        if key and key in u and len(key) > best_len:
            best_ans, best_len = ans, len(key)
    return best_ans

def contacts_block() -> str:
    return (
        f"Extension Office\n"
        f"- Email: {CONTACTS.get('office_email','')}\n"
        f"- Phone: {CONTACTS.get('office_phone','')}\n"
        f"- Hours: {CONTACTS.get('office_hours','')}\n"
        f"- Website: {CONTACTS.get('site','')}"
    )

FEW_SHOTS = [
    {"role": "user", "content": "When are summer internships due?"},
    {"role": "assistant", "content":
        "I don’t have the exact deadline. Here’s what to do next:\n"
        "1) Check the Extension site’s internships page.\n"
        "2) Email the Extension Office to confirm this year’s dates.\n"
        f"{contacts_block()}"
    },
    {"role": "user", "content": "Can you list current workshops?"},
    {"role": "assistant", "content":
        "I can’t verify today’s list, but here’s how to find it quickly:\n"
        "• Visit the Extension events page.\n"
        "• Or contact the office for this month’s schedule.\n"
        f"{contacts_block()}"
    }
]

GREETING_PAT = re.compile(
    r"^\s*(hi|hello|hey|yo|sup|good\s+(morning|afternoon|evening))\s*!?\s*$",
    re.IGNORECASE
)

def is_greeting(text: str) -> bool:
    return bool(GREETING_PAT.match(text or ""))

def postprocess(text: str, add_contacts: bool = True) -> str:
    text = (text or "").strip()
    if not add_contacts:
        return text
    lower = text.lower()
    has_bullets = any(tok in text for tok in ("- ", "• ", "1)", "1.", "next"))
    already_has_contacts = ("extension office" in lower) or ("@alcorn.edu" in lower) or ("https://www.alcorn.edu/extension" in lower)
    if (not has_bullets) and (not already_has_contacts):
        text += f"\n\nNext step: If you need specifics, contact the office.\n{contacts_block()}"
    return text

@app.route("/chat", methods=["POST"])
def chat():
    data = (request.json or {})
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    if is_greeting(user_message):
        greeting_reply = (
            "Hi! I’m VEA. I can help with internships, workshops, scholarships, research, "
            "or who to contact—what do you need?"
        )
        return jsonify({"reply": postprocess(greeting_reply, add_contacts=False)})

    kb = kb_lookup(user_message)
    if kb:
        return jsonify({"reply": postprocess(kb)})

    if re.search(r"\b(contact|email|phone|office|hours)\b", user_message.lower()):
        return jsonify({"reply": contacts_block()})

    try:
        messages = [{"role": "system", "content": VEA_SYSTEM}, *FEW_SHOTS, {"role": "user", "content": user_message}]
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3
        )
        reply = resp.choices[0].message.content
        return jsonify({"reply": postprocess(reply)})
    except Exception as e:
        return jsonify({"reply": f"Backend error: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
