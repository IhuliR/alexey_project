from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TextDocumentViewSet, LabelViewSet, AnnotationViewSet

v1_router = DefaultRouter()
v1_router.register('documents', TextDocumentViewSet, basename='document')
v1_router.register('labels', LabelViewSet, basename='label')
v1_router.register('annotations', AnnotationViewSet, basename='annotation')

urlpatterns = [
    path('v1/', include(v1_router.urls)),
    path('v1/', include('djoser.urls.jwt')),
]