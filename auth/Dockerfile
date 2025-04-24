FROM ubuntu:24.04
RUN DEBIAN_FRONTEND="noninteractive" apt update -y 
RUN DEBIAN_FRONTEND="noninteractive" apt install -y git python3-dev python3-venv python3-pip postgresql-client
RUN apt-get -y install libssl-dev
COPY . service
RUN cd service && pip3 install -r requirements.txt --break-system-packages
ENTRYPOINT [ "bash", "/service/startup.bash" ]
