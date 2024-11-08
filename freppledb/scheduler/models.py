from django.db import models
from django.utils.translation import gettext_lazy as _
from freppledb.common.models import AuditModel
from freppledb.input.models import Operation, Resource
from django.core.exceptions import ValidationError
from datetime import datetime
from django.utils import timezone
from .scheduler import SchedulerEngine

class SchedulerConfiguration(models.Model):
    """生產排程配置模型"""
    name = models.CharField(_('name'), max_length=300, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
    
    # 排程方向
    scheduling_method = models.CharField(
        _('scheduling method'),
        max_length=50,
        choices=[
            ('forward', _('Forward')),
            ('backward', _('Backward'))
        ],
        default='backward',
        help_text=_('Forward: ASAP scheduling, Backward: JIT scheduling')
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
    horizon_start = models.DateTimeField(
        _('horizon start'), 
        null=True, 
        blank=True,
        help_text=_('Start date and time of scheduling horizon (YYYY-MM-DD HH:mm:ss)')
    )
    horizon_end = models.DateTimeField(
        _('horizon end'), 
        null=True, 
        blank=True,
        help_text=_('End date and time of scheduling horizon (YYYY-MM-DD HH:mm:ss)')
    )
    
    # 求解器設定
    time_limit = models.IntegerField(
        _('time limit (seconds)'),
        default=60,
        help_text=_('Time limit for the scheduler in seconds')
    )
    
    # WIP 相關設定
    wip_consume_material = models.BooleanField(
        _('WIP consume material'),
        default=True,
        help_text=_('Whether confirmed manufacturing orders consume material')
    )
    wip_consume_capacity = models.BooleanField(
        _('WIP consume capacity'),
        default=True,
        help_text=_('Whether confirmed manufacturing orders consume capacity')
    )
    wip_produce_full_quantity = models.BooleanField(
        _('WIP produce full quantity'),
        default=True,
        help_text=_('Whether WIP orders must produce their full quantity')
    )
    
    # 批次相關設定
    size_minimum = models.DecimalField(
        _('minimum batch size'),
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_('Minimum quantity for manufacturing orders')
    )
    size_multiple = models.DecimalField(
        _('multiple batch size'),
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_('Manufacturing order quantities must be a multiple of this size')
    )
    
    # 新增生產排程相關設定
    fence_duration = models.DurationField(
        _('time fence'),
        null=True,
        blank=True,
        help_text=_('Time window during which manufacturing orders are frozen')
    )
    
    batch_window = models.DurationField(
        _('batch window'),
        null=True,
        blank=True,
        help_text=_('Time window for batching opportunities')
    )
    
    setup_matrix = models.ForeignKey(
        'input.SetupMatrix',
        verbose_name=_('setup matrix'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_('Matrix defining setup times between operations')
    )
    
    consider_material = models.BooleanField(
        _('consider material constraints'),
        default=True,
        help_text=_('Whether to consider material availability in scheduling')
    )
    
    consider_capacity = models.BooleanField(
        _('consider capacity constraints'),
        default=True,
        help_text=_('Whether to consider resource capacity in scheduling')
    )

    def clean(self):
        """驗證配置"""
        if self.horizon_start and self.horizon_end:
            if self.horizon_start >= self.horizon_end:
                raise ValidationError({
                    'horizon_end': _('End date must be later than start date')
                })
        
        if self.size_minimum and self.size_multiple:
            if self.size_minimum > self.size_multiple:
                raise ValidationError({
                    'size_multiple': _('Multiple size must be greater than or equal to minimum size')
                })
    
    class Meta:
        verbose_name = _('scheduler configuration')
        verbose_name_plural = _('scheduler configurations')
        
    def __str__(self):
        return self.name

class SchedulingJob(AuditModel):
    """排程作業模型"""
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('queued', _('Queued')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled'))
    ]
    
    name = models.CharField(_('name'), max_length=255, unique=True)
    demand = models.ForeignKey(
        'input.Demand',
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
        choices=STATUS_CHOICES,
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
    
    # 需要新增的關聯
    buffer = models.ForeignKey(
        'input.Buffer',
        verbose_name=_('buffer'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_('Related buffer for material requirements')
    )
    
    resource = models.ForeignKey(
        'input.Resource',
        verbose_name=_('resource'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_('Primary resource required')
    )
    
    item = models.ForeignKey(
        'input.Item',
        verbose_name=_('item'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_('Item being produced or consumed')
    )
    
    location = models.ForeignKey(
        'input.Location',
        verbose_name=_('location'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_('Location where the operation is performed')
    )
    
    class Meta:
        verbose_name = _('scheduling job')
        verbose_name_plural = _('scheduling jobs')
        ordering = ('sequence', 'priority', 'name')

    def __str__(self):
        return f"{self.name} ({self.demand.name})"

    def update_status(self, new_status, message=None):
        """更新作業狀態"""
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValueError(f"Invalid status: {new_status}")
            
        old_status = self.status
        self.status = new_status
        self.save()
        
        # 記錄狀態變更
        StatusLog.objects.create(
            job=self,
            old_status=old_status,
            new_status=new_status,
            message=message
        )
        
    @property
    def can_start(self):
        """
        定義排程作業是否可執行的邏輯。
        根據您的業務需求調整此方法。
        """
        return (
            self.status in ['draft', 'failed'] and
            self.demand and self.demand.status in ['open', 'quote'] and
            self.operation and
            self.configuration
        )
    
    def execute(self):
        """執行排程作業"""
        if not self.can_start:
            raise ValueError("Job cannot be started")
            
        try:
            self.update_status('running')
            
            # 初始化排程引擎
            engine = SchedulerEngine(self.configuration)
            
            # 執行排程
            success = engine.solve()
            
            if success:
                # 保存排程結果
                if self.save_results(engine):
                    self.update_status('completed')
                    
                    # 記錄求解信息
                    solution_info = engine.get_solution_info()
                    StatusLog.objects.create(
                        job=self,
                        old_status='running',
                        new_status='completed',
                        message=f"排程完成: {solution_info}"
                    )
                else:
                    self.update_status('failed', "Failed to save results")
            else:
                self.update_status('failed', "No feasible solution found")
                
        except Exception as e:
            self.update_status('failed', str(e))
            raise

    def save_results(self, engine):
        """保存排程結果"""
        if not engine.solver.ObjectiveValue():
            return False
            
        try:
            # 更新開始和結束時間
            for opplan in engine.operation_plans:
                start_time = datetime.fromtimestamp(
                    engine.solver.Value(opplan.start_var)
                )
                end_time = datetime.fromtimestamp(
                    engine.solver.Value(opplan.end_var)
                )
                
                opplan.startdate = start_time
                opplan.enddate = end_time
                opplan.save()
                
            # 更新作業時間（確保使用秒為單位）
            self.start_date = datetime.fromtimestamp(min(op.start_var for op in engine.operation_plans))
            self.end_date = datetime.fromtimestamp(max(op.end_var for op in engine.operation_plans))
            self.save()
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存排程結果失敗: {str(e)}")
            return False

    def start_execution(self):
        """開始執行排程作業"""
        execution = SchedulingJobExecution.objects.create(
            job=self,
            status='running'
        )
        
        try:
            # 初始化排程引擎
            engine = SchedulerEngine(self.configuration)
            
            # 執行排程
            success = engine.solve()
            
            if success:
                # 保存排程結果
                self.save_results(engine)
                solution_info = engine.get_solution_info()
                
                execution.status = 'completed'
                execution.solution_info = solution_info
                execution.end_time = timezone.now()
                
            else:
                execution.status = 'failed'
                execution.error_message = '無法找到可行解'
                execution.end_time = timezone.now()
                
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.end_time = timezone.now()
            raise
            
        finally:
            execution.save()

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

class StatusLog(models.Model):
    """排程作業狀態日誌"""
    job = models.ForeignKey(
        SchedulingJob,
        verbose_name=_('job'),
        on_delete=models.CASCADE,
        related_name='status_logs'
    )
    old_status = models.CharField(_('old status'), max_length=20)
    new_status = models.CharField(_('new status'), max_length=20)
    message = models.TextField(_('message'), blank=True, null=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    
    class Meta:
        ordering = ['-created']

class SchedulingJobExecution(models.Model):
    """排程作業執行記錄"""
    job = models.ForeignKey(
        SchedulingJob,
        verbose_name=_('job'),
        on_delete=models.CASCADE,
        related_name='executions'
    )
    start_time = models.DateTimeField(_('start time'), auto_now_add=True)
    end_time = models.DateTimeField(_('end time'), null=True, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('running', _('Running')),
            ('completed', _('Completed')),
            ('failed', _('Failed'))
        ]
    )
    solution_info = models.JSONField(_('solution info'), null=True, blank=True)
    error_message = models.TextField(_('error message'), null=True, blank=True)
    
    class Meta:
        ordering = ['-start_time']
