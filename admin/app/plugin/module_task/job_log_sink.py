"""``scheduler.job_log_sink`` 槽位实现：把任务日志写入 task_job 表。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.ap_scheduler import SchedulerUtil
from app.core.database import engine
from app.core.logger import log
from app.core.plugin.context import JobSpec

from .cronjob.job.model import JobModel

TRIGGER_TYPES = ("cron", "interval", "date")
"""``JobSpec.trigger`` 的合法取值（``register`` 的显式判别键）。"""

CRON_FIELD_COUNTS = (6, 7)
"""内核 ``add_cron_job`` 接受的字段数（秒 分 时 天 月 周 [年]）。"""

INTERVAL_FIELD_COUNT = 5
"""内核 ``add_interval_job`` 接受的字段数（秒 分 时 天 周）。"""


class JobLogSinkImpl:
    """任务日志落库实现（同步，与 APScheduler 线程模型一致）。

    唯一例外是 ``register``：运行时在插件启动阶段 ``await`` 它，它把任务交给内核调度器
    （插件 → 内核是允许的依赖方向）。
    """

    def create(
        self,
        job_id: str | int,
        job_name: str | None,
        trigger_type: str,
        status: str,
        next_run_time: str | None = None,
        job_state: str | None = None,
    ) -> int | None:
        """创建任务日志。

        参数:
        - job_id (str | int): 任务 ID。
        - job_name (str | None): 任务名。
        - trigger_type (str): 触发方式。
        - status (str): 状态。
        - next_run_time (str | None): 下次执行时间。
        - job_state (str | None): 任务状态快照。

        返回:
        - int | None: 新日志主键。
        """
        try:
            with Session(engine) as session:
                row = JobModel(
                    job_id=str(job_id),
                    job_name=job_name,
                    trigger_type=trigger_type,
                    status=status,
                    next_run_time=next_run_time,
                    job_state=job_state,
                )
                session.add(row)
                session.commit()
                log.info(f"执行日志创建成功: job_id={job_id}, id={row.id}")
                return int(row.id) if row.id is not None else None
        except Exception as e:
            log.error(f"创建执行日志失败: job_id={job_id}, error={e}", exc_info=True)
            return None

    def update(self, log_id: int, status: str, result: str | None, error: str | None) -> None:
        """按主键更新日志。

        参数:
        - log_id (int): 日志主键。
        - status (str): 新状态。
        - result (str | None): 执行结果。
        - error (str | None): 错误信息。

        返回:
        - None
        """
        with Session(engine) as session:
            row = session.get(JobModel, log_id)
            if row is None:
                log.warning(f"⚠️ 任务日志 {log_id} 不存在，跳过更新")
                return
            row.status = status
            row.result = result
            row.error = error
            session.commit()

    def update_pending(
        self,
        job_id: str | int,
        status: str,
        result: str | None = None,
        error: str | None = None,
        next_run_time: str | None = None,
        job_state: str | None = None,
    ) -> None:
        """更新该 job_id 最新的 pending 状态日志（周期性任务提交时 pending → running）。

        参数:
        - job_id (str | int): 任务 ID。
        - status (str): 新状态。
        - result (str | None): 执行结果。
        - error (str | None): 错误信息。
        - next_run_time (str | None): 下次运行时间。
        - job_state (str | None): 任务状态快照。

        返回:
        - None
        """
        with Session(engine) as session:
            row = (
                session
                .query(JobModel)
                .filter(JobModel.job_id == str(job_id), JobModel.status == "pending")
                .order_by(JobModel.id.desc())
                .first()
            )
            if row:
                row.status = status
                if next_run_time:
                    row.next_run_time = next_run_time
                if job_state:
                    row.job_state = job_state
                if result:
                    row.result = result
                if error:
                    row.error = error
                session.commit()
            else:
                log.warning(f"未找到任务 {job_id} 的待执行日志记录")

    def update_latest(
        self,
        job_id: str | int,
        status: str,
        result: str | None = None,
        error: str | None = None,
        next_run_time: str | None = None,
        job_state: str | None = None,
        job_name: str | None = None,
        trigger_type: str | None = None,
    ) -> None:
        """更新该任务最近一条日志；不存在时自动新建。

        参数:
        - job_id (str | int): 任务 ID。
        - status (str): 新状态。
        - result (str | None): 执行结果。
        - error (str | None): 错误信息。
        - next_run_time (str | None): 下次运行时间。
        - job_state (str | None): 任务状态快照。
        - job_name (str | None): 补建日志时的任务名（不传则前端该列空白）。
        - trigger_type (str | None): 补建日志时的触发方式（不传则前端该列空白）。

        返回:
        - None
        """
        try:
            with Session(engine) as session:
                # 首先尝试更新 running 状态的日志
                row = (
                    session
                    .query(JobModel)
                    .filter(JobModel.job_id == str(job_id), JobModel.status == "running")
                    .order_by(JobModel.id.desc())
                    .first()
                )
                if row:
                    row.status = status
                    if next_run_time:
                        row.next_run_time = next_run_time
                    if job_state:
                        row.job_state = job_state
                    if result:
                        row.result = result
                    if error:
                        row.error = error
                    session.commit()
                    log.info(f"执行日志更新成功: job_id={job_id}, id={row.id}, status={status}")
                    return

                # 没有 running 日志，尝试 cancelled 状态（一次性任务移除顺序问题）
                row = (
                    session
                    .query(JobModel)
                    .filter(JobModel.job_id == str(job_id), JobModel.status == "cancelled")
                    .order_by(JobModel.id.desc())
                    .first()
                )
                if row:
                    row.status = status
                    if next_run_time:
                        row.next_run_time = next_run_time
                    if job_state:
                        row.job_state = job_state
                    if result:
                        row.result = result
                    if error:
                        row.error = error
                    session.commit()
                    log.info(f"执行日志更新成功: job_id={job_id}, id={row.id}, status={status}")
                    return

                # 无已有日志，创建新记录
                log.debug(f"未找到任务 {job_id} 的日志记录，创建新日志")
                new_log = JobModel(
                    job_id=str(job_id),
                    job_name=job_name,
                    trigger_type=trigger_type or "manual",
                    status=status,
                    result=result,
                    error=error,
                    next_run_time=next_run_time,
                    job_state=job_state,
                )
                session.add(new_log)
                session.commit()
                log.info(f"执行日志创建成功: job_id={job_id}, id={new_log.id}, status={status}")
        except Exception as e:
            log.error(
                f"更新执行日志失败: job_id={job_id}, status={status}, error={e}", exc_info=True
            )

    def on_removed(self, job_id: str | int) -> None:
        """任务移除时标记未完成日志为 cancelled。

        参数:
        - job_id (str | int): 任务 ID。

        返回:
        - None
        """
        with Session(engine) as session:
            row = (
                session
                .query(JobModel)
                .filter(
                    JobModel.job_id == str(job_id),
                    JobModel.status.in_(["pending", "running"]),
                )
                .order_by(JobModel.id.desc())
                .first()
            )
            if row:
                row.status = "cancelled"
                session.commit()
                log.info(f"任务 {job_id} 的执行日志已标记为已取消")

    def clear_all(self) -> None:
        """清空全部任务日志。

        返回:
        - None
        """
        try:
            with Session(engine) as session:
                session.query(JobModel).delete()
                session.commit()
                log.info("所有任务日志已清空")
        except Exception as e:
            log.error(f"清空任务日志失败: {e!s}", exc_info=True)

    def cancel_pending(self) -> None:
        """把待执行日志标记为已取消。

        返回:
        - None
        """
        try:
            with Session(engine) as session:
                session.query(JobModel).filter(JobModel.status == "pending").update({
                    "status": "cancelled"
                })
                session.commit()
                log.info("所有待执行任务日志已标记为已取消")
        except Exception as e:
            log.error(f"取消待执行任务日志失败: {e!s}", exc_info=True)

    @staticmethod
    def _infer_trigger(job: JobSpec) -> str:
        """在声明未给出 ``trigger`` 时，按内核的读取优先级推断触发器类型。

        推断刻意**对齐内核 ``add_*_job`` 的取值优先级**，而不是「有 ``interval`` 就当
        interval」：内核读的是 ``trigger_args or interval`` / ``trigger_args or cron``，
        所以 ``interval`` 与 ``trigger_args`` 同时出现时，真正决定调度参数的是
        ``trigger_args``，按 ``interval`` 派发会把 6 字段 Cron 表达式送进 5 字段解析器。

        ``trigger_args`` 的具体类型再按其字段数对齐内核解析器的接受范围：
        ``add_cron_job`` 只接受 6/7 字段（秒 分 时 天 月 周 [年]），``add_interval_job``
        只接受 5 字段（秒 分 时 天 周）或整数秒 —— 故 6/7 字段判 cron、5 字段判 interval，
        其余形态（如 ``"2099-01-01 00:00:00"``）判 date（只有 ``DateTrigger`` 能解析它）。

        参数:
        - job (JobSpec): 任务定义。

        返回:
        - str: ``"cron"`` / ``"interval"`` / ``"date"``。

        异常:
        - ValueError: 既无 ``trigger_args``，也无 ``cron`` / ``interval``。
        """
        trigger_args = job.get("trigger_args")
        if trigger_args:
            field_count = len(str(trigger_args).split())
            if field_count in CRON_FIELD_COUNTS:
                return "cron"
            if field_count == INTERVAL_FIELD_COUNT:
                return "interval"
            return "date"
        if job.get("interval"):
            return "interval"
        if job.get("cron"):
            return "cron"
        raise ValueError(
            "插件定时任务缺少触发器配置：请声明 trigger（cron/interval/date）之一，"
            "或 trigger_args / cron / interval 任一触发器参数"
        )

    async def register(self, job: JobSpec) -> None:
        """把插件声明的定时任务注册进内核调度器。

        先定触发器类型，再调对应的内核包装器：

        - ``JobSpec.trigger`` 存在时它就是判别键（``"cron"`` / ``"interval"`` / ``"date"``），
          取值非法直接报错，不再猜测；
        - 未声明时按内核的取值优先级推断（见 ``_infer_trigger``）。

        两种情形都只决定调 ``add_cron_job`` / ``add_interval_job`` / ``add_date_job`` 中的
        哪一个；参数校验仍在内核，错误带内核原始信息抛出。任何失败都必须显式抛出，绝不静默
        跳过 —— 静默会让任务永远不执行且无人察觉（运行时逐条隔离并记 ERROR 日志）。

        参数:
        - job (JobSpec): 任务定义。

        返回:
        - None

        异常:
        - ValueError: ``trigger`` 取值非法，或无法确定触发器类型、缺少对应触发器参数。
        """
        declared = job.get("trigger")
        trigger = declared if declared else self._infer_trigger(job)
        if trigger not in TRIGGER_TYPES:
            raise ValueError(
                f"无效的 trigger 取值 {trigger!r}：只支持 {'/'.join(TRIGGER_TYPES)} 之一"
            )
        if trigger == "cron":
            SchedulerUtil.add_cron_job(job)
        elif trigger == "interval":
            SchedulerUtil.add_interval_job(job)
        else:
            SchedulerUtil.add_date_job(job)

    def sync_jobs(self, jobs_data: list[dict[str, str | None]]) -> int:
        """将调度器中的任务同步到数据库。

        参数:
        - jobs_data (list[dict]): 待同步的任务数据列表，每项含 job_id/job_name/trigger_type/next_run_time/job_state。

        返回:
        - int: 新建的日志条数。
        """
        sync_count = 0
        with Session(engine) as session:
            for data in jobs_data:
                existing = (
                    session
                    .query(JobModel)
                    .filter(
                        JobModel.job_id == str(data["job_id"]),
                        JobModel.status == "pending",
                    )
                    .first()
                )
                if not existing:
                    session.add(
                        JobModel(
                            job_id=str(data["job_id"]),
                            job_name=data.get("job_name"),
                            trigger_type=data.get("trigger_type", "manual"),
                            status="pending",
                            next_run_time=data.get("next_run_time"),
                            job_state=data.get("job_state"),
                        )
                    )
                    sync_count += 1
            session.commit()
        return sync_count
