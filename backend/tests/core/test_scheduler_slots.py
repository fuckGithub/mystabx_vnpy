"""调度器槽位契约、``JobSpec`` 归一化与插件入口绑定的行为测试。

本文件补齐 Task 14 修复轮发现、此前**无任何测试覆盖**的真实缺陷：

- ``C1``：``module_task/plugin.py`` 未绑定 ``PLUGIN`` → 入口被判不可用 → 槽位永不注入；
- ``C2``：节点调试执行传 ``NodeModel`` 实例（内核按 ``job_info.get(...)`` 取值 →``AttributeError``）；
- ``C3``/``C4``：``JobSpec`` 键集与内核实际读取不一致、取值类型与内核消费方式不匹配；
- ``I1``：``.get(k, default)`` 在「键存在但值为 ``None``」时反转语义（列均可空）；
- ``I2``：空 ``job_id``/``job_name`` 直到 APScheduler 内部才炸；
- ``I3``/``I4``：``JobLogSink`` 契约缺 ``update_pending``/``sync_jobs``/``register``。

调度器是模块级单例：本文件只在测试期间把它的 jobstore 换成内存实现并清理任务，不启动调度器
线程、不连接 MySQL/Redis，也不会 Dispose 真实 jobstore。
"""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core import ap_scheduler
from app.core.ap_scheduler import SchedulerUtil
from app.core.plugin.context import JobSpec
from app.core.plugin.contracts import JobLogSink
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, clear_slots, get

CODE_BLOCK = "def handler(*args, **kwargs):\n    return args, kwargs"
"""可被内核 ``exec`` 的代码块，等价 ``NodeModel.func``。"""

CRON = "0 0 3 * * ?"
"""合法 6 字段 Cron 表达式（秒 分 时 天 月 周）。"""

INTERVAL = "0 0 1 * *"
"""合法 5 字段 interval 参数（秒 分 时 天 周）。"""

RUN_DATE = "2099-01-01 00:00:00"
"""一次性任务的执行时刻（既非 cron 也非 interval 形态，用于验证 date 派发）。"""

KERNEL_SINK_CALLS = {
    "create",
    "update_pending",
    "update_latest",
    "on_removed",
    "clear_all",
    "cancel_pending",
    "sync_jobs",
    "register",
}
"""内核调度器 + 插件运行时实际调用的槽位方法：缺任何一个都是运行期 ``AttributeError``。

契约里还声明了 ``update``（按日志主键更新），当前内核无调用点，属于实现方可选的补充能力。
"""


@pytest.fixture(autouse=True)
def isolated_scheduler_state() -> Iterator[None]:
    """隔离调度器全局态。

    把模块级调度器的 jobstore 临时替换为内存实现（真实实现分别指向 MySQL 与 Redis），
    用完清空任务、``job_name`` 缓存与槽位，避免测试间互相污染。

    注意：测试进程里调度器**不能启动**（``AsyncIOScheduler.start()`` 要求运行中的事件
    循环），故 APScheduler 走的是「STOPPED → 只把待加任务记入 ``_pending_jobs``」分支。
    任务的 args/kwargs/name/coalesce/executor 落在返回的 ``Job`` 上，目标存储器别名落在
    ``_pending_jobs`` 三元组里——两者都是内核真实传给 APScheduler 的值。

    返回:
    - Iterator[None]: 无值 fixture。
    """
    scheduler = ap_scheduler.scheduler
    original_jobstores = dict(scheduler._jobstores)
    scheduler._jobstores = {alias: MemoryJobStore() for alias in original_jobstores}
    try:
        yield
    finally:
        scheduler.remove_all_jobs()
        del scheduler._pending_jobs[:]
        SchedulerUtil._job_name_cache.clear()
        scheduler._jobstores = original_jobstores
        clear_slots()


def _pending_jobstore_alias(job_id: str) -> str | None:
    """读回内核刚交给 APScheduler 的目标存储器别名。

    调度器未启动时 APScheduler 不查 jobstore，只把 ``(job, alias, replace_existing)``
    记入 ``_pending_jobs``（参见 ``BaseScheduler.add_job``）。

    参数:
    - job_id (str): 任务 ID。

    返回:
    - str | None: 存储器别名；任务不在暂存队列时返回 ``None``。
    """
    for job, alias, _ in reversed(ap_scheduler.scheduler._pending_jobs):
        if job.id == job_id:
            return alias
    return None


