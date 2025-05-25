from flask import Flask, jsonify, request, Response
import requests, logging
import psycopg2, os, time
import psycopg2.extras
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from proto import act_pb2, act_pb2_grpc
import grpc
from concurrent import futures

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger('grpc').setLevel(logging.DEBUG)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

SERVER_CONFIG = {
    "host": os.getenv("SERVER_HOST"),
    "port": os.getenv("SERVER_PORT")
}

def get_db_connection(max_retries=10, delay=2):
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

conn_db = get_db_connection(max_retries=10, delay=2)

class PostService(act_pb2_grpc.PostServiceServicer):
    def create_post(self, request, context):
        title = str(request.title)
        description = str(request.description)
        author_id = int(request.author_id)
        private_flag = bool(request.private_flag)
        tags = "|".join(list(request.tags))
        cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        logging.info("Trying to create post: (%s, %s, %s, %s, %s)", title, description, author_id, private_flag, tags)
        try:
            cursor.execute("INSERT INTO posts (title, description, author_id, private_flag, tags) VALUES (%s, %s, %s, %s, %s)", (title, description, author_id, private_flag, tags))
            conn_db.commit()
            cursor.execute("SELECT post_id FROM posts WHERE title = %s", (title,))
            post_id = cursor.fetchone()['post_id']
            logging.info("Create post \"%s\" with id = %s", title, post_id)
            cursor.close()
            return act_pb2.act_response(
                status=200,
                msg="Success",
                post_id=post_id
            )
        except:
            logging.info("Couldn't add post \"%s\"", title)
            cursor.close()
            return act_pb2.act_response(
                status=404,
                msg="Couldn't create post",
                post_id = 0
            )
    def get_post(self, request, context):
        post_id = request.post_id
        user_id = request.user_id
        cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM posts WHERE post_id = %s AND (author_id = %s OR private_flag = TRUE)", (post_id, user_id))
        info = cursor.fetchone()
        if info is None:
            logging.info("Couldn't find post with id = %s", post_id)
            cursor.close()
            return act_pb2.get_post_res(
                status=404,
                msg="Couldn't find post"
            )
        logging.info("Could find post with id = %s", post_id)
        cursor.close()
        post_res = act_pb2.post_info(
            post_id=info["post_id"],
            title=info["title"],
            description=info["description"],
            author_id=info["author_id"],
            created_at=str(info["created_at"]),
            updated_at=str(info["updated_at"]),
            private_flag=info["private_flag"],
            tags=info["tags"].split("|")
        )
        return act_pb2.get_post_res(
            post=post_res,
            status=200,
            msg="Success"
        )

    def delete_post(self, request, context):
        post_id = request.post_id
        cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT post_id FROM posts WHERE post_id = %s", (post_id,))
        if cursor.fetchone() is None:
            cursor.close()
            return act_pb2.act_response(
                status=404,
                msg="Post was not found"
            )
        cursor.execute("DELETE FROM posts WHERE post_id = %s", (post_id,))
        conn_db.commit()
        logging.info("Post %s was deleted", post_id)
        cursor.close()
        return act_pb2.act_response(
            status=200,
            msg="Post was deleted"
        )
    
    def update_post(self, request, context):
        post_id = request.post_id
        user_id = request.user_id
        cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            query = cursor.mogrify("UPDATE posts SET (title, description, private_flag, tags) = (%s, %s, %s, %s)" + " WHERE post_id = %s AND author_id = %s", 
                        (request.title, request.description, request.private_flag, "|".join(request.tags), post_id, user_id))
            logging.info(query)
            cursor.execute("UPDATE posts SET (title, description, private_flag, tags) = (%s, %s, %s, %s)" + " WHERE post_id = %s AND author_id = %s", 
                       (request.title, request.description, request.private_flag, "|".join(request.tags), post_id, user_id))
            
        except:
            cursor.close()
            return act_pb2.act_response(
                status=404,
                msg="Post was not found"
            )
        cursor.close()
        return act_pb2.act_response(
            status=200,
            msg="Post was updated"
        )
    def get_post_list(self, request, context):
        page_size = int(request.page_size)
        page_count = int(request.page_count)
        offset = int(request.offset)
        user_id = int(request.user_id)
        logging.info(f"offset {offset}, page_size {page_size}, page_count {page_count}")
        cursor = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM posts WHERE author_id = %s OR private_flag = FALSE", (user_id,))
        info = cursor.fetchall()
        if info is None:
            logging.info("Empty posts list")
            cursor.close()
            return act_pb2.post_list(
                posts=[]
            )
        logging.info("Searching for post")
        cur_offset = 0
        out_posts = []
        for post in info:
            if cur_offset >= offset and cur_offset < offset + page_size * page_count:
                logging.info("Find post")
                out_posts.append(act_pb2.post_info(
                    title=str(post['title']),
                    description=str(post['description']),
                    author_id=int(post['author_id']),
                    created_at=str(post["created_at"]),
                    updated_at=str(post['updated_at']),
                    private_flag=bool(post['private_flag']),
                    tags=str(post['tags']).split('|')
                ))
            cur_offset += len(post["description"])
        cursor.close()
        return act_pb2.post_list(
            posts=out_posts
        )
            

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
act_pb2_grpc.add_PostServiceServicer_to_server(PostService(), server)
server.add_insecure_port(SERVER_CONFIG["host"] + ":" + SERVER_CONFIG["port"])
logging.info("Start at address: " + SERVER_CONFIG["host"] + ":" + SERVER_CONFIG["port"])
server.start()
server.wait_for_termination()
