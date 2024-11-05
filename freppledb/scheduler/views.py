from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from freppledb.common.report import GridReport, GridFieldText, GridFieldDateTime, GridFieldInteger
from .models import SchedulingJob, SchedulerConfiguration
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .forms import SchedulingJobForm

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
        GridFieldText('name', title=_('name')),
        GridFieldText('scheduling_method', title=_('scheduling method')),
        GridFieldText('objective', title=_('objective')),
        GridFieldDateTime('horizon_start', title=_('horizon start')),
        GridFieldDateTime('horizon_end', title=_('horizon end')),
        GridFieldInteger('time_limit', title=_('time limit')),
    )
    
    default_sort = (0, 'asc')

class SchedulingJobCreate(CreateView):
    model = SchedulingJob
    form_class = SchedulingJobForm
    template_name = 'scheduler/schedulingjob_form.html'
    success_url = '/data/scheduler/jobs/'
