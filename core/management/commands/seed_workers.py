from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
from core.models import CustomUser, WorkerProfile, ServiceCategory, Service, Booking


class Command(BaseCommand):
    help = "Seed diverse worker profiles and sample work location bookings across all service categories."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Diverse Worker Profiles & Work Location Bookings..."))

        # Ensure sample customer exists
        customer, _ = CustomUser.objects.get_or_create(
            username="customer_demo",
            defaults={
                "email": "customer_demo@kaamconnect.org",
                "role": CustomUser.Role.CUSTOMER,
                "first_name": "Rohan",
                "last_name": "Sharma",
                "phone_number": "+91 9876543210",
                "city": "Mumbai",
                "pincode": "400001",
                "latitude": 18.9388,
                "longitude": 72.8353,
            },
        )

        WORKERS_DATA = [
            {
                "username": "worker_rajesh_plumber",
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "email": "rajesh.plumbing@kaamconnect.org",
                "phone": "+91 9811223344",
                "city": "Mumbai",
                "pincode": "400050",
                "lat": 19.0596,
                "lng": 72.8295,
                "coop_id": "COOP-MUM-101",
                "skills": ["plumbing-services"],
                "hourly_rate": Decimal("350.00"),
                "rating": Decimal("4.85"),
                "reviews_count": 28,
                "bio": "Experienced master plumber with over 10 years of expertise in high-pressure piping, bathroom mixer fittings, and tank cleaning.",
            },
            {
                "username": "worker_sunil_electrician",
                "first_name": "Sunil",
                "last_name": "Verma",
                "email": "sunil.electrical@kaamconnect.org",
                "phone": "+91 9822334455",
                "city": "Mumbai",
                "pincode": "400058",
                "lat": 19.1197,
                "lng": 72.8464,
                "coop_id": "COOP-MUM-102",
                "skills": ["electrical-services", "appliance-repair"],
                "hourly_rate": Decimal("400.00"),
                "rating": Decimal("4.92"),
                "reviews_count": 45,
                "bio": "Certified industrial and residential electrician. Specializes in MCB fuse replacements, modular switchboards, and heavy appliance wiring.",
            },
            {
                "username": "worker_amit_carpenter",
                "first_name": "Amit",
                "last_name": "Sutar",
                "email": "amit.carpentry@kaamconnect.org",
                "phone": "+91 9833445566",
                "city": "Mumbai",
                "pincode": "400078",
                "lat": 19.1412,
                "lng": 72.9312,
                "coop_id": "COOP-MUM-103",
                "skills": ["carpentry-services"],
                "hourly_rate": Decimal("450.00"),
                "rating": Decimal("4.78"),
                "reviews_count": 19,
                "bio": "Craftsman carpenter specializing in custom teak furniture assembly, lock fittings, and wardrobe repairs.",
            },
            {
                "username": "worker_vikram_mover",
                "first_name": "Vikram",
                "last_name": "Singh",
                "email": "vikram.movers@kaamconnect.org",
                "phone": "+91 9844556677",
                "city": "Mumbai",
                "pincode": "400069",
                "lat": 19.1176,
                "lng": 72.8631,
                "coop_id": "COOP-MUM-104",
                "skills": ["packers-and-movers"],
                "hourly_rate": Decimal("600.00"),
                "rating": Decimal("4.95"),
                "reviews_count": 52,
                "bio": "Lead operator for cooperative movers. Safe packaging with bubble wrap, furniture dismantling, and local house relocation.",
            },
            {
                "username": "worker_priya_cleaner",
                "first_name": "Priya",
                "last_name": "Jadhav",
                "email": "priya.cleaning@kaamconnect.org",
                "phone": "+91 9855667788",
                "city": "Mumbai",
                "pincode": "400016",
                "lat": 19.0330,
                "lng": 72.8570,
                "coop_id": "COOP-MUM-105",
                "skills": ["home-cleaning", "pest-control"],
                "hourly_rate": Decimal("300.00"),
                "rating": Decimal("4.88"),
                "reviews_count": 34,
                "bio": "Eco-friendly deep cleaning expert. Uses non-toxic sanitizers for full home deep scrub, sofa shampooing, and pest disinfection.",
            },
            {
                "username": "worker_suresh_painter",
                "first_name": "Suresh",
                "last_name": "Painter",
                "email": "suresh.painter@kaamconnect.org",
                "phone": "+91 9866778899",
                "city": "Mumbai",
                "pincode": "400028",
                "lat": 19.0178,
                "lng": 72.8478,
                "coop_id": "COOP-MUM-106",
                "skills": ["painting-renovation"],
                "hourly_rate": Decimal("380.00"),
                "rating": Decimal("4.75"),
                "reviews_count": 22,
                "bio": "Professional painter with expertise in emulsion wall finishes, damp proofing, and texture accent walls.",
            },
            {
                "username": "worker_anil_ac_tech",
                "first_name": "Anil",
                "last_name": "Deshmukh",
                "email": "anil.ac@kaamconnect.org",
                "phone": "+91 9877889900",
                "city": "Mumbai",
                "pincode": "400067",
                "lat": 19.2045,
                "lng": 72.8376,
                "coop_id": "COOP-MUM-107",
                "skills": ["appliance-repair", "electrical-services"],
                "hourly_rate": Decimal("500.00"),
                "rating": Decimal("4.90"),
                "reviews_count": 39,
                "bio": "HVAC certified AC & refrigeration technician. Specialists in split AC jet cleaning, gas charging, and PCB repairs.",
            },
            {
                "username": "worker_manoj_pest_specialist",
                "first_name": "Manoj",
                "last_name": "Shinde",
                "email": "manoj.pest@kaamconnect.org",
                "phone": "+91 9888990011",
                "city": "Mumbai",
                "pincode": "400080",
                "lat": 19.1726,
                "lng": 72.9426,
                "coop_id": "COOP-MUM-108",
                "skills": ["pest-control"],
                "hourly_rate": Decimal("350.00"),
                "rating": Decimal("4.80"),
                "reviews_count": 16,
                "bio": "Government-licensed pest control technician. Odorless gel treatment for cockroaches and subterranean termite barrier protection.",
            },
        ]

        worker_profiles = []
        for w in WORKERS_DATA:
            user, u_created = CustomUser.objects.get_or_create(
                username=w["username"],
                defaults={
                    "email": w["email"],
                    "role": CustomUser.Role.PROVIDER,
                    "first_name": w["first_name"],
                    "last_name": w["last_name"],
                    "phone_number": w["phone"],
                    "city": w["city"],
                    "pincode": w["pincode"],
                    "latitude": w["lat"],
                    "longitude": w["lng"],
                    "bio": w["bio"],
                },
            )
            if u_created:
                user.set_password("Worker@123")
                user.save()

            profile, p_created = WorkerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "coop_member_id": w["coop_id"],
                    "skills": w["skills"],
                    "availability_status": WorkerProfile.AvailabilityStatus.AVAILABLE,
                    "verification_status": WorkerProfile.VerificationStatus.VERIFIED,
                    "hourly_rate": w["hourly_rate"],
                    "rating": w["rating"],
                    "total_reviews_count": w["reviews_count"],
                    "service_radius_km": 25,
                    "latitude": w["lat"],
                    "longitude": w["lng"],
                },
            )
            # Ensure skills are updated
            profile.skills = w["skills"]
            profile.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            profile.save()
            worker_profiles.append(profile)

            status_str = "Created" if u_created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {status_str} Worker: {user.get_full_name()} ({', '.join(w['skills'])})"))

        # Create sample job bookings with GPS locations for map testing
        SAMPLE_BOOKINGS = [
            {
                "service_slug": "plumbing-inspection-repair",
                "worker": worker_profiles[0],  # Rajesh Plumber
                "address": "Flat 402, Sea Breeze Heights, Bandra West, Mumbai 400050",
                "lat": 19.0544,
                "lng": 72.8280,
                "instructions": "Master bathroom tap leak. Please call before arrival.",
                "amount": Decimal("499.00"),
                "status": Booking.BookingStatus.ACCEPTED,
            },
            {
                "service_slug": "wiring-switchboard-installation",
                "worker": worker_profiles[1],  # Sunil Electrician
                "address": "Shop 12, Prime Plaza, Andheri West, Mumbai 400058",
                "lat": 19.1136,
                "lng": 72.8397,
                "instructions": "Main MCB tripping frequently during AC usage.",
                "amount": Decimal("449.00"),
                "status": Booking.BookingStatus.IN_PROGRESS,
            },
            {
                "service_slug": "ac-servicing-repair",
                "worker": None,  # Open pending job for map matching
                "address": "Building 5, Green Park Society, Powai, Mumbai 400076",
                "lat": 19.1176,
                "lng": 72.9060,
                "instructions": "Split AC cooling issue and filter wash required.",
                "amount": Decimal("599.00"),
                "status": Booking.BookingStatus.PENDING,
            },
            {
                "service_slug": "furniture-repair-assembly",
                "worker": None,  # Open pending job
                "address": "Tower B, Horizon Enclave, Thane West, Mumbai 400601",
                "lat": 19.2183,
                "lng": 72.9781,
                "instructions": "Wooden dining table leg repair and door hinge fix.",
                "amount": Decimal("499.00"),
                "status": Booking.BookingStatus.PENDING,
            },
        ]

        now = timezone.now()
        for i, sb in enumerate(SAMPLE_BOOKINGS):
            service = Service.objects.filter(slug=sb["service_slug"]).first()
            if not service:
                continue
            booking, _ = Booking.objects.get_or_create(
                customer=customer,
                service=service,
                service_address=sb["address"],
                defaults={
                    "worker": sb["worker"],
                    "scheduled_time": now + datetime.timedelta(hours=(i + 1) * 3),
                    "status": sb["status"],
                    "total_amount": sb["amount"],
                    "special_instructions": sb["instructions"],
                    "customer_latitude": sb["lat"],
                    "customer_longitude": sb["lng"],
                },
            )
            booking.customer_latitude = sb["lat"]
            booking.customer_longitude = sb["lng"]
            booking.save()

        self.stdout.write(self.style.SUCCESS(f"\nWorker seeding completed! Seeded {len(WORKERS_DATA)} worker profiles and sample map bookings."))
