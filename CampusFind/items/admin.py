from django.contrib import admin

from .models import Category, Claim, Item, SavedItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)


class ClaimInline(admin.TabularInline):
    model = Claim
    extra = 0
    fields = ('claimant', 'contact', 'status', 'created_at')
    readonly_fields = ('created_at',)


@admin.action(description='Mark selected items as Returned')
def mark_returned(modeladmin, request, queryset):
    queryset.update(status=Item.RETURNED)


@admin.action(description='Mark selected items as Active')
def mark_active(modeladmin, request, queryset):
    queryset.update(status=Item.ACTIVE)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'category', 'location', 'status', 'user', 'date_reported')
    list_filter = ('item_type', 'status', 'category', 'date_reported')
    search_fields = ('title', 'description', 'location', 'user__username')
    list_editable = ('status',)
    date_hierarchy = 'created_at'
    inlines = [ClaimInline]
    actions = [mark_returned, mark_active]


@admin.action(description='Approve selected claims')
def approve_claims(modeladmin, request, queryset):
    for claim in queryset:
        claim.status = Claim.APPROVED
        claim.save(update_fields=['status'])
        claim.item.status = Item.CLAIMED
        claim.item.save(update_fields=['status'])


@admin.action(description='Reject selected claims')
def reject_claims(modeladmin, request, queryset):
    queryset.update(status=Claim.REJECTED)


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('item', 'claimant', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('item__title', 'claimant__username', 'verification_answer')
    list_editable = ('status',)
    actions = [approve_claims, reject_claims]


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'created_at')
    search_fields = ('user__username', 'item__title')
    list_select_related = ('user', 'item')
