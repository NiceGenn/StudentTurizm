from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

BOOTSTRAP_INPUT = {"class": "form-control"}


class RegisterForm(UserCreationForm):
    """Регистрация посетителя портала.

    Учебный проект: все данные вымышленные, подтверждение почты не выполняется.
    """

    first_name = forms.CharField(label=_("Имя"), max_length=150, widget=forms.TextInput(attrs=BOOTSTRAP_INPUT))
    last_name = forms.CharField(label=_("Фамилия"), max_length=150, widget=forms.TextInput(attrs=BOOTSTRAP_INPUT))
    email = forms.EmailField(label=_("Электронная почта"), widget=forms.EmailInput(attrs=BOOTSTRAP_INPUT))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "password1", "password2"):
            self.fields[name].widget.attrs.update(BOOTSTRAP_INPUT)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Пользователь с такой почтой уже зарегистрирован."))
        return email


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(BOOTSTRAP_INPUT)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": _("Имя"),
            "last_name": _("Фамилия"),
            "email": _("Электронная почта"),
        }
        widgets = {
            "first_name": forms.TextInput(attrs=BOOTSTRAP_INPUT),
            "last_name": forms.TextInput(attrs=BOOTSTRAP_INPUT),
            "email": forms.EmailInput(attrs=BOOTSTRAP_INPUT),
        }

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("Эта почта уже используется другим пользователем."))
        return email
