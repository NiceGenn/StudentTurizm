from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review


class ReviewForm(forms.ModelForm):
    """Форма отзыва. Отзыв попадает на модерацию, а не сразу на сайт."""

    class Meta:
        model = Review
        fields = ["rating", "text"]
        labels = {
            "rating": _("Оценка"),
            "text": _("Ваш отзыв"),
        }
        widgets = {
            "rating": forms.RadioSelect(attrs={"class": "rating-input"}),
            "text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": _("Расскажите, что понравилось и что стоит учесть другим гостям"),
                }
            ),
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if len(text) < 20:
            raise forms.ValidationError(_("Отзыв слишком короткий — напишите хотя бы 20 символов."))
        return text


class AttractionFilterForm(forms.Form):
    """Фильтры каталога. Значения приходят из GET-параметров."""

    q = forms.CharField(
        required=False,
        label=_("Поиск"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Название, тег, описание")}),
    )
    category = forms.ChoiceField(required=False, label=_("Категория"), choices=[])
    village = forms.ChoiceField(required=False, label=_("Село"), choices=[])
    season = forms.ChoiceField(required=False, label=_("Сезон"), choices=[])
    sort = forms.ChoiceField(required=False, label=_("Сортировка"), choices=[])

    def __init__(self, *args, categories=None, villages=None, seasons=None, sort_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        any_label = _("Все")
        self.fields["category"].choices = [("", any_label)] + list(categories or [])
        self.fields["village"].choices = [("", any_label)] + list(villages or [])
        self.fields["season"].choices = [("", any_label)] + list(seasons or [])
        self.fields["sort"].choices = list(sort_choices or [])
        for name in ("category", "village", "season", "sort"):
            self.fields[name].widget.attrs["class"] = "form-select"
