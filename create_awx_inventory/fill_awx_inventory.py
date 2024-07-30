from awxkit import api, config, utils
from collections import defaultdict
import os
import inspect
import time
import json
import argparse
import yaml
import sys

class Colors:
  HEADER = '\033[95m'  # Фиолетовый
  OKBLUE = '\033[94m'  # Синий
  OKGREEN = '\033[92m'  # Зеленый
  WARNING = '\033[93m'  # Желтый
  FAIL = '\033[91m'  # Красный
  ENDC = '\033[0m'  # Возвращает стандартный цвет текста
  BOLD = '\033[1m'  # Жирный текст
  UNDERLINE = '\033[4m'  # Подчеркнутый текст

def parse_parent(parent_str, tofu_groups, tofu_hosts):
  parent, entities_str = parent_str.split(":")
  entities = entities_str.split(",")
  child_groups = []
  child_hosts = []
  for entity in entities:
    if entity in tofu_groups:
      child_groups.append(entity)
    elif entity in tofu_hosts.keys():
      child_hosts.append(entity)
    else:
      print(f'{Colors.FAIL}Группа или хост с именем {entity} не добавлена в {parent}, т.к. отсутствует в предоставленном словаре hosts{Colors.ENDC}, пожалуйста убедитесь в правильности написания переменной окружения PARENTS_GROUPS, она должна быть строкой с подстроками, разделенными пробелом, вида PARENT_GROUP_NAME:GROUP1,FQDN2 /nгде PARENT_GROUP_NAME может быть любой строкой, а GROUP1,FQDN2 - примеры имен групп(==имя модуля) и/или FQDN хостов, существующих в словаре hosts')
  return parent, child_groups, child_hosts

def load_from_file(filepath):
  with open(filepath, "r") as file:
    return json.load(file)

def getParentGroups(parents_groups_str, tofu_grops, tofu_hosts):
  list_relations = parents_groups_str.split(' ')
  parent_groups = defaultdict(lambda: {"groups": [], "hosts": []})
  for element in list_relations:
    parent, groups, hosts = parse_parent(element, tofu_grops, tofu_hosts)
    parent_groups[parent]["groups"].extend(groups)
    parent_groups[parent]["hosts"].extend(hosts)
  return parent_groups

def createInventoryFile(parent_groups, hosts, groups):
  with open('inventory.ini', 'w') as file:
    file.write(f"[ALL]\n")
    for host, data in hosts.items():
      file.write(f"{host} ansible_host={data['address']}\n")
    file.write(f"\n")
    for group in groups:
      file.write(f"[{group}]\n")
      for hostname, data in hosts.items():
        if group == data["group"]:
          file.write(f"{hostname}\n")
      file.write(f"\n")
    if parent_groups:
      for parent_group, child_group in parent_groups.items():
        file.write(f"[{parent_group}]\n")
        for host in child_group['hosts']:
          file.write(f"{host}\n")
        file.write(f"\n")
        file.write(f"[{parent_group}:children]\n")
        for group in child_group['groups']:
          file.write(f"{group}\n")
        file.write(f"\n")

def createHostVarsFile(hosts):
  if not os.path.exists(f'host_vars'):
    os.makedirs(f'host_vars')
  for host, data in hosts.items():
    with open(f'host_vars/{host}.yml', 'w') as file:
      yaml.dump(data['variables'], file, allow_unicode=True, default_flow_style=False)
      

def string_to_bool(str):
  return str.lower() in ['true', 'yes', '1']

