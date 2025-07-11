from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('social-auth/', include('social_django.urls', namespace='social')),
    path('blog/', include('blog.urls')),
    path('options/', include('dasoptions.urls')),
    path('future/', include('ddfuture.urls')),
    path('indfuture/', include('indfuture.urls')),
    path('staticfuture/', include('staticfuture.urls')),
    path('designapps/', include('designapps.urls')),
    path('maindas/', include('maindas.urls')),
    path('xheat/', include('xheat.urls')),
    path('alerts/', include('xalert.urls')),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

