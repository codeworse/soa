from flask import Flask, jsonify, request, Response
import requests
import psycopg2, os, time
import psycopg2.extras
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
app = Flask('auth')
with open("/service/secret_key.key") as f:
    app.config["JWT_SECRET_KEY"] = f.readline()
jwt = JWTManager(app)


def get_db_connection(max_retries=5, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.OperationalError as e:
            retries += 1
            print(f"Connection failed (attempt {retries}/{max_retries}): {e}")
            time.sleep(delay)
    raise Exception("Failed to connect to the database after multiple retries")



conn_db = get_db_connection(max_retries=5, delay=5)
@app.route('/signup', methods=["POST"])
def register():
    data = request.get_json()
    try:
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        app.logger.info("%s is trying to sign up with email %s and password %s", username, email, password)
        cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("INSERT INTO logins_info (username, password, email) VALUES (%s, %s, %s)", (username, password, email))
        except:
            app.logger.info("user %s already exists", username)
            cursor.close()
            return jsonify(response={"error": "User already exists"}), 400
        conn_db.commit()
        cursor.execute("SELECT user_id FROM logins_info WHERE username = %s", (username,))
        user_id = cursor.fetchone()["user_id"];
        cursor.execute("INSERT INTO users_info (user_id) VALUES (%s)", (user_id,))
        conn_db.commit()
        cursor.close()
        return jsonify(response={"message": "Successful registration"}), 200
    except:
        app.logger.info("Couldn't register the user %s", username)
        return jsonify(response={"error": "Some register data was not provided"}), 404

@app.route('/login', methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT user_id, password FROM logins_info WHERE username = %s AND email = %s", (username, email))
    info = cursor.fetchone()
    if info is None:
        app.logger.info("User was not found")
        cursor.close()
        return jsonify(response={"error": "No user was found"}), 400
    app.logger.info("Find password %s in database for user_id %s", info["password"], info["user_id"])
    if (info['password'] != password):
        cursor.close()
        return jsonify(response={"error": "Invalid username, email or password"}), 400
    user_id = info['user_id']
    cursor.execute("INSERT INTO sessions_info (user_id) VALUES (%s)", (user_id,))
    conn_db.commit()
    cursor.execute("SELECT session_id FROM sessions_info WHERE user_id = %s", (user_id,))
    session_id = cursor.fetchone()['session_id']
    app.logger.info("session_id: %s", session_id)
    token = create_access_token(identity=str(session_id))
    cursor.close()
    return jsonify({"session_id": session_id, "user_id": info["user_id"], "access_token": token}), 200

@app.route('/get_info', methods=["GET"])
@jwt_required()
def get_info():
    # app.logger.info("auth token: %s", request.headers["Authorization"])
    session_id = get_jwt_identity()
    app.logger.info("session id: %s", session_id)
    cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT user_id FROM sessions_info WHERE session_id = %s", (session_id,))
    info = cursor.fetchone()
    if info is None:
        cursor.close()
        return jsonify({"error": "Session was not found"}), 404
    user_id = info['user_id']
    cursor.execute("SELECT * FROM users_info WHERE user_id = %s", (user_id,))
    info = cursor.fetchone()
    if info is None:
        cursor.close()
        return jsonify({"info": {}, "message": "No user info was found"}), 200
    cursor.close()
    return jsonify({"info": info}), 200

@app.route('/set_info', methods=["PUT"])
@jwt_required()
def set_info():
    session_id = get_jwt_identity()
    data = request.get_json()
    cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT user_id FROM sessions_info WHERE session_id = %s", (session_id,))
    info = cursor.fetchone()
    if info is None:
        cursor.close()
        return jsonify({"error": "Session was not found"}), 404
    user_id = info['user_id']
    columns = ['first_name', 'second_name', 'birth_date', 'address', 'age']
    values = []
    for c in columns:
        values.append(data.get(c))

    for i in range(len(columns)):
        if values[i] is None:
            continue
        cursor.execute("UPDATE users_info SET %s = %%s WHERE user_id = %%s" % columns[i], (values[i], user_id))
    conn_db.commit()
    cursor.close()
    return jsonify(response={}), 200


@app.route('/logout', methods=["POST"])
@jwt_required()
def logout():
    session_id = get_jwt_identity()
    data = request.get_json()
    cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT user_id FROM sessions_info WHERE session_id = %s", (session_id,))
    info = cursor.fetchone()
    if info is None:
        cursor.close()
        return jsonify({"error": "Session was not found"}), 404
    cursor.execute("DELETE FROM sessions_info WHERE session_id = %s", (session_id,))
    conn_db.commit()
    cursor.close()
    return jsonify(response={"msg": "session was deleted correctly"}), 200

app.run(host="0.0.0.0", debug=True)
