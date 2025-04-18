from flask import Flask

app = Flask(__name__)

@app.route('/')
def hey_there():
    return "To the wall."

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
