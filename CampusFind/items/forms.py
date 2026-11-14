from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category, Claim, Item

MAX_IMAGE_MB = 3


class RegisterForm(UserCreationForm):
    """Registration with name + email. Password validators run automatically."""
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, label='Last name', required=False)
    email = forms.EmailField(label='College email')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class ItemForm(forms.ModelForm):
    """One ModelForm used for both lost and found reports."""

    class Meta:
        model = Item
        fields = ['title', 'category', 'description', 'location',
                  'date_reported', 'contact', 'image', 'private_details']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Blue Boat earphones'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g. Library, 2nd floor'}),
            'date_reported': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'contact': forms.TextInput(attrs={'placeholder': 'Phone number or email'}),
            'private_details': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Something only the real owner would know (hidden from the public)'}),
        }

    def __init__(self, *args, item_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_type = item_type or (self.instance.item_type if self.instance.pk else Item.LOST)
        for name, field in self.fields.items():
            if name == 'image':
                field.widget.attrs['class'] = 'form-control'
            elif name == 'category':
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'
        if self.item_type == Item.LOST:
            # Lost reports do not need private verification details
            del self.fields['private_details']
            self.fields['location'].label = 'Last seen location'
            self.fields['date_reported'].label = 'Date lost'
        else:
            self.fields['location'].label = 'Found location'
            self.fields['date_reported'].label = 'Date found'
            self.fields['private_details'].required = True
            self.fields['private_details'].label = 'Private identifying details'

    def clean_date_reported(self):
        d = self.cleaned_data['date_reported']
        if d > date.today():
            raise forms.ValidationError('The date cannot be in the future.')
        return d

    def clean_image(self):
        img = self.cleaned_data.get('image')
        # Only validate fresh uploads (existing files have no content_type)
        if img and hasattr(img, 'content_type'):
            if img.size > MAX_IMAGE_MB * 1024 * 1024:
                raise forms.ValidationError(f'Image must be smaller than {MAX_IMAGE_MB} MB.')
            if img.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
                raise forms.ValidationError('Only JPG, PNG or WEBP images are allowed.')
        return img

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 3:
            raise forms.ValidationError('Please enter a longer item name.')
        return title

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.item_type = self.item_type
        if commit:
            obj.save()
        return obj


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['contact', 'verification_answer', 'explanation']
        widgets = {
            'contact': forms.TextInput(attrs={'placeholder': 'Phone number or email'}),
            'verification_answer': forms.Textarea(attrs={
                'rows': 3, 'placeholder': 'Describe identifying details of the item (marks, contents, serial no.)'}),
            'explanation': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Anything else that proves it is yours'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_verification_answer(self):
        ans = self.cleaned_data['verification_answer'].strip()
        if len(ans) < 10:
            raise forms.ValidationError('Please give at least 10 characters so the owner can verify you.')
        return ans


class ItemFilterForm(forms.Form):
    """GET form for search and filters."""
    q = forms.CharField(required=False, label='Search')
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False,
                                      empty_label='All categories')
    location = forms.CharField(required=False)
    status = forms.ChoiceField(required=False,
                               choices=[('', 'Any status')] + Item.STATUS_CHOICES)