def test_scheduler_slot_missing_is_safe() -> None:
    """槽位缺失时取到 None，调度器应跳过日志落库而不是崩溃。"""
    clear_slots()
    assert get(SLOT_SCHEDULER_JOB_LOG_SINK) is None


def test_ap_scheduler_has_no_plugin_import() -> None:
    """内核调度器不得 import 插件模型。"""
    text = (
        Path(__file__).resolve().parent.parent.parent / "app" / "core" / "ap_scheduler.py"
    ).read_text(encoding="utf-8")
    assert "app.plugin" not in text
    assert "NodeModel" not in text


def test_add_cron_job_reads_text_form_spec() -> None:
    """数据库文本形态（``NodeModel`` → adapter）：逗号分隔 args 与 JSON kwargs 原样解析。"""
    job = SchedulerUtil.add_cron_job(
        {
            "job_id": "cron-1",
            "job_name": "字符串形态",
            "code": CODE_BLOCK,
            "jobstore": "default",
            "executor": "default",
            "coalesce": True,
            "args": " a , b ",
            "kwargs": '{"k": 1}',
        },
        trigger_args=CRON,
    )

    assert isinstance(job.trigger, CronTrigger)
    assert job.id == "cron-1"
    assert job.name == "字符串形态"
    assert job.coalesce is True
    assert job.executor == "default"
    assert list(job.args) == ["cron-1", CODE_BLOCK, "a", "b"]
    assert job.kwargs == {"k": 1}
    assert _pending_jobstore_alias("cron-1") == "default"


def test_add_interval_job_reads_natural_form_spec() -> None:
    """自然形态（``args`` 列表 / ``kwargs`` 字典）无需先序列化成文本。"""
    job = SchedulerUtil.add_interval_job(
        {
            "job_id": "interval-1",
            "job_name": "自然形态",
            "code": CODE_BLOCK,
            "jobstore": "default",
            "executor": "default",
            "coalesce": False,
            "args": ["x", " y "],
            "kwargs": {"n": 2},
        },
        trigger_args=INTERVAL,
    )

    assert isinstance(job.trigger, IntervalTrigger)
    assert job.trigger.interval == timedelta(hours=1)
    assert list(job.args) == ["interval-1", CODE_BLOCK, "x", "y"]
    assert job.kwargs == {"n": 2}
    assert job.coalesce is False
    assert _pending_jobstore_alias("interval-1") == "default"


def test_add_interval_job_accepts_int_seconds() -> None:
    """``interval`` 为 int 时按秒处理，且**不得**经过 5 字段解析器。"""
    job = SchedulerUtil.add_interval_job({
        "job_id": "interval-2",
        "job_name": "整型秒",
        "code": CODE_BLOCK,
        "jobstore": "default",
        "interval": 90,
    })

    assert isinstance(job.trigger, IntervalTrigger)
    assert job.trigger.interval == timedelta(seconds=90)


def test_null_jobstore_and_executor_fall_back_to_defaults() -> None:
    """列可空：键存在但值为 ``None`` 时必须回退默认值。

    ``.get("jobstore", "sqlalchemy")`` 在值为 None 时返回 None → 调度进「名字叫 None」的
    存储器；``.get("executor", "threadpool")`` 返回 None → ``TypeError``。
    """
    job = SchedulerUtil.add_date_job(
        {
            "job_id": "null-1",
            "job_name": "空值兜底",
            "code": CODE_BLOCK,
            "jobstore": None,
            "executor": None,
            "coalesce": None,
        },
        run_date="2099-01-01 00:00:00",
    )

    assert _pending_jobstore_alias("null-1") == "sqlalchemy"
    assert job.executor == "threadpool"
    assert job.coalesce is False


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ({"job_id": "x", "code": CODE_BLOCK}, "任务名称不能为空"),
        ({"job_id": "x", "job_name": "   ", "code": CODE_BLOCK}, "任务名称不能为空"),
        ({"job_name": "x", "code": CODE_BLOCK}, "任务ID不能为空"),
        ({"job_id": "  ", "job_name": "x", "code": CODE_BLOCK}, "任务ID不能为空"),
        ({"job_id": "x", "job_name": "x"}, "任务代码块不能为空"),
        ({"job_id": "x", "job_name": "x", "code": "   "}, "任务代码块不能为空"),
        (
            {"job_id": "x", "job_name": "x", "code": CODE_BLOCK, "kwargs": "{oops"},
            "关键字参数JSON格式无效",
        ),
    ],
)
def test_invalid_spec_fails_fast_with_clear_message(spec: JobSpec, message: str) -> None:
    """缺 ID/名称/代码块或 kwargs 非法时，给出指向调用方的 ``ValueError``。"""
    with pytest.raises(ValueError) as exc_info:
        SchedulerUtil.add_cron_job(spec, trigger_args=CRON)

    assert message in str(exc_info.value)


