from django.forms import Form, FileField

class UploadForm(Form):
    gdrive_file = FileField(label='Select a File to Upload')
