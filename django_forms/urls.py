from django.views.static import serve
from django.urls import path, include, re_path
from django.contrib import admin

from django.conf import settings

admin.site.site_header = settings.ADMIN_SITE_HEADER

urlpatterns = [
        re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
        path('', include('numen.urls')),
        path('be/', include('numen.urls')),
        path('', include('chatbot.urls')),
        path('admin/', admin.site.urls)
]
