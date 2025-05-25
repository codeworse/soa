FROM python:3.9-slim
COPY requirements.txt .
RUN pip3 install -r requirements.txt --break-system-packages
COPY . .
RUN python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. proto/stat.proto
ENTRYPOINT [ "bash", "startup.bash" ]