from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import SchedulingJob
from freppledb.input.models import Demand, OperationPlan

class SchedulingJobForm(forms.ModelForm):
    class Meta:
        model = SchedulingJob
        fields = ['name', 'demand', 'operation_plan', 'priority', 'configuration']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 只顯示未完成的訂單
        self.fields['demand'].queryset = Demand.objects.filter(
            status__in=['open', 'quote']
        )
        # 只顯示可用的操作計劃
        self.fields['operation_plan'].queryset = OperationPlan.objects.exclude(
            status='completed'
        )
        # 為所有字段添加 Bootstrap 類
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.ModelChoiceField):
                field.widget.attrs['class'] = 'form-select'

    def clean(self):
        cleaned_data = super().clean()
        demand = cleaned_data.get("demand")
        operation_plan = cleaned_data.get("operation_plan")

        if demand and operation_plan:
            # 添加自定義驗證邏輯
            if demand.status != 'open':
                raise forms.ValidationError(_('Demand must be open to create a scheduling job.'))