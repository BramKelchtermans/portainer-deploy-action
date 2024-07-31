FROM python:3.8-slim

COPY scripts /scripts

RUN pip install requests

ENTRYPOINT ["python", "/scripts/deploy_portainer.py"]
