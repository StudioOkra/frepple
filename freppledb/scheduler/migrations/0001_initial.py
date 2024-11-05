from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('input', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchedulerConfiguration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, serialize=False, verbose_name='name')),
                ('scheduling_method', models.CharField(choices=[('forward', 'forward'), ('backward', 'backward')], default='forward', max_length=20, verbose_name='scheduling method')),
                ('horizon_start', models.DateTimeField(blank=True, null=True, verbose_name='horizon start')),
                ('horizon_end', models.DateTimeField(blank=True, null=True, verbose_name='horizon end')),
                ('description', models.CharField(blank=True, max_length=500, null=True, verbose_name='description')),
            ],
            options={
                'verbose_name': 'scheduler configuration',
                'verbose_name_plural': 'scheduler configurations',
                'db_table': 'scheduler_configuration',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SchedulingJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, serialize=False, verbose_name='name')),
                ('start_date', models.DateTimeField(blank=True, null=True, verbose_name='start date')),
                ('end_date', models.DateTimeField(blank=True, null=True, verbose_name='end date')),
                ('status', models.CharField(choices=[('proposed', 'proposed'), ('confirmed', 'confirmed'), ('completed', 'completed')], default='proposed', max_length=20, verbose_name='status')),
                ('sequence', models.IntegerField(default=0, verbose_name='sequence')),
                ('priority', models.IntegerField(default=0, verbose_name='priority')),
                ('configuration', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='scheduler.schedulerconfiguration', verbose_name='configuration')),
                ('operation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='input.operation', verbose_name='operation')),
            ],
            options={
                'verbose_name': 'scheduling job',
                'verbose_name_plural': 'scheduling jobs',
                'db_table': 'scheduler_job',
                'ordering': ('sequence', 'priority', 'name'),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SchedulingResource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=8, default='1.00', max_digits=20, verbose_name='quantity')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scheduler.schedulingjob', verbose_name='job')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='input.resource', verbose_name='resource')),
            ],
            options={
                'verbose_name': 'scheduling resource',
                'verbose_name_plural': 'scheduling resources',
                'db_table': 'scheduler_resource',
                'abstract': False,
            },
        ),
    ]
