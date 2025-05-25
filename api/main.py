from flask import Flask, request, jsonify, Response
import requests
import json
from proto import act_pb2, act_pb2_grpc
from proto import stat_pb2, stat_pb2_grpc
import grpc
import uuid
from datetime import datetime
from confluent_kafka import Producer
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

class KafkaProducer:
    def __init__(self, server):
        self.producer = Producer({'bootstrap.servers': server})
        
    
    def callback_produce(self, err, msg):
        if err is not None:
            print("Message sending failed:", err)
        else:
            print("Success sending")

    def send_event(self, topic, data):

        json_data = json.dumps(data)
        
        self.producer.produce(
            topic=topic,
            value=json_data,
            callback=self.callback_produce
        )

        self.producer.flush()
    
    def send_registration(self, user_id, date):
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'user_registration',
            'user_id': user_id,
            'registration_date': date,
            'timestamp': datetime.now().isoformat()
        }   
        self.send_event('user_registration', event)

    def send_like(self, user_id, post_id):
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'like',
            'user_id': user_id,
            'post_id': post_id,
            'timestamp': datetime.now().isoformat()
        }
        
        self.send_event('like', event)
    
    def send_view(self, user_id, post_id):
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'view',
            'user_id': user_id,
            'post_id': post_id,
            'timestamp': datetime.now().isoformat()
        }
        
        self.send_event('views', event)
    
    def send_comment(self, user_id, post_id, comment_id):
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'comment',
            'user_id': user_id,
            'post_id': post_id,
            'comment_id': comment_id,
            'timestamp': datetime.now().isoformat()
        }
        
        self.send_event('comment', event)


app = Flask('api')
with open("secret_key.key") as f:
    app.config["JWT_SECRET_KEY"] = f.readline()
jwt = JWTManager(app)

kafka_producer = KafkaProducer('kafka:9092')

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

@app.route("/post/create_comment", methods=["POST"])
@jwt_required
def create_post_comment():
    data = request.get_json()
    user_id = int(get_jwt_identity().split("#")[1])
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)
    res = act_stub.create_comment(act_pb2.create_comment_req(
        post_id=data.get("post_id"),
        description=data.get("description"),
        author_id=user_id
    ))
    if res.status == 200:
        return jsonify(response={"msg": res.msg, "comment_id": res.comment_id}), res.status
    return jsonify(response={"msg": res.msg}), res.status_code

@app.route('/event/user_registration', methods=["POST"])
def registration_event():
    try:
        data = request.get_json()
        res = requests.request(url='http://auth_service:5000/check',
                           method="GET",
                           headers={key: value for (key, value) in request.headers if key != 'Host'},
                           data=request.get_data(),
                           cookies=request.cookies)
        if res.status_code != 200:
            raise Exception("User not found")
        kafka_producer.send_registration(data.get("user_id"), data.get("date"))
    except:
        return jsonify(response="Some error"), 500
    return jsonify(response="OK"), 200


@app.route('/event/like', methods=["POST"])
def like_event():
    data = request.get_json()
    act_channel = grpc.insecure_channel("act_service:50051")
    act_stub = act_pb2_grpc.PostServiceStub(act_channel)
    res = act_stub.check_post(act_pb2.post_id_info(
        post_id=int(data.get("post_id")),
        user_id=0
    ))
    try:
        if res.status != 200:
            raise Exception("Post not found")
        kafka_producer.send_like(data.get("user_id"), data.get("post_id"))
    except:
        return jsonify(response="Some error"), 500
    return jsonify(response="OK"), 200

@app.route('/event/view', methods=["POST"])
def view_event():
    try:
        data = request.get_json()
        act_channel = grpc.insecure_channel("act_service:50051")
        act_stub = act_pb2_grpc.PostServiceStub(act_channel)
        res = act_stub.check_post(act_pb2.post_id_info(
            post_id=int(data.get("post_id")),
            user_id=0
        ))
        if res.status != 200:
            raise Exception("Post not found")
        kafka_producer.send_view(data.get("user_id"), data.get("post_id"))
    except:
        return jsonify(response="Some error"), 500
    return jsonify(response="OK"), 200

@app.route('/event/comment', methods=["POST"])
def comment_event():
    try:
        data = request.get_json()
        act_channel = grpc.insecure_channel("act_service:50051")
        act_stub = act_pb2_grpc.PostServiceStub(act_channel)
        res = act_stub.check_post(act_pb2.post_id_info(
            post_id=int(data.get("post_id")),
            user_id=0
        ))
        if res.status != 200:
            raise Exception("Post not found")    
        res = act_stub.check_comment(act_pb2.check_comment_req(
            comment_id=int(data.get("comment_id"))
        ))
        if res.status != 200:
            raise Exception("Comment not found") 
        kafka_producer.send_comment(data.get("user_id"), data.get("post_id"), data.get("comment_id"))
    except:
        return jsonify(response="Some error"), 500
    return jsonify(response="OK"), 200

@app.route('/get_stat/<event_type>', methods=["GET"])
def get_stat(event_type):
    data = request.get_json()
    stat_channel = grpc.insecure_channel("stat_service:50051")
    stat_stub = stat_pb2_grpc.StatServiceStub(stat_channel)
    res = stat_stub.get_info(stat_pb2.post_id_info(
        post_id = int(data.get("post_id")),
        event_type=str(event_type)
    ))
    ans = 0
    if event_type == "view":
        ans = res.views
    elif event_type == "like":
        ans = res.likes
    else:
        ans = res.comments
    return jsonify(response={event_type: ans}), 200

@app.route('/get_dynamic_stat/<event_type>', methods=["GET"])
def get_dynamic_stat(event_type):
    data = request.get_json()
    stat_channel = grpc.insecure_channel("stat_service:50051")
    stat_stub = stat_pb2_grpc.StatServiceStub(stat_channel)
    res = stat_stub.get_dynamic_info(stat_pb2.post_id_info(
        post_id = int(data.get("post_id")),
        event_type=str(event_type)
    ))
    ans = []
    for stat in res.stat:
        date = str(stat.date)
        value = 0
        if event_type == "view":
            value = stat.stat.views
        elif event_type == "like":
            value = stat.stat.likes
        else:
            value = res.comments
        ans.append({"date": date, "stat": value})
    return jsonify(response=ans), 200

@app.route('/get_top/<sort_type>/<event_type>', methods=["GET"])
def get_top(sort_type, event_type):    
    stat_channel = grpc.insecure_channel("stat_service:50051")
    stat_stub = stat_pb2_grpc.StatServiceStub(stat_channel)
    sort_posts = False
    if sort_type == "posts":
        sort_posts = True
    res = stat_stub.get_top(stat_pb2.sort_type(
        event_type=event_type,
        posts=sort_posts
    ))
    result_ids = []
    for i in res.ids:
        result_ids.append(i)
    return jsonify(response=result_ids), 200
app.run(host="0.0.0.0", debug=True)
