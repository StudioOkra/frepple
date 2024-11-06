from django.urls import path
from .views import (
    SchedulerConfigList, SchedulerConfigCreate, 
    SchedulerConfigUpdate, SchedulerJobList,
    SchedulerJobCreate, ExecuteSchedulingJob,
    SchedulerConfigurationCreate, SchedulerConfigurationEdit,
    SchedulerJobEdit
)

# Automatically add these URLs when the application is installed
autodiscover = True

app_name = "scheduler"

urlpatterns = [
    # 排程作業相關 URL
    path('data/scheduler/jobs/', SchedulerJobList.as_view(), name='scheduler_job_list'),
    # path('data/scheduler/schedulingjob/add/', SchedulingJobCreate.as_view(), name='scheduler_job_add'),
    path('data/scheduler/schedulingjob/add/', SchedulerJobCreate.as_view(), name='schedulingjob_add'),
    path('execute/<int:pk>/', ExecuteSchedulingJob.as_view(), name='execute_scheduling_job'),
    
    # 排程配置相關 URL
    path('data/scheduler/config/', SchedulerConfigList.as_view(), name='scheduler_config_list'),
    # path('data/scheduler/schedulerconfiguration/add/', SchedulerConfigCreate.as_view(), name='scheduler_config_add'),
    path('data/scheduler/schedulerconfiguration/add/', SchedulerConfigurationCreate.as_view(), name='scheduler_configuration_add'),
    path('data/scheduler/config/<int:pk>/edit/', SchedulerConfigUpdate.as_view(), name='scheduler_config_edit'),
    
    # 排程設定相關 URL
    path('configuration/<int:pk>/edit/', SchedulerConfigurationEdit.as_view(), name='scheduler_configuration_edit'),
    path('schedulingjob/<int:pk>/edit/', SchedulerJobEdit.as_view(), name='schedulingjob_edit'),
]
