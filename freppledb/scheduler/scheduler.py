from django.db import models
from django.utils.translation import gettext_lazy as _
from freppledb.input.models import Resource, Operation, OperationPlan
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import logging

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
        self.resources = []
        self.horizon_start = configuration.horizon_start or datetime.now()
        self.horizon_end = configuration.horizon_end
        
        # 添加優化目標相關屬性
        self.objective_variables = []
        self.objective_coefficients = []
        
        # 添加求解狀態追蹤
        self.solution_status = None
        self.solution_info = {}
        
        # 添加日誌記錄
        self.logger = logging.getLogger(__name__)
        
    def load_frepple_data(self):
        """載入 frepple 的資料"""
        # 載入資源
        self.resources = Resource.objects.all()
        
        # 載入操作計劃
        self.operation_plans = OperationPlan.objects.filter(
            status='proposed'
        ).select_related(
            'operation',
            'resource'
        )
        
        if self.horizon_start:
            self.operation_plans = self.operation_plans.filter(
                startdate__gte=self.horizon_start
            )
        if self.horizon_end:
            self.operation_plans = self.operation_plans.filter(
                enddate__lte=self.horizon_end
            )
        
    def build_model(self):
        """建立 CP-SAT 模型"""
        # 轉換時間到分鐘為單位
        horizon_start_minutes = int(self.horizon_start.timestamp() / 60)
        horizon_end_minutes = int(self.horizon_end.timestamp() / 60) if self.horizon_end else horizon_start_minutes + 60 * 24 * 30
        
        # 根據排程方向設定變數範圍
        is_forward = self.configuration.scheduling_method == 'forward'
        
        for opplan in self.operation_plans:
            duration = int(opplan.operation.duration / 60)
            
            if is_forward:
                # 前推排程：從最早開始時間往後排
                start_min = horizon_start_minutes
                start_max = horizon_end_minutes - duration
                end_min = horizon_start_minutes + duration
                end_max = horizon_end_minutes
            else:
                # 後推排程：從最晚完工時間往前排
                if hasattr(opplan, 'due_date'):
                    due_date_minutes = int(opplan.due_date.timestamp() / 60)
                    start_min = horizon_start_minutes
                    start_max = due_date_minutes - duration
                    end_min = horizon_start_minutes + duration
                    end_max = due_date_minutes
                else:
                    # 如果沒有交期，使用排程範圍結束時間
                    start_min = horizon_start_minutes
                    start_max = horizon_end_minutes - duration
                    end_min = horizon_start_minutes + duration
                    end_max = horizon_end_minutes
            
            # 創建開始時間變數
            opplan.start_var = self.model.NewIntVar(
                start_min,
                start_max,
                f'start_{opplan.id}'
            )
            
            # 創建結束時間變數
            opplan.end_var = self.model.NewIntVar(
                end_min,
                end_max,
                f'end_{opplan.id}'
            )
            
            # 添加持續時間約束
            self.model.Add(opplan.end_var == opplan.start_var + duration)
            
    def add_resource_constraints(self):
        """添加資源約束"""
        for resource in self.resources:
            intervals = []
            demands = []
            
            for opplan in self.operation_plans:
                if opplan.resource == resource:
                    # 計算資源需求量
                    load_quantity = opplan.quantity * opplan.operation.resource_qty
                    
                    interval = self.model.NewIntervalVar(
                        opplan.start_var,
                        int(opplan.operation.duration / 60),
                        opplan.end_var,
                        f'interval_{opplan.id}'
                    )
                    
                    intervals.append(interval)
                    demands.append(load_quantity)
            
            # 添加資源容量約束
            if intervals:
                if resource.maximum is not None:
                    self.model.AddCumulative(
                        intervals,
                        demands,
                        resource.maximum
                    )
                else:
                    # 如果沒有最大容量限制，則確保不重疊
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
                window_start = int(opplan.operation.time_window_start.timestamp() / 60)
                self.model.Add(opplan.start_var >= window_start)
                
            if hasattr(opplan.operation, 'time_window_end') and opplan.operation.time_window_end:
                window_end = int(opplan.operation.time_window_end.timestamp() / 60)
                self.model.Add(opplan.end_var <= window_end)
                
            # 檢查資源可用時間
            if opplan.resource and hasattr(opplan.resource, 'available_from'):
                resource_start = int(opplan.resource.available_from.timestamp() / 60)
                self.model.Add(opplan.start_var >= resource_start)
                
            if opplan.resource and hasattr(opplan.resource, 'available_until'):
                resource_end = int(opplan.resource.available_until.timestamp() / 60)
                self.model.Add(opplan.end_var <= resource_end)
            
    def set_objective(self):
        """設置優化目標"""
        if self.configuration.objective == 'makespan':
            # 最小化完工時間
            makespan = self.model.NewIntVar(0, self.horizon_end_minutes, 'makespan')
            for opplan in self.operation_plans:
                self.model.Add(makespan >= opplan.end_var)
            self.model.Minimize(makespan)
            
        elif self.configuration.objective == 'tardiness':
            # 最小化延遲時間
            total_tardiness = self.model.NewIntVar(0, self.horizon_end_minutes * len(self.operation_plans), 'total_tardiness')
            tardiness_vars = []
            for opplan in self.operation_plans:
                if hasattr(opplan, 'due_date'):
                    tardiness = self.model.NewIntVar(0, self.horizon_end_minutes, f'tardiness_{opplan.id}')
                    due_date_minutes = int(opplan.due_date.timestamp() / 60)
                    self.model.Add(tardiness >= opplan.end_var - due_date_minutes)
                    tardiness_vars.append(tardiness)
            self.model.Add(total_tardiness == sum(tardiness_vars))
            self.model.Minimize(total_tardiness)
            
        elif self.configuration.objective == 'priority':
            # 基於優先級的優化
            total_weighted_completion = self.model.NewIntVar(0, self.horizon_end_minutes * len(self.operation_plans), 'total_weighted_completion')
            weighted_vars = []
            for opplan in self.operation_plans:
                weight = opplan.priority if hasattr(opplan, 'priority') else 1
                weighted_vars.append(opplan.end_var * weight)
            self.model.Add(total_weighted_completion == sum(weighted_vars))
            self.model.Minimize(total_weighted_completion)
            
    def solve(self):
        """執行求解"""
        try:
            # 建立基本模型
            self.build_model()
            
            # 添加各種約束
            self.add_resource_constraints()
            self.add_precedence_constraints()
            self.add_time_window_constraints()
            
            # 設置優化目標
            self.set_objective()
            
            # 設定求解器參數
            solver_params = cp_model.SatParameters()
            solver_params.max_time_in_seconds = self.configuration.time_limit or 60
            
            # 創建求解器並求解
            solver = cp_model.CpSolver()
            solver.parameters.CopyFrom(solver_params)
            
            status = solver.Solve(self.model)
            
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                self._update_solution(solver)
                return True
                
            self.logger.warning(f"求解未找到可行解，狀態：{status}")
            return False
            
        except Exception as e:
            self.logger.error(f"排程求解過程發生錯誤：{str(e)}")
            raise
