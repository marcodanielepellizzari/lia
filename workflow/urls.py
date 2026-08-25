from rest_framework.routers import DefaultRouter
from .views import SavedFilterViewSet, DatasetViewSet

router = DefaultRouter()
router.register("saved-filters", SavedFilterViewSet, basename="savedfilter")
router.register("datasets", DatasetViewSet, basename="dataset")

urlpatterns = router.urls
