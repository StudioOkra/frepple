from django.db import models
from django.utils.translation import gettext_lazy as _
from freppledb.common.models import AuditModel
from freppledb.input.models import Operation, Resource

class SchedulerConfiguration(AuditModel):
    """
    Configuration settings for the scheduler
    """
    name = models.CharField(_("name"), max_length=300, primary_key=True)
    scheduling_method = models.CharField(
        _("scheduling method"),
        max_length=20,
        default="forward",
        choices=(
            ("forward", _("forward")),
            ("backward", _("backward")),
        ),
    )
    horizon_start = models.DateTimeField(_("horizon start"), null=True, blank=True)
    horizon_end = models.DateTimeField(_("horizon end"), null=True, blank=True)
    description = models.CharField(
        _("description"), max_length=500, null=True, blank=True
    )

    def __str__(self):
        return self.name

    class Meta(AuditModel.Meta):
        db_table = "scheduler_configuration"
        verbose_name = _("scheduler configuration")
        verbose_name_plural = _("scheduler configurations")

class SchedulingJob(AuditModel):
    """
    Represents a scheduling job
    """
    name = models.CharField(_("name"), max_length=300, primary_key=True)
    operation = models.ForeignKey(
        Operation,
        verbose_name=_("operation"),
        on_delete=models.CASCADE,
        db_index=True,
    )
    start_date = models.DateTimeField(_("start date"), null=True, blank=True)
    end_date = models.DateTimeField(_("end date"), null=True, blank=True)
    status = models.CharField(
        _("status"),
        max_length=20,
        default="proposed",
        choices=(
            ("proposed", _("proposed")),
            ("confirmed", _("confirmed")),
            ("completed", _("completed")),
        ),
    )
    sequence = models.IntegerField(_("sequence"), default=0)
    priority = models.IntegerField(_("priority"), default=0)
    configuration = models.ForeignKey(
        SchedulerConfiguration,
        verbose_name=_("configuration"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    class Meta(AuditModel.Meta):
        db_table = "scheduler_job"
        verbose_name = _("scheduling job")
        verbose_name_plural = _("scheduling jobs")
        ordering = ("sequence", "priority", "name")

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
