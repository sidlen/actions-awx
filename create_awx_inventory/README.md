# actions/awx/create_awx_inventory@v1
Данный action предназначен для создания и заполнения инвентаря AWX используяю json строку или файл hosts.json формата:

      {
      "host_name_1": {
            "address": "x.x.x.x",
            "group": "group_name_1",
            "variables": {},
            "disks": [
                  {
                      "label": "system",
                      "uuid": "some_uuid",
                      "size": int_size
                  },
                  {
                      "label": "var",
                      "uuid": "some_uuid",
                      "size": int_size
                  }
            ]
            },
      "host_name_2": {
            "address": "x.x.x.x",
            "group": "group_name_1",
            "variables": {},
            "disks": [
                  {
                      "label": "system",
                      "uuid": "some_uuid",
                      "size": int_size
                  },
                  {
                      "label": "var",
                      "uuid": "some_uuid",
                      "size": int_size
                  }
            ]
            },
      "host_name_3": {
            "address": "x.x.x.x",
            "group": "group_name_1",
            "variables": {},
            "disks": [
                  {
                      "label": "system",
                      "uuid": "some_uuid",
                      "size": int_size
                  },
                  {
                      "label": "var",
                      "uuid": "some_uuid",
                      "size": int_size
                  }
            ]
            }
      }

Если вы задали secrets, vars и env как указано в [README.md](../README.md), то для использования action достаточно передать hosts_data_json_string:

или предварительно использовать [actions/awx/create_hosts_dict@v1](../create_hosts_dict/)

так же можно передать *.outputs.result из [actions/awx/create_hosts_dict@v1](../create_hosts_dict/) в параметр hosts_data_json_string:


Action по умолчанию генерирует inventory.ini и host_vars/*hostname*.yml файлы для ansible-playbook, файлы выводятся в консоль и сохраняются в рабочую область workflow.

При необходимости можно получить только inventory.ini файл и host_vars/*hostname*.yml без создания инвентаря в AWX. Для этого нужно передать параметр only_inventory_ini: "True".


Скрипт проходится по словарю hosts.json и создает через API AWX объекты host (с переменными из host['variables] ansible_host: ip) и group в указанном инвентаре (если не указан - создается инвентарь в указанной Организации с именем "${{ github.repository }}", можно заменить указав параметр awx_inventory_name: MY_INVENTORY_NAME, а так же после создания инвентаря выведется его id)

Можно записать в переменные uuid дисков для их последующего подключения в системе. Для этого необходимо передать параметр include_disks_uuid: "True"
переменная формируется по следующему шаблону

    {...other vars...
      "disks_uuid": {
        disk["label"]: {disk["controller_type"]}-SVMware_Virtual_disk_{disk["uuid"].replace("-","").lower()},
        ...other disks...
      }
    }

Скрипт позволяет создавать дополнительные родительский группы.

На основе переданного параметра

    with:
      parent_groups: "parent_group1:group1,hostname_1 parent_group2:group2,group3"

- action создаст дополнительные группы parent_group1 и parent_group2
- сделает группу parent_group1 родительской для группы group1
- сделает группу parent_group2 родительской для групп group2 и group3
- добавит hostname_1 в группу parent_group1


Если указанный инвентарь в указанной организации уже существует, то он будет перезаписан с сохранением id. Все существующие группы и хосты вместе с объявленными в них переменными удалятся.