from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StationViewSet, FareViewSet, BusDetailsViewSet,
    UserViewSet, TicketBookingAPIView, CustomerViewSet, BusCapacityAPIView, TicketCancelAPIView,
)

# ---------------
# Default Router
# Resource register
# ---------------
router = DefaultRouter()
# stations resource registered
router.register('stations', StationViewSet, basename='stations')
# fares resources registered
router.register('fares', FareViewSet, basename='fares')
# bus_details resource registered
router.register('bus-details', BusDetailsViewSet, basename='bus-details')
# user resource registered
router.register('users', UserViewSet, basename='users')
# customer resource registred
router.register('customer-details', CustomerViewSet, basename='customer-details')
urlpatterns = [
    # default router included for all ViewSet
    path('', include(router.urls)),
    # -------------------
    # BusCapacity APIView
    # -------------------
    path('bus-capacity/', BusCapacityAPIView.as_view(), name='bus-capacity'),
    path('bus-capacity/<int:pk>/', BusCapacityAPIView.as_view(), name='bus-capacity'),
    # ---------------------
    # Ticket Booking APIView
    # ---------------------
    path('ticket_booking/', TicketBookingAPIView.as_view(), name='ticket_booking'),
    # ----------------------
    # Ticket Cancel APIView
    # -----------------------
    path('ticket_cancel/', TicketCancelAPIView.as_view(), name='ticket_cancel'),
]
