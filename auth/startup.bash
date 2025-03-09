set -eEx
export SECRET_KEY=$(cat /service/secret_key.key)
python3 service/src/main.py
