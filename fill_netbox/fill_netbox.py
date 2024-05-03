import requests, os, json, sys, time
from ldap3 import Server, Connection, ALL

class Colors:
  HEADER = '\033[95m'  # Фиолетовый
  OKBLUE = '\033[94m'  # Синий
  OKGREEN = '\033[92m'  # Зеленый
  WARNING = '\033[93m'  # Желтый
  FAIL = '\033[91m'  # Красный
  ENDC = '\033[0m'  # Возвращает стандартный цвет текста
  BOLD = '\033[1m'  # Жирный текст
  UNDERLINE = '\033[4m'  # Подчеркнутый текст

def get_full_name(login, ldap_server, ldap_user, ldap_password, search_base, search_filter):
    """
    Получает полное имя пользователя из AD по логину.

    :param login: Логин пользователя (sAMAccountName).
    :param ldap_server: Адрес сервера LDAP.
    :param ldap_user: Пользователь для подключения к LDAP.
    :param ldap_password: Пароль для подключения к LDAP.
    :param search_base: Базовый DN для поиска.
    :param search_filter: Фильтр поиска LDAP.
    :return: Полное имя пользователя или None, если пользователь не найден.
    """
    server = Server(ldap_server, get_info=ALL)
    with Connection(server, ldap_user, ldap_password) as conn:
        if not conn.bind():
            print('Error in bind', conn.result)
            return None
        conn.search(search_base, search_filter.format(login=login), attributes=['cn'])
        if conn.entries:
            full_name = conn.entries[0].cn.value
            return full_name
        else:
            return None

def createIPObjects(hosts_data: dict, description_host_string, force_flag, netbox_url, netbox_api_token, owner):
  for hostname, data in hosts_data.items():
    time.sleep(2)
    headers = {
      'Authorization': f'Token {netbox_api_token}',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    }
    
    data = {
      "address": data['address'],
      "description": description_host_string,
      "dns_name": hostname,
      "custom_fields": {
        "Owner": owner
      }
    }
    check = requests.get(f'{netbox_url}/api/ipam/ip-addresses/?address={data['address']}', headers=headers, verify=False, timeout=5)
    if check.json()['count'] < 1:
      response = requests.post(f'{netbox_url}/api/ipam/ip-addresses/', headers=headers, json=data, verify=False, timeout=5)
      print(f'{Colors.OKGREEN}Запись {data['address']} создана{Colors.ENDC}')
    elif check.json()['count'] == 1:
      if check.json()['results'][0]['custom_fields']['Owner'] == owner or check.json()['results'][0]['custom_fields']['Owner'] is None or force_flag:
        response = requests.patch(f'{netbox_url}/api/ipam/ip-addresses/{check.json()['results'][0]['id']}/', headers=headers, json=data, verify=False, timeout=5)
        print(f'{Colors.OKBLUE}Запись {data['address']} заменена{Colors.ENDC}')
      else:
        print(f'{Colors.FAIL}Вы не являетесь владельцем записи {data['address']}, замена скриптом отменена, текущий владелец: {check.json()['results'][0]['custom_fields']['Owner']}{Colors.ENDC}')
        sys.exit(1)
    else:
      print(f'{Colors.FAIL}Записей на ip аддрес {data['address']} больше одной, пожалуйста почистите неактуальные записи в ручную и перезапустите скрипт{Colors.ENDC}')
      sys.exit(1)

def string_to_bool(str):
  return str.lower() in ['true', 'yes', '1']
  

def main() -> None:
  netbox_api_token = os.getenv('NETBOX_API_TOKEN')
  login = os.getenv('AD_USER_LOGIN')
  hosts_data_file_path = os.getenv('HOSTS_FILE_PATH')
  hosts_data_json_string = os.getenv('HOSTS_JSON_STRING')
  ldap_user = os.getenv('LDAP_USER')
  ldap_password = os.getenv('LDAP_PASSWORD')
  search_base = os.getenv('LDAP_SEARCH_BASE')
  ldap_server = os.getenv('LDAP_SERVER')
  description_host_string = os.getenv('HOSTS_DESCRIPTION')
  netbox_url = os.getenv('NETBOX_URL')
  search_filter = '(sAMAccountName={login})'
  force_flag = os.getenv('FORCE_FLAG')
  force_flag = string_to_bool(force_flag)
  
  owner = get_full_name(login, ldap_server, ldap_user, ldap_password, search_base, search_filter)
  
  if not hosts_data_json_string:
    file_name = hosts_data_file_path if len(hosts_data_file_path) > 0 else 'hosts.json'
    with open(file_name, "r", encoding="utf-8") as file:
      hosts_data = json.load(file)
  else:
    hosts_data = json.loads(json.loads(hosts_data_json_string))

  createIPObjects(hosts_data, description_host_string, force_flag, netbox_url, netbox_api_token, owner)

if __name__ == "__main__":
    main()