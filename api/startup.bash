set -eEx
export SECRET_KEY=$(cat /secret_key.key)
python3 main.py