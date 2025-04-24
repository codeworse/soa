import unittest, requests, json, string, random
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
    
class TestAuthentication(unittest.TestCase):
    def test_registration(self):
        headers = requests.utils.default_headers()

        user_data = {"username" : id_generator(), "email": id_generator(), "password": id_generator()}
        res = requests.post("http://localhost:8002/signup", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        res = requests.post("http://localhost:8002/login", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        access_token = json.loads(res.text)["response"]["access_token"]
        headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )

        res = requests.get("http://localhost:8002/get_info", headers=headers, json={})
        self.assertEqual(res.status_code, 200)

        res = requests.post("http://localhost:8002/update", headers=headers, json={})
        self.assertEqual(res.status_code, 200)
        access_token = json.loads(res.text)["response"]["access_token"]
        headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )

        res = requests.get("http://localhost:8002/get_info", headers=headers, json={})
        self.assertEqual(res.status_code, 200)

        res = requests.post("http://localhost:8002/logout", headers=headers, json={})
        self.assertEqual(res.status_code, 200)

    def test_info(self):
        headers = requests.utils.default_headers()
        user_data = {"username" : id_generator(), "email": id_generator(), "password": id_generator()}
        res = requests.post("http://localhost:8002/signup", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        res = requests.post("http://localhost:8002/login", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        access_token = json.loads(res.text)["response"]["access_token"]
        headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )
        res = requests.get("http://localhost:8002/get_info", headers=headers, json={})
        self.assertEqual(res.status_code, 200)

        res = requests.put("http://localhost:8002/set_info", headers=headers, json={"first_name": "Yura", "second_name": "Borisov"})
        self.assertEqual(res.status_code, 200)

        res = requests.get("http://localhost:8002/get_info", headers=headers, json={})
        data = json.loads(res.text)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["response"]["info"]["first_name"], "Yura")
        self.assertEqual(data["response"]["info"]["second_name"], "Borisov")
        res = requests.post("http://localhost:8002/logout", headers=headers, json={})
        self.assertEqual(res.status_code, 200)
    def test_bad_request(self):
        headers = requests.utils.default_headers()
        user_data = {"username" : id_generator(), "email": id_generator(), "password": id_generator()}
        res = requests.post("http://localhost:8002/login", headers=headers, json=user_data)
        self.assertNotEqual(res.status_code, 200)
        res = requests.get("http://localhost:8002/get_info", headers=headers, json={})
        self.assertNotEqual(res.status_code, 200)
class TestPost(unittest.TestCase):
    def test_create_get(self):
        headers = requests.utils.default_headers()

        user_data = {"username" : id_generator(), "email": id_generator(), "password": id_generator()}
        res = requests.post("http://localhost:8002/signup", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        res = requests.post("http://localhost:8002/login", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        access_token = json.loads(res.text)["response"]["access_token"]
        headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )
        post_json = {"title": id_generator(), "description": "...", "private_flag": False, "tags": ["Some"]}
        res = requests.post("http://localhost:8002/post/create", headers=headers, json=post_json)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.text)
        post_id_json = {"post_id": data["response"]["post_id"]}

        res = requests.get("http://localhost:8002/post/get", headers=headers, json=post_id_json)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.text)["response"]
        self.assertEqual(data["title"], post_json["title"])
        self.assertEqual(data["description"], post_json["description"])
        self.assertEqual(data["private_flag"], post_json["private_flag"])
        self.assertEqual(data["tags"], post_json["tags"])

        res = requests.post("http://localhost:8002/logout", headers=headers, json={})

    def test_bad_create(self):
        headers = requests.utils.default_headers()
        post_json = {"title": id_generator(), "description": "...", "private_flag": False, "tags": []}
        res = requests.post("http://localhost:8002/post/create", headers=headers, json=post_json)
        self.assertNotEqual(res.status_code, 200)

    def test_update_delete(self):
        headers = requests.utils.default_headers()
        user_data = {"username" : id_generator(), "email": id_generator(), "password": id_generator()}
        res = requests.post("http://localhost:8002/signup", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        res = requests.post("http://localhost:8002/login", headers=headers, json=user_data)
        self.assertEqual(res.status_code, 200)
        access_token = json.loads(res.text)["response"]["access_token"]
        headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )
        post_json = {"title": id_generator(), "description": "...", "private_flag": False, "tags": ["Some"]}
        res = requests.post("http://localhost:8002/post/create", headers=headers, json=post_json)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.text)
        new_post = {"post_id": data["response"]["post_id"], "title": id_generator(), "description": "...", "private_flag": True, "tags": ["Some", "NewSome"]}

        res = requests.put("http://localhost:8002/post/update", headers=headers, json=new_post)
        self.assertEqual(res.status_code, 200)
        post_id_json = {"post_id": data["response"]["post_id"]}

        res = requests.get("http://localhost:8002/post/get", headers=headers, json=post_id_json)
        data = json.loads(res.text)
        self.assertEqual(data["response"]["title"], new_post["title"])


        page_info = {"page_size": 20, "page_count": 20, "offset": 0}
        res = requests.get("http://localhost:8002/post/get_list", headers=headers, json=page_info)
        data = json.loads(res.text)
        self.assertEqual(len(data['response']), 1)
        
        res = requests.delete("http://localhost:8002/post/delete", headers=headers, json=post_id_json)
        self.assertEqual(res.status_code, 200)

        res = requests.get("http://localhost:8002/post/get", headers=headers, json=post_id_json)
        self.assertNotEqual(res.status_code, 200)
class TestKafka(unittest.TestCase):
    def test_kafka_events(self):
        headers = requests.utils.default_headers()
        event_data = {"user_id": "id", "date": "date"}
        res = requests.post("http://localhost:8002/event/user_registration", headers=headers, json=event_data)
        self.assertEqual(res.status_code, 200)

        event_data = {"user_id": "user_id", "post_id": "post_id"}
        res = requests.post("http://localhost:8002/event/like", headers=headers, json=event_data)
        self.assertEqual(res.status_code, 200)

        event_data = {"user_id": "user_id", "post_id": "post_id"}
        res = requests.post("http://localhost:8002/event/view", headers=headers, json=event_data)
        self.assertEqual(res.status_code, 200)

        event_data = {"user_id": "user_id", "post_id": "post_id", "comment_id": "comment_id"}
        res = requests.post("http://localhost:8002/event/comment", headers=headers, json=event_data)
        self.assertEqual(res.status_code, 200)

unittest.main()