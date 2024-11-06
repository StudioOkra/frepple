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
            'wip_produce_full_quantity',
            'size_minimum', 'size_multiple',
            'fence_duration', 'batch_window',
            'setup_matrix',
            'consider_material', 'consider_capacity'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 為所有字段添加 Bootstrap 類
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field, forms.DateTimeField):
                field.widget = forms.DateTimeInput(
                    attrs={
                        'class': 'form-control datetimepicker',
                        'autocomplete': 'off'
                    },
                    format='%Y-%m-%d %H:%M:%S'
                )
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        horizon_start = cleaned_data.get('horizon_start')
        horizon_end = cleaned_data.get('horizon_end')
        
        if horizon_start and horizon_end and horizon_start >= horizon_end:
            raise forms.ValidationError(_('開始時間必須早於結束時間'))
        
        return cleaned_data