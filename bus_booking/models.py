from django.db import models, transaction
from rest_framework.exceptions import ValidationError


# Create your models here.
# -------------------------------
# MASTER TABLES
# -------------------------------

class Stations(models.Model):
    """
    Master table for bus stations.
    """
    station_name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.station_name


class Fare(models.Model):
    """
    Master table representing a fare for a given distance, price, etc.
    """
    distance = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Fare for {self.distance}km = {self.price}"


class BusDetails(models.Model):
    """
    Master table for bus information.
    """
    bus_number = models.CharField(max_length=50, unique=True)
    # route_number could be a free text or a reference to the Route table
    route_number = models.CharField(max_length=50, null=True, blank=True)
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bus {self.bus_number}"


class User(models.Model):
    """
    Master table for all users of the system (could be admin, staff, or customer).
    """
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=20)
    email_id = models.EmailField(unique=True)
    user_name = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # In real apps, use a secure hashing approach!
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Customer(models.Model):
    """
    Master table for all customers who avail the services.
    In real systems, you'd often do:
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')

    That way, you can do: self.user.user_name
    """
    customer_number = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=20)
    email_id = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def user_id(self):
        return f"{self.user.user_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# -------------------------------
# TRANSACTIONAL TABLES
# -------------------------------

# class CustomerDetail(models.Model):
#     """
#     Transactional table for extended customer info (if different from main User).
#     If not needed, you can store everything in User directly.
#     """
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
#     # Alternatively: if you want a separate ID for customer:
#     # customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     # Additional fields if needed (address, city, etc.)
#     def __str__(self):
#         return f"Customer profile for {self.user.user_name}"


class RouteTable(models.Model):
    """
    Transactional table that defines a bus route across stations.
    Potentially references many stations,
    but simplified here to a single station foreign key.
    """
    route_number = models.CharField(max_length=50)
    station = models.ForeignKey(Stations, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Route {self.route_number} includes station {self.station}"


class BusCapacity(models.Model):
    """
    Transactional table that might track real-time seat availability
    for a given bus on a given date/time or route, etc.
    Tracks the *current* seat availability for a given bus.
    """
    bus = models.ForeignKey(BusDetails, on_delete=models.CASCADE, related_name='capacity_records')
    available_capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """
        Ensure available_capacity is not negative and does not exceed the bus's max capacity.
        """
        if self.available_capacity < 0:
            raise ValidationError("Available capacity cannot be negative.")
        if self.bus and self.available_capacity > self.bus.capacity:
            raise ValidationError("Available capacity cannot exceed the bus's total capacity.")

    def save(self, *args, **kwargs):
        # Run custom validation
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bus {self.bus.bus_number} capacity {self.available_capacity}"


class TicketBooking(models.Model):
    """
    Transactional table storing each booking.
    1) Check if the bus has enough available seats (in BusCapacity).
    2) Deduct the booked seats from BusCapacity in a transaction-safe way.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    bus = models.ForeignKey(BusDetails, on_delete=models.CASCADE)
    seat_booked = models.PositiveIntegerField()
    source_station = models.ForeignKey(
        Stations,
        on_delete=models.CASCADE,
        related_name='bookings_as_source',
        null=True, blank=True
    )
    destination_station = models.ForeignKey(
        Stations,
        on_delete=models.CASCADE,
        related_name='bookings_as_destination',
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # E.g., on save, you could reduce the bus's capacity if you want
    def save(self, *args, **kwargs):
        """
        Custom logic:
        1) Ensure the bus has enough available seats in BusCapacity before saving.
        2) Deduct seats if booking is new or if seat_booked is changed.
        """
        if self.pk is None:
            # This is a new booking
            bus_capacity = BusCapacity.objects.get_or_create(
                bus=self.bus,
                defaults={'available_capacity': self.bus.capacity}
            )[0]
        if bus_capacity.available_capacity < self.seat_booked:
            raise ValidationError(f"Not enough seats on bus {self.bus.bus_number}.")

        # reduce seat count
        bus_capacity.available_capacity -= self.seat_booked
        bus_capacity.save()

        # if you also allow updates to seat_booked, handle changes here.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"TicketBooking for {self.customer}, seats={self.seat_booked}"


class TicketCancel(models.Model):
    """
    Transactional table for canceled tickets.
    Stores each booking transaction. We'll use a custom create flow (via serializer) to:
    1) Check if the bus has enough available seats (in BusCapacity).
    2) Deduct the booked seats from BusCapacity in a transaction-safe way.
    """
    # Link to the actual booking being canceled
    ticket_booking = models.ForeignKey(TicketBooking, on_delete=models.CASCADE)
    seat_canceled = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk is None:
            # The bus is always known from the booking
            with transaction.atomic():
                booking = self.ticket_booking
                bus_capacity = BusCapacity.objects.select_for_update().get_or_create(
                    bus=booking.bus,
                    defaults={'available_capacity': booking.bus.capacity}
                )[0]
                new_capacity = bus_capacity.available_capacity + self.seat_canceled
                bus_capacity.available_capacity = min(new_capacity, booking.bus.capacity)
                bus_capacity.save()
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Transactional table for payments.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ticket_booking = models.ForeignKey(TicketBooking, on_delete=models.CASCADE)
    total_amount_paid = models.DecimalField(max_digits=7, decimal_places=2)
    payment_mode = models.CharField(max_length=50)  # e.g. "Credit Card", "UPI", etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment of {self.total_amount_paid} by {self.customer.user.user_name}"
