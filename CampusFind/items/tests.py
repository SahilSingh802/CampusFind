import io
import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, Claim, Item, SavedItem

TMP_MEDIA = tempfile.mkdtemp()


def make_user(name='alice', password='Str0ng!pass#1', **kw):
    return User.objects.create_user(username=name, password=password,
                                    email=f'{name}@college.edu', first_name=name.title(), **kw)


def make_item(user, item_type=Item.FOUND, **kw):
    cat = Category.objects.get(name='Wallet')
    data = dict(user=user, title='Black wallet', category=cat, description='Leather wallet',
                item_type=item_type, location='Library', date_reported=date.today(),
                contact='9999999999', private_details='Has a blue sticker inside')
    data.update(kw)
    return Item.objects.create(**data)


def image_file(name='x.png', fmt='PNG'):
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), 'blue').save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f'image/{fmt.lower()}')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class CampusFindTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice')
        self.bob = make_user('bob')
        self.cat = Category.objects.get(name='Wallet')

    def login(self, name='alice'):
        self.client.login(username=name, password='Str0ng!pass#1')

    # 1. Registration
    def test_registration_creates_user_and_logs_in(self):
        r = self.client.post(reverse('register'), {
            'username': 'carol', 'first_name': 'Carol', 'last_name': 'X',
            'email': 'carol@college.edu', 'password1': 'Zx9!kLmQ2#', 'password2': 'Zx9!kLmQ2#'})
        self.assertRedirects(r, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='carol').exists())

    def test_registration_rejects_weak_password_and_duplicate_email(self):
        r = self.client.post(reverse('register'), {
            'username': 'dave', 'first_name': 'D', 'email': 'alice@college.edu',
            'password1': '12345678', 'password2': '12345678'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='dave').exists())

    # 2. Login / logout
    def test_login_and_logout(self):
        r = self.client.post(reverse('login'), {'username': 'alice', 'password': 'Str0ng!pass#1'})
        self.assertRedirects(r, reverse('dashboard'))
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_wrong_password(self):
        r = self.client.post(reverse('login'), {'username': 'alice', 'password': 'nope'})
        self.assertContains(r, 'Incorrect username or password')

    # 3 & 4. Report lost / found
    def test_report_lost_item(self):
        self.login()
        r = self.client.post(reverse('report_item', args=['lost']), {
            'title': 'Student ID', 'category': self.cat.pk, 'description': 'Blue lanyard',
            'location': 'Canteen', 'date_reported': date.today().isoformat(), 'contact': '12345'})
        item = Item.objects.get(title='Student ID')
        self.assertRedirects(r, item.get_absolute_url())
        self.assertEqual(item.item_type, Item.LOST)
        self.assertEqual(item.user, self.alice)

    def test_report_found_item_with_image_and_private_details(self):
        self.login()
        r = self.client.post(reverse('report_item', args=['found']), {
            'title': 'Keys', 'category': self.cat.pk, 'description': 'Bunch of 3 keys',
            'location': 'Block 34', 'date_reported': date.today().isoformat(), 'contact': '12345',
            'private_details': 'Red keychain', 'image': image_file()})
        item = Item.objects.get(title='Keys')
        self.assertRedirects(r, item.get_absolute_url())
        self.assertEqual(item.item_type, Item.FOUND)
        self.assertTrue(item.image.name.endswith('.png'))

    def test_found_report_requires_private_details(self):
        self.login()
        r = self.client.post(reverse('report_item', args=['found']), {
            'title': 'Keys', 'category': self.cat.pk, 'description': 'x', 'location': 'y',
            'date_reported': date.today().isoformat(), 'contact': '1'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Item.objects.filter(title='Keys').exists())

    def test_future_date_and_bad_upload_rejected(self):
        self.login()
        base = {'title': 'Pen', 'category': self.cat.pk, 'description': 'x', 'location': 'y',
                'contact': '1'}
        r = self.client.post(reverse('report_item', args=['lost']),
                             {**base, 'date_reported': (date.today() + timedelta(days=3)).isoformat()})
        self.assertEqual(r.status_code, 200)
        bad = SimpleUploadedFile('evil.txt', b'not an image', content_type='text/plain')
        r = self.client.post(reverse('report_item', args=['lost']),
                             {**base, 'date_reported': date.today().isoformat(), 'image': bad})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Item.objects.count(), 0)

    # 5. Listing
    def test_listing_pages_separate_lost_and_found(self):
        make_item(self.alice, Item.LOST, title='Lost phone')
        make_item(self.alice, Item.FOUND, title='Found bag')
        self.assertContains(self.client.get(reverse('lost_items')), 'Lost phone')
        self.assertNotContains(self.client.get(reverse('lost_items')), 'Found bag')
        self.assertContains(self.client.get(reverse('found_items')), 'Found bag')

    def test_item_cards_show_labeled_reference_photos_when_no_upload_exists(self):
        make_item(self.alice, title='Found wallet')
        response = self.client.get(reverse('found_items'))
        self.assertContains(response, 'images/wallet.jpg')
        self.assertContains(response, 'Reference photo')

    def test_item_detail_suggests_active_opposite_type_in_same_category(self):
        lost_wallet = make_item(self.alice, Item.LOST, title='Lost wallet')
        found_wallet = make_item(self.bob, Item.FOUND, title='Found wallet')
        make_item(self.bob, Item.FOUND, title='Found phone',
                  category=Category.objects.get(name='Mobile Phone'))
        make_item(self.bob, Item.FOUND, title='Claimed wallet', status=Item.CLAIMED)

        response = self.client.get(lost_wallet.get_absolute_url())

        self.assertEqual(list(response.context['matching_items']), [found_wallet])
        self.assertContains(response, 'Possible matches')
        self.assertNotContains(response, 'Claimed wallet')
        self.assertNotContains(response, 'Found phone')

    def test_empty_state(self):
        self.assertContains(self.client.get(reverse('lost_items')), 'Nothing matches yet')

    # 6. Search & filters
    def test_search_and_filters(self):
        phone = Category.objects.get(name='Mobile Phone')
        make_item(self.alice, title='Samsung phone', category=phone, location='Gym',
                  description='Cracked screen')
        make_item(self.alice, title='Red wallet', location='Library', description='Has coins')
        url = reverse('found_items')
        self.assertContains(self.client.get(url, {'q': 'samsung'}), 'Samsung phone')
        self.assertNotContains(self.client.get(url, {'q': 'samsung'}), 'Red wallet')
        self.assertContains(self.client.get(url, {'q': 'coins'}), 'Red wallet')       # description
        self.assertNotContains(self.client.get(url, {'category': phone.pk}), 'Red wallet')
        self.assertContains(self.client.get(url, {'location': 'gym'}), 'Samsung phone')
        Item.objects.filter(title='Red wallet').update(status=Item.RETURNED)
        r = self.client.get(url, {'status': 'RETURNED'})
        self.assertContains(r, 'Red wallet')
        self.assertNotContains(r, 'Samsung phone')

    def test_home_search_redirects_and_stores_session(self):
        r = self.client.get(reverse('home'), {'q': 'wallet'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('wallet', self.client.session['recent_searches'])

    def test_global_search_type_filter(self):
        make_item(self.alice, Item.LOST, title='Lost umbrella')
        make_item(self.alice, Item.FOUND, title='Found umbrella')
        r = self.client.get(reverse('search'), {'q': 'umbrella', 'type': 'LOST'})
        self.assertContains(r, 'Lost umbrella')
        self.assertNotContains(r, 'Found umbrella')

    # 7. Claim submission
    def claim_payload(self):
        return {'contact': 'bob@college.edu', 'verification_answer': 'Blue sticker inside the wallet',
                'explanation': 'It is mine'}

    def test_claim_submission(self):
        item = make_item(self.alice)
        self.login('bob')
        r = self.client.post(reverse('claim_item', args=[item.pk]), self.claim_payload())
        self.assertRedirects(r, reverse('dashboard'))
        self.assertEqual(Claim.objects.get().status, Claim.PENDING)

    def test_cannot_claim_own_item_twice_or_lost_item(self):
        item = make_item(self.alice)
        self.login('alice')
        self.client.post(reverse('claim_item', args=[item.pk]), self.claim_payload())
        self.assertEqual(Claim.objects.count(), 0)
        self.login('bob')
        self.client.post(reverse('claim_item', args=[item.pk]), self.claim_payload())
        self.client.post(reverse('claim_item', args=[item.pk]), self.claim_payload())
        self.assertEqual(Claim.objects.count(), 1)
        lost = make_item(self.alice, Item.LOST)
        self.assertEqual(self.client.get(reverse('claim_item', args=[lost.pk])).status_code, 404)

    # 8. Claim status updates
    def test_owner_approves_claim(self):
        item = make_item(self.alice)
        c1 = Claim.objects.create(item=item, claimant=self.bob, contact='x', verification_answer='y' * 12)
        carol = make_user('carol')
        c2 = Claim.objects.create(item=item, claimant=carol, contact='x', verification_answer='z' * 12)
        self.login('alice')
        self.client.post(reverse('review_claim', args=[c1.pk, 'approve']))
        c1.refresh_from_db(); c2.refresh_from_db(); item.refresh_from_db()
        self.assertEqual(c1.status, Claim.APPROVED)
        self.assertEqual(c2.status, Claim.REJECTED)
        self.assertEqual(item.status, Item.CLAIMED)

    def test_owner_rejects_claim(self):
        item = make_item(self.alice)
        c = Claim.objects.create(item=item, claimant=self.bob, contact='x', verification_answer='y' * 12)
        self.login('alice')
        self.client.post(reverse('review_claim', args=[c.pk, 'reject']))
        c.refresh_from_db()
        self.assertEqual(c.status, Claim.REJECTED)

    def test_non_owner_cannot_review_claim(self):
        item = make_item(self.alice)
        c = Claim.objects.create(item=item, claimant=self.bob, contact='x', verification_answer='y' * 12)
        self.login('bob')
        r = self.client.post(reverse('review_claim', args=[c.pk, 'approve']))
        self.assertEqual(r.status_code, 403)
        c.refresh_from_db()
        self.assertEqual(c.status, Claim.PENDING)

    # 9. Dashboard
    def test_dashboard_shows_stats_and_items(self):
        make_item(self.alice, Item.LOST, title='My lost thing')
        make_item(self.alice, Item.FOUND, title='My found thing')
        self.login()
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.context['total_reported'], 2)
        self.assertEqual(r.context['lost_count'], 1)
        self.assertEqual(r.context['found_count'], 1)
        self.assertContains(r, 'My lost thing')

    def test_saved_items_can_be_added_removed_and_seen_on_dashboard(self):
        item = make_item(self.alice, title='Wallet to revisit')
        self.login('bob')
        url = reverse('toggle_saved_item', args=[item.pk])

        response = self.client.post(url, {'next': reverse('dashboard')})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(SavedItem.objects.filter(user=self.bob, item=item).exists())
        self.assertContains(self.client.get(reverse('dashboard')), 'Wallet to revisit')

        response = self.client.post(url, {'next': 'https://example.com'})
        self.assertRedirects(response, item.get_absolute_url())
        self.assertFalse(SavedItem.objects.filter(user=self.bob, item=item).exists())

    def test_saved_items_require_login_and_post(self):
        item = make_item(self.alice)
        url = reverse('toggle_saved_item', args=[item.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.login('bob')
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_edit_and_delete_own_item(self):
        item = make_item(self.alice)
        self.login()
        r = self.client.post(reverse('edit_item', args=[item.pk]), {
            'title': 'Updated wallet', 'category': self.cat.pk, 'description': 'new', 'location': 'Gym',
            'date_reported': date.today().isoformat(), 'contact': '1', 'private_details': 'sticker'})
        self.assertRedirects(r, item.get_absolute_url())
        item.refresh_from_db()
        self.assertEqual(item.title, 'Updated wallet')
        self.client.post(reverse('delete_item', args=[item.pk]))
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())

    # 10. Admin
    def test_admin_pages_load_for_superuser(self):
        User.objects.create_superuser('root', 'root@x.com', 'Adm1n!pass#9')
        self.client.login(username='root', password='Adm1n!pass#9')
        make_item(self.alice)
        for name in ('category', 'item', 'claim', 'saveditem'):
            self.assertEqual(self.client.get(f'/admin/items/{name}/').status_code, 200)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 200)

    def test_admin_blocked_for_normal_user(self):
        self.login()
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    # 11. Unauthorized access & privacy
    def test_login_required_views_redirect(self):
        item = make_item(self.alice)
        for url in (reverse('dashboard'), reverse('report_item', args=['lost']),
                    reverse('claim_item', args=[item.pk]), reverse('edit_item', args=[item.pk])):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r.url.startswith(reverse('login')))

    def test_user_cannot_edit_or_delete_others_item(self):
        item = make_item(self.alice)
        self.login('bob')
        self.assertEqual(self.client.get(reverse('edit_item', args=[item.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('delete_item', args=[item.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('update_item_status', args=[item.pk]),
                                          {'status': 'RETURNED'}).status_code, 403)
        self.assertTrue(Item.objects.filter(pk=item.pk).exists())

    def test_private_details_hidden_from_public_and_other_users(self):
        item = make_item(self.alice, private_details='SECRET-MARK-123')
        self.assertNotContains(self.client.get(item.get_absolute_url()), 'SECRET-MARK-123')
        self.login('bob')
        self.assertNotContains(self.client.get(item.get_absolute_url()), 'SECRET-MARK-123')
        self.assertNotContains(self.client.get(reverse('found_items')), 'SECRET-MARK-123')
        self.login('alice')
        self.assertContains(self.client.get(item.get_absolute_url()), 'SECRET-MARK-123')

    def test_contact_hidden_from_anonymous(self):
        item = make_item(self.alice, contact='777-SECRET-PHONE')
        self.assertNotContains(self.client.get(item.get_absolute_url()), '777-SECRET-PHONE')

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse('login'), {'username': 'alice', 'password': 'Str0ng!pass#1'})
        self.assertEqual(r.status_code, 403)

    # Cookies, errors
    def test_cookie_set_on_item_view_and_shown_on_home(self):
        item = make_item(self.alice)
        r = self.client.get(item.get_absolute_url())
        self.assertEqual(r.cookies['last_viewed_item'].value, str(item.pk))
        self.assertContains(self.client.get(reverse('home')), 'You last viewed')

    def test_404_page_and_invalid_report_type(self):
        self.assertEqual(self.client.get(reverse('item_detail', args=[9999])).status_code, 404)
        self.login()
        self.assertEqual(self.client.get('/report/banana/').status_code, 400)

    def test_home_page_content(self):
        r = self.client.get(reverse('home'))
        self.assertContains(r, 'Lost something?')
        self.assertContains(r, 'Let’s get it back.')
