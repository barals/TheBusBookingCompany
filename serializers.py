from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from bus_booking.models import Stations, Fare, BusDetails, User, Customer, RouteTable, BusCapacity, TicketBooking, TicketCancel, \
    Payment


class StationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stations
        fields = '__all__'


class FareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fare
        fields = '__all__'


class BusDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusDetails
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = ['customer_number', 'user_id', 'first_name', 'last_name', 'contact_number', 'email_id', 'created_at',
                  'updated_at']

    # def create(self, validated_data):
    #     """
    #     If the user data is nested, handle creation for the nested user as well.
    #     """
    #     user_data = validated_data.pop('user')
    #     user_instance = User.objects.create(**user_data)
    #     customer = CustomerDetail.objects.create(user_name=user_instance, **validated_data)
    #     return customer
    #
    # def update(self, instance, validated_data):
    #     """
    #     If updating the nested user data is allowed, handle that here.
    #     """
    #     user_data = validated_data.pop('user', None)
    #     if user_data:
    #         user_instance = instance.user
    #         for key, value in user_data.items():
    #             setattr(user_instance, key, value)
    #         user_instance.save()
    #
    #     return super().update(instance, validated_data)


class RouteTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteTable
        fields = '__all__'


class BusCapacitySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusCapacity
        fields = '__all__'

    def validate(self, data):
        """
        Optionally ensure that 'available_capacity' does not exceed 'bus.capacity'.
        This is mostly enforced by the model's clean() method, but you can double-check here too.
        """
        bus = data.get('bus')
        available_capacity = data.get('available_capacity', 0)
        if bus and available_capacity > bus.capacity:
            raise serializers.ValidationError("Available capacity cannot exceed bus total capacity.")
        return data


class TicketBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketBooking
        fields = '__all__'

    def validate(self, data):
        """
        Check if the bus has enough seats before creating the booking.
        """
        bus = data['bus']
        seat_booked = data['seat_booked']

        # get current capacity record, or create if doesn't exist
        bus_capacity, created = BusCapacity.objects.get_or_create(
            bus=bus, defaults={'available_capacity': bus.capacity}
        )
        if bus_capacity.available_capacity < seat_booked:
            raise serializers.ValidationError("Not enough seats available.")
        return data

    # def create(self, validated_data):
    #     """
    #     Deduct seats from bus capacity upon creating a booking.
    #     """
    #     bus = validated_data['bus']
    #     seat_booked = validated_data['seat_booked']
    #     bus_capacity = BusCapacity.objects.get(bus=bus)
    #     # deduct seats
    #     bus_capacity.available_capacity -= seat_booked
    #     bus_capacity.save()
    #     # create the TicketBooking record
    #     booking = TicketBooking.objects.create(**validated_data)
    #     return booking

    def create_booking_safe(self, data):
        with transaction.atomic():
            bus = data['bus']
            seat_booked = data['seat_booked']
            # lock BusCapacity row for update
            bus_capacity = BusCapacity.objects.select_for_update().get(bus=bus)
            if bus_capacity.available_capacity < seat_booked:
                raise ValidationError("Not enough seats!")
            bus_capacity.available_capacity -= seat_booked
            bus_capacity.save()
            # now create the booking
            booking = TicketBooking.objects.create(**data)
        return booking


class TicketCancelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketCancel
        fields = '__all__'

    def validate(self, attrs):
        ticket_booking = attrs['ticket_booking']
        seat_canceled = attrs['seat_canceled']

        if seat_canceled > ticket_booking.seat_booked:
            raise serializers.ValidationError(
                "Can't cancel more seats than were originally booked."
            )
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            canceled_obj = super().create(validated_data)
        return canceled_obj


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
