from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AuthViewSet, TempAdminCreationViewSet 

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'auth', AuthViewSet, basename='auth')

router.register(r'temp-admin', TempAdminCreationViewSet, basename='temp-admin')

urlpatterns = [
    path('', include(router.urls)),
]
