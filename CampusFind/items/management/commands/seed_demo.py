"""Optional: fill the database with sample data for a demo.

Usage:  python manage.py seed_demo --password "YourDemoPass#123"
"""
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from items.models import Category, Item


class Command(BaseCommand):
    help = 'Create demo users and sample lost/found items'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=None,
                            help='Password for demo users (random one is generated if omitted)')

    def handle(self, *args, **opts):
        password = opts['password'] or secrets.token_urlsafe(10)
        users = []
        for name, first in [('demo_asha', 'Asha'), ('demo_ravi', 'Ravi')]:
            user, created = User.objects.get_or_create(
                username=name, defaults={'first_name': first, 'email': f'{name}@campus.edu'})
            if created:
                user.set_password(password)
                user.save()
            users.append(user)
        today = timezone.localdate()
        cat = lambda n: Category.objects.get(name=n)
        samples = [
            ('Black leather wallet', 'Wallet', Item.FOUND, 'Central Library, 2nd floor', 1,
             'Black wallet with a few cards inside.', 'Contains a photo of a dog and a Rs 500 note'),
            ('Samsung Galaxy phone', 'Mobile Phone', Item.LOST, 'Block 32 canteen', 2,
             'Blue phone with a cracked corner and transparent case.', ''),
            ('College ID card', 'ID Card', Item.FOUND, 'Main gate', 0,
             'ID card on a green lanyard.', 'Registration number ends with 47'),
            ('Boat earphones', 'Earphones', Item.LOST, 'Sports ground', 3,
             'Black wired earphones in a small red pouch.', ''),
            ('Maths notebook', 'Books & Notebooks', Item.FOUND, 'Lecture hall 5', 4,
             'Spiral notebook with calculus notes.', 'First page has name written in pencil'),
            ('Grey backpack', 'Bag', Item.LOST, 'Bus stop near Gate 2', 5,
             'Grey Wildcraft backpack with a laptop charger inside.', ''),
            ('Navy campus backpack', 'Bag', Item.FOUND, 'Student centre lost & found', 1,
             'Navy backpack handed in at the student centre.', 'Inside pocket contains a small USB drive'),
        ]
        created = 0
        for i, (title, c, typ, loc, ago, desc, private) in enumerate(samples):
            _, was_created = Item.objects.get_or_create(
                title=title, item_type=typ,
                defaults=dict(user=users[i % 2], category=cat(c), location=loc,
                              date_reported=today - timedelta(days=ago), description=desc,
                              contact='demo@campus.edu', private_details=private))
            created += was_created
        self.stdout.write(self.style.SUCCESS(f'{created} sample items created.'))
        self.stdout.write(f'Demo users: demo_asha / demo_ravi   password: {password}')
