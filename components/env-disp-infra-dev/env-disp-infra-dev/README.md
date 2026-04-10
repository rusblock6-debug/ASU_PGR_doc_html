# env-disp-infra

Ansible-проект для подготовки и деплоя инфраструктуры на хосты dispatching.

Что настраивается:
- `docker-compose` и `docker compose`
- `gitlab-runner`
- SSH-ключи и `known_hosts` для `gitlab-runner`
- логин в Docker registry
- `/srv/dispatching-repo`
- `/srv/deploy-lock-agent`
- `docker-compose.yaml` для `deploy-lock-agent`
- запуск `deploy-lock-agent` через `docker compose up -d`

## Файлы

`.ansible/inventory`  
Список хостов.

Пример:
```ini
[servers]
10.109.51.17
10.109.51.18
```

`.ansible/settings.yml`  
Общие настройки проекта.

Тут задаются:
- `gitlab_runner_tokens` - токены runner по хостам
- `gitlab_runner_known_hosts_entries` - SSH host keys для GitLab
- `docker_registry_*` - креды для `docker login`
- `deploy_lock_agent_image` - образ агента
- `deploy_lock_agent_compose_up` - запускать ли `docker compose up -d`
- `deploy_lock_agent_defaults` - общие значения для всех хостов
- `deploy_lock_agent_hosts` - переопределения для конкретных хостов

`.ansible/host_vars`  
Необязательные host-specific overrides.

## Что вносить

### 1. Добавить хост в inventory

Файл: `.ansible/inventory`

```ini
[servers]
10.109.51.17
10.109.51.18
```

### 2. Добавить токен GitLab Runner

Файл: `.ansible/settings.yml`

```yaml
gitlab_runner_tokens:
  "10.109.51.17": "glrt-..."
  "10.109.51.18": "glrt-..."
```

### 3. Задать SSH host keys GitLab

Файл: `.ansible/settings.yml`

```yaml
gitlab_runner_known_hosts_entries:
  - "git.dmi-msk.ru ssh-ed25519 AAAA..."
  - "git.dmi-msk.ru ssh-rsa AAAA..."
  - "git.dmi-msk.ru ecdsa-sha2-nistp256 AAAA..."
```

Роль автоматически:
- создает `/home/gitlab-runner/.ssh`
- кладет фиксированные `id_ed25519` и `id_ed25519.pub`, если они заданы в `settings.yml`
- иначе генерирует `id_ed25519` и `id_ed25519.pub`, если их нет
- восстанавливает `.pub`, если потерян только публичный ключ
- добавляет записи в `known_hosts`

Если нужно использовать заранее подготовленную пару ключей:

```yaml
gitlab_runner_ssh_private_key_content: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----
gitlab_runner_ssh_public_key_content: "ssh-ed25519 AAAA... gitlab-runner@host"
```

### 4. Задать креды Docker Registry

Файл: `.ansible/settings.yml`

```yaml
docker_registry_login_enabled: true
docker_registry_url: registry.dmi-msk.ru
docker_registry_username: reader-01
docker_registry_password: ZX31hweNR
docker_registry_login_users:
  - root
  - gitlab-runner
```

### 5. Задать общие настройки deploy-lock-agent

Файл: `.ansible/settings.yml`

```yaml
deploy_lock_agent_enabled: true
deploy_lock_agent_image: registry.dmi-msk.ru/base-images:deploy-lock-agent-567d0dea
deploy_lock_agent_compose_up: true

deploy_lock_agent_defaults:
  deploy_lock_url: https://deploy-lock.dmi-msk.ru
  deploy_lock_token: 6ou2X5
  server_ip: null
```

Если `server_ip: null`, IP подставится автоматически.

### 6. Задать настройки для конкретного хоста

Файл: `.ansible/settings.yml`

```yaml
deploy_lock_agent_hosts:
  "10.109.51.17":
    deploy_lock_env_key: dispa-stage-bort-4
    server_ip: 10.109.51.4
```

Если `server_ip` не задан, берется автоматически из фактов Ansible.

## Запуск

Пользователь для SSH берется из `.ansible/ansible.cfg` (`remote_user`).

Проверка синтаксиса:

```bash
ANSIBLE_CONFIG=.ansible/ansible.cfg ansible-playbook .ansible/main.yml --syntax-check
```

Тестовый прогон:

```bash
sudo env ANSIBLE_CONFIG=.ansible/ansible.cfg \
  ansible-playbook .ansible/main.yml --check --diff
```

Полное применение:

```bash
sudo env ANSIBLE_CONFIG=.ansible/ansible.cfg \
  ansible-playbook .ansible/main.yml
```

На один хост:

```bash
sudo env ANSIBLE_CONFIG=.ansible/ansible.cfg \
  ansible-playbook .ansible/main.yml --limit 10.109.51.17
```

Если нужно перерегистрировать `gitlab-runner`:

```bash
sudo env ANSIBLE_CONFIG=.ansible/ansible.cfg \
  ansible-playbook .ansible/main.yml \
  -e gitlab_runner_reconfigure=true
```

Посмотреть публичный SSH-ключ `gitlab-runner` после применения:

```bash
sudo -u gitlab-runner cat /home/gitlab-runner/.ssh/id_ed25519.pub
```

Если нужно перевыпустить SSH-ключи `gitlab-runner`:

```bash
sudo env ANSIBLE_CONFIG=.ansible/ansible.cfg \
  ansible-playbook .ansible/main.yml \
  -e gitlab_runner_ssh_regenerate_keypair=true
```
