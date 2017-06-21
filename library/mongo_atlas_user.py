#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule
import requests
from requests.auth import HTTPDigestAuth

DOCUMENTATION = '''
---
module: mongo_atlas_user
short_description: Module for provisioning users in MongoDB Atlas
description:
    - This module provides the ability to provision users on MongoDB instances
    - hosted in Atlas
version_added: "2.2"
author: "Jesse Dearing, @jessedearing"
requirements:
    - MongoDB Atlas account access
    - MongoDB Atlas API key
options:
    atlas_username:
        description:
            - The username for the MongoDB Atlas account
        required: true
    atlas_api_key:
        description:
            - The API required to access MongoDB Atlas's REST API
        required: true
    atlas_group_id:
        description:
            - The group ID is a representation of your account ID in MongoDB
            - Atlas. To get it go to Settings > Group Settings.
        required: true
    user:
        description:
            - The name of the user to create on your MongoDB instances.
        required: true
    password:
        description:
            - The password to set for the MongoDB user being provisioned.
            - Please note that the password is always set, even on update if
            - this option is provided and the update_password option is not set
            - to 'on_create'.
        required: false
    state:
        description:
            - "'present' will create the user if the user does not exist and"
            - update existing users as needed
            - "'absent' removes the user if the user exists"
        required: false
        default: present
        choices: [present, absent]
    update_password:
        description:
            - "'on_create' only updates the password if a user needs to be"
            - created. Otherwise, do nothing for existing users.
            - "'always' will always set the password on create and update."
        required: false
        default: always
    roles:
        description:
            - MongoDB roles to associate with the user. Can be specified as
            - single global roles. I.e. readWriteAnyDatabase, atlasAdmin, etc.
            - Or, may be scoped to database via a dictionary in a playbook. See
            - the examples.
        required: false
'''

EXAMPLES = '''
    - name: create ansible user in atlas
      mongo_atlas_user:
        atlas_username: 'jessedearing@invisionapp.com'
        atlas_api_key: '12345-678-90abcd-ef1234'
        atlas_group_id: 'abcabcabc123123123'
        user: my_new_service
        state: present
        roles:
          - db: my_new_service_test
            role: read
'''


def map_roles(role):
    """ Transform roles into the format needed by the api """
    if type(role) is str:
        return dict(roleName=role, databaseName='admin')
    elif role.get('db') is not None and role.get('role') is not None:
        # this makes the playbook look better. I.e. the roles section looks
        # like:
        # mongo_atlas_user:
        #   user: foo
        #   roles:
        #       db: mydb
        #       role: readWrite
        #
        # Instead of having the roleName and databaseName fields like:
        # mongo_atlas_user:
        #   user: foo
        #   roles:
        #       databaseName: mydb
        #       roleName: readWrite
        return dict(roleName=role['role'], databaseName=role['db'])
    else:
        return role


def get_user(atlas_group_id, atlas_username, atlas_api_key, user):
    """
    Calls GET /api/atlas/v1.0/groups/GROUPID/databaseUsers/admin/USERNAME

    Returns:
        The JSON of the user object with the URL called to get it added as
        'url' in the JSON
    """
    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/databaseUsers/admin/" + user
    response = requests.get(url, auth=HTTPDigestAuth(atlas_username,
                            atlas_api_key))
    user_json = response.json()
    response.close()
    user_json['url'] = url
    return user_json


def create_user(atlas_group_id, atlas_username, atlas_api_key, user, roles,
                password):
    roles_with_dbs = map(map_roles, roles)
    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/databaseUsers"
    user = dict(databaseName='admin',
                groupId=atlas_group_id,
                username=user,
                roles=roles_with_dbs,
                password=password)
    response = requests.post(url, json=user,
                             auth=HTTPDigestAuth(atlas_username,
                                                 atlas_api_key))
    post_json = response.json()
    response.close()
    post_json['url'] = url
    return post_json


def delete_user(atlas_group_id, atlas_username, atlas_api_key, user):
    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/databaseUsers/admin/"+user
    response = requests.delete(url, auth=HTTPDigestAuth(atlas_username,
                                                        atlas_api_key))
    delete_json = response.json()
    response.close()
    delete_json['url'] = url
    return delete_json


