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
from freppledb.input.models.operation import Operation
from .models import SchedulingJob, SchedulerConfiguration
from django.views.generic.edit import CreateView, UpdateView
from django.views import View
from .tasks import execute_scheduling_job
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from .forms.scheduler_config import SchedulerConfigurationForm
from django.contrib import messages
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger(__name__)


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
        GridFieldInteger('id', title=_('ID'), key=True, formatter='detail', extra='"role":"scheduler_job"'),
        GridFieldText('name', title=_('Name')),
        GridFieldText('operation_plan', title=_('Operation Plan')),
        GridFieldDateTime('start_date', title=_('Start Date')),
        GridFieldDateTime('end_date', title=_('End Date')),
        GridFieldText('status', title=_('Status')),
        GridFieldInteger('sequence', title=_('Sequence')),
        GridFieldInteger('priority', title=_('Priority')),
        GridFieldText('configuration', title=_('Configuration')),
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
        GridFieldInteger('id', title=_('ID'), key=True, formatter='detail', extra='"role":"scheduler_config"'),
        GridFieldText('name', title=_('name')),
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
    
    fields = ['name', 'demand', 'operation_plan', 'configuration', 'priority', 'status']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        return context

    def get_success_url(self):
        messages.success(self.request, _('排程作業成功建立！'))
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
        messages.success(self.request, _('排程作業成功更新！'))
        return reverse('scheduler:scheduler_job_list')

class ExecuteSchedulingJob(View):
    """執行排程作業"""
    def post(self, request, pk):
        try:
            job = SchedulingJob.objects.get(pk=pk)
            
            if not job.can_start:
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

class SchedulerConfigurationEdit(UpdateView):
    """排程配置編輯視圖"""
    model = SchedulerConfiguration
    template_name = 'scheduler/schedulerconfig_form.html'
    title = _('編輯排程配置')
    form_class = SchedulerConfigurationForm  # 使用自定義表單類

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        return context

    def get_success_url(self):
        return reverse('scheduler:scheduler_config_list')

class GanttDataView(View):
    def get(self, request, job_id=None):
        try:
            logger.debug("Received request for Gantt data with job_id: %s", job_id)
            data = {
                "data": [],
                "links": []
            }
            
            if job_id:
                logger.debug("Fetching data for job with ID: %s", job_id)
                job = SchedulingJob.objects.get(id=job_id)
                operations = job.operation_plan.operation_set.all()  # 使用 related_name 獲取所有操作
            else:
                logger.debug("Fetching data for all jobs")
                operations = Operation.objects.all()  # 獲取所有操作
            
            for op in operations:
                job_name = job.name if job_id else "All Jobs"  # 如果 job_id 為 None，則使用 "All Jobs"
                
                data["data"].append({
                    "name": op.name,
                    "text": f"{job_name} - {op.name}",
                    "start_date": op.effective_start.strftime("%Y-%m-%d %H:%M:%S") if op.effective_start else None,
                    "end_date": op.effective_end.strftime("%Y-%m-%d %H:%M:%S") if op.effective_end else None,
                    "progress": 0,
                    "job_id": job.id if job_id else None  # 如果 job_id 為 None，則設置為 None
                })
                
                if op.dependencies.exists():
                    for dep in op.dependencies.all():
                        data["links"].append({
                            "id": f"{op.name}_{dep.name}",
                            "source": dep.name,
                            "target": op.name,
                            "type": "0"
                        })
            
            logger.debug("Successfully fetched Gantt data")
            return JsonResponse(data)
            
        except Exception as e:
            logger.error("Error fetching Gantt data: %s", str(e))
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UpdateOperationView(View):
    def post(self, request):
        operation_name = request.POST.get('operation_id')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        resource = request.POST.get('resource')
        
        try:
            operation = Operation.objects.get(name=operation_name)
            
            # 檢查更新是否可行
            if self.is_update_feasible(operation, start_date, end_date, resource):
                operation.effective_start = start_date
                operation.effective_end = end_date
                operation.save()
                
                return JsonResponse({"success": True})
            else:
                return JsonResponse({
                    "success": False,
                    "message": "更新不可行，請檢查資源可用性和相依關係"
                })
                
        except Operation.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Operation not found"
            }, status=404)
            
    def is_update_feasible(self, operation, start_date, end_date, resource):
        # 實現可行性檢查邏輯
        return True
