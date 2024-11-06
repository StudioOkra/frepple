from django.utils.translation import gettext_lazy as _
from freppledb.input.models import OperationPlan
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import logging
from django.db.models import Sum

class SchedulerEngine:
    def __init__(self, configuration):
        """
        初始化排程引擎
        Args:
            configuration: SchedulerConfiguration 實例
        """
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.configuration = configuration
        self.operation_plans = []
        
        # 根據排程方向設定時間範圍
        if configuration.scheduling_method == 'backward':
            self.horizon_end = configuration.horizon_end or datetime.now()
            self.horizon_start = configuration.horizon_start
        else:  # forward
            self.horizon_start = configuration.horizon_start or datetime.now()
            self.horizon_end = configuration.horizon_end
        
        # 設定求解器時間限制
        self.solver.parameters.max_time_in_seconds = configuration.time_limit
        
        # 初始化變數
        self.intervals = {}
        self.start_vars = {}
        self.end_vars = {}
        
        # 添加日誌記錄
        self.logger = logging.getLogger(__name__)
        
    def load_frepple_data(self):
        """載入 frepple 的資料"""
        query = OperationPlan.objects.filter(status='proposed')
        
        # 根據 WIP 設定過濾
        if not self.configuration.wip_consume_material:
            query = query.exclude(status='confirmed')
            
        # 根據時間範圍過濾
        if self.horizon_start:
            query = query.filter(startdate__gte=self.horizon_start)
        if self.horizon_end:
            query = query.filter(enddate__lte=self.horizon_end)
            
        self.operation_plans = query.select_related('operation', 'demand')
        
    def build_model(self):
        """建立生產排程模型"""
        # 時間範圍轉換為秒（frepple 使用秒作為基本單位）
        horizon_start_seconds = int(self.horizon_start.timestamp())
        horizon_end_seconds = int(self.horizon_end.timestamp())
        
        for operation in self.operations:
            # 建立操作變數
            start_var = self.model.NewIntVar(
                horizon_start_seconds,
                horizon_end_seconds,
                f'start_{operation.id}'
            )
            duration = int(operation.duration)
            end_var = self.model.NewIntVar(
                horizon_start_seconds,
                horizon_end_seconds,
                f'end_{operation.id}'
            )
            
            # 根據排程方向設定約束
            if self.configuration.scheduling_method == 'backward':
                # 後排：從交期往前排
                if operation.due_date:
                    due_date_seconds = int(operation.due_date.timestamp())
                    self.model.Add(end_var <= due_date_seconds)
            else:
                # 前排：從最早可開始時間往後排
                if operation.earliest_start:
                    earliest_seconds = int(operation.earliest_start.timestamp())
                    self.model.Add(start_var >= earliest_seconds)
            
            # 添加持續時間約束
            self.model.Add(end_var == start_var + duration)
            
            # 保存變數供後續使用
            self.start_vars[operation.id] = start_var
            self.end_vars[operation.id] = end_var
    
    def find_batching_opportunities(self, operation):
        """尋找批次機會"""
        # 將 batch_window 轉換為秒
        batch_window_seconds = int(self.configuration.batch_window.total_seconds())
        batch_start = operation.due_date - timedelta(seconds=batch_window_seconds)
        batch_end = operation.due_date + timedelta(seconds=batch_window_seconds)
        
        similar_ops = self.operations.filter(
            operation_type=operation.operation_type,
            start_date__gte=batch_start,
            end_date__lte=batch_end
        )
        
        if similar_ops.exists():
            self.create_batch_constraints(similar_ops)
    
    def add_resource_constraints(self):
        """添加資源約束"""
        for resource in self.resources:
            intervals = []
            demands = []
            
            for opplan in self.operation_plans:
                if opplan.resource == resource:
                    # 使用 frepple 的資源負載計算
                    load = opplan.operation.get_resource_load(resource)
                    if not load:
                        continue
                        
                    interval = self.model.NewIntervalVar(
                        opplan.start_var,
                        int(load.duration),  # frepple 已經使用秒為單位
                        opplan.end_var,
                        f'interval_{opplan.id}'
                    )
                    
                    intervals.append(interval)
                    demands.append(load.quantity)
            
            if intervals:
                capacity = resource.maximum or resource.get_capacity()
                if capacity:
                    self.model.AddCumulative(intervals, demands, capacity)
                else:
                    self.model.AddNoOverlap(intervals)
    
    def add_precedence_constraints(self):
        """添加優先順序約束"""
        for opplan in self.operation_plans:
            # 檢查是否有前置操作
            if opplan.operation.prerequisites.exists():
                for prereq in opplan.operation.prerequisites.all():
                    # 找到前置操作的計劃
                    prereq_plans = [op for op in self.operation_plans 
                                  if op.operation == prereq]
                    for prereq_plan in prereq_plans:
                        self.model.Add(opplan.start_var >= prereq_plan.end_var)
                        
    def add_time_window_constraints(self):
        """添加時間窗口約束"""
        for opplan in self.operation_plans:
            # 檢查操作是否有時間窗口限制
            if hasattr(opplan.operation, 'time_window_start') and opplan.operation.time_window_start:
                window_start = int(opplan.operation.time_window_start.timestamp())
                self.model.Add(opplan.start_var >= window_start)
                
            if hasattr(opplan.operation, 'time_window_end') and opplan.operation.time_window_end:
                window_end = int(opplan.operation.time_window_end.timestamp())
                self.model.Add(opplan.end_var <= window_end)
                
            # 檢查資源可用時間
            if opplan.resource and hasattr(opplan.resource, 'available_from'):
                resource_start = int(opplan.resource.available_from.timestamp())
                self.model.Add(opplan.start_var >= resource_start)
                
            if opplan.resource and hasattr(opplan.resource, 'available_until'):
                resource_end = int(opplan.resource.available_until.timestamp())
                self.model.Add(opplan.end_var <= resource_end)
            
    def add_batch_constraints(self):
        """添加批次約束"""
        for op in self.operation_plans:
            if not hasattr(op, 'quantity'):
                continue
            
            # 使用 frepple 的批次設定
            operation = op.operation
            if operation.batch:
                # 最小批量
                if self.configuration.size_minimum:
                    min_size = max(float(self.configuration.size_minimum), 
                                 operation.batch.minimumsize)
                    self.model.Add(op.quantity >= min_size)
                
                # 批量倍數
                if self.configuration.size_multiple:
                    multiple = operation.batch.multiple or float(self.configuration.size_multiple)
                    self.model.Add(op.quantity % multiple == 0)
    
    def set_objective(self):
        """設置優化目標"""
        if self.configuration.objective == 'makespan':
            # 最小化完工時間
            makespan = self.model.NewIntVar(0, self.horizon_end_seconds, 'makespan')
            for opplan in self.operation_plans:
                self.model.Add(makespan >= opplan.end_var)
            self.model.Minimize(makespan)
            
        elif self.configuration.objective == 'tardiness':
            # 最小化延遲時間
            total_tardiness = self.model.NewIntVar(0, self.horizon_end_seconds * len(self.operation_plans), 'total_tardiness')
            tardiness_vars = []
            for opplan in self.operation_plans:
                if hasattr(opplan, 'due_date'):
                    tardiness = self.model.NewIntVar(0, self.horizon_end_seconds, f'tardiness_{opplan.id}')
                    due_date_seconds = int(opplan.due_date.timestamp())
                    self.model.Add(tardiness >= opplan.end_var - due_date_seconds)
                    tardiness_vars.append(tardiness)
            self.model.Add(total_tardiness == sum(tardiness_vars))
            self.model.Minimize(total_tardiness)
            
        elif self.configuration.objective == 'priority':
            # 基於優先級的優化
            total_weighted_completion = self.model.NewIntVar(0, self.horizon_end_seconds * len(self.operation_plans), 'total_weighted_completion')
            weighted_vars = []
            for opplan in self.operation_plans:
                weight = opplan.priority if hasattr(opplan, 'priority') else 1
                weighted_vars.append(opplan.end_var * weight)
            self.model.Add(total_weighted_completion == sum(weighted_vars))
            self.model.Minimize(total_weighted_completion)
            
    def get_solution_info(self):
        """獲取求解結果信息"""
        if not self.solver.ObjectiveValue():
            return None
            
        return {
            'status': self.solver.StatusName(),
            'objective_value': self.solver.ObjectiveValue(),
            'wall_time': self.solver.WallTime(),
            'branches': self.solver.NumBranches(),
            'conflicts': self.solver.NumConflicts()
        }
    
    def solve(self):
        """執行求解"""
        try:
            self.load_frepple_data()
            self.build_model()
            self.add_resource_constraints()
            self.add_precedence_constraints()
            self.add_time_window_constraints()
            
            if self.configuration.size_minimum or self.configuration.size_multiple:
                self.add_batch_constraints()
                
            self.set_objective()
            
            status = self.solver.Solve(self.model)
            success = status == cp_model.OPTIMAL or status == cp_model.FEASIBLE
            
            if success:
                solution_info = self.get_solution_info()
                self.logger.info(f"排程完成: {solution_info}")
            else:
                self.logger.warning(f"排程未找到可行解: {self.solver.StatusName()}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"排程求解錯誤: {str(e)}")
            return False

    def add_material_constraints(self):
        """添加物料約束"""
        for opplan in self.operation_plans:
            # 獲取物料需求
            material_requirements = opplan.operation.materials.all()
            
            for material in material_requirements:
                # 檢查物料庫存
                available_qty = material.buffer.onhand if hasattr(material.buffer, 'onhand') else 0
                
                # 如果是消耗物料
                if material.type == 'consumption':
                    required_qty = opplan.quantity * material.quantity
                    
                    # 檢查 WIP 設定
                    if not self.configuration.wip_consume_material:
                        wip_qty = self.get_wip_quantity(material.buffer)
                        available_qty += wip_qty
                        
                    # 添加物料可用性約束
                    self.model.Add(required_qty <= available_qty)
                    
                # 如果是產出物料
                elif material.type == 'production':
                    produced_qty = opplan.quantity * material.quantity
                    
                    # 檢查 WIP 設定
                    if self.configuration.wip_produce_full_quantity:
                        self.model.Add(produced_qty == material.quantity)

    def get_wip_quantity(self, buffer):
        """獲取 WIP 數量"""
        return OperationPlan.objects.filter(
            operation__materials__buffer=buffer,
            status='confirmed'
        ).aggregate(
            total_qty=Sum('quantity')
        )['total_qty'] or 0
