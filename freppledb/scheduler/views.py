from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from freppledb.common.report import (
    GridReport,
    GridFieldText,
    GridFieldBool,
    GridFieldDateTime,
    GridFieldInteger,
    GridFieldNumber,
    GridFieldDuration,
)
from .models import SchedulingJob, SchedulerConfiguration
from django.views.generic.edit import CreateView, UpdateView
from django.views import View
from .tasks import execute_scheduling_job
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from .forms.scheduler_config import SchedulerConfigurationForm

class GanttView(GridReport):
    """
    Gantt chart view for scheduling results
    """
    template = "scheduler/gantt.html"
    title = _("Scheduling Gantt Chart")
    
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            # Handle updates from gantt chart
            job_id = request.POST.get("id")
            start_date = request.POST.get("start_date") 
            end_date = request.POST.get("end_date")
            
            job = SchedulingJob.objects.get(id=job_id)
            job.start_date = start_date
            job.end_date = end_date
            job.save()
            
            return JsonResponse({"status": "ok"})
            
        return super().dispatch(request, *args, **kwargs)

    def get_data(self):
        """Return data for gantt chart"""
        jobs = SchedulingJob.objects.all()
        data = []
        for job in jobs:
            data.append({
                "id": job.id,
                "text": job.name,
                "start_date": job.start_date,
                "end_date": job.end_date,
                "progress": 0
            })
        return JsonResponse({"data": data})

class SchedulerJobList(GridReport):
    """
    顯示排程作業列表的視圖
    """
    title = _('Scheduling Jobs')
    model = SchedulingJob
    template = 'scheduler/schedulingjob_list.html'
    
    # 定義基礎查詢集
    basequeryset = SchedulingJob.objects.all()
    
    # 定義欄位格式
    rows = (
        GridFieldText('name', title=_('name')),
        GridFieldText('operation', title=_('operation')),
        GridFieldDateTime('start_date', title=_('start date')),
        GridFieldDateTime('end_date', title=_('end date')),
        GridFieldText('status', title=_('status')),
        GridFieldInteger('sequence', title=_('sequence')),
        GridFieldInteger('priority', title=_('priority')),
        GridFieldText('configuration', title=_('configuration')),
    )
    
    default_sort = (0, 'asc')
    
    @classmethod
    def filter_items(cls, request, items):
        # 可選：添加自定義過濾邏輯
        return items

class SchedulerConfigList(GridReport):
    """排程配置列表視圖"""
    title = _('Scheduler Configurations')
    model = SchedulerConfiguration
    template = 'scheduler/schedulerconfig_list.html'
        
    basequeryset = SchedulerConfiguration.objects.all()
    
    rows = (
        GridFieldText('name', title=_('name'), key=True, 
                     formatter='detail', extra='"role":"scheduler_config"'),
        GridFieldText('description', title=_('description')),
        GridFieldText('scheduling_method', title=_('scheduling method')),
        GridFieldText('objective', title=_('objective')),
        GridFieldDateTime('horizon_start', title=_('horizon start')),
        GridFieldDateTime('horizon_end', title=_('horizon end')),
        GridFieldInteger('time_limit', title=_('time limit')),
        GridFieldBool('wip_consume_material', title=_('WIP consume material')),
        GridFieldBool('wip_consume_capacity', title=_('WIP consume capacity')),
        GridFieldText('setup_matrix', title=_('setup matrix')),
        GridFieldNumber('size_minimum', title=_('minimum batch size')),
        GridFieldNumber('size_multiple', title=_('multiple batch size')),
        GridFieldBool('wip_produce_full_quantity', title=_('WIP produce full quantity')),
        GridFieldDuration('fence_duration', title=_('time fence')),
        GridFieldDuration('batch_window', title=_('batch window')),
        GridFieldBool('consider_material', title=_('consider material')),
        GridFieldBool('consider_capacity', title=_('consider capacity')),
    )
    
    default_sort = (0, 'asc')

class SchedulerJobCreate(CreateView):
    """排程作業建立視圖"""
    model = SchedulingJob
    template_name = 'scheduler/schedulingjob_form.html'
    title = _('新增排程作業')
    
    fields = [
        'name',
        'demand',
        'operation',
        'configuration',
        'priority',
        'status'
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        return context

    def get_success_url(self):
        return reverse('scheduler:scheduler_job_list')

class SchedulerJobEdit(UpdateView):
    """排程作業編輯視圖"""
    model = SchedulingJob
    template_name = 'scheduler/schedulingjob_form.html'
    title = _('編輯排程作業')
    fields = SchedulerJobCreate.fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        return context

    def get_success_url(self):
        return reverse('scheduler:scheduler_job_list')

class ExecuteSchedulingJob(View):
    """執行排程作業"""
    def post(self, request, pk):
        try:
            job = SchedulingJob.objects.get(pk=pk)
            
            if not job.can_start():
                return JsonResponse({
                    'success': False,
                    'message': _('Job cannot be started')
                })
            
            execute_scheduling_job(pk)
            
            return JsonResponse({
                'success': True,
                'message': _('Job started successfully')
            })
            
        except SchedulingJob.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': _('Job not found')
            }, status=404)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

class SchedulerConfigurationCreate(CreateView):
    """排程配置建立視圖"""
    title = _('新增排程配置')
    model = SchedulerConfiguration
    template_name = 'scheduler/schedulerconfig_form.html'
    form_class = SchedulerConfigurationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        return context

    def get_success_url(self):
        return reverse('scheduler:scheduler_config_list')
