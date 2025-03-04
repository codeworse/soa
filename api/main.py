from flask import Flask, request, jsonify, Response
import requests
import json

app = Flask('api')

@app.route('/login', methods=["POST"])
@app.route('/signup', methods=["POST"])
@app.route('/get_info', methods=["GET"])
@app.route('/set_info', methods=["PUT"])
@app.route('/logout', methods=["POST"])
@app.route('/update', methods=["POST"])
def redirect_auth():
    res = requests.request(url='http://auth_service:5000' + request.path,
                           method=request.method,
                           headers={key: value for (key, value) in request.headers if key != 'Host'},
                           data=request.get_data(),
                           cookies=request.cookies)
    return jsonify(response=json.loads(res.text)), res.status_code


app.run(host="0.0.0.0", debug=True)
