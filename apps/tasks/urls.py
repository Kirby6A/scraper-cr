from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TaskExecutionViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)
router.register(r'executions', TaskExecutionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]