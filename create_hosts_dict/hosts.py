import os
import sys
import io
import json
import requests
import base64
import boto3
from botocore.client import Config


def download_chunk(consul_url, headers):
    response = requests.get(consul_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    encoded = data[0]['Value']
    return base64.b64decode(encoded).decode('utf-8')

def download_state_from_consul(consul_address, consul_scheme, access_token, state_key):

    base_url = f"{consul_scheme}://{consul_address}/v1/kv/opentofu/{state_key}.tfstate"
    headers = {'X-Consul-Token': access_token} if access_token else {}

    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        print("Failed to download state file from Consul.")
        exit(1)

    data = response.json()[0]
    decoded_data = base64.b64decode(data['Value']).decode('utf-8')

    try:
        obj = json.loads(decoded_data)
    except json.JSONDecodeError:
        with open('terraform_state.json', 'w') as f:
            f.write(decoded_data)
        print("State file downloaded from Consul")
        return json.loads(decoded_data)

    if 'chunks' in obj:
        chunks = obj['chunks']
        full_state = ''
        for chunk_key in chunks:
            chunk_url = f"{consul_scheme}://{consul_address}/v1/kv/{chunk_key}"
            chunk_data = download_chunk(chunk_url, headers)
            full_state += chunk_data
        with open('terraform_state.json', 'w') as f:
            f.write(full_state)
        print("State file downloaded from Consul")
        return json.loads(full_state)
    else:
        with open('terraform_state.json', 'w') as f:
            f.write(decoded_data)
        print("State file downloaded from Consul")
        return json.loads(decoded_data)

def getFileFromS3(tofu_state_s3_address, tofu_state_s3_key, tofu_state_s3_secret, tofu_state_s3_bucket, tofu_state_s3_path):
  s3_client = boto3.client(
                            's3',
                            endpoint_url="https://" + tofu_state_s3_address,
                            aws_access_key_id=tofu_state_s3_key,
                            aws_secret_access_key=tofu_state_s3_secret,
                            config=Config(signature_version='s3v4'),
                            region_name='us-east-1'
                          )
  file_obj = io.BytesIO()
  s3_client.download_fileobj(tofu_state_s3_bucket, tofu_state_s3_path + ".tfstate", file_obj)
  file_obj.seek(0)
  return json.load(file_obj)


def getTFState(
  tofu_state_url,
  tofu_state_path,
  tofu_state_backend,
  tofu_state_s3_address,
  tofu_state_s3_bucket,
  tofu_state_s3_path,
  tofu_state_s3_key,
  tofu_state_s3_secret,
  tofu_state_consul_address,
  tofu_state_consul_scheme,
  tofu_state_consul_token,
  tofu_state_consul_path
):
  if not tofu_state_backend:
    if not tofu_state_url:
      if not tofu_state_path:
        raise ValueError("укажите state_url, state_path или backend_type")
      else:
        with open(tofu_state_path, "r") as file:
          return json.load(file)
    else:
      return requests.get(f'{tofu_state_url}')
  else:
    if tofu_state_backend.lower() != "consul":
      if tofu_state_backend.lower() != "s3":
        raise ValueError("параметр backend_type должен быть или s3, или consul")
      else:
        if all([
          tofu_state_s3_address,
          tofu_state_s3_bucket,
          tofu_state_s3_path,
          tofu_state_s3_key,
          tofu_state_s3_secret
        ]):
          return getFileFromS3(tofu_state_s3_address, tofu_state_s3_key, tofu_state_s3_secret, tofu_state_s3_bucket, tofu_state_s3_path)
    else:
      if all([
        tofu_state_consul_address,
        tofu_state_consul_scheme,
        tofu_state_consul_token,
        tofu_state_consul_path
      ]):
        return download_state_from_consul(tofu_state_consul_address, tofu_state_consul_scheme, tofu_state_consul_token, tofu_state_consul_path)


def extract_host_data(state_file):
  hosts_data = {}
  for resource in state_file['resources']:
      if resource['type'] == 'vsphere_virtual_machine' and resource['name'] == 'vm':
          for instance in resource['instances']:
              hostname = instance['attributes']['name'] # add this to use FQDN # + "." + instance['attributes']['clone'][0]['customize'][0]['linux_options'][0]['domain']
              ip_address = instance['attributes']['default_ip_address']
              if ip_address:
                  hosts_data[hostname] = {
                    'address': ip_address,
                    'group': resource['module'].removeprefix('module.'),
                    'variables': {},
                    'disks': []
                  }
                  for disk in instance['attributes']['disk']:
                    hosts_data[hostname]['disks'].append({
                      'label': disk['label'],
                      'uuid': disk['uuid'],
                      'size': disk['size'],
                      'controller_type': disk['controller_type']
                    })
      elif resource['type'] == 'vcd_vapp_vm' and resource['name'] == 'vm':
          for instance in resource['instances']:
              hostname = instance['attributes']['name']
              for net_adapter in instance['attributes']['network']:
                if net_adapter["connected"]:
                  ip_address = net_adapter['ip']
              if ip_address:
                  hosts_data[hostname] = {
                    'address': ip_address,
                    'group': resource['module'].removeprefix('module.'),
                    'variables': {},
                    'disks': []
                  }
                  for disk in instance['attributes']['internal_disk']:
                    hosts_data[hostname]['disks'].append({
                      'unit_number': disk['unit_number'],
                      'disk_id': disk['disk_id'],
                      'size_in_mb': disk['size_in_mb']
                    })
  for resource in state_file['resources']:
    if resource['type'] == 'terraform_data' and resource['name'] == 'awx_vars_storage':
      for instance in resource['instances']:
        hostname = instance['attributes']['output']['value']['vm_name']
        if hosts_data[hostname]['address'] == instance['attributes']['output']['value']['vm_ip']:
          hosts_data[hostname]['variables'].update(instance['attributes']['output']['value'])
          del hosts_data[hostname]['variables']['vm_ip']
          del hosts_data[hostname]['variables']['vm_name']
          del hosts_data[hostname]['variables']['vm_uuid']
  return hosts_data

def main() -> None:
  tofu_state_url = os.getenv('TOFU_STATE_URL')
  tofu_state_path = os.getenv('TOFU_STATE_PATH')
  tofu_state_backend = os.getenv('TOFU_STATE_BACKEND_TYPE')
  tofu_state_s3_address = os.getenv('TOFU_S3_ADDRESS')
  tofu_state_s3_bucket = os.getenv('TOFU_S3_BUCKET')
  tofu_state_s3_path = os.getenv('TOFU_S3_PATH')
  tofu_state_s3_key = os.getenv('TOFU_S3_KEY')
  tofu_state_s3_secret = os.getenv('TOFU_S3_SECRET')
  tofu_state_consul_address = os.getenv('TOFU_CONSUL_ADDRESS')
  tofu_state_consul_scheme = os.getenv('TOFU_CONSUL_SCHEME')
  tofu_state_consul_token = os.getenv('TOFU_CONSUL_TOKEN')
  tofu_state_consul_path = os.getenv('TOFU_CONSUL_PATH')
    
  tofu_state = getTFState(tofu_state_url,
                          tofu_state_path,
                          tofu_state_backend,
                          tofu_state_s3_address,
                          tofu_state_s3_bucket,
                          tofu_state_s3_path,
                          tofu_state_s3_key,
                          tofu_state_s3_secret,
                          tofu_state_consul_address,
                          tofu_state_consul_scheme,
                          tofu_state_consul_token,
                          tofu_state_consul_path
                          )

  hosts_data = extract_host_data(tofu_state)
  print(json.dumps(hosts_data, ensure_ascii=False))
  with open("hosts.json", "w", encoding="utf-8") as file:
    file.write(json.dumps(hosts_data, ensure_ascii=False))
  with open("output.json", "w", encoding="utf-8") as file:
    file.write(json.dumps(json.dumps(hosts_data, ensure_ascii=False)))

if __name__ == "__main__":
    main()