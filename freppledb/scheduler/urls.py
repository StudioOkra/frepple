from django.urls import path

from . import views

# Automatically add these URLs when the application is installed
autodiscover = True

app_name = "scheduler"

urlpatterns = [
    # Add your URL patterns here
    path(
        "data/scheduler/jobs/",
        views.SchedulerJobList.as_view(),
        name="scheduler_job_list"
    ),
]
