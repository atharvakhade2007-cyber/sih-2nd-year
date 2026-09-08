import django
django.setup()
from core.models import ServiceCategory, Service
categories = ServiceCategory.objects.all()
for cat in categories:
    print(f'Category: {cat.name}')
    services = Service.objects.filter(category=cat)
    for s in services:
        print(f'  - {s.title} - ₹{s.base_price}')
    print()