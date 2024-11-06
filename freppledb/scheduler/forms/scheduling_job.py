from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import SchedulingJob
from freppledb.input.models import Demand

class SchedulingJobForm(forms.ModelForm):
    class Meta:
        model = SchedulingJob
        fields = ['name', 'demand', 'operation', 'priority', 'configuration']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 只顯示未完成的訂單
        self.fields['demand'].queryset = Demand.objects.filter(
            status__in=['open', 'quote']
        )
        # 為所有字段添加 Bootstrap 類
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.ModelChoiceField):
                field.widget.attrs['class'] = 'form-select'