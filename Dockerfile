FROM python:3.8-slim

# Copy the script into the container
COPY scripts /scripts

# Install required Python packages
RUN pip install requests

# Set the working directory
WORKDIR /scripts

# Set the entrypoint to the script
ENTRYPOINT ["python", "deploy_portainer.py"]
