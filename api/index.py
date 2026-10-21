from flask import Flask
app = Flask(__name__)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def main(path):
    return "Tes aktif", 200