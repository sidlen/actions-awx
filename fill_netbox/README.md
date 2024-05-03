# actions/awx/fill_netbox@v1
Данный action предназначен для автоматического заполнения ipam в netbox в соответствии с переданным ему файлом hosts.json или строкой outputs сформированными [actions/awx/create_hosts_dict@v1](../create_hosts_dict/) формата:

      {
      "host_name_1": {
            "address": "x.x.x.x",
            "group": "group_name_1"
            },
      "host_name_2": {
            "address": "x.x.x.x",
            "group": "group_name_1"
            },
      "host_name_3": {
            "address": "x.x.x.x",
            "group": "group_name_1"
            }
      }

Если вы задали secrets, vars и env как указано в [README.md](../README.md), то для использования action достаточно передать hosts_data_json_string:

или предварительно использовать [actions/awx/create_hosts_dict@v1](../create_hosts_dict/)

так же можно передать *.outputs.result из [actions/awx/create_hosts_dict@v1](../create_hosts_dict/) в параметр hosts_data_json_string:


Скрипт проходится по словарю hosts.json и для каждого элемента создает ip запись в ipam netbox, владельцем ресурса по умолчанию выставляется пользователь запустивший action, из ldap подтягивается полное имя пользователя, необходимое в netbox в поле owner