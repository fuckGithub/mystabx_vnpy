"""类型诊断（Pyright）与真实调用才暴露的缺陷回归测试。

这些缺陷 **ruff 查不出来** —— 它们不属于任何 lint 规则的表达范围，只有类型诊断或
真实调用才会暴露。因此用测试锁定，防止再次静默回归：

1. ``UploadFileResponse`` 向 ``FileResponse.__init__`` 传了 Starlette 1.6 已移除的
   ``method`` 参数。Python 函数不接收未声明的关键字参数，**构造即 TypeError**，
   导致文件下载接口（``/common/file/download``、``/monitor/resource/download``）
   完全不可用。
2. ``UploadUtil.download_file`` 误用 ``generate_file`` —— 后者是产出**文件内容分片**
   的生成器（``Iterator[bytes]``），不是文件名生成器。于是 ``str(generator)`` 把下载
   文件名变成 ``<generator object ...>``。
3. 承接 2：``download_file`` 是协程，``download_service`` 漏了 ``await``，文件名进一步
   变成 ``<coroutine object ...>``，且协程从未执行。
4. ``SchedulerUtil.add_interval_job`` 未拦 ``bool``。``bool`` 是 ``int`` 子类，原判据
   ``isinstance(x, int) and not isinstance(x, bool)`` 会让 ``bool`` 残留到
   ``.strip()`` 上，抛 ``AttributeError`` 而非预期的 ``ValueError``。
"""

from __future__ import annotations

import asyncio
import inspect

from app.common.response import UploadFileResponse
from app.core.ap_scheduler import SchedulerUtil
from app.core.plugin.context import JobSpec
from app.utils.upload_util import UploadUtil


def _make_file(tmp_path, name: str = "demo.txt"):
    """在临时目录建一个待下载文件。

    参数:
    - tmp_path (Path): pytest 临时目录。
    - name (str): 文件名。

    返回:
    - Path: 文件路径。
    """
    p = tmp_path / name
    p.write_text("hello-download", encoding="utf-8")
    return p


# ------------------------------------------------------------------
#  1. UploadFileResponse 必须可构造（Starlette 无 method 参数）
# ------------------------------------------------------------------


def test_upload_file_response_constructs(tmp_path) -> None:
    """构造不得抛 TypeError（回归：多余的 method=None 关键字参数）。"""
    p = _make_file(tmp_path)
    resp = UploadFileResponse(file_path=str(p), filename=p.name)

    assert resp.status_code == 200
    assert resp.filename == p.name
    assert resp.path == str(p)


def test_upload_file_response_is_attachment(tmp_path) -> None:
    """下载响应必须带 attachment 处置头，文件名可被标准解析还原。"""
    from email.message import Message

    p = _make_file(tmp_path, "报表 2026.txt")
    resp = UploadFileResponse(file_path=str(p), filename=p.name)

    header = resp.headers["content-disposition"]
    assert header.startswith("attachment")

    msg = Message()
    msg["content-disposition"] = header
    assert msg.get_filename() == p.name


# ------------------------------------------------------------------
#  2 & 3. download_file 必须返回文件名，且调用方必须 await
# ------------------------------------------------------------------


def test_download_file_is_coroutine(tmp_path) -> None:
    """返回值必须是协程：漏 await 会把文件名变成 ``<coroutine object ...>``。"""
    p = _make_file(tmp_path)
    coro = UploadUtil.download_file(str(p))
    assert inspect.iscoroutine(coro)
    coro.close()  # 避免 "coroutine was never awaited" 警告


def test_download_file_returns_basename(tmp_path) -> None:
    """await 后必须得到真实文件名，而不是生成器对象的 repr。"""
    p = _make_file(tmp_path, "报表 2026.txt")
    name = asyncio.run(UploadUtil.download_file(str(p)))

    assert name == p.name
    # 回归护栏：既不是 <generator object ...> 也不是 <coroutine object ...>
    assert "object" not in name


# ------------------------------------------------------------------
#  4. interval 触发器的 bool 必须被拒绝
# ------------------------------------------------------------------


def _job_spec(interval: str | int | None) -> JobSpec:
    """构造最小可用的 interval 任务声明。

    参数:
    - interval (str | int | None): ``JobSpec.interval`` 的取值。
      （``bool`` 是其子类型，故 ``_job_spec(True)`` 在类型上合法 —— 这正是
      运行期需要显式拦住 bool 的原因。）

    返回:
    - JobSpec: 任务声明。
    """
    return {
        "job_id": "regression_interval_job",
        "job_name": "回归测试任务",
        "code": "def handler(**kwargs):\n    return None\n",
        "interval": interval,
    }


def test_interval_rejects_true() -> None:
    """``interval=True`` 应报 ValueError，而非在 .strip() 上抛 AttributeError。

    校验在触碰调度器之前完成，因此用例不依赖调度器状态。
    """
    try:
        SchedulerUtil.add_interval_job(_job_spec(True))
    except ValueError as exc:
        assert "interval" in str(exc)
    except AttributeError as exc:  # pragma: no cover - 回归时才会走到
        raise AssertionError(f"bool 泄漏到 .strip()：{exc}") from None
    else:  # pragma: no cover - 回归时才会走到
        raise AssertionError("interval=True 竟然被当成 1 秒接受了")
