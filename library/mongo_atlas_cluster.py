#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule
import requests
from requests.auth import HTTPDigestAuth


def delete_cluster(atlas_username, atlas_api_key, atlas_group_id, name):
    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/clusters/" + name
    response = requests.delete(url, auth=HTTPDigestAuth(atlas_username,
                                                        atlas_api_key))

    delete_json = response.json()
    response.close()
    return delete_json


def create_cluster(atlas_username, atlas_api_key, atlas_group_id, name,
                   num_shards, replication_factor, instance_size, disk_iops,
                   encrypt, backup_enabled, region_name, disk_size):
    payload = dict(name=name)
    if backup_enabled is not None:
        payload['backupEnabled'] = backup_enabled
    if num_shards is not None:
        payload['numShards'] = num_shards
    if replication_factor is not None:
        payload['replicationFactor'] = replication_factor
    if disk_size is not None:
        payload['diskSizeGB'] = disk_size

    provider_settings = payload['providerSettings'] = dict(providerName='AWS')

    # Have to use a bunch of ifs so we don't put nulls in the JSON
    if region_name is not None:
        provider_settings['regionName'] = region_name
    if instance_size is not None:
        provider_settings['instanceSizeName'] = instance_size
    if disk_iops is not None:
        provider_settings['diskIOPS'] = disk_iops
    if encrypt is not None:
        provider_settings['encryptEBSVolume'] = encrypt

    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/clusters"

    res = requests.post(url, json=payload, auth=HTTPDigestAuth(atlas_username,
                                                               atlas_api_key))

    post_json = res.json()
    res.close()
    post_json['url'] = url
    return post_json


def get_cluster(atlas_username, atlas_api_key, atlas_group_id, name):
    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/clusters/" + name
    response = requests.get(url, auth=HTTPDigestAuth(atlas_username,
                                                     atlas_api_key))
    cluster_json = response.json()
    response.close()
    cluster_json['url'] = url
    return cluster_json


def main():
    module = AnsibleModule(
            argument_spec=dict(
                atlas_username=dict(required=True, type='str'),
                atlas_api_key=dict(required=True, type='str', no_log=True),
                atlas_group_id=dict(required=True, type='str'),
                name=dict(required=True, type='str'),
                num_shards=dict(required=False, type='int', default=1),
                replication_factor=dict(required=False, type='int', default=3),
                instance_size=dict(required=False, type='str', default='M10'),
                disk_iops=dict(required=False, type='int'),
                encrypt=dict(required=False, type='bool'),
                backup_enabled=dict(required=False, default=True, type='bool'),
                region_name=dict(required=False, default='US_EAST_1',
                                 type='str'),
                state=dict(default='present', choices=['absent', 'present']),
                disk_size=dict(type='int')
                ),
            supports_check_mode=False
            )
    atlas_username = module.params['atlas_username']
    atlas_api_key = module.params['atlas_api_key']
    atlas_group_id = module.params['atlas_group_id']
    name = module.params['name']
    num_shards = module.params['num_shards']
    replication_factor = module.params['replication_factor']
    instance_size = module.params['instance_size']
    disk_iops = module.params['disk_iops']
    encrypt = module.params['encrypt']
    backup_enabled = module.params['backup_enabled']
    region_name = module.params['region_name']
    state = module.params['state']
    disk_size = module.params['disk_size']

    subject_cluster = get_cluster(atlas_username=atlas_username,
                                  atlas_api_key=atlas_api_key,
                                  atlas_group_id=atlas_group_id,
                                  name=name)

    if subject_cluster.get('error') is None:
        subject_state = 'present'
    elif subject_cluster.get('error') == 404:
        subject_state = 'absent'

    if state == 'absent' and subject_state == 'absent':
        module.exit_json(changed=False, cluster=name)
        return

    if state == 'present' and subject_state == 'absent':
        cluster = create_cluster(atlas_username=atlas_username,
                                 atlas_api_key=atlas_api_key,
                                 atlas_group_id=atlas_group_id,
                                 name=name,
                                 num_shards=num_shards,
                                 replication_factor=replication_factor,
                                 instance_size=instance_size,
                                 disk_iops=disk_iops,
                                 encrypt=encrypt,
                                 backup_enabled=backup_enabled,
                                 region_name=region_name,
                                 disk_size=disk_size)
        if cluster.get('error') is not None:
            module.fail_json(msg="Could not create cluster", response=cluster)
        else:
            module.exit_json(changed=True, cluster=cluster)
        return

    if state == 'absent' and subject_state == 'present':
        cluster = delete_cluster(atlas_username=atlas_username,
                                 atlas_api_key=atlas_api_key,
                                 atlas_group_id=atlas_group_id,
                                 name=name)
        if cluster.get('error') is not None:
            module.fail_json(msg="Could not delete cluster", response=cluster)
        else:
            module.exit_json(changed=True, cluster=cluster)
        return

    if state == 'present' and subject_state == 'present':
        module.exit_json(changed=False, cluster=subject_cluster)


if __name__ == "__main__":
    main()
