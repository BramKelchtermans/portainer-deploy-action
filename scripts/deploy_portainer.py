import os
import sys
import json
import requests
import uuid

def get_environment_id(portainer_url, api_key, environment_name):
    env_map = requests.get(f'{portainer_url}/api/endpoints', headers={'X-API-Key': f'{api_key}'}, verify=False).json()
    environment = next((env for env in env_map if env['Name'] == environment_name), None)
    return environment['Id'] if environment else None

def get_stacks(portainer_url, api_key, environment_id):
    headers = {
        'X-API-Key': f'{api_key}'
    }
    response = requests.get(f'{portainer_url}/api/stacks', headers=headers, params={'filters': json.dumps({'EndpointId': environment_id})}, verify=False)
    return response.json()

def create_stack(portainer_url, api_key, environment_id, stack_name, compose_file_path, repository_url, repository_username, repository_password):
    headers = {
        'X-API-Key': f'{api_key}',
        'Content-Type': 'application/json'
    }
    randUuid = uuid.uuid4()

    data = {
        "name": stack_name,
        "repositoryURL": repository_url,
        "repositoryUsername": repository_username,
        "repositoryPassword": repository_password,
        "repositoryAuthentication": True,
        "composeFile": compose_file_path,
        "autoUpdate": {
            "webhook": str(randUuid)
        }
    }

    response = requests.post(f'{portainer_url}/api/stacks?type=2&method=repository&endpointId=' + str(environment_id), headers=headers, json=data, verify=False)
    return response.status_code, response.json()

def parse_environment_file(environment_file):
    with open(environment_file, 'r') as file:
        environment = file.read()
        
    environment = environment.split('\n')
    environment = [x for x in environment if x]
    environment = [x.split('=') for x in environment]
    environment = [{"name": x[0], "value": x[1]} for x in environment]
    return environment

def update_stack(portainer_url, endpoint_id, api_key, stack_id, webhook_uuid, file_path, environment_file):
    headers = {
        'X-API-Key': f'{api_key}'
    }
    with open(file_path, 'r') as file:
        compose_file = file.read()
        print(f"Updating stack {stack_id} with compose file {compose_file}...")
    
    webhook_url = f'{portainer_url}/api/stacks/webhooks/{webhook_uuid}'
    if environment_file is not None and environment_file != "":
        webhook_url += '?'
        environment = parse_environment_file(environment_file)
        # add parameters to url
        for env in environment:
            webhook_url += f'{env["name"]}={env["value"]}&'
        
    print(f"Triggering webhook {webhook_url}...")
    response = requests.post(webhook_url, verify=False, headers=headers)
    return response.status_code, response.text

def main():
    if len(sys.argv) != 8:
        print(f"Expected 7 arguments but got {len(sys.argv) - 1}")
        print("Arguments received:", sys.argv)
        sys.exit(1)

    print("Starting deployment script...")

    portainer_url = sys.argv[1]
    api_key = sys.argv[2]
    changed_files_path = sys.argv[3]
    
    repository_url = sys.argv[4]
    repository_username = sys.argv[5]
    repository_password = sys.argv[6]
    environment_file = sys.argv[7]

    if not changed_files_path or not os.path.isfile(changed_files_path):
        print(f"Changed files path is invalid or file not found: {changed_files_path}")
        sys.exit(1)

    with open(changed_files_path, 'r') as file:
        changed_files = file.readlines()

    for file_path in changed_files:
        file_path = file_path.strip()
        if file_path.endswith("docker-compose.yml"):
            parts = file_path.split('/')
            if len(parts) >= 2:
                environment_name = parts[0]
                stack_name = parts[1]
                environment_id = get_environment_id(portainer_url, api_key, environment_name)

                if environment_id is None:
                    print(f"Environment {environment_name} not found in environment map.")
                    sys.exit(1)

                stacks = get_stacks(portainer_url, api_key, environment_id)
                stack = next((stack for stack in stacks if stack['Name'] == stack_name and stack['EndpointId'] == environment_id), None)
                print(f"Stack {stack_name} found in environment {environment_name}: {stack}")

                if stack:
                    # Stack exists, update it
                    status_code, response = update_stack(portainer_url, environment_id, api_key, stack['Id'], stack['AutoUpdate']['Webhook'], file_path, environment_file)
                    if status_code == 500:
                        print(f"Failed to update stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")
                        sys.exit(1)
                    print(f"Updated stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")
                else:
                    # Stack does not exist, create it
                    print(f"Creating stack {stack_name} in environment {environment_name}...")
                    status_code, response = create_stack(portainer_url, api_key, environment_id, stack_name, file_path, repository_url, repository_username, repository_password)
                    if status_code == 500:
                        print(f"Failed to create stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")
                        sys.exit(1)
                    print(f"Created stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")

if __name__ == "__main__":
    main()
