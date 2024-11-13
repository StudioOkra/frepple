from django.urls import re_path
from .views import (
    SchedulerJobList,
    SchedulerJobCreate,
    SchedulerJobEdit,
    ExecuteSchedulingJob,
    SchedulerConfigList,
    SchedulerConfigurationCreate,
    SchedulerConfigurationEdit
)

# Automatically add these URLs when the application is installed
autodiscover = True

app_name = "scheduler"

urlpatterns = [
    # 排程作業相關 URL
    re_path(r'^data/scheduler/jobs/$', SchedulerJobList.as_view(), name='scheduler_job_list'),
    re_path(r'^data/scheduler/schedulingjob/add/$', SchedulerJobCreate.as_view(), name='schedulingjob_add'),
    re_path(r'^detail/scheduler_job/(?P<pk>\d+)/$', SchedulerJobEdit.as_view(), name='schedulingjob_edit'),
    re_path(r'^scheduler/execute/(?P<pk>\d+)/$', ExecuteSchedulingJob.as_view(), name='execute_scheduling_job'),
    
    # 排程配置相關 URL
    re_path(r'^data/scheduler/config/$', SchedulerConfigList.as_view(), name='scheduler_config_list'),
    re_path(r'^data/scheduler/schedulerconfiguration/add/$', SchedulerConfigurationCreate.as_view(), name='schedulerconfiguration_add'),
    re_path(r'^detail/scheduler_config/(?P<pk>.+)/$', SchedulerConfigurationEdit.as_view(), name='scheduler_configuration_edit'),
]
