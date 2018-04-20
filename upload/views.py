
import json
from django.http import HttpResponse
from django.views.generic.edit import FormView
from googleapi import GoogleDrive
from .forms import UploadForm

# Create your views here.

class UploadView(FormView):

    form_class = UploadForm
    template_name = 'upload.html'

    def post(self, request, *args, **kwargs):
        form = UploadForm(request.POST, request.FILES)
        status_code = 200 
        if form.is_valid():
            file_obj = request.FILES['gdrive_file']
            try:
                upload = self._handle_upload(request, file_obj)
                response_content = {'success': True, 'upload': upload}
            except Exception, ex:
                response_content = {'failure': True, 'error': str(ex)}
                status_code = 500
        else:
            response_content = {'failure': True, 'error': 'invalid form'}
            status_code = 400
        return HttpResponse(content=json.dumps(response_content), status=status_code)

    def _handle_upload(self, request, file_obj):
        range_content = request.META.get('HTTP_X_CONTENT_RANGE')
        upload_id = request.META.get('HTTP_X_UPLOAD_ID')
        if range_content:
            file_name = request.META.get('HTTP_X_FILE_NAME')
            return self._google_drive_upload_chunk(file_name, file_obj, range_content, upload_id)
        else:
            return self._google_drive_whole_file(file_obj)

    def _google_drive_whole_file(self, file_obj):
        gdrive = GoogleDrive()
        return gdrive.upload_file(file_obj.name, file_obj.size, file_obj.read())

    def _google_drive_upload_chunk(self, file_name, file_chunk_obj, range_content, upload_id):
        range_start, range_ends, file_size = self._parse_range_content(range_content, file_chunk_obj.size)
        gdrive = GoogleDrive()
        return gdrive.upload_file_chunk(file_name, file_size, range_start, range_ends,
                                        file_chunk_obj.read(), upload_id)

    def _parse_range_content(self, range_content, chunk_size):
        if not range_content.startswith('bytes '):
            raise Exception('Unsuported range unit')
        try:
            range_content = range_content.replace('bytes ', '')
            range_parts = range_content.split('/')
            range_boundaries = range_parts[0]
            file_size = int(range_parts[1])
            boundaries = range_boundaries.split('-')
            range_start = int(boundaries[0])
            range_ends = int(boundaries[1])
            assert range_ends - range_start + 1 == chunk_size
            return range_start, range_ends, file_size
        except:
            raise Exception('Incorrect file range specification')
