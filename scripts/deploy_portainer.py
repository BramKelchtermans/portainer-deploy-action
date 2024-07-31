import os
import sys
import json
import requests

def get_environment_id(environment_name, environment_map):
    env_map = json.loads(environment_map)
    return env_map.get(environment_name)

def get_stacks(portainer_url, api_key, environment_id):
    headers = {
        'X-API-Key': f'{api_key}'
    }
    response = requests.get(f'{portainer_url}/api/stacks', headers=headers, params={'filters': json.dumps({'EnvironmentId': environment_id})}, verify=False)
    return response.json()

def create_stack(portainer_url, api_key, environment_id, stack_name, compose_file_path):
    headers = {
        'X-API-Key': f'{api_key}',
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
    response = requests.post(f'{portainer_url}/api/stacks', headers=headers, json=data, params={'type': 2, 'method': 'string', 'endpointId': environment_id}, verify=False)
    return response.status_code, response.json()

def update_stack(portainer_url, webhook_uuid):
    webhook_url = f'{portainer_url}/api/stacks/webhooks/{webhook_uuid}'
    response = requests.post(webhook_url, verify=False)
    return response.status_code, response.text

def main():
    if len(sys.argv) != 5:
        print(f"Expected 4 arguments but got {len(sys.argv) - 1}")
        print("Arguments received:", sys.argv)
        sys.exit(1)

    print("Starting deployment script...")

    portainer_url = sys.argv[1]
    api_key = sys.argv[2]
    environment_map = sys.argv[3]
    changed_files_path = sys.argv[4]

    print("portainer_url:", portainer_url)
    print("api_key:", api_key)
    print("environment_map:", environment_map)
    print("changed_files_path:", changed_files_path)

    if not changed_files_path or not os.path.isfile(changed_files_path):
        print(f"Changed files path is invalid or file not found: {changed_files_path}")
        sys.exit(1)

    try:
        env_map = json.loads(environment_map)
    except json.JSONDecodeError as e:
        print(f"Error decoding environment map: {e}")
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
                environment_id = get_environment_id(environment_name, environment_map)

                if environment_id is None:
                    print(f"Environment {environment_name} not found in environment map.")
                    sys.exit(1)
                    continue

                stacks = get_stacks(portainer_url, api_key, environment_id)
                stack = next((stack for stack in stacks if stack['Name'] == stack_name), None)
                print(f"Stack {stack_name} found in environment {environment_name}: {stack}")

                if stack:
                    # Stack exists, update it
                    status_code, response = update_stack(portainer_url, stack['AutoUpdate']['Webhook'])
                    print(f"Updated stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")
                else:
                    # Stack does not exist, create it
                    status_code, response = create_stack(portainer_url, api_key, environment_id, stack_name, file_path)
                    print(f"Created stack {stack_name} in environment {environment_name}. Status code: {status_code}. Response: {response}")

if __name__ == "__main__":
    main()
