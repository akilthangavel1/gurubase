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
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

