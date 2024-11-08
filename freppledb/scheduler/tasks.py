from freppledb.common.middleware import _thread_locals
from freppledb.execute.models import Task
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

def execute_scheduling_job(job_id):
    """執行排程作業的任務"""
    try:
        from .models import SchedulingJob
        
        # 建立任務記錄
        task = Task(
            name='排程作業',
            submitted=timezone.now(),
            status='0',  # 等待中
            user=_thread_locals.request.user if hasattr(_thread_locals, 'request') else None,
        )
        task.save()
        
        try:
            with transaction.atomic():
                job = SchedulingJob.objects.get(id=job_id)
                job.start_execution()
                task.status = '2'  # 完成
                task.finished = timezone.now()
                
        except Exception as e:
            task.status = '3'  # 失敗
            task.message = str(e)
            task.finished = timezone.now()
            raise
            
        finally:
            task.save()
            
    except SchedulingJob.DoesNotExist:
        logger.error(f"排程作業不存在: {job_id}")
    except Exception as e:
        logger.error(f"執行排程作業時發生錯誤: {str(e)}")
        raise