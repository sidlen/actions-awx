# actions/awx/create_hosts_dict@v1
Данный action предназначен для обработки tofu state формата шаблонного репозитория [opentofu/template-opentofu-manifest](https://git.softline.com/opentofu/template-opentofu-manifest) создания файла hosts.json и json строки в outputs формата:

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

Если вы задали secrets, vars и env как указано в [README.md](../README.md), то для использования action дополнительные парметры не нужны. 

Если необходимо передать полченную json строку или файл hosts.json в другие steps/jobs можно 
шагу присвоить id, например:

      - uses: ${{ gitea.server_url }}/actions/awx/create_hosts_dict@v1
        id: get_hosts

и затем использовать outputs этого step:

      - uses: ${{ gitea.server_url }}/actions/awx/fill_netbox@v1
        with:
          hosts_data_json_string: ${{ steps.get_hosts.outputs.result }}

или из другой job с использованием needs и outputs:


      jobs:
        job1:
          runs-on: ubuntu-latest
          outputs:
            output1: ${{ steps.get_hosts.outputs.result }}
          steps:
            - uses: ${{ gitea.server_url }}/actions/awx/create_hosts_dict@v1
              id: get_hosts
        job2:
          needs: job1
          runs-on: ubuntu-latest
          steps:
            - uses: ${{ gitea.server_url }}/actions/awx/fill_netbox@v1
              with:
                hosts_data_json_string: ${{ needs.job1.outputs.output }}


Скрипт читает указанный tofu state файл (созданный c использованиtv модульного манифеста) и составляет файл hosts.json. Имя модуля в tofu manifest - это имя грппы