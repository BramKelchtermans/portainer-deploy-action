import os
import sys
import json
import requests

def get_environment_id(environment_name, environment_map):
    env_map = json.loads(environment_map)
    return env_map.get(environment_name)

def get_stacks(portainer_url, api_key, environment_id):
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.get(f'{portainer_url}/api/stacks', headers=headers, params={'filters': json.dumps({'EnvironmentId': environment_id})})
    return response.json()

def create_stack(portainer_url, api_key, environment_id, stack_name, compose_file_path):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    with open(compose_file_path, 'r') as file:
        compose_content = file.read()
    
    data = {
        'Name': stack_name,
        'SwarmID': '',
        'StackFileContent': compose_content,
        'Env': [],
        'Prune': False,
    }
    response = requests.post(f'{portainer_url}/api/stacks', headers=headers, json=data, params={'type': 2, 'method': 'string', 'endpointId': environment_id})
    return response.status_code, response.json()

def update_stack(webhook_url):
    response = requests.post(webhook_url)
    return response.status_code, response.text

def main():
    if len(sys.argv) != 5:
        print(f"Expected 4 arguments but got {len(sys.argv) - 1}")
        sys.exit(1)

    portainer_url = sys.argv[1]
    api_key = sys.argv[2]
    environment_map = sys.argv[3]
    workspace = sys.argv[4]

    try:
        env_map = json.loads(environment_map)
    except json.JSONDecodeError as e:
        print(f"Error decoding environment map: {e}")
        sys.exit(1)

    for root, dirs, files in os.walk(workspace):
        for file in files:
            if file == "docker-compose.yml":
                parts = root.split('/')
                if len(parts) >= 2:
                    environment_name = parts[1]
                    stack_name = parts[2]
                    environment_id = get_environment_id(environment_name, environment_map)

                    if environment_id is None:
                        print(f"Environment {environment_name} not found in environment map.")
                        continue

                    stacks = get_stacks(portainer_url, api_key, environment_id)
                    stack = next((stack for stack in stacks if stack['Name'] == stack_name), None)

                    if stack:
                        # Stack exists, update it
                        status_code, response = update_stack(stack['Webhook'])
                        print(f"Updated stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")
                    else:
                        # Stack does not exist, create it
                        status_code, response = create_stack(portainer_url, api_key, environment_id, stack_name, os.path.join(root, file))
                        print(f"Created stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")

if __name__ == "__main__":
    main()
