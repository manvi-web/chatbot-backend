from django.urls import path, re_path
from django.contrib import admin
from . import views
from django.conf import settings

admin.site.site_header = settings.ADMIN_SITE_HEADER

urlpatterns = [
    path("health", views.health_check),
    path("", views.RenderMainDashboard),
    path("numen", views.RenderMainDashboard),
    path("be/", views.RenderMainDashboard),

    re_path(r'^mainDashboard', views.RenderMainDashboard, name="mainDashboard"),
    re_path(r'^renderApplicationSessions', views.renderResources, name="renderApplicationSessions"),
    re_path(r'^getApplicationTemplates', views.getApplicationTemplates, name="getApplicationTemplates"),
    re_path(r'^rebootResourceButton', views.rebootResourceButton, name='rebootResourceButton'),
    re_path(r'^startResourceButton', views.startResourceButton, name='startResourceButton'),
    re_path(r'^stopResourceButton', views.stopResourceButton, name='stopResourceButton'),
    re_path(r'^terminateResourceButton', views.deleteResourceButton, name='terminateResourceButton'),
    re_path(r'^connectEC2Machine', views.connectEC2Machine, name='connectEC2Machine'),
    re_path(r'^shareResourceButton', views.shareResourceButton, name='shareResourceButton'),
    re_path(r'^getLicencestatus', views.getLicencestatus, name='getLicencestatus'),
    re_path(r'^launchApplication', views.withoutCodeBuild, name='launchApplication'),
    re_path(r'^unShareResourceButton', views.unShareResourceButton, name='unShareResourceButton'),
    re_path(r'^getBudget', views.getBudget, name='getBudget'),
    re_path(r'^updateBudget', views.updateBudget, name='updateBudget'),
    re_path(r'^getInstanceList', views.getInstanceList, name='getInstanceList'),
    re_path(r'^checkLaunch', views.checkLaunch, name='checkLaunch'),
    re_path(r'^list_s3_objects', views.list_s3_objects, name='list_s3_objects'),
    re_path(r'^create_s3_folder', views.create_s3_folder, name='create_s3_folder'),
    re_path(r'^get_download_url', views.get_download_url, name='get_download_url'),
    re_path(r'^get-presigned-urls', views.generate_presigned_urls, name="get_presigned_urls"),
    re_path(r'^getResourceDetails', views.getResourceDetails, name='getResourceDetails'),
    re_path(r'^getDatabaseResources', views.getDatabaseResources, name='getDatabaseResources'),
    re_path(r'^startShell', views.startShell, name='startShell'),
    re_path(r'^shellInput', views.shellInput, name='shellInput'),
    re_path(r'^shellOutput', views.shellOutput, name='shellOutput'),
    re_path(r'^stopShell', views.stopShell, name='stopShell'),
] 