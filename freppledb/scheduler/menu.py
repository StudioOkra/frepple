from django.utils.translation import gettext_lazy as _

from freppledb.menu import menu
from .models import SchedulingJob
from .views import SchedulerJobList

menu.addGroup(
    "scheduler_menu",
    label=_("Scheduler"),
    index=1100
)
menu.addItem(
    "scheduler_menu",
    "scheduler_jobs",
    url="/data/scheduler/jobs/",
    report=SchedulerJobList,
    index=100,
    model=SchedulingJob,
)
menu.addItem(
    "scheduler_menu",
    "scheduler_config",
    url="/data/scheduler/config/",
    label=_("排程設定"),
    index=200,
    permission="scheduler.view_schedulerconfig",
)
