from django.db import migrations

CATEGORIES = [
    ('ID Card', 'bi-person-vcard'), ('Wallet', 'bi-wallet2'), ('Mobile Phone', 'bi-phone'),
    ('Laptop', 'bi-laptop'), ('Books & Notebooks', 'bi-journal-bookmark'), ('Bag', 'bi-backpack2'),
    ('Keys', 'bi-key'), ('Earphones', 'bi-headphones'), ('Other', 'bi-box-seam'),
]


def add_categories(apps, schema_editor):
    Category = apps.get_model('items', 'Category')
    for name, icon in CATEGORIES:
        Category.objects.get_or_create(name=name, defaults={'icon': icon})


def remove_categories(apps, schema_editor):
    apps.get_model('items', 'Category').objects.filter(name__in=[c[0] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [('items', '0001_initial')]
    operations = [migrations.RunPython(add_categories, remove_categories)]
