import re

with open('autoresponder.py', 'r') as f:
    content = f.read()

old = '@app.route("/webhook", methods=["POST", "GET"])'
new = '''@app.route("/webhook", methods=["POST", "GET"])
def zd_echo_check():
    zd_echo = request.args.get("zd_echo", "")
    if zd_echo:
        return zd_echo
    return webhook()

@app.route("/webhook_real", methods=["POST"])'''

content = content.replace(old, new)
content = content.replace('def webhook():', 'def webhook():')

with open('autoresponder.py', 'w') as f:
    f.write(content)
print("Done")
