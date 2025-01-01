from django.db import transaction
from rest_framework import serializers
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from serializers import StationsSerializer, FareSerializer, BusDetailsSerializer, UserSerializer, CustomerSerializer, \
    BusCapacitySerializer, TicketBookingSerializer, TicketCancelSerializer
from .models import (
    Stations, Fare, BusDetails, User, TicketBooking, Customer, BusCapacity, TicketCancel,
)


# Create your views here.
# -------------
# STATIONS
# -------------
class StationViewSet(viewsets.ModelViewSet):
    queryset = Stations.objects.all()
    serializer_class = StationsSerializer


# -------------
# FARE
# -------------
class FareViewSet(viewsets.ModelViewSet):
    queryset = Fare.objects.all()
    serializer_class = FareSerializer


# -------------
# BUS DETAILS
# -------------
class BusDetailsViewSet(viewsets.ModelViewSet):
    queryset = BusDetails.objects.all()
    serializer_class = BusDetailsSerializer


# -------------
# USER
# -------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# -------------
# Customer
# -------------
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


# -------------
# Bus Capacity
# -------------
class BusCapacityAPIView(APIView):
    """
    A custom API to manage BusCapacity records:

    GET /bus-capacity/          -> List all capacity records
    GET /bus-capacity/<pk>/     -> Retrieve a single capacity record
    POST /bus-capacity/         -> Create a new capacity record
    PATCH /bus-capacity/<pk>/   -> Partially update a record (e.g. adjust capacity)
    DELETE /bus-capacity/<pk>/  -> Delete a capacity record

    Example for POST:
    {
        "bus": 1,
        "available_capacity": 40
    }
    """

    def get(self, request, pk=None):
        """
        Returns all BusCapacity records if no pk is provided,
        otherwise returns a single record with the given pk.
        """
        try:
            if pk:
                bus_capacity = BusCapacity.objects.get(pk=pk)
                serializer = BusCapacitySerializer(bus_capacity)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # List all capacity records
                bus_capacities = BusCapacity.objects.all()
                serializer = BusCapacitySerializer(bus_capacities, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except BusCapacity.DoesNotExist:
            return Response(
                {"error": "BusCapacity not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """
        Create a new BusCapacity record for a bus.
        Example request body:
        {
            "bus": <bus_id>,
            "available_capacity": 40
        }
        """
        serializer = BusCapacitySerializer(data=request.data)
        if serializer.is_valid():
            try:
                # If you want concurrency checks even on creation, wrap in transaction:
                with transaction.atomic():
                    bus_capacity = serializer.save()
                return Response(
                    BusCapacitySerializer(bus_capacity).data,
                    status=status.HTTP_201_CREATED
                )
            except serializers.ValidationError as e:
                return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as ex:
                return Response({"error": str(ex)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        """"
        Update the entire BusCapacity record (all fields).
        'partial=False' ensures that every required field must be present.

        Example request body:
        {
            "bus": 1,
            "available_capacity": 35
        }
        """
        if not pk:
            return Response({"error": "PUT requires a resource ID (pk)"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                # Lock the row for update to prevent race conditions
                bus_capacity = BusCapacity.objects.select_for_update().get(pk=pk)
                # By default, ModelSerializer uses partial=False with .is_valid(),
                # but we'll be explicit:
                serializer = BusCapacitySerializer(bus_capacity, data=request.data, partial=False)
                if serializer.is_valid():
                    updated_capacity = serializer.save()
                    return Response(BusCapacitySerializer(updated_capacity).data, status=status.HTTP_200_OK)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusCapacity.DoesNotExist:
            return Response({"error": "BusCapacity not found."}, status=status.HTTP_404_NOT_FOUND)
        except serializers.ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response({"error": str(ex)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        """
        Partially update a BusCapacity record (e.g., adjust available_capacity).
        Example request body:
        {
            "available_capacity": 35
        }
        This could be used if you need direct control over capacity,
        but typically capacity is adjusted by booking/cancellation logic.
        """
        if not pk:
            return Response(
                {"error": "PATCH requires a resource ID (pk)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Wrap in transaction if you want concurrency protection
            with transaction.atomic():
                bus_capacity = BusCapacity.objects.select_for_update().get(pk=pk)
                serializer = BusCapacitySerializer(bus_capacity, data=request.data, partial=True)
                if serializer.is_valid():
                    updated_capacity = serializer.save()
                    return Response(
                        BusCapacitySerializer(updated_capacity).data,
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusCapacity.DoesNotExist:
            return Response({"error": "BusCapacity not found."}, status=status.HTTP_404_NOT_FOUND)
        except serializers.ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response({"error": str(ex)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        """
        Delete a specific BusCapacity record.
        """
        if not pk:
            return Response(
                {"error": "DELETE requires a resource ID (pk)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bus_capacity = BusCapacity.objects.get(pk=pk)
            bus_capacity.delete()
            return Response({"success": "BusCapacity deleted."}, status=status.HTTP_204_NO_CONTENT)
        except BusCapacity.DoesNotExist:
            return Response({"error": "BusCapacity not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------
# Ticket Booking
# ---------------
class TicketBookingAPIView(APIView):

    def get(self, request, pk=None):
        try:
            if pk:
                ticket = TicketBooking.objects.get(pk=pk)
                serializer = TicketBookingSerializer(ticket)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                tickets = TicketBooking.objects.all()
                serializer = TicketBookingSerializer(tickets, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except TicketBooking.DoesNotExist:
            return Response({"error": "TicketBooking not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Creates a new booking and auto-decrements bus capacity.
        Example request body:
        {
            "customer": 1,
            "bus": 2,
            "seat_booked": 3
            "source_station": 10,
            "destination_station": 11
        }
        """
        serializer = TicketBookingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # use a transaction to lock the BusCapacity row for update:
                with transaction.atomic():
                    booking = serializer.save()  # calls create() in serializer
                return Response(TicketBookingSerializer(booking).data, status=status.HTTP_201_CREATED)
            except serializers.ValidationError as e:
                return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as ex:
                return Response({"error": str(ex)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --------------
# Ticket Cancel
# ---------------
class TicketCancelAPIView(APIView):
    """
    APIView for creating and retrieving TicketCancel records.

    GET /ticket-cancel/         -> List all cancellations
    GET /ticket-cancel/<pk>/    -> Get a specific cancellation
    POST /ticket-cancel/        -> Create a new cancellation (restore seats)
    """

    def get(self, request, pk=None):
        """
        If pk is provided, return one cancellation record;
        otherwise, return the full list of cancellations.
        """
        try:
            if pk:
                canceled_record = TicketCancel.objects.get(pk=pk)
                serializer = TicketCancelSerializer(canceled_record)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                all_cancellations = TicketCancel.objects.all()
                serializer = TicketCancelSerializer(all_cancellations, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except TicketCancel.DoesNotExist:
            return Response(
                {"error": "TicketCancel record not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """
        APIView for creating and retrieving TicketCancel records.

        GET /ticket-cancel/         -> List all cancellations
        GET /ticket-cancel/<pk>/    -> Get a specific cancellation
        POST /ticket-cancel/        -> Create a new cancellation (restore seats)

        Example request body for POST:
        {
            "ticket_booking": 5,
            "seat_canceled": 2
        }
        Where 'ticket_booking' is the primary key of an existing TicketBooking object.
        """
        serializer = TicketCancelSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    canceled_ticket = serializer.save()  # calls create() in serializer
                return Response(
                    TicketCancelSerializer(canceled_ticket).data,
                    status=status.HTTP_201_CREATED
                )
            except serializers.ValidationError as e:
                return Response(
                    {"error": e.detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as ex:
                return Response(
                    {"error": str(ex)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
