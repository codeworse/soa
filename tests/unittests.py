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

unittest.main()