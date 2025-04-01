from flask import Flask, request, jsonify, Response
import requests
import json
from proto import act_pb2, act_pb2_grpc
import grpc
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

app = Flask('api')
with open("secret_key.key") as f:
    app.config["JWT_SECRET_KEY"] = f.readline()
jwt = JWTManager(app)

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

def post_to_dict(post):
    return {
        "title": str(post.title),
        "description": str(post.description),
        "author_id": int(post.author_id),
        "created_at": str(post.created_at),
        "updated_at": str(post.updated_at),
        "private_flag": bool(post.private_flag),
        "tags": list(post.tags)
    }

@app.route('/post/create', methods=["POST"])
@jwt_required()
def create_post():
    user_id = get_jwt_identity().split("#")[1]
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)
    data = request.get_json()
    app.logger.info("user(%s) creating post with title \"%s\"", user_id, data.get("title"))
    res = act_stub.create_post(act_pb2.create_post_req(
        title=data.get("title"),
        description=data.get("description"),
        author_id=int(user_id),
        private_flag=bool(data.get("private_flag")),
        tags=data.get("tags")
    ))
    return jsonify(response={"status": res.status, "msg": res.msg, "post_id": res.post_id}), res.status

@app.route('/post/get', methods=["GET"])
@jwt_required()
def get_info():
    data = request.get_json()
    post_id = int(data.get("post_id"))
    user_id = int(get_jwt_identity().split("#")[1])
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)
    res = act_stub.get_post(act_pb2.post_id_info(
        post_id=post_id,
        user_id=user_id
    ))
    if res.status != 200:
        return jsonify(response={"msg": res.msg}), res.status
    return jsonify(response=post_to_dict(res.post)), res.status

@app.route('/post/update', methods=["PUT"])
@jwt_required()
def update_post():
    data = request.get_json()
    post_id = int(data.get("post_id"))
    user_id = int(get_jwt_identity().split("#")[1])
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)

    
    res = act_stub.update_post(act_pb2.update_post_req(
        post_id=int(post_id),
        user_id=int(user_id),
        title=data.get("title"),
        description=data.get("description"),
        private_flag=bool(data.get("private_flag")),
        tags=data.get("tags")
    ))
    return jsonify(response={"msg": res.msg}), res.status

@app.route("/post/delete", methods=["DELETE"])
@jwt_required()
def delete_post():
    data = request.get_json()
    post_id = int(data.get("post_id"))
    user_id = int(get_jwt_identity().split("#")[1])
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)
    res = act_stub.delete_post(act_pb2.post_id_info(
        post_id=post_id,
        user_id=user_id
    ))
    return jsonify(response={"msg": res.msg}), res.status

@app.route("/post/get_list", methods=["GET"])
@jwt_required()
def get_post_list():
    data = request.get_json()
    user_id = int(get_jwt_identity().split("#")[1])
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)
    res = act_stub.get_post_list(act_pb2.page_info(
        page_size=data.get("page_size"),
        page_count=data.get("page_count"),
        offset=data.get("offset"),
        user_id=user_id
    ))
    out = res.posts
    out_json = []
    for post in out:
        out_json.append(post_to_dict(post))
    return jsonify(response=out_json), 200


app.run(host="0.0.0.0", debug=True)
