from flask import Flask
app = Flask(__name__)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def catch_all(path): return "Bot Active", 200
