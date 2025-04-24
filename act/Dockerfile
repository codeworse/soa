FROM python:3.9-slim
COPY . .
RUN pip3 install -r requirements.txt --break-system-packages
RUN python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. proto/act.proto
ENTRYPOINT [ "python3", "main.py" ]