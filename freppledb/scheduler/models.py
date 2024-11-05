from django.db import models
from django.utils.translation import gettext_lazy as _
from freppledb.common.models import AuditModel
from freppledb.input.models import Operation, Resource, Demand

class SchedulerConfiguration(models.Model):
    """排程配置模型"""
    name = models.CharField(_('name'), max_length=300)
    description = models.TextField(_('description'), blank=True, null=True)
    
    # 排程方向
    scheduling_method = models.CharField(
        _('scheduling method'),
        max_length=50,
        choices=[
            ('forward', _('Forward')),
            ('backward', _('Backward'))
        ],
        default='forward'
    )
    
    # 優化目標
    objective = models.CharField(
        _('objective'),
        max_length=50,
        choices=[
            ('makespan', _('Minimize makespan')),
            ('tardiness', _('Minimize tardiness')),
            ('priority', _('Priority based'))
        ],
        default='makespan'
    )
    
    # 時間範圍
    horizon_start = models.DateTimeField(_('horizon start'), null=True, blank=True)
    horizon_end = models.DateTimeField(_('horizon end'), null=True, blank=True)
    
    # 求解器設定
    time_limit = models.IntegerField(
        _('time limit (seconds)'),
        default=60,
        help_text=_('Maximum time allowed for solving')
    )
    
    class Meta:
        verbose_name = _('scheduler configuration')
        verbose_name_plural = _('scheduler configurations')
        
    def __str__(self):
        return self.name

class SchedulingJob(AuditModel):
    """排程作業模型"""
    name = models.CharField(_('name'), max_length=300)
    demand = models.ForeignKey(
        Demand,
        verbose_name=_('demand'),
        on_delete=models.CASCADE,
        related_name='scheduling_jobs'
    )
    operation = models.ForeignKey(
        Operation,
        verbose_name=_('operation'),
        on_delete=models.CASCADE
    )
    start_date = models.DateTimeField(_('start date'), null=True, blank=True)
    end_date = models.DateTimeField(_('end date'), null=True, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('draft', _('Draft')),
            ('confirmed', _('Confirmed')),
            ('completed', _('Completed'))
        ],
        default='draft'
    )
    sequence = models.IntegerField(_('sequence'), default=0)
    priority = models.IntegerField(_('priority'), default=0)
    configuration = models.ForeignKey(
        SchedulerConfiguration,
        verbose_name=_('configuration'),
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        verbose_name = _('scheduling job')
        verbose_name_plural = _('scheduling jobs')
        ordering = ('sequence', 'priority', 'name')

    def __str__(self):
        return f"{self.name} ({self.demand.name})"

class SchedulingResource(AuditModel):
    """
    Links resources to scheduling jobs
    """
    resource = models.ForeignKey(
        Resource,
        verbose_name=_("resource"),
        on_delete=models.CASCADE,
        db_index=True,
    )
    job = models.ForeignKey(
        SchedulingJob,
        verbose_name=_("job"),
        on_delete=models.CASCADE,
        db_index=True,
    )
    quantity = models.DecimalField(
        _("quantity"), max_digits=20, decimal_places=8, default="1.00"
    )

    def __str__(self):
        return f"{self.job.name} - {self.resource.name}"

    class Meta(AuditModel.Meta):
        db_table = "scheduler_resource"
        verbose_name = _("scheduling resource")
        verbose_name_plural = _("scheduling resources")
