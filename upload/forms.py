from django.forms import Form, FileField

class UploadForm(Form):
    gdrive_upload = FileField(label='Select a Small File to Upload')
