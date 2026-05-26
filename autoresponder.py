from flask import Flask, request, jsonify
import requests, os, json
from datetime import datetime

app = Flask(__name__)

CLAUDE_API_KEY     = "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"
OPENAI_API_KEY     = "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"
ELEVENLABS_KEY     = "sk_bfc2d77a9f7e4dd16545b0fdd0142d01955f8a8a8de4f966"
ELEVENLABS_VOICE   = "TPIitICAZ8CqlGZ81AKm"
TELEGRAM_TOKEN     = "5918599508:AAEMcCN9q9fPE3oLWBA6FhJobtM6hE_L8ss"
TELEGRAM_CHAT_ID   = "493124834"
ZADARMA_USER_KEY   = "c6718865fb95d3e2b661"
ZADARMA_SECRET_KEY = "c940b60c4d9f4ce08d33"

SYSTEM_PROMPT = """Ты вежливый помощник инструктора по вождению из Одессы.
Отвечай кратко (2-3 предложения), на языке звонящего.
Если спрашивают о записи — скажи что инструктор перезвонит сегодня."""

def transcribe(audio_bytes):
    resp = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        files={"file": ("call.mp3", audio_bytes, "audio/mpeg")},
        data={"model": "whisper-1", "language": "ru"},
        timeout=60
    )
    return resp.json().get("text", "").strip()

def ask_claude(transcript):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-sonnet-4-20250514", "max_tokens": 300, "system": SYSTEM_PROMPT,
              "messages": [{"role": "user", "content": f"Звонящий сказал: «{transcript}». Дай краткое резюме и ответ."}]},
        timeout=30
    )
    return resp.json()["content"][0]["text"]

def send_telegram(text, audio_bytes=None, caller=""):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = f"📞 <b>Звонок</b>: {caller}\n🕐 {now}\n\n{text}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    if audio_bytes:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendAudio",
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": "🎙 Запись"},
            files={"audio": ("call.mp3", audio_bytes, "audio/mpeg")}, timeout=30)

@app.route("/webhook", methods=["POST", "GET"])
def zd_echo_check():
    zd_echo = request.args.get("zd_echo", "")
    if zd_echo:
        return zd_echo
    return webhook()

@app.route("/webhook_real", methods=["POST"])
def webhook():
    data = request.form.to_dict() or request.json or {}
    event  = data.get("event", "")
    caller = data.get("caller_id", "Неизвестный")
    call_id = data.get("pbx_call_id", "")
    if event not in ("NOTIFY_END", "NOTIFY_RECORD"):
        return jsonify({"status": "skip"})
    import hashlib, hmac
    params = f"pbx_call_id={call_id}&lifetime=1800"
    sign = hmac.new(ZADARMA_SECRET_KEY.encode(), f"/v1/pbx/record/request/?{params}".encode(), hashlib.sha1).hexdigest()
    rec = requests.get("https://api.zadarma.com/v1/pbx/record/request/",
        params={"pbx_call_id": call_id, "lifetime": 1800},
        headers={"Authorization": f"{ZADARMA_USER_KEY}:{sign}"}, timeout=15)
    if rec.status_code != 200:
        send_telegram("⚠️ Запись недоступна", caller=caller)
        return jsonify({"status": "no_record"})
    audio = rec.content
    transcript = transcribe(audio)
    if not transcript:
        send_telegram("🔇 Тишина в записи", audio_bytes=audio, caller=caller)
        return jsonify({"status": "silence"})
    ai = ask_claude(transcript)
    send_telegram(f"🗣 <b>Сказал:</b>\n{transcript}\n\n🤖 <b>Claude:</b>\n{ai}", audio_bytes=audio, caller=caller)
    return jsonify({"status": "ok"})

@app.route("/health")
def health():
    return jsonify({"status": "running", "time": datetime.now().isoformat()})

@app.route("/test")
def test():
    send_telegram("✅ Автоответчик работает!", caller="test")
    return jsonify({"status": "sent"})

if __name__ == "__main__":
    print("🤖 Автоответчик запущен на порту 5000")
    app.run(host="0.0.0.0", port=5000)
