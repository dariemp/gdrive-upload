import requests
from django.conf import settings
from oauth2client import service_account
from urlparse import urlparse, parse_qs


class GoogleDrive(object):

    def __init__(self):
        self.token = self.authenticate()

    def authenticate(self):
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.ServiceAccountCredentials.from_json_keyfile_name(
            settings.SERVICE_ACCOUNT_FILE, scopes=scopes)
        return credentials.get_access_token().access_token

    def upload_file(self, filename, file_size, file_data):
        upload_url = self._get_upload_url(filename, file_size)
        resp = self._upload_full_file_data(upload_url, file_size, file_data)
        return self._is_upload_completed(resp)

    def upload_file_chunk(self, filename, file_size, range_start, range_ends, file_chunk_data, upload_id=None):
        upload_url = self._get_upload_url(filename, file_size, upload_id)
        if not upload_id:
            upload_id = self._extract_upload_id(upload_url)
        resp = self._upload_file_chunk_data(upload_url, file_size, range_start, range_ends, file_chunk_data)
        return self._is_upload_completed(resp) or upload_id

    def _get_upload_url(self, filename, file_size, upload_id=None):
        return ('https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=%s' % upload_id
                if upload_id else self._start_file_upload(filename, file_size))

    def _extract_upload_id(self, upload_url):
        try:
            url_parts = urlparse(upload_url)
            query_params = parse_qs(url_parts.query)
            return query_params['upload_id'][0]
        except:
            raise Exception('Unexpected upload URL format')

    def _get_base_headers(self):
        return {'Authorization': 'Bearer %s' % self.token}

    def _start_file_upload(self, filename, file_size):
        url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable'
        headers = self._get_base_headers()
        headers.update({'X-Upload-Content-Length': str(file_size)})
        resp = requests.post(url, headers=headers, json={'name': filename})
        if resp.status_code != 200:
            raise Exception('Bad upload initialization')
        return resp.headers['Location']

    def _upload_full_file_data(self, upload_url, file_size, file_data):
        headers = self._get_base_headers()
        headers.update({'Content-Length': str(file_size)})
        return requests.put(upload_url, headers=headers, data=file_data)

    def _upload_file_chunk_data(self, upload_url, file_size, range_start, range_ends, file_chunk_data):
        chunk_size = range_ends - range_start + 1
        headers = self._get_base_headers()
        headers.update({'Content-Length': str(chunk_size)})
        headers.update({'Content-Range': 'bytes %i-%i/%i' % (range_start, range_ends, file_size)})
        return requests.put(upload_url, headers=headers, data=file_chunk_data)

    def _is_upload_completed(self, response):
        if response.status_code in [200, 201]:
            return self._upload_completed(response)
        elif response.status_code == 308:
            return False
        else:
            raise Exception('Error while uploading to backend cloud: %i' % response.status_code)

    def _upload_completed(self, response):
        file_id = response.json()['id']
        self._grant_access(file_id)
        return True

    def _grant_access(self, gdrive_file_id):
        url = 'https://www.googleapis.com/drive/v3/files/%s/permissions?sendNotificationEmail=false' % gdrive_file_id
        headers = self._get_base_headers()
        permission_data = {
            'type': 'user',
            'role': 'reader'
        }
        users_to_gran_access = settings.GRANT_ACCESS
        for email_address in users_to_gran_access:
            self._create_user_permission(url, headers, email_address, permission_data)

    def _create_user_permission(self, url, headers, email_address, permission_data):
        user_permission = permission_data.copy()
        user_permission.update({'emailAddress': email_address})
        resp = requests.post(url, headers=headers, json=user_permission)
        if resp.status_code not in [200, 201]:
            raise Exception('Could not grant access to user identified as: %s' % email_address)