def sync_user(atlas_group_id, atlas_username, atlas_api_key, user,
              http_response, roles, password):
    roles_with_dbs = map(map_roles, roles)
    if http_response['roles'] == roles_with_dbs and password is None:
        return dict(changed=False)

    payload = dict(databaseName='admin',
                   groupId=atlas_group_id,
                   username=user,
                   roles=roles_with_dbs)

    if password is not None:
        payload['password'] = password

    url = "https://cloud.mongodb.com/api/atlas/v1.0/groups/" + atlas_group_id \
        + "/databaseUsers/admin/"+user

    response = requests.patch(url, json=payload, auth=HTTPDigestAuth(
                              atlas_username,
                              atlas_api_key))

    patch_json = response.json()
    patch_json['changed'] = True
    response.close()
    patch_json['url'] = url
    return patch_json


def main():
    """Load the option and route the methods to call"""
    module = AnsibleModule(
            argument_spec=dict(
                atlas_username=dict(required=True, type='str'),
                atlas_api_key=dict(required=True, type='str', no_log=True),
                atlas_group_id=dict(required=True, type='str'),
                user=dict(required=True, type='str', no_log=False),
                password=dict(required=False, type='str', no_log=True),
                state=dict(default='present', choices=['absent', 'present']),
                update_password=dict(default='always', choices=['always',
                                     'on_create']),
                roles=dict(default=None, type='list')
                ),
            supports_check_mode=False
            )
    user = module.params['user']
    password = module.params['password']
    atlas_username = module.params['atlas_username']
    atlas_api_key = module.params['atlas_api_key']
    atlas_group_id = module.params['atlas_group_id']
    state = module.params['state']
    update_password = module.params['update_password']
    roles = module.params['roles']

    # Do an initial query for the user so we can inspect if it needs to change
    subject_response = get_user(atlas_group_id, atlas_username, atlas_api_key,
                                user)

    if subject_response.get('error') is None:
        subject_state = 'present'
    # If we get a 404 we know the user is not there
    elif subject_response.get('error') == 404:
        subject_state = 'absent'
    else:
        module.fail_json(msg=str(subject_response))
        return

    # The user is not there so we must create it
    if state == 'present' and subject_state == 'absent':
        response = create_user(atlas_group_id=atlas_group_id,
                               atlas_username=atlas_username,
                               atlas_api_key=atlas_api_key,
                               user=user, roles=roles, password=password)
        if response.get('error') is None:
            module.exit_json(changed=True, user=response)
        else:
            module.fail_json(msg="Failed to create user:\n"+str(response))
        return

    # The user is not there and we don't want it there. Nothing to do here
    if state == 'absent' and subject_state == 'absent':
        module.exit_json(changed=False, user=user)
        return

    # The user is there and we don't wait it to be. Delete it.
    if state == 'absent' and subject_state == 'present':
        response = delete_user(atlas_group_id, atlas_username, atlas_api_key,
                               user)
        if response.get('error') is None:
            module.exit_json(changed=True, user=response)
        else:
            module.fail_json(msg="Failed to delete user:\n"+str(response))
        return

    # The user is there and we want it to be.
    if state == 'present' and subject_state == 'present':
        # Need to update the password
        # Note: we always have to update if the password is present because we
        # cannot get the password though the API to compare it for change
        if update_password == 'always' and password is not None:
            response = sync_user(atlas_group_id=atlas_group_id,
                                 atlas_username=atlas_username,
                                 atlas_api_key=atlas_api_key,
                                 user=user, http_response=subject_response,
                                 roles=roles,
                                 password=password)
        # Not going to update the password
        else:
            response = sync_user(atlas_group_id=atlas_group_id,
                                 atlas_username=atlas_username,
                                 atlas_api_key=atlas_api_key,
                                 roles=roles,
                                 user=user, http_response=subject_response,
                                 password=None)
        if response.get('error') is None:
            module.exit_json(changed=response['changed'],
                             user=subject_response)
        else:
            module.fail_json(msg="Failed to update user:\n"+str(response),
                             subject=subject_response)
        return


if __name__ == '__main__':
    main()
