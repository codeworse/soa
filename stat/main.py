from flask import Flask, jsonify, request, Response
from clickhouse_driver import Client
from confluent_kafka import Consumer
import requests, logging, time, json, grpc
from proto import stat_pb2, stat_pb2_grpc
from concurrent import futures
from threading import Thread

app = Flask('stat')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_db_connection(max_retries=5, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            conn = Client(host="clickhouse-server", port=9000, user="default", password="default", database="default")
            conn.execute(
                 "CREATE TABLE IF NOT EXISTS actions (post_id Int NOT NULL, user_id Int NOT NULL, type String NOT NULL, date String NOT NULL) ENGINE=MergeTree ORDER BY date"
            )
            return conn
        except:
            retries += 1
            print(f"Connection failed (attempt {retries}/{max_retries})")
            time.sleep(delay)
    raise Exception("Failed to connect to the database after multiple retries")


conn_db = get_db_connection()


class KafkaConsumer:
    def __init__(self, server):
        self.consumer = Consumer({'bootstrap.servers': server, "group.id": "stat-consumer"})
        self.topics = ["user_registration", "like", "views", "comment"]
        self.running = False

    def process_message(self, msg):
        try:
            value = json.loads(msg.value().decode('utf-8'))
            return value
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return None
    
    def execute_message(self, data):
        event_type = data.get("event_type")
        user_id = data.get("user_id")
        post_id = data.get("post_id")
        date = str(data.get("timestamp"))

        logging.info(f"date: {date}")

        if event_type == "user_registration":
            return

        query = f"INSERT INTO actions VALUES ({post_id}, {user_id}, \'{event_type}\', toString(toDate(\'{date}\')))"
        conn_db.execute(query)

    def run(self):
        logging.info("Start running...")
        self.running = True
        self.consumer.subscribe(self.topics)
        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue

                if msg.error():
                    raise Exception(msg.error())
                
                data = self.process_message(msg)
                if data is None:
                    continue

                logging.info(data)

                self.execute_message(data)                

            except:
                continue

class StatService(stat_pb2_grpc.StatServiceServicer):
    def get_info(self, request, context):
        post_id = int(request.post_id)
        event_type = str(request.event_type)
        data = dict()
        data["view"] = 0
        data["like"] = 0
        data["comment"] = 0
        query = f"SELECT count(*) FROM actions WHERE (post_id == {post_id}) AND (type == \'{event_type}\')"
        logging.info(query)
        res = conn_db.execute(query)
        logging.info(res)
        data[event_type] = res[0][0]
        return stat_pb2.stat_info(
            views=data["view"],
            likes=data["like"],
            comments=data["comment"]
        )
    def get_dynamic_info(self, request, context):
        post_id = int(request.post_id)
        event_type = str(request.event_type)

        query = f"SELECT date, count(*) FROM actions WHERE (post_id == {post_id}) AND (type == \'{event_type}\') GROUP BY date"
        logging.info(query)

        res = conn_db.execute(query)

        logging.info(res)

        ans = []
        for c in res:
            data = dict()
            data["view"] = 0
            data["like"] = 0
            data["comment"] = 0
            data[event_type] = c[1]
            stat = stat_pb2.stat_info(
                views=data["view"],
                likes=data["like"],
                comments=data["comment"]
            )
            daily_stat = stat_pb2.daily_stat(
                date=c[0],
                stat=stat
            )
            ans.append(daily_stat)
        return stat_pb2.dynamic_stat_info(
            stat=ans
        )
    
    def get_top(seld, request, context):
        event_type = str(request.event_type)
        sort_posts = bool(request.posts)
        limit = int(request.k)
        ans = []
        if sort_posts:
            query = f"SELECT post_id, count(*) AS counter FROM actions GROUP BY post_id ORDER BY counter"
            res = conn_db.execute(query)
            for c in res:
                ans.append(c[0])
        else:
            query = f"SELECT user_id, count(*) AS counter FROM actions GROUP BY user_id ORDER BY counter"
            res = conn_db.execute(query)
            for c in res:
                ans.append(c[0])
        return stat_pb2.top_rating(
            ids=ans
        )

def run_service():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    stat_pb2_grpc.add_StatServiceServicer_to_server(StatService(), server)
    server.add_insecure_port("0.0.0.0:50051")
    logging.info("Start at address: 0.0.0.0:50051")
    server.start()
    server.wait_for_termination()

class StatServer:
    def __init__(self):
        self.consumer = KafkaConsumer('kafka:9092')
        self.service_thread = Thread(target=run_service)
        self.service_thread.start()

    def start(self):
        self.consumer.run()
        self.service_thread.join()

server = StatServer()
server.start()
