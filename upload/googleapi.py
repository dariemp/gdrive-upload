import requests
from django.conf import settings
from oauth2client import service_account


class GoogleDrive(object):

    def __init__(self):
        self.token = self.authenticate()

    def authenticate(self):
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.ServiceAccountCredentials.from_json_keyfile_name(
            settings.SERVICE_ACCOUNT_FILE, scopes=scopes)
        return credentials.get_access_token().access_token

    def get_base_headers(self):
        return {'Authorization': 'Bearer %s' % self.token}

    def start_file_upload(self, filename, file_size):
        url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable'
        headers = self.get_base_headers()
        headers.update({'X-Upload-Content-Length': str(file_size)})
        resp = requests.post(url, headers=headers, json={'name': filename})
        if resp.status_code != 200:
            raise Exception('Bad upload initialization')
        return resp.headers['Location']

    def upload_file_data(self, upload_url, file_size, file_data):
        headers = self.get_base_headers()
        headers.update({'Content-Length': str(file_size)})
        resp = requests.put(upload_url, headers=headers, data=file_data)
        if resp.status_code not in [200, 201]:
            raise Exception('Upload error')
        return resp.json()['id']

    def grant_access(self, gdrive_file_id):
        url = 'https://www.googleapis.com/drive/v3/files/%s/permissions?sendNotificationEmail=false' % gdrive_file_id
        headers = self.get_base_headers()
        permission_data = {
            'type': 'user',
            'role': 'reader'
        }
        users_to_gran_access = settings.GRANT_ACCESS
        for email_address in users_to_gran_access:
            self.create_user_permission(url, headers, email_address, permission_data)

    def create_user_permission(self, url, headers, email_address, permission_data):
        user_permission = permission_data.copy()
        user_permission.update({'emailAddress': email_address})
        resp = requests.post(url, headers=headers, json=user_permission)
        if resp.status_code not in [200, 201]:
            raise Exception('Could not grant access to user identified as: %s' % email_address)

    def upload_file(self, filename, file_size, file_data):
        upload_url = self.start_file_upload(filename, file_size)
        file_id = self.upload_file_data(upload_url, file_size, file_data)
        self.grant_access(file_id)
