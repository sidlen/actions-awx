import os
import sys
import io
import json
import requests
import base64
import boto3
from botocore.client import Config


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
        headers = {
          'X-Consul-Token': tofu_state_consul_token
        }
        data = requests.get(f'{tofu_state_consul_scheme}://{tofu_state_consul_address}/v1/kv/opentofu/{tofu_state_consul_path}.tfstate', headers=headers)
        encoded_tofu_state = data.json()[0]['Value']
        return json.loads(base64.b64decode(encoded_tofu_state).decode('utf-8'))


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