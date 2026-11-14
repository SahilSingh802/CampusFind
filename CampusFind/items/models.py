from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    """Item categories such as ID Card, Wallet, Phone (Unit V: model)."""
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=40, default='bi-box-seam',
                            help_text='Bootstrap Icons class, e.g. bi-phone')

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    """A lost or found report."""
    LOST = 'LOST'
    FOUND = 'FOUND'
    TYPE_CHOICES = [(LOST, 'Lost'), (FOUND, 'Found')]

    ACTIVE = 'ACTIVE'
    CLAIMED = 'CLAIMED'
    RETURNED = 'RETURNED'
    STATUS_CHOICES = [(ACTIVE, 'Active'), (CLAIMED, 'Claimed'), (RETURNED, 'Returned')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='items')
    title = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='items')
    description = models.TextField()
    item_type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    location = models.CharField(max_length=150)
    date_reported = models.DateField(help_text='Date the item was lost or found')
    image = models.ImageField(
        upload_to='items/%Y/%m/', blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])
    contact = models.CharField(max_length=120)
    private_details = models.TextField(
        blank=True,
        help_text='Hidden identifying details used to verify the owner (found items).')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['item_type', 'status'])]

    def __str__(self):
        return f'{self.title} ({self.get_item_type_display()})'

    def get_absolute_url(self):
        return reverse('item_detail', args=[self.pk])

    @property
    def is_lost(self):
        return self.item_type == self.LOST

    @property
    def days_ago(self):
        return (timezone.localdate() - self.date_reported).days


class Claim(models.Model):
    """A request by a user to claim a found item."""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (REJECTED, 'Rejected')]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='claims')
    contact = models.CharField(max_length=120)
    verification_answer = models.TextField()
    explanation = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # A user may only claim a given item once
            models.UniqueConstraint(fields=['item', 'claimant'], name='one_claim_per_user_item'),
        ]

    def __str__(self):
        return f'Claim by {self.claimant} on {self.item.title}'


class SavedItem(models.Model):
    """An item a user wants to revisit later."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='saved_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'item'], name='one_saved_item_per_user'),
        ]

    def __str__(self):
        return f'{self.user} saved {self.item.title}'