def main() -> None:
  awx_url = os.getenv('AWX_URL')
  awx_user = os.getenv('AWX_USER')
  awx_password = os.getenv('AWX_PASSWORD')
  awx_org = os.getenv('AWX_ORG')
  awx_inventory_name = os.getenv('AWX_INVENTORY_NAME')
  awx_inventory_id = os.getenv('AWX_INVENTORY_ID')
  parents_groups_str = os.getenv('PARENTS_GROUPS')
  delete_flag = os.getenv('DELETE_FLAG')
  delete_flag = string_to_bool(delete_flag)

  config.base_url = awx_url
  config.credentials = utils.PseudoNamespace({'default': {'username': awx_user, 'password': awx_password}})

  connection = api.Api()
  connection.load_session().get()
  api_v2 = connection.available_versions.v2.get()

  orga = api_v2.organizations.get(name=awx_org)['results'][0]

  if not hosts_data_json_string:
    file_name = hosts_data_file_path if len(hosts_data_file_path) > 0 else 'hosts.json'
    with open(file_name, "r", encoding="utf-8") as file:
      hosts = json.load(file)
  else:
    hosts = json.loads(json.loads(hosts_data_json_string))
  
  groups = list(set(host['group'] for host in hosts.values()))

  if not awx_inventory_id:
    inventory_search = api_v2.inventory.get(name=awx_inventory_name)
  else:
    inventory_search = api_v2.inventory.get(id=awx_inventory_id)

  if inventory_search['count'] < 1 and not delete_flag:
    inventory = api_v2.inventory.create_or_replace(name=awx_inventory_name, description="test inventory example", organization=orga)
    print(f'Инвентарь {inventory['name']} в организации {orga.name} создан')
    print(f'id инвентаря = {inventory['id']}')
  elif inventory_search['count'] < 1 and delete_flag:
      print(f'Передан параметр delete на очистку инвентаря. Инвентарь не существует, скрипт завершает работу')
      sys.exit(0)
  else:
    print(f'Обнаружны существующие инвентари с именем {awx_inventory_name}')
    found_flag = False
    for inventory in inventory_search['results']:
      if inventory['summary_fields']['organization']['id'] == orga.id:
        found_flag = True
        print(f'...удаление существующих хостов в инвентаре {awx_inventory_name}...')
        while inventory.related.hosts.get()['count'] != 0:
          print(f'удаляется хост {inventory.related.hosts.get()['results'][0]['name']}')
          inventory.related.hosts.get()['results'][0].delete()
          print(f'готово')
        print(f'...удаление существующих групп в инвентаре {awx_inventory_name}...')
        while inventory.related.groups.get()['count'] != 0:
          print(f'удаляется группа {inventory.related.groups.get()['results'][0]['name']}')
          inventory.related.groups.get()['results'][0].delete()
          print(f'готово')
        current_inventory = inventory
    if found_flag:    
      inventory = current_inventory
    else:
      print(f'{Colors.FAIL}Инвентарь с именем {awx_inventory_name} найден, но принадлежит другой организации\nПожалуйста смените организацию или имя инвентаря{Colors.ENDC}')
      sys.exit(1)
    print(f'Инвентарь {inventory['name']} в организации {orga.name} очищен')
    print(f'{Colors.OKGREEN}id инвентаря = {inventory['id']}{Colors.ENDC}')

  if delete_flag:
    print(f'Передан параметр delete на очистку инвентаря. Инвентарь найден и очищен, скрипт завершает работу')
    sys.exit(0)
  
  for host_name, host_info in hosts.items():
    host_vars = {"ansible_host": host_info['address']}
    for var_key, var_value in host_info['variables']:
      host_vars[var_key] = var_value
    if include_disks_uuid:
      host_vars['disks_uuid'] = {}
      for disk in host_info['disks']:
        host_vars['disks_uuid'][disk['label']] = f'{disk['controller_type']}-SVMware_Virtual_disk_{disk["uuid"].replace("-","").lower()}'
    hosts[host_name]['variables'] = host_vars
    host_info['obj'] = api_v2.hosts.create(name=host_name, description="added by gitea action", inventory=inventory, variables=host_vars)

  createHostVarsFile(hosts)
  
  groups_obj = {}

  print(f'создание групп в инвентаре')
  for group in groups:
    groups_obj[group] = api_v2.groups.create(name=group, inventory=inventory, description='created by gitea action')
  print(f'готово')

  print(f'создание хостов в инвентаре')
  for host in hosts.values():
    groups_obj[host['group']].add_host(host=host['obj'])
  print(f'готово')

  
  if parents_groups_str:
    print(f'генерация словаря с родительскими группами')
    parent_groups = getParentGroups(parents_groups_str, groups, hosts)
    for parent_key in parent_groups.keys():
      groups_obj[parent_key] = api_v2.groups.create(name=parent_key, inventory=inventory, description='created by gitea action')
    print(f'установка отношений между объектами инвентаря')
    for parent_key, parent_dict in parent_groups.items():
      for group in parent_dict["groups"]:
        groups_obj[parent_key].add_group(group=groups_obj[group])
      for host in parent_dict["hosts"]:
        groups_obj[parent_key].add_host(host=hosts[host]['obj'])

    print(f'генерация inventory.ini для ansible-playbook')
    createInventoryFile(parent_groups, hosts, groups)
  else:
    createInventoryFile(None, hosts, groups)

  print(f'Ваш inventory.ini файл для ansible-playbook')
  with open('inventory.ini', 'r') as file:
    content = file.read()
    print(content)
  print()
  
  for host in hosts.keys():
    print(f'Ваш host_vars/{host}.yml файл для ansible-playbook')
    with open(f'host_vars/{host}.yml', 'r') as file:
      content = file.read()
      print(content)
    print()
 

  print("Complete")

