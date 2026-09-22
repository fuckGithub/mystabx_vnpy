import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.events import (
    EVENT_ALL,
    EVENT_ALL_JOBS_REMOVED,
    EVENT_EXECUTOR_ADDED,
    EVENT_EXECUTOR_REMOVED,
    EVENT_JOB_ADDED,
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
    EVENT_JOB_MODIFIED,
    EVENT_JOB_REMOVED,
    EVENT_JOB_SUBMITTED,
    EVENT_JOBSTORE_ADDED,
    EVENT_JOBSTORE_REMOVED,
    EVENT_SCHEDULER_PAUSED,
    EVENT_SCHEDULER_RESUMED,
    EVENT_SCHEDULER_SHUTDOWN,
    EVENT_SCHEDULER_START,
    EVENT_SCHEDULER_STARTED,
    JobEvent,
    JobExecutionEvent,
    JobSubmissionEvent,
    SchedulerEvent,
)
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.job import Job
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from redis.asyncio import Redis

from app.config.setting import settings
from app.core.database import engine
from app.core.logger import log
from app.core.plugin.context import JobSpec
from app.core.plugin.slots import (
    SLOT_CONFIG_PARAMS_PROVIDER,
    SLOT_SCHEDULER_JOB_LOG_SINK,
    get,
)
from app.utils.cron_util import CronUtil

scheduler = AsyncIOScheduler()
scheduler.configure(
    jobstores={
        "default": MemoryJobStore(),
        "sqlalchemy": SQLAlchemyJobStore(url=settings.DB_URI, engine=engine),
        "redis": RedisJobStore(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            username=settings.REDIS_USER,
            password=settings.REDIS_PASSWORD,
            db=int(settings.REDIS_DB_NAME),
        ),
    },
    executors={
        "default": AsyncIOExecutor(),
        "threadpool": ThreadPoolExecutor(max_workers=10),
        "processpool": ProcessPoolExecutor(max_workers=1),
    },
    job_defaults={
        "coalesce": True,
        "max_instances": 5,
    },
    timezone="Asia/Shanghai",
)