def test_job_log_sink_contract_and_impl_cover_every_call_site() -> None:
    """``JobLogSink`` 契约与 ``JobLogSinkImpl`` 都必须覆盖内核/运行时的每个 ``sink.*`` 调用。"""
    app_dir = Path(__file__).resolve().parents[2] / "app"
    call_sites = {
        name
        for rel in ("core/ap_scheduler.py", "core/plugin/runtime.py")
        for name in re.findall(r"sink\.([a-z_]+)\(", (app_dir / rel).read_text(encoding="utf-8"))
    }
    assert call_sites == KERNEL_SINK_CALLS, (
        f"调用点清单变化：{sorted(call_sites ^ KERNEL_SINK_CALLS)}；"
        "新增/删除槽位方法时必须同步更新契约与实现"
    )

    declared = {name for name in dir(JobLogSink) if not name.startswith("_")}
    assert call_sites <= declared, f"契约缺少方法：{sorted(call_sites - declared)}"
    assert "update" in declared, "契约应保留 update（实现方可选能力）"

    from app.plugin.module_task.job_log_sink import JobLogSinkImpl

    impl = JobLogSinkImpl()
    assert isinstance(impl, JobLogSink), "JobLogSinkImpl 未满足 JobLogSink 契约"
    implemented = {name for name in dir(impl) if not name.startswith("_")}
    assert call_sites <= implemented, f"实现缺少方法：{sorted(call_sites - implemented)}"
    assert inspect.iscoroutinefunction(impl.register), (
        "runtime 以 await sink.register(job) 调用，register 必须是协程"
    )


def test_job_log_sink_register_delegates_to_scheduler() -> None:
    """``register`` 把插件声明的任务真正交给内核调度器（按触发器键分派）。"""
    from app.plugin.module_task.job_log_sink import JobLogSinkImpl

    sink = JobLogSinkImpl()

    async def _register_all() -> None:
        await sink.register({
            "job_id": "reg-cron",
            "job_name": "注册 cron",
            "code": CODE_BLOCK,
            "jobstore": "default",
            "cron": CRON,
        })
        await sink.register({
            "job_id": "reg-interval",
            "job_name": "注册 interval",
            "code": CODE_BLOCK,
            "jobstore": "default",
            "interval": 30,
        })

    asyncio.run(_register_all())

    pending = {job.id: job for job, _, _ in ap_scheduler.scheduler._pending_jobs}
    assert isinstance(pending["reg-cron"].trigger, CronTrigger)
    assert isinstance(pending["reg-interval"].trigger, IntervalTrigger)
    assert pending["reg-interval"].trigger.interval == timedelta(seconds=30)

    # 既无 interval 也无 cron/trigger_args：无法确定调度方式，必须显式失败而不是静默跳过
    with pytest.raises(ValueError):
        asyncio.run(
            sink.register({
                "job_id": "reg-none",
                "job_name": "无触发器",
                "code": CODE_BLOCK,
                "jobstore": "default",
            })
        )