if __name__ == "__main__":
  only_inventory_ini = os.getenv('FLAG_ONLY_INVENTORY')
  hosts_data_file_path = os.getenv('HOSTS_FILE_PATH')
  hosts_data_json_string = os.getenv('HOSTS_JSON_STRING')
  parents_groups_str = os.getenv('PARENTS_GROUPS')
  only_inventory_ini = string_to_bool(only_inventory_ini)
  include_disks_uuid = os.getenv('INCLUDE_DISKS_UUID')
  include_disks_uuid = string_to_bool(include_disks_uuid)
  if not only_inventory_ini:
    main()
  else:
    if not hosts_data_json_string:
      file_name = hosts_data_file_path if len(hosts_data_file_path) > 0 else 'hosts.json'
      with open(file_name, "r", encoding="utf-8") as file:
        hosts = json.load(file)
    else:
      hosts = json.loads(json.loads(hosts_data_json_string))
    
    for host_name, host_info in hosts.items():
      host_vars = {"ansible_host": host_info['address']}
      for var_key, var_value in host_info['variables']:
        host_vars[var_key] = var_value
      if include_disks_uuid:
        for disk in host_info['disks']:
          host_vars['disks_uuid'][disk['label']] = f'{disk['controller_type']}-SVMware_Virtual_disk_{disk["uuid"].replace("-","").lower()}'
      hosts[host_name]['variables'] = host_vars
    
    createHostVarsFile(hosts)
    
    groups = list(set(host['group'] for host in hosts.values()))
    if parents_groups_str:
      print(f'генерация словаря с родительскими группами')
      parent_groups = getParentGroups(parents_groups_str, groups, hosts)
      print(f'генерация inventory.ini для ansible-playbook')
      createInventoryFile(parent_groups, hosts, groups)
    else:
      print(f'генерация inventory.ini для ansible-playbook')
      createInventoryFile(None, hosts, groups)
    print(f'Ваш inventory.ini файл для ansible-playbook')
    with open('inventory.ini', 'r') as file:
      content = file.read()
      print(content)  
    print()
    for host in hosts.keys():
      print(f'Ваш host_vars/{host}.yml файл для ansible-playbook')
      with open(f'host_vars/{host}.yml', 'r') as file:
        content = file.read()
        print(content)
      print()
    print("Complete")
