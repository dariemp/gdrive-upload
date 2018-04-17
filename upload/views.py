from django.shortcuts import render
from django.views.generic.edit import FormView
from googleapi import GoogleDrive
from .forms import UploadForm

# Create your views here.

class UploadView(FormView):

    form_class = UploadForm
    template_name = 'upload.html'

    def post(self, request, *args, **kwargs):
        form = UploadForm(request.POST, request.FILES)
        context = self.get_context_data(form=form)
        if form.is_valid():
            fileobj = request.FILES['gdrive_upload']
            try:
                gdrive = GoogleDrive()
                gdrive.upload_file(fileobj.name, fileobj.size, fileobj.read())
                context.update({'success': True})
            except Exception, ex:
                context.update({'failure': True, 'error': str(ex)})
        return self.render_to_response(context)
