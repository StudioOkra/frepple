from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import SchedulerConfiguration

class SchedulerConfigurationForm(forms.ModelForm):
    class Meta:
        model = SchedulerConfiguration
        fields = [
            'name', 'description', 'scheduling_method', 'objective',
            'horizon_start', 'horizon_end', 'time_limit',
            'wip_consume_material', 'wip_consume_capacity',
            'size_minimum', 'size_multiple'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 為所有字段添加 Bootstrap 類
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.BooleanField):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field, forms.DateTimeField):
                field.widget.attrs['class'] = 'form-control datetimepicker'