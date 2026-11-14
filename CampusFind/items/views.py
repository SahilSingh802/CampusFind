"""CampusFind views (function-based, Unit II).

Sections: public pages -> auth -> reporting (CRUD) -> claims -> dashboard.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode
from django.views.decorators.http import require_POST

from .forms import ClaimForm, ItemFilterForm, ItemForm, RegisterForm
from .models import Category, Claim, Item, SavedItem

PAGE_SIZE = 9


# ---------------------------------------------------------------- helpers
def _filter_items(request, queryset):
    """Apply search + filters from GET parameters using the Django ORM."""
    form = ItemFilterForm(request.GET or None)
    if form.is_valid():
        data = form.cleaned_data
        if data['q']:
            q = data['q'].strip()
            # Search by item name OR description (case-insensitive)
            queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if data['category']:
            queryset = queryset.filter(category=data['category'])
        if data['location']:
            queryset = queryset.filter(location__icontains=data['location'].strip())
        if data['status']:
            queryset = queryset.filter(status=data['status'])
    return form, queryset


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get('page'))


def _can_manage(user, item):
    return user.is_authenticated and (user == item.user or user.is_staff)


def _querystring_without_page(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


# ---------------------------------------------------------------- public pages
def home(request):
    # Session demo (Unit VI): count visits and remember recent searches
    request.session['visit_count'] = request.session.get('visit_count', 0) + 1
    q = request.GET.get('q', '').strip()
    if q:
        recent = request.session.get('recent_searches', [])
        if q in recent:
            recent.remove(q)
        recent.insert(0, q)
        request.session['recent_searches'] = recent[:5]
        return redirect(f"{reverse('search')}?{urlencode({'q': q})}")

    # Cookie demo (Unit VI): last viewed item id is stored in a browser cookie
    last_viewed = None
    cookie_id = request.COOKIES.get('last_viewed_item')
    if cookie_id and cookie_id.isdigit():
        last_viewed = Item.objects.filter(pk=int(cookie_id)).select_related('category').first()

    stats = {
        'total': Item.objects.count(),
        'lost': Item.objects.filter(item_type=Item.LOST).count(),
        'found': Item.objects.filter(item_type=Item.FOUND).count(),
        'returned': Item.objects.filter(status__in=[Item.CLAIMED, Item.RETURNED]).count(),
    }
    context = {
        'recent_items': Item.objects.select_related('category')[:6],
        'stats': stats,
        'last_viewed': last_viewed,
        'recent_searches': request.session.get('recent_searches', []),
        'categories': Category.objects.all(),
    }
    return render(request, 'home.html', context)


def _listing(request, item_type, template, title):
    qs = Item.objects.filter(item_type=item_type).select_related('category')
    form, qs = _filter_items(request, qs)
    return render(request, template, {
        'form': form, 'page': _paginate(request, qs), 'title': title,
        'querystring': _querystring_without_page(request), 'count': qs.count(),
    })


def lost_items(request):
    return _listing(request, Item.LOST, 'lost_items.html', 'Lost items')


def found_items(request):
    return _listing(request, Item.FOUND, 'found_items.html', 'Found items')


def search_items(request):
    """Search across both lost and found. Extra filter: type (lost/found)."""
    qs = Item.objects.select_related('category')
    item_type = request.GET.get('type', '')
    if item_type in (Item.LOST, Item.FOUND):
        qs = qs.filter(item_type=item_type)
    form, qs = _filter_items(request, qs)
    return render(request, 'search.html', {
        'form': form, 'page': _paginate(request, qs), 'selected_type': item_type,
        'querystring': _querystring_without_page(request), 'count': qs.count(),
    })


def item_detail(request, pk):
    item = get_object_or_404(Item.objects.select_related('category', 'user'), pk=pk)
    can_manage = _can_manage(request.user, item)
    matching_items = Item.objects.filter(
        category=item.category,
        item_type=Item.LOST if item.item_type == Item.FOUND else Item.FOUND,
        status=Item.ACTIVE,
    ).exclude(pk=item.pk).select_related('category')[:3]
    user_claim = None
    claims = None
    is_saved = False
    if request.user.is_authenticated:
        user_claim = item.claims.filter(claimant=request.user).first()
        is_saved = SavedItem.objects.filter(user=request.user, item=item).exists()
    if can_manage:
        claims = item.claims.select_related('claimant')
    can_claim = (
        request.user.is_authenticated and item.item_type == Item.FOUND
        and item.status == Item.ACTIVE and request.user != item.user and user_claim is None
    )
    response = render(request, 'item_detail.html', {
        'item': item, 'can_manage': can_manage, 'claims': claims,
        'user_claim': user_claim, 'can_claim': can_claim, 'is_saved': is_saved,
        'matching_items': matching_items,
    })
    # Cookie: remember last viewed item for 7 days
    response.set_cookie('last_viewed_item', item.pk, max_age=60 * 60 * 24 * 7, samesite='Lax')
    return response


@login_required
@require_POST
def toggle_saved_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    saved_item, created = SavedItem.objects.get_or_create(user=request.user, item=item)
    if created:
        messages.success(request, 'Item saved to your dashboard.')
    else:
        saved_item.delete()
        messages.info(request, 'Item removed from your saved list.')

    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect(item)


# ---------------------------------------------------------------- authentication
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # creates the session
            messages.success(request, f'Welcome to CampusFind, {user.first_name}!')
            return redirect('dashboard')  # POST-Redirect-GET
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


# ---------------------------------------------------------------- report / edit / delete
@login_required
def report_item(request, item_type):
    item_type = item_type.upper()
    if item_type not in (Item.LOST, Item.FOUND):
        return HttpResponse('Unknown report type.', status=400)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, item_type=item_type)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, 'Your report has been published.')
            return redirect(item)  # POST-Redirect-GET
    else:
        initial = {'contact': request.user.email}
        form = ItemForm(item_type=item_type, initial=initial)
    return render(request, 'report_item.html', {
        'form': form, 'item_type': item_type, 'is_edit': False})


@login_required
def edit_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if not _can_manage(request.user, item):
        raise PermissionDenied  # ownership check
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Report updated.')
            return redirect(item)
    else:
        form = ItemForm(instance=item)
    return render(request, 'report_item.html', {
        'form': form, 'item_type': item.item_type, 'is_edit': True, 'item': item})


@login_required
def delete_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if not _can_manage(request.user, item):
        raise PermissionDenied
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Report deleted.')
        return redirect('dashboard')
    return render(request, 'confirm_delete.html', {'item': item})


@login_required
@require_POST
def update_item_status(request, pk):
    """Owner marks an item ACTIVE / CLAIMED / RETURNED."""
    item = get_object_or_404(Item, pk=pk)
    if not _can_manage(request.user, item):
        raise PermissionDenied
    new_status = request.POST.get('status')
    if new_status in dict(Item.STATUS_CHOICES):
        item.status = new_status
        item.save(update_fields=['status'])
        messages.success(request, f'Status changed to {item.get_status_display()}.')
    else:
        messages.error(request, 'Invalid status.')
    return redirect(item)


# ---------------------------------------------------------------- claims
@login_required
def claim_item(request, pk):
    item = get_object_or_404(Item, pk=pk, item_type=Item.FOUND)
    if item.user == request.user:
        messages.error(request, 'You cannot claim an item you reported yourself.')
        return redirect(item)
    if item.status != Item.ACTIVE:
        messages.error(request, 'This item is no longer available to claim.')
        return redirect(item)
    if item.claims.filter(claimant=request.user).exists():
        messages.info(request, 'You have already submitted a claim for this item.')
        return redirect(item)

    if request.method == 'POST':
        form = ClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item = item
            claim.claimant = request.user
            claim.save()
            messages.success(request, 'Claim submitted. The finder will review it.')
            return redirect('dashboard')
    else:
        form = ClaimForm(initial={'contact': request.user.email})
    return render(request, 'claim_item.html', {'form': form, 'item': item})


@login_required
@require_POST
def review_claim(request, pk, action):
    """Item owner (or admin) approves or rejects a claim."""
    claim = get_object_or_404(Claim.objects.select_related('item'), pk=pk)
    if not _can_manage(request.user, claim.item):
        raise PermissionDenied
    if action not in ('approve', 'reject'):
        return HttpResponseNotAllowed(['POST'])
    with transaction.atomic():
        if action == 'approve':
            claim.status = Claim.APPROVED
            claim.item.status = Item.CLAIMED
            claim.item.save(update_fields=['status'])
            # Other pending claims on the same item are rejected automatically
            claim.item.claims.exclude(pk=claim.pk).filter(status=Claim.PENDING).update(
                status=Claim.REJECTED)
            messages.success(request, 'Claim approved. Share the pickup details with the claimant.')
        else:
            claim.status = Claim.REJECTED
            messages.info(request, 'Claim rejected.')
        claim.save(update_fields=['status'])
    return redirect(claim.item)


# ---------------------------------------------------------------- dashboard
@login_required
def dashboard(request):
    my_items = Item.objects.filter(user=request.user).select_related('category')
    my_claims = Claim.objects.filter(claimant=request.user).select_related('item')
    incoming = Claim.objects.filter(item__user=request.user).select_related('item', 'claimant')
    saved_items = SavedItem.objects.filter(user=request.user).select_related(
        'item__category', 'item__user')
    context = {
        'total_reported': my_items.count(),
        'lost_count': my_items.filter(item_type=Item.LOST).count(),
        'found_count': my_items.filter(item_type=Item.FOUND).count(),
        'pending_claims': incoming.filter(status=Claim.PENDING).count(),
        'my_items': my_items,
        'my_claims': my_claims,
        'saved_items': saved_items,
        'incoming_claims': incoming.filter(status=Claim.PENDING)[:5],
        'visit_count': request.session.get('visit_count', 0),
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------- errors
def custom_404(request, exception):
    return render(request, '404.html', status=404)
