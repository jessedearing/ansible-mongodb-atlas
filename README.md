# ansible-mongodb-atlas

Ansible modules for provisioning users and clusters with MongoDB Atlas.

Example:

Create a config file for your atlas credentials (~/.atlas.ini):

```ini
[atlas]
username=you@email.com
api_key=abcdef01-2345-6789-abcd-ef0123456789
atlas_group_id=0123456890abcef012345678
```

roles/mongodb_atlas/tasks/main.yml:

```yaml
---
# This is a stub for the creation of clusters
- name: create MongoDB Atlas clusters
  with_items: "{{ clusters }}"
  mongo_atlas_cluster:
    atlas_username: "{{ lookup('ini', 'username section=atlas file=~/.atlas.ini') }}"
    atlas_api_key: "{{ lookup('ini', 'api_key section=atlas file=~/.atlas.ini') }}"
    atlas_group_id: "{{ lookup('ini', 'atlas_group_id section=atlas file=~/.atlas.ini') }}"
    name: "{{ item.name }}"
    instance_size: "{{ item.size }}"
    encrypt: true
    backup_enabled: false
    state: "{{ item.state }}"

- name: create MongoDB Atlas users
  with_items: "{{ users }}"
  mongo_atlas_user:
    atlas_username: "{{ lookup('ini', 'username section=atlas file=~/.atlas.ini') }}"
    atlas_api_key: "{{ lookup('ini', 'api_key section=atlas file=~/.atlas.ini') }}"
    atlas_group_id: "{{ lookup('ini', 'atlas_group_id section=atlas file=~/.atlas.ini') }}"
    user: "{{ item.user }}"
    state: "{{ item.state }}"
    update_password: on_create
    roles: "{{ item.roles }}"
    password: "{{ item.password }}"

```

mongodb_atlas.yml:

```yaml
---
- hosts: localhost
  connection: local
  roles:
    - role: mongodb_atlas
      clusters:
        - name: test-mongo
          size: M10
          state: present
        - name: staging-mongo
          size: M30
          state: present
        - name: prod-mongo
          size: M30
          state: present
      users:
        - user: mongo_app_user
          password: "{{ lookup('password', 'creds/atlas/mongo_app_user chars=ascii_letters') }}"
          state: present
          roles:
            - readWrite
```

Simply run `ansible-playbook mongodb_atlas.yml`