@pytest.mark.parametrize(
    ("spec", "expected_kind", "expected_interval"),
    [
        pytest.param(
            {
                "job_id": "d1",
                "job_name": "显式 cron",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger": "cron",
                "trigger_args": CRON,
            },
            "cron",
            None,
            id="显式trigger-cron",
        ),
        pytest.param(
            {
                "job_id": "d2",
                "job_name": "显式 interval（5 字段）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger": "interval",
                "interval": INTERVAL,
            },
            "interval",
            timedelta(hours=1),
            id="显式trigger-interval-五字段",
        ),
        pytest.param(
            {
                "job_id": "d3",
                "job_name": "显式 interval（整数秒）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger": "interval",
                "interval": 30,
            },
            "interval",
            timedelta(seconds=30),
            id="显式trigger-interval-整数秒",
        ),
        pytest.param(
            {
                "job_id": "d4",
                "job_name": "显式 date",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger": "date",
                "trigger_args": RUN_DATE,
            },
            "date",
            None,
            id="显式trigger-date",
        ),
        pytest.param(
            {
                "job_id": "d5",
                "job_name": "推断 cron（cron 键）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "cron": CRON,
            },
            "cron",
            None,
            id="推断-cron键",
        ),
        pytest.param(
            {
                "job_id": "d6",
                "job_name": "推断 cron（trigger_args 6 字段）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger_args": CRON,
            },
            "cron",
            None,
            id="推断-trigger_args六字段",
        ),
        pytest.param(
            {
                "job_id": "d7",
                "job_name": "推断 interval（整数秒）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "interval": 30,
            },
            "interval",
            timedelta(seconds=30),
            id="推断-interval整数秒",
        ),
        pytest.param(
            {
                "job_id": "d8",
                "job_name": "推断 interval（trigger_args 5 字段）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger_args": INTERVAL,
            },
            "interval",
            timedelta(hours=1),
            id="推断-trigger_args五字段",
        ),
        pytest.param(
            {
                "job_id": "d9",
                "job_name": "推断 date（trigger_args 时间串）",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "trigger_args": RUN_DATE,
            },
            "date",
            None,
            id="推断-trigger_args时间串",
        ),
        pytest.param(
            {
                "job_id": "d10",
                "job_name": "interval 与 trigger_args 共存",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "executor": "default",
                "interval": 30,
                "trigger_args": CRON,
            },
            "cron",
            None,
            id="共存-interval与trigger_args",
        ),
    ],
)
def test_job_log_sink_register_dispatch_matrix(
    spec: JobSpec, expected_kind: str, expected_interval: timedelta | None
) -> None:
    """``I-NEW-1`` 守卫：``register`` 必须派发到正确的内核 ``add_*_job``。

    覆盖三条触发路径（cron/interval/date）× 显式 ``trigger`` 与推断两种来源，其中修复前必然
    失败的三类是：``trigger_args`` 为 5 字段 interval（旧代码送进 Cron 解析器）、
    ``trigger_args`` 为日期串（旧代码送进 Cron 解析器，无 date 分支）、
    ``interval`` 与 ``trigger_args`` 共存（旧代码按 interval 派发，但内核读的是
    ``trigger_args``）。

    断言落在**真实注册结果**上（APScheduler 任务的触发器类型与参数），而不是「调了哪个
    方法」，这样派发错分支（如 interval 参数被当成 cron 表达式）一样会炸出来。
    """
    from app.plugin.module_task.job_log_sink import JobLogSinkImpl

    asyncio.run(JobLogSinkImpl().register(spec))

    pending = {job.id: job for job, _, _ in ap_scheduler.scheduler._pending_jobs}
    job_id = str(spec.get("job_id"))
    assert job_id in pending, f"{job_id} 未注册进调度器（静默跳过？）"

    trigger = pending[job_id].trigger
    kind_by_type = {CronTrigger: "cron", IntervalTrigger: "interval", DateTrigger: "date"}
    assert kind_by_type[type(trigger)] == expected_kind, (
        f"{job_id} 派发到 {type(trigger).__name__}，期望 {expected_kind}"
    )
    if expected_interval is not None:
        assert trigger.interval == expected_interval, (
            f"{job_id} 的间隔参数取错（{trigger.interval} != {expected_interval}）"
        )


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        pytest.param(
            {
                "job_id": "f1",
                "job_name": "无触发器键",
                "code": CODE_BLOCK,
                "jobstore": "default",
            },
            "缺少触发器配置",
            id="无任何触发器键",
        ),
        pytest.param(
            {
                "job_id": "f2",
                "job_name": "trigger 非法",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "trigger": "daily",
                "cron": CRON,
            },
            "无效的 trigger 取值",
            id="trigger取值非法",
        ),
        pytest.param(
            {
                "job_id": "f3",
                "job_name": "显式 cron 无参数",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "trigger": "cron",
            },
            "Cron触发器缺少参数",
            id="显式cron缺参数",
        ),
        pytest.param(
            {
                "job_id": "f4",
                "job_name": "显式 interval 无参数",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "trigger": "interval",
            },
            "interval触发器缺少参数",
            id="显式interval缺参数",
        ),
        pytest.param(
            {
                "job_id": "f5",
                "job_name": "显式 date 无时间",
                "code": CODE_BLOCK,
                "jobstore": "default",
                "trigger": "date",
            },
            "date触发器缺少执行时间参数",
            id="显式date缺时间",
        ),
    ],
)
def test_job_log_sink_register_unresolvable_trigger_fails_loudly(
    spec: JobSpec, message: str
) -> None:
    """触发器类型或参数无法确定时必须显式报错，绝不静默跳过（否则任务永不执行且无人察觉）。"""
    from app.plugin.module_task.job_log_sink import JobLogSinkImpl

    with pytest.raises(ValueError) as exc_info:
        asyncio.run(JobLogSinkImpl().register(spec))

    assert message in str(exc_info.value), f"错误信息不可行动：{exc_info.value}"