class SchedulerUtil:
    """
    定时任务相关方法
    """

    redis_instance: Redis | None = None
    # 临时存储 job_name，用于在 EVENT_JOB_SUBMITTED 时获取
    # 格式可以是: str (任务名称) 或 tuple[str, str] (原任务ID, 任务名称)
    _job_name_cache: dict[str, str | tuple[str, str]] = {}

    @classmethod
    def scheduler_event_listener(cls, event: JobEvent | JobExecutionEvent) -> None:
        """
        监听任务执行事件，记录执行日志；每次执行新建日志行，保留历史。

        参数:
        - event (JobEvent | JobExecutionEvent): APScheduler 事件对象。

        返回:
        - None
        """
        try:
            # 事件处理器映射
            event_handlers: dict[int, Callable] = {
                # 调度器事件
                EVENT_SCHEDULER_STARTED: cls._handle_scheduler_started,
                EVENT_SCHEDULER_START: cls._handle_scheduler_started,
                EVENT_SCHEDULER_SHUTDOWN: cls._handle_scheduler_shutdown,
                EVENT_SCHEDULER_PAUSED: cls._handle_scheduler_paused,
                EVENT_SCHEDULER_RESUMED: cls._handle_scheduler_resumed,
                # 执行器事件
                EVENT_EXECUTOR_ADDED: cls._handle_executor_added,
                EVENT_EXECUTOR_REMOVED: cls._handle_executor_removed,
                # JobStore 事件
                EVENT_JOBSTORE_ADDED: cls._handle_jobstore_added,
                EVENT_JOBSTORE_REMOVED: cls._handle_jobstore_removed,
                EVENT_ALL_JOBS_REMOVED: cls._handle_all_jobs_removed,
                # 任务事件
                EVENT_JOB_ADDED: cls._handle_job_added,
                EVENT_JOB_REMOVED: cls._handle_job_removed,
                EVENT_JOB_MODIFIED: cls._handle_job_modified,
                EVENT_JOB_SUBMITTED: cls._handle_job_submitted,
                EVENT_JOB_EXECUTED: cls._handle_job_executed,
                EVENT_JOB_ERROR: cls._handle_job_error,
                EVENT_JOB_MISSED: cls._handle_job_missed,
                EVENT_JOB_MAX_INSTANCES: cls._handle_job_max_instances,
            }

            # 处理事件
            if event.code in event_handlers:
                handler = event_handlers[event.code]
                handler(event)
            else:
                # 处理其他事件
                cls._handle_other_event(event)

        except Exception as e:
            log.error(f"处理任务执行事件失败: {e!s}", exc_info=True)

    @classmethod
    def _handle_job_submitted(cls, event: JobSubmissionEvent) -> None:
        """
        处理任务提交事件
        """
        job_id = str(event.job_id)
        job = cls.get_job(job_id=job_id)

        if job:
            log.info(f"任务 {job_id} ({job.name}) 已提交执行")

            trigger_type = cls._get_trigger_type(job_id)

            # 周期性任务（cron/interval）：更新 pending 状态为 running
            if trigger_type in ("cron", "interval"):
                cls._update_job_log(
                    job_id=job_id,
                    status="running",
                )
            else:
                # 一次性任务（manual/date）：创建新的 running 状态日志
                cls._create_job_log(
                    job_id=job_id,
                    job_name=job.name,
                    trigger_type=trigger_type,
                    status="running",
                )
        else:
            # 任务可能已经被移除（一次性任务执行完毕后自动移除）
            # 尝试从缓存获取 job_name 和原任务 ID
            cached_value = cls._job_name_cache.pop(job_id, None)
            # 处理新的缓存格式 (原任务ID, 任务名称) 或旧的格式 任务名称
            if isinstance(cached_value, tuple):
                original_job_id, job_name = cached_value
            else:
                original_job_id, job_name = job_id, cached_value

            log.info(f"任务 {job_id} 提交执行，但未找到任务信息（可能已被移除），尝试创建日志")
            result = cls._create_job_log(
                job_id=original_job_id,
                job_name=job_name,
                trigger_type="manual",
                status="running",
            )
            if result:
                log.info(f"任务 {original_job_id} 日志创建成功，id={result}")
            else:
                # 槽位缺失＝设计内降级（module_task 插件缺失），此处只记 WARNING；
                # 真正的写入失败由槽位实现自己记 ERROR 并带堆栈。
                log.warning(
                    f"任务 {original_job_id} 日志未创建（槽位未提供或写入失败），任务执行不受影响"
                )

    @classmethod
    def _handle_job_executed(cls, event: JobExecutionEvent) -> None:
        """
        处理任务执行成功事件
        """
        job_id = str(event.job_id)
        retval = getattr(event, "retval", None)
        scheduled_run_time = getattr(event, "scheduled_run_time", None)

        log.info(f"任务 {job_id} 执行成功")
        if retval:
            log.debug(f"任务 {job_id} 返回值: {retval}")
        if scheduled_run_time:
            log.debug(f"任务 {job_id} 计划执行时间: {scheduled_run_time}")

        # 更新执行日志
        cls._update_latest_job_log(
            job_id=job_id,
            status="success",
            result=str(retval) if retval else None,
        )

        # 为周期性任务创建新的 pending 状态日志，等待下次执行
        job = cls.get_job(job_id=job_id)
        if job:
            trigger_type = cls._get_trigger_type(job_id)
            if trigger_type in ("cron", "interval") and job.next_run_time:
                cls._create_job_log(
                    job_id=job_id,
                    job_name=job.name,
                    trigger_type=trigger_type,
                    status="pending",
                )
                log.debug(f"任务 {job_id} 已创建新的 pending 状态日志，等待下次执行")

    @classmethod
    def _handle_job_error(cls, event: JobExecutionEvent) -> None:
        """
        处理任务执行失败事件
        """
        job_id = str(event.job_id)
        exception = getattr(event, "exception", None)
        traceback = getattr(event, "traceback", None)
        scheduled_run_time = getattr(event, "scheduled_run_time", None)

        log.error(f"任务 {job_id} 执行失败: {exception!s}")
        if traceback:
            log.debug(f"任务 {job_id} 错误堆栈: {traceback}")
        if scheduled_run_time:
            log.debug(f"任务 {job_id} 计划执行时间: {scheduled_run_time}")

        # 更新执行日志
        cls._update_latest_job_log(
            job_id=job_id,
            status="failed",
            result="failed",
            error=str(exception) if exception else "未知错误",
        )

        # 为周期性任务创建新的 pending 状态日志，等待下次执行
        job = cls.get_job(job_id=job_id)
        if job:
            trigger_type = cls._get_trigger_type(job_id)
            if trigger_type in ("cron", "interval") and job.next_run_time:
                cls._create_job_log(
                    job_id=job_id,
                    job_name=job.name,
                    trigger_type=trigger_type,
                    status="pending",
                )
                log.debug(f"任务 {job_id} 已创建新的 pending 状态日志，等待下次执行")

    @classmethod
    def _handle_job_missed(cls, event: JobEvent) -> None:
        """
        处理任务错过执行时间事件
        """
        job_id = str(event.job_id)
        job = cls.get_job(job_id=job_id)

        log.warning(f"任务 {job_id} 错过执行时间")
        if job:
            log.debug(f"任务 {job_id} ({job.name}) 错过执行")

        # 更新执行日志
        cls._update_latest_job_log(
            job_id=job_id,
            status="timeout",
            result="timeout",
            error="任务错过执行时间",
        )

        # 为周期性任务创建新的 pending 状态日志，等待下次执行
        if job:
            trigger_type = cls._get_trigger_type(job_id)
            if trigger_type in ("cron", "interval") and job.next_run_time:
                cls._create_job_log(
                    job_id=job_id,
                    job_name=job.name,
                    trigger_type=trigger_type,
                    status="pending",
                )
                log.debug(f"任务 {job_id} 已创建新的 pending 状态日志，等待下次执行")

    @classmethod
    def _handle_job_removed(cls, event: JobEvent) -> None:
        """
        处理任务被移除事件

        注意：APScheduler 对于一次性任务（DateTrigger）会先触发 JOB_REMOVED，
        然后再触发 JOB_SUBMITTED 和 JOB_EXECUTED。因此：
        - 对于一次性任务，不应该在 JOB_REMOVED 时创建或更新日志
        - 只有周期性任务在移除时才需要更新日志状态
        """
        job_id = str(event.job_id)
        jobstore = getattr(event, "jobstore", "unknown")

        log.info(f"任务 {job_id} 从 {jobstore} 存储器中移除")

        # 检查是否是一次性任务（DateTrigger）
        # 如果任务已经不存在，说明可能是一次性任务执行后被自动移除
        # 这种情况下不需要更新日志，因为 JOB_EXECUTED 会处理
        job = cls.get_job(job_id=job_id)
        if job is None:
            # 任务已经被移除，可能是一次性任务
            # 不需要在这里创建日志，JOB_SUBMITTED 和 JOB_EXECUTED 会处理
            log.debug(f"任务 {job_id} 已从调度器中移除（可能是一次性任务），跳过日志更新")
            return

        # 任务还存在，说明是周期性任务被手动移除
        # 更新执行日志
        cls._update_job_log_on_removed(job_id=job_id)

    @classmethod
    def _handle_job_added(cls, event: JobEvent) -> None:
        """
        处理任务添加事件
        """
        job_id = str(event.job_id)
        jobstore = event.jobstore
        job = cls.get_job(job_id=job_id)

        if job:
            log.info(f"任务 {job_id} ({job.name}) 已添加到 {jobstore} 存储器")

            # 为周期性任务（cron/interval）创建初始的 pending 状态日志
            trigger_type = cls._get_trigger_type(job_id)
            if trigger_type in ("cron", "interval"):
                cls._create_job_log(
                    job_id=job_id,
                    job_name=job.name,
                    trigger_type=trigger_type,
                    status="pending",
                )
                log.debug(f"任务 {job_id} 已创建初始 pending 状态日志")
        else:
            log.info(f"任务 {job_id} 已添加到 {jobstore} 存储器")

    @classmethod
    def _handle_job_modified(cls, event: JobEvent) -> None:
        """
        处理任务修改事件
        """
        job_id = str(event.job_id)
        jobstore = event.jobstore
        job = cls.get_job(job_id=job_id)

        if job:
            log.info(f"任务 {job_id} ({job.name}) 已在 {jobstore} 存储器中修改")
        else:
            log.info(f"任务 {job_id} 已在 {jobstore} 存储器中修改")

    @classmethod
    def _handle_scheduler_started(cls, event: SchedulerEvent) -> None:
        """
        处理调度器启动事件
        """
        log.info("调度器已启动")
        cls._update_scheduler_status("running")

    @classmethod
    def _handle_scheduler_shutdown(cls, event: SchedulerEvent) -> None:
        """
        处理调度器关闭事件
        """
        log.info("调度器已关闭")
        cls._update_scheduler_status("stopped")

    @classmethod
    def _handle_scheduler_paused(cls, event: SchedulerEvent) -> None:
        """
        处理调度器暂停事件
        """
        log.info("调度器已暂停")
        cls._update_scheduler_status("paused")

    @classmethod
    def _handle_scheduler_resumed(cls, event: SchedulerEvent) -> None:
        """
        处理调度器恢复事件
        """
        log.info("调度器已恢复运行")
        cls._update_scheduler_status("running")

    @classmethod
    def _handle_executor_added(cls, event: SchedulerEvent) -> None:
        """
        处理执行器添加事件
        """
        alias = event.alias
        if alias:
            log.info(f"执行器 {alias} 已添加到调度器")
            cls._update_executor_info(alias, "added")
        else:
            log.warning("执行器添加事件，但别名为空")

    @classmethod
    def _handle_executor_removed(cls, event: SchedulerEvent) -> None:
        """
        处理执行器移除事件
        """
        alias = event.alias
        if alias:
            log.info(f"执行器 {alias} 已从调度器中移除")
            cls._update_executor_info(alias, "removed")
        else:
            log.warning("执行器移除事件，但别名为空")

    @classmethod
    def _handle_jobstore_added(cls, event: SchedulerEvent) -> None:
        """
        处理 JobStore 添加事件
        """
        alias = event.alias
        if alias:
            log.info(f"JobStore {alias} 已添加到调度器")
            cls._update_jobstore_info(alias, "added")
        else:
            log.warning("JobStore 添加事件，但别名为空")

    @classmethod
    def _handle_jobstore_removed(cls, event: SchedulerEvent) -> None:
        """
        处理 JobStore 移除事件
        """
        alias = event.alias
        if alias:
            log.info(f"JobStore {alias} 已从调度器中移除")
            cls._update_jobstore_info(alias, "removed")
        else:
            log.warning("JobStore 移除事件，但别名为空")

    @classmethod
    def _handle_all_jobs_removed(cls, event: SchedulerEvent) -> None:
        """
        处理所有任务移除事件
        注意：清空调度器任务不应该清空执行日志，而是将所有 pending 状态的日志更新为 cancelled
        """
        log.info("所有任务已从调度器中移除")
        cls._cancel_all_pending_job_logs()

    @classmethod
    def _handle_job_max_instances(cls, event: JobEvent) -> None:
        """
        处理任务达到最大实例数事件
        """
        job_id = str(event.job_id)
        log.warning(f"任务 {job_id} 已达到最大实例数限制，无法启动新实例")

    @classmethod
    def _handle_other_event(
        cls, event: SchedulerEvent | JobEvent | JobExecutionEvent | JobSubmissionEvent
    ) -> None:
        """
        处理其他事件
        """
        event_code = event.code
        event_type = type(event).__name__
        log.debug(f"收到未处理的事件: {event_type} (code: {event_code})")

    @classmethod
    def _update_scheduler_status(cls, status: str) -> None:
        """
        更新调度器状态到系统参数

        参数:
        - status (str): 调度器状态 (running/stopped/paused)
        """
        try:
            provider = get(SLOT_CONFIG_PARAMS_PROVIDER)
            if provider is None:
                log.debug("参数槽位未提供，跳过调度器状态持久化")
                return
            provider.set_param("scheduler_status", status, "调度器状态")
            log.debug(f"调度器状态已更新: {status}")
        except Exception as e:
            log.error(f"更新调度器状态失败: {e!s}", exc_info=True)

    @classmethod
    def _update_executor_info(cls, alias: str | None, action: str) -> None:
        """
        更新执行器信息到系统参数

        参数:
        - alias (str | None): 执行器别名
        - action (str): 操作 (added/removed)
        """
        if not alias:
            log.warning("执行器别名为空，跳过更新")
            return

        try:
            provider = get(SLOT_CONFIG_PARAMS_PROVIDER)
            if provider is None:
                log.debug("参数槽位未提供，跳过执行器信息持久化")
                return

            key = f"executor_{alias}"
            value = "active" if action == "added" else "inactive"
            provider.set_param(key, value, f"执行器 {alias}")
            log.debug(f"执行器 {alias} 已标记为{value}")
        except Exception as e:
            log.error(f"更新执行器信息失败: {e!s}", exc_info=True)

    @classmethod
    def _update_jobstore_info(cls, alias: str | None, action: str) -> None:
        """
        更新 JobStore 信息到系统参数

        参数:
        - alias (str | None): JobStore 别名
        - action (str): 操作 (added/removed)
        """
        if not alias:
            log.warning("JobStore 别名为空，跳过更新")
            return

        try:
            provider = get(SLOT_CONFIG_PARAMS_PROVIDER)
            if provider is None:
                log.debug("参数槽位未提供，跳过 JobStore 信息持久化")
                return

            key = f"jobstore_{alias}"
            value = "active" if action == "added" else "inactive"
            provider.set_param(key, value, f"JobStore {alias}")
            log.debug(f"JobStore {alias} 已标记为{value}")
        except Exception as e:
            log.error(f"更新 JobStore 信息失败: {e!s}", exc_info=True)

    @classmethod
    def _clear_all_job_logs(cls) -> None:
        """
        清空所有任务日志（仅用于手动清空，不建议使用）
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            log.debug("任务日志槽位未提供，跳过清空")
            return
        sink.clear_all()

    @classmethod
    def _cancel_all_pending_job_logs(cls) -> None:
        """
        将所有 pending 状态的执行日志更新为 cancelled
        用于清空调度器任务时，不删除日志而是更新状态
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            log.debug("任务日志槽位未提供，跳过取消待执行日志")
            return
        sink.cancel_pending()

    @classmethod
    def _get_trigger_type(cls, job_id: str) -> str:
        """
        获取任务的触发类型
        """
        job = cls.get_job(job_id=job_id)
        if not job:
            return "manual"
        trigger = job.trigger
        if isinstance(trigger, CronTrigger):
            return "cron"
        elif isinstance(trigger, IntervalTrigger):
            return "interval"
        elif isinstance(trigger, DateTrigger):
            if trigger.run_date:
                now = datetime.now(trigger.run_date.tzinfo)
                diff = abs((trigger.run_date - now).total_seconds())
                if diff < 60:
                    return "manual"
            return "date"
        return "manual"

    @classmethod
    async def init_scheduler(cls, redis: Redis | None = None) -> None:
        """
        应用启动时初始化定时任务调度器。

        参数:
        - redis (Redis | None): 可选 Redis 实例，供任务侧使用。

        返回:
        - None
        """
        if redis:
            cls.redis_instance = redis
        scheduler.start()
        scheduler.add_listener(cls.scheduler_event_listener, EVENT_ALL)
        scheduler.resume()

    @classmethod
    def _task_wrapper(cls, job_id: str | int, code_block: str | None, *args, **kwargs):
        """
        任务执行包装器，执行自定义代码块（同步版本，用于 ThreadPoolExecutor）

        支持完整的 Python 语法，包括 import 语句
        """
        import types

        def run_sync_handler():
            """
            在独立模块命名空间中执行代码块并调用 handler。

            返回:
            - Any: handler 返回值；无代码块时为 None。
            """
            if not code_block:
                return None

            # 创建一个新的模块作为执行环境
            module = types.ModuleType(f"node_task_{job_id}")
            module.__dict__["__builtins__"] = __builtins__

            # 在模块环境中执行代码
            exec(code_block, module.__dict__)

            # 获取 handler 函数
            handler = module.__dict__.get("handler")
            if handler and callable(handler):
                return handler(*args, **kwargs)
            raise ValueError("代码块必须定义 handler(*args, **kwargs) 函数")

        try:
            result = run_sync_handler()
            return result
        except Exception as e:
            log.error(f"任务 {job_id} 执行失败: {e!s}")
            raise

    @classmethod
    def _get_job_state(cls, job) -> str | None:
        """
        获取任务状态（解析为可读的JSON格式）
        """
        import json
        import pickle

        if not job:
            return None

        state = job.__getstate__()

        def serialize_value(obj):
            """
            将 job state 中的嵌套对象转为可 JSON 化的 Python 结构。

            参数:
            - obj (Any): 任意嵌套对象。

            返回:
            - Any: 标量、dict、list 或简化后的描述。
            """
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, bytes):
                try:
                    decoded = pickle.loads(obj)
                    return serialize_value(decoded)
                except Exception:
                    return obj.decode("utf-8", errors="replace")
            if isinstance(obj, dict):
                return {k: serialize_value(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [serialize_value(item) for item in obj]
            if hasattr(obj, "__dict__"):
                obj_dict = {}
                for k, v in obj.__dict__.items():
                    if not k.startswith("_"):
                        obj_dict[k] = serialize_value(v)
                return {"__class__": obj.__class__.__name__, **obj_dict}
            try:
                return str(obj)
            except Exception:
                return f"<{type(obj).__name__}>"

        parsed_state = serialize_value(state)
        return json.dumps(parsed_state, ensure_ascii=False, indent=2)

    @classmethod
    def get_job_state_from_blob(cls, blob_data: bytes) -> Any:
        """
        从 BLOB 数据反序列化任务状态

        参数:
        - blob_data: apscheduler_jobs 表中的 job_state 字段（BLOB 类型）

        返回:
        - 反序列化后的任务状态
        """
        import pickle

        if not blob_data:
            return None

        def serialize_value(obj: Any) -> Any:
            """
            递归反序列化 BLOB 中的嵌套结构为可 JSON 化数据。

            参数:
            - obj (Any): 节点对象。

            返回:
            - Any: 标量、dict、list 或字符串化结果。
            """
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, bytes):
                try:
                    decoded = pickle.loads(obj)
                    return serialize_value(decoded)
                except Exception:
                    return obj.decode("utf-8", errors="replace")
            if isinstance(obj, dict):
                return {k: serialize_value(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [serialize_value(item) for item in obj]
            if hasattr(obj, "__dict__"):
                obj_dict = {}
                for k, v in obj.__dict__.items():
                    if not k.startswith("_"):
                        obj_dict[k] = serialize_value(v)
                return {"__class__": obj.__class__.__name__, **obj_dict}
            try:
                return str(obj)
            except Exception:
                return f"<{type(obj).__name__}>"

        try:
            state = pickle.loads(blob_data)
            return serialize_value(state)
        except Exception as e:
            return {"error": str(e), "raw_data": str(blob_data[:200])}

    @classmethod
    def _create_job_log(
        cls,
        job_id: str,
        job_name: str | None = None,
        trigger_type: str = "manual",
        status: str = "running",
    ) -> int | None:
        """
        创建执行日志（委托给槽位实现）。

        参数:
        - job_id (str): 任务 ID。
        - job_name (str | None): 任务名称；为空时从调度器任务对象回填。
        - trigger_type (str): 触发方式。
        - status (str): 初始状态。

        返回:
        - int | None: 新日志主键；槽位缺失或写入失败时为 None。
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            # 设计内降级（module_task 插件缺失/未定义 PLUGIN 绑定），不是写入失败：
            # 真正的写入失败由槽位实现自己记 ERROR，调用方只记 WARNING。
            log.debug(f"任务日志槽位未提供，跳过日志创建: job_id={job_id}")
            return None

        job = cls.get_job(job_id=job_id)
        next_run_time = str(job.next_run_time) if job and job.next_run_time else None
        job_state = cls._get_job_state(job) if job else None
        # 没有传入 job_name 时，从调度器任务对象回填（否则日志列表该列会空白）
        if not job_name and job:
            job_name = job.name

        return sink.create(job_id, job_name, trigger_type, status, next_run_time, job_state)

    @classmethod
    def _update_job_log(
        cls, job_id: str, status: str, result: str | None = None, error: str | None = None
    ) -> None:
        """
        更新执行日志（更新该 job_id 最新的 pending 状态日志）
        用于周期性任务在提交执行时将 pending 更新为 running
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            return

        job = cls.get_job(job_id=job_id)
        next_run_time = str(job.next_run_time) if job and job.next_run_time else None
        job_state = cls._get_job_state(job) if job else None
        sink.update_pending(job_id, status, result, error, next_run_time, job_state)

    @classmethod
    def _update_latest_job_log(
        cls, job_id: str, status: str, result: str | None = None, error: str | None = None
    ) -> None:
        """
        更新最新的执行日志（更新该 job_id 最新的一条日志）
        用于每次执行完成后更新状态
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            return

        try:
            job = cls.get_job(job_id=job_id)
            next_run_time = str(job.next_run_time) if job and job.next_run_time else None
            job_state = cls._get_job_state(job) if job else None
            # job_name / trigger_type 会在"无日志可更新、需要补建"时落库，
            # 不传则前端任务日志列表的这两列会空白。
            sink.update_latest(
                job_id,
                status,
                result,
                error,
                next_run_time,
                job_state,
                job_name=job.name if job else None,
                trigger_type=cls._get_trigger_type(job_id) if job else "manual",
            )
        except Exception as e:
            log.error(
                f"更新执行日志失败: job_id={job_id}, status={status}, error={e}", exc_info=True
            )

    @classmethod
    def _update_job_log_on_removed(cls, job_id: str) -> None:
        """
        任务被移除时，更新最新的 pending 或 running 状态日志为 cancelled

        事件触发顺序分析：
        1. 一次性任务（manual/date）：
           - EVENT_JOB_SUBMITTED -> 创建日志（status=running）
           - EVENT_JOB_EXECUTED/ERROR -> 更新日志（status=success/failed）
           - EVENT_JOB_REMOVED -> 日志已更新，不会被标记为 cancelled

        2. 周期性任务（cron/interval）：
           - EVENT_JOB_SUBMITTED -> 创建日志（status=running）
           - EVENT_JOB_EXECUTED/ERROR -> 更新日志（status=success/failed）
           - 下次执行 -> EVENT_JOB_SUBMITTED -> 创建新日志（status=running）
           - EVENT_JOB_REMOVED -> 将 pending/running 标记为 cancelled

        3. 特殊情况：
           - 一次性任务在执行前被删除：running -> cancelled
           - 周期性任务在 pending 状态被删除：pending -> cancelled

        注意：
        - 只有当任务还在 pending 或 running 状态时才更新为 cancelled
        - 如果任务已经执行完成（success/failed/timeout），则不需要更新
        - 如果任务已经标记为 cancelled，则不需要更新
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            return
        sink.on_removed(job_id)

    @classmethod
    def get_job_status(cls, job_id: str | int) -> str:
        """
        获取单个任务的当前状态文案。

        参数:
        - job_id (str | int): 调度器任务 ID。

        返回:
        - str: 运行中 / 暂停中 / 已停止 / 未知 等。
        """
        job = cls.get_job(job_id=str(job_id))
        if not job:
            return "未知"

        # 判断是否暂停：next_run_time 为 None 表示任务已暂停
        if job.next_run_time is None:
            return "暂停中"

        if scheduler.state == 0:
            return "已停止"

        return "运行中"

    @classmethod
    def add_and_run_job_now(cls, job_info: JobSpec) -> Job:
        """
        立即执行任务（加入调度器并尽快触发一次）。

        参数:
        - job_info (JobSpec): 任务配置字典。

        返回:
        - Job: APScheduler Job 对象。
        """
        # 使用稍微延迟的时间，确保事件监听器能够捕获事件
        from datetime import timedelta

        trigger = DateTrigger(run_date=datetime.now() + timedelta(seconds=0.1))
        job = cls._add_job_with_trigger(job_info, trigger)
        # 注意：不需要手动创建执行日志，EVENT_JOB_SUBMITTED 事件会自动创建
        return job

    @classmethod
    def add_cron_job(
        cls,
        job_info: JobSpec,
        trigger_args: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Job:
        """
        创建 Cron 定时任务。

        参数:
        - job_info (JobSpec): 任务信息字典。
        - trigger_args (str | None): Cron 表达式，默认取节点配置。
        - start_date (str | None): 开始时间。
        - end_date (str | None): 结束时间。

        返回:
        - Job: 已注册的 APScheduler Job。
        """
        cron_expr = trigger_args or job_info.get("trigger_args") or job_info.get("cron")
        if not cron_expr:
            raise ValueError("Cron触发器缺少参数")

        fields = cron_expr.strip().split()
        if len(fields) not in (6, 7):
            raise ValueError("无效的 Cron 表达式")
        if not CronUtil.validate_cron_expression(cron_expr):
            raise ValueError(f"Cron表达式不正确: {cron_expr}")

        parsed_fields = [field if field != "?" else "*" for field in fields]
        if len(fields) == 6:
            parsed_fields.append("*")

        second, minute, hour, day, month, day_of_week, year = tuple(parsed_fields)

        if (
            second == "*"
            and minute == "*"
            and hour == "*"
            and day == "*"
            and month == "*"
            and day_of_week in ("*", "?")
        ):
            raise ValueError(
                "Cron表达式不允许每秒执行，请至少指定秒数（如：0 * * * * ? * 表示每分钟执行）"
            )

        trigger = CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            year=year,
            start_date=start_date or job_info.get("start_date"),
            end_date=end_date or job_info.get("end_date"),
            timezone="Asia/Shanghai",
        )
        return cls._add_job_with_trigger(job_info, trigger)

    @classmethod
    def add_interval_job(
        cls,
        job_info: JobSpec,
        trigger_args: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Job:
        """
        创建间隔执行任务。

        参数:
        - job_info (JobSpec): 任务信息字典。
        - trigger_args (str | None): 间隔参数「秒 分 时 天 周」，默认取节点配置。
        - start_date (str | None): 开始时间。
        - end_date (str | None): 结束时间。

        返回:
        - Job: 已注册的 APScheduler Job。
        """
        interval_args = trigger_args or job_info.get("trigger_args") or job_info.get("interval")
        if not interval_args:
            raise ValueError("interval触发器缺少参数")

        resolved_start = start_date or job_info.get("start_date")
        resolved_end = end_date or job_info.get("end_date")

        # 自然形态：int 直接表示秒数（不进下面的 5 字段解析器）。
        # ``bool`` 是 ``int`` 的子类，必须显式排除：``interval=True`` 会被当成「1 秒」
        # 这种没人想要的语义（声明层应是 1 而不是 True），因此直接报错让作者改对类型。
        # 必须在 ``isinstance(..., int)`` 之前拦住：否则 ``bool`` 会落到下面的
        # ``.strip()`` 上（bool 没有 strip），报出的 AttributeError 不指向调用方。
        if isinstance(interval_args, bool):
            raise ValueError("无效的 interval 表达式，格式: 秒 分 时 天 周")

        if isinstance(interval_args, int):
            return cls._add_job_with_trigger(
                job_info,
                IntervalTrigger(
                    seconds=interval_args,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    timezone="Asia/Shanghai",
                ),
            )

        fields = interval_args.strip().split()
        if len(fields) != 5:
            raise ValueError("无效的 interval 表达式，格式: 秒 分 时 天 周")

        second, minute, hour, day, week = tuple(
            int(field) if field != "*" else 0 for field in fields
        )
        trigger = IntervalTrigger(
            weeks=week,
            days=day,
            hours=hour,
            minutes=minute,
            seconds=second,
            start_date=resolved_start,
            end_date=resolved_end,
            timezone="Asia/Shanghai",
        )
        return cls._add_job_with_trigger(job_info, trigger)

    @classmethod
    def add_date_job(cls, job_info: JobSpec, run_date: str | None = None) -> Job:
        """
        创建指定时刻执行一次的任务。

        参数:
        - job_info (JobSpec): 任务信息字典。
        - run_date (str | None): 执行时间字符串，默认取节点 trigger 配置。

        返回:
        - Job: 已注册的 APScheduler Job。
        """
        date_str = run_date or job_info.get("trigger_args") or job_info.get("cron")
        if not date_str:
            raise ValueError("date触发器缺少执行时间参数")

        trigger = DateTrigger(run_date=date_str, timezone="Asia/Shanghai")
        return cls._add_job_with_trigger(job_info, trigger)

    @classmethod
    def _normalize_job_args(cls, raw: Any) -> list[str]:
        """
        把 ``JobSpec.args`` 归一化为位置参数列表，同时接受两种形态。

        参数:
        - raw (Any): ``list``/``tuple``（自然形态）或逗号分隔字符串（数据库文本形态）。

        返回:
        - list[str]: 去除首尾空白后的参数列表；无参数时为 ``[]``。
        """
        if isinstance(raw, (list, tuple)):
            return [str(item).strip() for item in raw if str(item).strip()]

        args_str = str(raw).strip() if raw else ""
        if not args_str:
            return []
        return [arg.strip() for arg in args_str.split(",") if arg.strip()]

    @classmethod
    def _normalize_job_kwargs(cls, raw: Any) -> dict[str, Any]:
        """
        把 ``JobSpec.kwargs`` 归一化为关键字参数字典，同时接受两种形态。

        参数:
        - raw (Any): ``dict``（自然形态）或 JSON 字符串（数据库文本形态）。

        返回:
        - dict[str, Any]: 关键字参数字典；无参数时为 ``{}``。

        异常:
        - ValueError: JSON 文本无法解析，或 JSON 根不是对象（``**`` 只接受映射，
          ``"[]"``/``"1"``/``"null"`` 会在 ``add_job`` 内部以 ``TypeError`` 报错，
          错误信息不指向调用方）。
        """
        if isinstance(raw, dict):
            return dict(raw)

        kwargs_str = str(raw).strip() if raw else ""
        if not kwargs_str:
            return {}
        try:
            parsed = json.loads(kwargs_str)
        except json.JSONDecodeError:
            raise ValueError(f"关键字参数JSON格式无效: {kwargs_str}")
        if not isinstance(parsed, dict):
            raise ValueError(f'关键字参数必须是JSON对象（形如 {{"k": 1}}）: {kwargs_str}')
        return parsed

    @classmethod
    def _add_job_with_trigger(cls, job_info: JobSpec, trigger) -> Job:
        """
        添加任务到调度器（``JobSpec`` 两种取值形态在此统一归一化）

        参数:
        - job_info (JobSpec): 任务定义。
        - trigger (BaseTrigger): 已构建的触发器。

        返回:
        - Job: 已注册的 APScheduler Job。

        异常:
        - ValueError: 代码块/任务 ID/任务名称为空，或关键字参数 JSON 无效。
        """
        code_block = job_info.get("code") or job_info.get("func")
        if not code_block or not str(code_block).strip():
            raise ValueError("任务代码块不能为空")

        # 空值校验放在最前：APScheduler 拿到空 name 会抛 TypeError（信息不指向调用方），
        # 拿到空 id 会静默建出非法任务，两者都应在入口给出明确错误。
        job_id = str(job_info.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("任务ID不能为空")
        job_name = str(job_info.get("job_name") or "").strip()
        if not job_name:
            raise ValueError("任务名称不能为空")

        # jobstore/executor 列均为 nullable=True：键存在但值为 None 时
        # ``.get(k, default)`` 返回的是 None 而不是默认值 —— 必须用 ``or`` 兜底，
        # 否则 executor=None 抛 TypeError，jobstore=None 会调度进"名字叫 None"的存储器，
        # 后续 KeyError: No such job store: None。
        jobstore = job_info.get("jobstore") or "sqlalchemy"
        executor = job_info.get("executor") or "threadpool"
        coalesce = job_info.get("coalesce") or False

        job_args = cls._normalize_job_args(job_info.get("args"))
        job_kwargs = cls._normalize_job_kwargs(job_info.get("kwargs"))

        # 缓存 job_name，用于 EVENT_JOB_SUBMITTED 时获取
        cls._job_name_cache[job_id] = job_name

        try:
            job = scheduler.add_job(
                func=cls._task_wrapper,
                trigger=trigger,
                args=[job_id, code_block, *job_args],
                kwargs=job_kwargs,
                id=job_id,
                name=job_name,
                coalesce=coalesce,
                max_instances=1,
                jobstore=jobstore,
                executor=executor,
            )
            log.info(f"任务 {job_id} 添加到 {jobstore} 存储器成功")
            return job
        except ConflictingIdError:
            scheduler.remove_job(job_id=job_id, jobstore=jobstore)
            job = scheduler.add_job(
                func=cls._task_wrapper,
                trigger=trigger,
                args=[job_id, code_block, *job_args],
                kwargs=job_kwargs,
                id=job_id,
                name=job_name,
                coalesce=coalesce,
                max_instances=1,
                jobstore=jobstore,
                executor=executor,
            )
            log.info(f"任务 {job_id} 已存在，已移除旧任务并重新添加")
            return job

    @classmethod
    def start(cls, paused: bool = False) -> None:
        """
        启动全局调度器。

        参数:
        - paused (bool): 是否以暂停状态启动。

        返回:
        - None
        """
        scheduler.start(paused=paused)

    @classmethod
    async def shutdown(cls, wait: bool = False):
        """
        关闭调度器。

        参数:
        - wait (bool): 是否等待当前任务结束。

        返回:
        - 与 APScheduler shutdown 返回值一致。
        """
        return scheduler.shutdown(wait=wait)

    @classmethod
    def configure(
        cls, gconfig: dict | None = None, prefix: str = "apscheduler.", **options
    ) -> None:
        """
        透传配置底层 APScheduler。

        参数:
        - gconfig (dict | None): 全局配置字典。
        - prefix (str): 配置键前缀。
        - **options: 其它 configure 关键字参数。

        返回:
        - None
        """
        scheduler.configure(gconfig or {}, prefix, **options)

    @classmethod
    def pause(cls) -> None:
        """
        暂停调度器。

        返回:
        - None
        """
        scheduler.pause()

    @classmethod
    def resume(cls) -> None:
        """
        恢复调度器。

        返回:
        - None
        """
        scheduler.resume()

    @classmethod
    def is_running(cls) -> bool:
        """
        调度器是否处于运行态。

        返回:
        - bool: 是否 running。
        """
        return scheduler.running

    @classmethod
    def get_scheduler_state(cls) -> str:
        """
        将调度器内部 state 码映射为中文状态。

        返回:
        - str: 停止 / 运行中 / 暂停 / 未知。
        """
        if scheduler.state == 0:
            return "停止"
        if scheduler.state == 1:
            return "运行中"
        if scheduler.state == 2:
            return "暂停"
        return "未知"

    @classmethod
    def get_job(cls, job_id: str | int, jobstore: str | None = None) -> Job | None:
        """
        按 ID 获取单个任务。

        参数:
        - job_id (str | int): 任务 ID。
        - jobstore (str | None): 存储器别名。

        返回:
        - Job | None: 任务对象或不存在。
        """
        return scheduler.get_job(str(job_id), jobstore)

    @classmethod
    def get_jobs(cls, jobstore: str | None = None) -> list[Job]:
        """
        列出指定存储器中的任务。

        参数:
        - jobstore (str | None): 存储器别名，None 表示默认存储。

        返回:
        - list[Job]: 任务列表。
        """
        return scheduler.get_jobs(jobstore)

    @classmethod
    def get_all_jobs(cls) -> list[Job]:
        """
        列出所有存储器中的任务。

        返回:
        - list[Job]: 任务列表。
        """
        return scheduler.get_jobs()

    @classmethod
    def remove_job(cls, job_id: str | int, jobstore: str | None = None) -> None:
        """
        从调度器移除指定任务。

        参数:
        - job_id (str | int): 任务 ID。
        - jobstore (str | None): 存储器别名。

        返回:
        - None
        """
        scheduler.remove_job(str(job_id), jobstore)

    @classmethod
    def clear_jobs(cls) -> None:
        """
        移除所有存储器中的全部任务。

        返回:
        - None
        """
        scheduler.remove_all_jobs()

    @classmethod
    def print_jobs(cls, jobstore: str | None = None) -> str:
        """
        打印调度器任务信息

        参数:
        - jobstore: 存储器别名，None 表示所有存储器

        返回:
        - str: 格式化的任务信息
        """
        import io

        output = io.StringIO()
        scheduler.print_jobs(jobstore=jobstore, out=output)
        return output.getvalue()

    @classmethod
    def sync_jobs_to_db(cls) -> int:
        """
        将调度器中的任务同步到数据库

        返回:
        - int: 同步的任务数量
        """
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            log.debug("任务日志槽位未提供，跳过同步")
            return 0

        jobs = cls.get_all_jobs()
        jobs_data: list[dict[str, str | None]] = []
        for job in jobs:
            jobs_data.append({
                "job_id": str(job.id),
                "job_name": job.name,
                "trigger_type": cls._get_trigger_type(str(job.id)),
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "job_state": cls._get_job_state(job),
            })

        return sink.sync_jobs(jobs_data)

    @classmethod
    def pause_job(cls, job_id: str | int, jobstore: str | None = None) -> Job | None:
        """
        暂停单个任务。

        参数:
        - job_id (str | int): 任务 ID。
        - jobstore (str | None): 存储器别名。

        返回:
        - Job | None: 暂停后的 Job 或 None。
        """
        return scheduler.pause_job(str(job_id), jobstore)

    @classmethod
    def resume_job(cls, job_id: str | int, jobstore: str | None = None) -> Job | None:
        """
        恢复单个任务。

        参数:
        - job_id (str | int): 任务 ID。
        - jobstore (str | None): 存储器别名。

        返回:
        - Job | None: 恢复后的 Job 或 None。
        """
        return scheduler.resume_job(str(job_id), jobstore)

    @classmethod
    def modify_job(cls, job_id: str | int, jobstore: str | None = None, **changes) -> Job | None:
        """
        修改已存在任务的属性。

        参数:
        - job_id (str | int): 任务 ID。
        - jobstore (str | None): 存储器别名。
        - **changes: 传给 modify_job 的变更字段。

        返回:
        - Job | None: 修改后的 Job 或 None。
        """
        return scheduler.modify_job(str(job_id), jobstore, **changes)

    @classmethod
    def run_job_now(cls, job_id: str | int, jobstore: str | None = None) -> Job | None:
        """
        立即执行任务（通过临时 Job，不修改原任务 trigger）。

        参数:
        - job_id (str | int): 原任务 ID。
        - jobstore (str | None): 存储器别名。

        返回:
        - Job | None: 临时任务对象；原任务不存在时为 None。

        注意:
        - 不改变原任务的触发器配置，仅追加一次性执行。
        """
        job = cls.get_job(job_id=job_id, jobstore=jobstore)
        if not job:
            return None

        # 创建一个新的临时任务 ID
        temp_job_id = f"{job_id}_run_now_{datetime.now().timestamp()}"

        # 缓存 job_name 和原任务 ID，用于 EVENT_JOB_SUBMITTED 时获取
        # 格式: (原任务ID, 任务名称)
        cls._job_name_cache[temp_job_id] = (str(job_id), f"{job.name}(立即执行)")

        # 创建临时任务，延迟 0.1 秒执行，确保事件监听器能够捕获事件
        from datetime import timedelta

        trigger = DateTrigger(
            run_date=datetime.now() + timedelta(seconds=0.1), timezone="Asia/Shanghai"
        )
        temp_job = scheduler.add_job(
            func=job.func,
            trigger=trigger,
            args=job.args,
            kwargs=job.kwargs,
            id=temp_job_id,
            name=f"{job.name}(立即执行)",
            jobstore=jobstore or "default",
            executor=job.executor,
            max_instances=1,
        )

        log.info(f"任务 {job_id} 已触发立即执行，临时任务 ID: {temp_job_id}")
        return temp_job
