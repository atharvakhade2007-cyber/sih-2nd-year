from django.core.management.base import BaseCommand
from core.models import ServiceCategory, Service


class Command(BaseCommand):
    help = "Seed initial household service categories and service items into the database."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Service Categories and Services..."))

        SEED_DATA = [
            {
                "category": {
                    "name": "Plumbing Services",
                    "slug": "plumbing-services",
                    "description": "Comprehensive plumbing solutions including pipe repair, tap installations, and water tank cleaning.",
                    "icon": "fa-solid fa-wrench",
                },
                "services": [
                    {
                        "title": "Plumbing Inspection & Repair",
                        "slug": "plumbing-inspection-repair",
                        "description": "Professional diagnosis and repair for clogged drains, low pressure, and minor pipe leaks.",
                        "base_price": 499.00,
                    },
                    {
                        "title": "Pipe Fitting & Leakage Repair",
                        "slug": "pipe-fitting-leakage",
                        "description": "Leak detection, pipe joint sealing, and replacement of damaged PVC/metal pipes.",
                        "base_price": 399.00,
                    },
                    {
                        "title": "Tap & Mixer Installation",
                        "slug": "tap-mixer-installation",
                        "description": "Installation and replacement of bathroom taps, sink mixers, and shower heads.",
                        "base_price": 299.00,
                    },
                    {
                        "title": "Water Tank Cleaning & Fitting",
                        "slug": "water-tank-cleaning",
                        "description": "Overhead and underground water tank deep cleaning, sanitization, and pipe valve installation.",
                        "base_price": 799.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Electrical Services",
                    "slug": "electrical-services",
                    "description": "Safe electrical work for home appliances, switchboards, fans, and circuit protection.",
                    "icon": "fa-solid fa-bolt",
                },
                "services": [
                    {
                        "title": "Electrician Inspection & Fault Repair",
                        "slug": "electrician-inspection-repair",
                        "description": "Detailed electrical diagnostic, short-circuit troubleshooting, and wiring check.",
                        "base_price": 349.00,
                    },
                    {
                        "title": "Wiring & Switchboard Installation",
                        "slug": "wiring-switchboard-installation",
                        "description": "New switchboard installation, socket replacement, and modular switch wiring.",
                        "base_price": 449.00,
                    },
                    {
                        "title": "Fan & Ceiling Light Installation",
                        "slug": "fan-light-installation",
                        "description": "Assembly and ceiling mounting for fans, chandeliers, tube lights, and fancy LEDs.",
                        "base_price": 299.00,
                    },
                    {
                        "title": "MCB & Circuit Breaker Replacement",
                        "slug": "mcb-fuse-replacement",
                        "description": "Installation of miniature circuit breakers (MCBs), main switches, and surge protectors.",
                        "base_price": 399.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Carpentry Services",
                    "slug": "carpentry-services",
                    "description": "Expert woodworking, door fitting, custom furniture assembly, and lock installations.",
                    "icon": "fa-solid fa-hammer",
                },
                "services": [
                    {
                        "title": "Furniture Repair & Assembly",
                        "slug": "furniture-repair-assembly",
                        "description": "Assembly of flat-pack furniture, bed frame fixes, chair repair, and table hinge adjustment.",
                        "base_price": 499.00,
                    },
                    {
                        "title": "Door & Window Lock Installation",
                        "slug": "door-lock-fitting",
                        "description": "Fitting new door handles, mortise locks, latch repairs, and window alignment.",
                        "base_price": 399.00,
                    },
                    {
                        "title": "Custom Woodwork & Shelving",
                        "slug": "custom-woodwork-shelving",
                        "description": "Wall shelf mounting, wooden cabinet repair, and custom timber work.",
                        "base_price": 899.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Packers & Movers",
                    "slug": "packers-and-movers",
                    "description": "Hassle-free residential shifting, heavy luggage transport, and secure packing services.",
                    "icon": "fa-solid fa-truck-ramp-box",
                },
                "services": [
                    {
                        "title": "Local 1BHK Home Shifting",
                        "slug": "local-1bhk-shifting",
                        "description": "Complete packing, loading, local transportation, and unloading for 1BHK apartments.",
                        "base_price": 3499.00,
                    },
                    {
                        "title": "Local 2BHK Home Shifting",
                        "slug": "local-2bhk-shifting",
                        "description": "Comprehensive packing with bubble wrap, dedicated mini-truck, and unpacking assistance for 2BHK.",
                        "base_price": 5999.00,
                    },
                    {
                        "title": "Single Item / Furniture Transport",
                        "slug": "single-item-transport",
                        "description": "Safe packing and single-vehicle transport for heavy furniture, fridges, or sofas.",
                        "base_price": 1499.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Appliance Repair",
                    "slug": "appliance-repair",
                    "description": "Repair and servicing for ACs, washing machines, refrigerators, and kitchen electronics.",
                    "icon": "fa-solid fa-snowflake",
                },
                "services": [
                    {
                        "title": "AC Servicing & Repair",
                        "slug": "ac-servicing-repair",
                        "description": "Foam jet cleaning, filter wash, refrigerant check, and cooling performance repair.",
                        "base_price": 599.00,
                    },
                    {
                        "title": "Washing Machine Repair",
                        "slug": "washing-machine-repair",
                        "description": "Fixing drum vibration, motor issues, drainage blockage, and electronic panel repair.",
                        "base_price": 499.00,
                    },
                    {
                        "title": "Refrigerator Repair & Gas Refill",
                        "slug": "refrigerator-repair-gas",
                        "description": "Compressor check, thermostat replacement, leak repair, and gas refilling.",
                        "base_price": 699.00,
                    },
                    {
                        "title": "Microwave & Oven Repair",
                        "slug": "microwave-oven-repair",
                        "description": "Magnetron replacement, heating issue fixes, and touch pad panel repair.",
                        "base_price": 399.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Home Cleaning",
                    "slug": "home-cleaning",
                    "description": "Deep home sanitization, kitchen & bathroom scrub, and upholstery steam cleaning.",
                    "icon": "fa-solid fa-broom",
                },
                "services": [
                    {
                        "title": "Full House Deep Cleaning",
                        "slug": "full-house-deep-cleaning",
                        "description": "Thorough room-by-room scrub, floor degreasing, window glass cleaning, and cobweb removal.",
                        "base_price": 1999.00,
                    },
                    {
                        "title": "Bathroom Deep Cleaning",
                        "slug": "bathroom-deep-cleaning",
                        "description": "Tile stain removal, hard water stain descaling, toilet bowl sanitization, and fittings polish.",
                        "base_price": 499.00,
                    },
                    {
                        "title": "Sofa & Mattress Cleaning",
                        "slug": "sofa-mattress-cleaning",
                        "description": "Vacuuming, fabric shampooing, stain removal, and sanitization for 5-seater sofa sets.",
                        "base_price": 799.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Painting & Renovation",
                    "slug": "painting-renovation",
                    "description": "Professional house painting, wall repair, texture coating, and dampness treatment.",
                    "icon": "fa-solid fa-paint-roller",
                },
                "services": [
                    {
                        "title": "Interior House Painting",
                        "slug": "interior-house-painting",
                        "description": "Double coat interior wall painting with premium emulsion paint and wall surface prep.",
                        "base_price": 4999.00,
                    },
                    {
                        "title": "Wall Patchwork & Touch-up",
                        "slug": "wall-patchwork-touchup",
                        "description": "Putty filling for cracks, surface sanding, and spot painting touch-ups.",
                        "base_price": 899.00,
                    },
                    {
                        "title": "Wall Waterproofing Service",
                        "slug": "wall-waterproofing-service",
                        "description": "Seepage treatment, damp proof coating application, and tile seam sealant.",
                        "base_price": 1499.00,
                    },
                ],
            },
            {
                "category": {
                    "name": "Pest Control",
                    "slug": "pest-control",
                    "description": "Eco-friendly pest treatment for cockroaches, bed bugs, ants, and termites.",
                    "icon": "fa-solid fa-bug",
                },
                "services": [
                    {
                        "title": "Cockroach & Insect Control",
                        "slug": "cockroach-insect-control",
                        "description": "Odorless herbal gel application and spray treatment for kitchen & living areas.",
                        "base_price": 699.00,
                    },
                    {
                        "title": "Termite Inspection & Treatment",
                        "slug": "termite-inspection-treatment",
                        "description": "Drill-fill-seal chemical barrier treatment to protect wooden fixtures from termites.",
                        "base_price": 1299.00,
                    },
                ],
            },
        ]

        category_count = 0
        service_count = 0

        for item in SEED_DATA:
            cat_data = item["category"]
            category, cat_created = ServiceCategory.objects.update_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "icon": cat_data["icon"],
                },
            )
            if cat_created:
                category_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created Category: {category.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Updated Category: {category.name}"))

            for s_data in item["services"]:
                service, s_created = Service.objects.update_or_create(
                    slug=s_data["slug"],
                    defaults={
                        "title": s_data["title"],
                        "category": category,
                        "description": s_data["description"],
                        "base_price": s_data["base_price"],
                        "is_active": True,
                    },
                )
                if s_created:
                    service_count += 1
                    self.stdout.write(self.style.SUCCESS(f"    - Added Service: {service.title} (Rs.{service.base_price})"))
                else:
                    self.stdout.write(self.style.WARNING(f"    - Updated Service: {service.title} (Rs.{service.base_price})"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding completed successfully! Processed {len(SEED_DATA)} categories ({category_count} new) and {service_count} services."
            )
        )