class _NodeStandIn:
    """``NodeModel`` 属性级替身（只覆盖适配器真正读取的字段）。

    不实例化真实 ``NodeModel``：那会触发 SQLAlchemy mapper 配置，而它引用的 ``UserModel``
    定义在尚未迁入 `app/plugin` 的 ``app/api/v1/module_system``（且该包存在既有导入顺序问题）。
    适配器只做属性读取，替身足以覆盖 ``func → code`` 的映射语义。
    """

    def __init__(self, **fields: object) -> None:
        """按属性名写入字段。

        参数:
        - **fields (object): 模型字段。

        返回:
        - None
        """
        self.__dict__.update(fields)


def test_node_adapter_maps_func_to_code_and_feeds_kernel() -> None:
    """``C2``/``C5``：``NodeModel`` → ``JobSpec`` 适配器。

    - 内核按 ``job_info.get(...)`` 取值，直接传 ORM 实例会 ``AttributeError``（调试执行 500）；
    - spec 的 ``code`` 必须是**代码块**（``NodeModel.func``），**不是**节点编码
      （``NodeModel.code``）——否则调度器会把节点编码当 Python 代码 ``exec``。
    """
    from app.plugin.module_task.cronjob.node.service import node_to_job_spec

    node = _NodeStandIn(
        id=7,
        name="节点",
        code="node_code_1",  # 节点编码：String(32), unique
        func=CODE_BLOCK,  # 代码块：Text —— spec.code 必须取这个
        jobstore="default",
        executor="default",
        coalesce=False,
        trigger_args=CRON,
        args=None,
        kwargs=None,
        start_date=None,
        end_date=None,
    )

    spec = node_to_job_spec(node)  # type: ignore[arg-type] - 见替身说明
    # 替身用 __dict__ 动态挂字段，静态分析看不到属性；spec 的键又是 NotRequired，
    # 故两边都走 getter 访问。
    assert spec.get("code") == CODE_BLOCK
    assert spec.get("code") != getattr(node, "code")

    job = SchedulerUtil.add_cron_job(spec, trigger_args=CRON)

    assert job.id == "7"
    assert job.name == "节点"
    assert list(job.args) == ["7", CODE_BLOCK]


def test_task_plugin_entry_injects_job_log_sink_slot() -> None:
    """``C1`` 守卫：``module_task`` 入口必须绑定模块级 ``PLUGIN``，否则槽位永不注入。"""
    from app.core.plugin.base import PluginBase
    from app.core.plugin.runtime import PluginRuntime
    from app.plugin.module_task import plugin as task_plugin

    assert isinstance(task_plugin.PLUGIN, PluginBase), (
        "plugin.py 缺少模块级 PLUGIN = Plugin() 绑定：runtime 会判定入口不可用，"
        "setup()/start() 都不执行，scheduler.job_log_sink 槽位永不注入（日志静默丢失）"
    )

    clear_slots()
    runtime = PluginRuntime().discover_and_setup(names={"task"})
    entries = {entry.plugin_dir.name: entry for entry in runtime.registry.entries}
    entry = entries["task"]
    assert entry.instance is not None, "task 插件被降级为无实例（入口未能通过 PLUGIN 绑定加载）"

    # setup() 只收集注册项（不触达数据库），槽位在 start() 阶段注入
    assert get(SLOT_SCHEDULER_JOB_LOG_SINK) is None
    asyncio.run(entry.instance.start())
    assert get(SLOT_SCHEDULER_JOB_LOG_SINK) is not None
