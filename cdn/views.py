from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from filetransfers.api import prepare_upload
from cdn.forms import ImageForm

def upload_to_cdn(request):
    view_url = '/cdn/upload/'
    if request.POST:
        image = ImageForm(request.POST, request.FILES)
        try:
            if image.is_valid():
               image.save()
            else:
                view_url += '?error=Not a valid image'
            return HttpResponseRedirect(view_url)
        except Exception,e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error('caught %s in image upload',e)
            raise e
    else:
        image = ImageForm()
    
    upload_url, upload_data = prepare_upload(request, view_url, backend='djangoappengine.storage.prepare_upload')
    
    template = 'cdn/upload.html'
    data = {'image':image, 'upload_url':upload_url, 'upload_data':upload_data }
    
    return render_to_response(template, data,context_instance=RequestContext(request))