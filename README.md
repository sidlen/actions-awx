# awx
При использовании каждого action необходимо передать параметры, описанные в action.yml
Описание функционала каждого action в README.md в соответствующей директории
Для удобства использования данного набора actions можно задать переменные:
- create_hosts_dict
  - Задать secrets на уровне организации или репозитория
  
        S3_SECRET_KEY: # при хранении tofu state в s3 # <секретный токен доступа к s3>
        CONSUL_TOKEN: # при хранении tofu state в consul # <токен доступа к consul с правами на запись в kv opentofu>
  - Задать variables на уровне организации или репозитория

        S3_ACCESS_KEY: # при хранении tofu state в s3 # <токен доступа к s3>
  - Задать env в вашем workflow на любом уровне

        S3_ADDRESS: # при хранении tofu state в s3 # <доменное имя s3 сервера>
        CONSUL_ADDRESS: # при хранении tofu state в consul # <доменное имя сервера consul>
        ENVIRONMENT: <dev/stage/prod по сути имя файла стейта без расширения .tfstate>

- fill_netbox
  - Задать secrets на уровне организации или репозитория
  
        NETBOX_API_TOKEN: <токен доступа к netbox>
        LDAP_PASSWORD: <пароль LDAP_USER>
  - Задать variables на уровне организации или репозитория

        LDAP_USER: <ldap пользователь для ldapsearch в формате CN=,OU=,DC=,>
        LDAP_SERVER: <url ldap сервера в формате ldap://ip:port>
  - Задать env в вашем workflow на любом уровне

        NETBOX_URL: <http/https url сервера netbox>
        SEARCH_BASE_DN: <search base в формате OU=,DC=,>

- create_awx_inventory
  - Задать secrets на уровне организации или репозитория
  
        AWX_PASSWORD: <пароль пользователя, указанного в AWX_USER>
  - Задать variables на уровне организации или репозитория

        AWX_USER: <пользователь AWX с RW правами>
  - Задать env в вашем workflow на любом уровне

        AWX_URL: <http/https url сервера AWX>
        AWX_ORGANIZATION: <имя организации в AWX>
        AWX_INVENTORY_ID: #необязательный параметр# <inventory id из AWX если необходимо пересоздать существующий инвентарь, существущие данные в инвентаре будут удалены>
        PARENT_GROUPS: #необязательный параметр# <строка с родительскими группами и дочерними группами/хостами>, например, parent_group1:group1,hostname_1 parent_group2:group2,group3 создаст дополнительные группы, каждый блок parent:child необходимо разделять пробелами

        # inventory.ini
        [parent_group1]
        group1
        hostname_1

        [parent_group2]
        group2
        group3


Полный список vars, secrets, env:
- secrets:
  - S3_SECRET_KEY
  - CONSUL_TOKEN
  - NETBOX_API_TOKEN
  - LDAP_PASSWORD
  - AWX_PASSWORD
- vars:
  - S3_ACCESS_KEY
  - LDAP_USER
  - AWX_USER
- env:
  - S3_ADDRESS
  - CONSUL_ADDRESS
  - LDAP_SERVER
  - ENVIRONMENT
  - NETBOX_URL
  - SEARCH_BASE_DN
  - AWX_URL
  - AWX_ORGANIZATION
  - AWX_INVENTORY_ID
  - PARENT_GROUPS