from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template

from upload.forms import UploadForm
from upload.models import UploadModel

from filetransfers.api import prepare_upload, serve_file

def upload_handler(request):
    view_url = reverse('upload.views.upload_handler')
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        try:
            if form.is_valid():
                form.save()
            else:
                view_url += '?error=Not a valid image'
            return HttpResponseRedirect(view_url)
        except Exception,e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error('caught %s in image upload',e)
            raise e

    upload_url, upload_data = prepare_upload(request, view_url)
    form = UploadForm()
    return direct_to_template(request, 'upload/upload.html',
        {'form': form, 'upload_url': upload_url, 'upload_data': upload_data,
         'uploads': UploadModel.objects.all(), 'error': request.GET.get('error')})

def download_handler(request, pk):
    upload = get_object_or_404(UploadModel, pk=pk)
    return serve_file(request, upload.file, save_as=True)

def delete_handler(request, pk):
    if request.method == 'POST':
        get_object_or_404(UploadModel, pk=pk).delete()
    return HttpResponseRedirect(reverse('upload.views.upload_handler'))