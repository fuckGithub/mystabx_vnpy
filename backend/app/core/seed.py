"""种子数据应用器：按行幂等 + 外键解析 + 层级递归。

内核不硬编码任何表名、顺序或外键关系；全部由插件通过 ``PluginContext`` 声明。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import MappedBase
from app.core.logger import log
from app.core.plugin.context import SeedSpec

SEED_NATURAL_KEYS: dict[str, str | tuple[str, ...]] = {
    "sys_tenant": "code",
    "sys_menu": ("route_path", "name"),
    "sys_param": "config_key",
    "sys_dept": "code",
    "sys_role": "code",
    "sys_dict_type": "dict_type",
    "sys_dict_data": ("dict_type", "dict_value"),
    "sys_position": "name",
    "sys_user": "username",
    "sys_user_roles": ("user_id", "role_id"),
}
"""``module_system`` 推荐使用的自然键参考表（应用器本身不读取）。

自然键**必须是目标表的真实列**（``_find_existing_id`` 直接 ``getattr(model, key)``），
且必须在首启时具备区分度 —— 含 NULL 的列单独做键会让 ``col IS NULL`` 命中已插入的前
一行：``sys_menu`` 有 135 条按钮行的 ``route_path`` 为 NULL，单用 ``route_path`` 实测
177 行只落 43 行，故补 ``name``；``sys_position`` 模型没有 ``code`` 列，键取 ``name``。
"""


def resolve_model(table: str) -> type | None:
    """按表名找到已注册的 ORM 模型类。

    参数:
    - table (str): ``__tablename__``。

    返回:
    - type | None: 模型类；未注册时返回 ``None``。
    """
    for mapper in MappedBase.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tablename__", None) == table:
            return cls
    return None


def _as_tuple(key: str | tuple[str, ...]) -> tuple[str, ...]:
    """把自然键统一成元组。

    参数:
    - key (str | tuple[str, ...]): 自然键。

    返回:
    - tuple[str, ...]: 字段名元组。
    """
    return (key,) if isinstance(key, str) else key


def _single_pk_column(model: type) -> Any | None:
    """返回模型的单列主键列；复合主键表返回 ``None``。

    应用器不能假定 ``model.id`` 存在：关联表（如 ``sys_user_roles``）只有复合主键
    ``(user_id, role_id)``，无 ``id`` 列，也不能充当父行。

    参数:
    - model (type): 目标模型类。

    返回:
    - Any | None: 单列主键列；复合主键或无主键时返回 ``None``。
    """
    primary_key = sa_inspect(model).primary_key
    return primary_key[0] if len(primary_key) == 1 else None


class SeedApplier:
    """把 ``SeedSpec`` 幂等地写入数据库。"""

    def __init__(self, session: AsyncSession) -> None:
        """初始化。

        参数:
        - session (AsyncSession): 数据库会话。
        """
        self.session = session

    async def apply_all(self, specs: list[SeedSpec]) -> int:
        """按声明顺序应用多份种子。

        参数:
        - specs (list[SeedSpec]): 种子声明列表（顺序即写入顺序）。

        返回:
        - int: 总写入行数。
        """
        total = 0
        for spec in specs:
            total += await self.apply(spec)
        log.info(f"✅ 种子写入完成: 共 {total} 行 / {len(specs)} 份声明")
        return total

    async def apply(self, spec: SeedSpec) -> int:
        """应用一份种子。

        参数:
        - spec (SeedSpec): 种子声明。

        返回:
        - int: 本次实际写入行数。
        """
        model = resolve_model(spec.table)
        if model is None:
            log.warning(f"⚠️ 跳过种子 {spec.table}：未找到对应的 ORM 模型（插件未提供模型？）")
            return 0

        if spec.natural_key is None:
            count = await self.session.scalar(select(func.count()).select_from(model))
            if count:
                log.warning(f"⚠️ 跳过种子 {spec.table}：未声明 natural_key 且表已有 {count} 条记录")
                return 0

        written = 0
        for row in spec.rows:
            written += await self._write_row(model, spec, dict(row))
        # 分子含递归子孙行、分母只数顶层行，故分列标注，避免树形种子打印出
        # 「写入 3 / 1 行」这类误导排障的读数。
        log.info(f"  ↳ {spec.table}: 新增行（含子行）{written} 行 / 顶层行 {len(spec.rows)} 行")
        return written

    async def _write_row(self, model: type, spec: SeedSpec, row: dict[str, Any]) -> int:
        """写入单行（递归处理 children）。

        父行按自然键命中时**不早退**：不插入父行、``written`` 不增，但继续处理其
        ``children``，并以**既有父行主键**作为子行的 ``parent_field``。这样在已有数据
        的库上新增的子行仍能补齐（子行有各自的自然键，逐行判定）。

        子行的 ``parent_field`` **以嵌套位置为权威**：父键一律由嵌套关系下发，且与
        ``parent_field`` 冲突的来源键（如 ``parent_code``）在同一步被剥离，避免
        ``_resolve_relations`` 二次改写父键（静默挂错父行）或整行跳过（子行消失）。

        复合主键表（如关联表 ``sys_user_roles``）没有单值主键：按自然键命中判定存在性，
        插入后不产出 ``parent_id``；因它们也不可能充当父行，故带 ``children`` 的这一
        结构会被拒绝（WARNING，子行整体不写，而不是写成孤儿行）。

        参数:
        - model (type): 目标模型类。
        - spec (SeedSpec): 种子声明。
        - row (dict[str, Any]): 单行数据。

        返回:
        - int: 写入行数（含子行）。
        """
        children = row.pop(spec.children_field, None)

        if not await self._resolve_relations(model, spec, row):
            return 0

        pk_column = _single_pk_column(model)
        exists_already = False
        parent_id: int | None = None
        if spec.natural_key is not None:
            exists_already, parent_id = await self._find_existing(model, spec, row, pk_column)

        if not exists_already:
            # 列过滤只在真要插入时才做：命中既有行的分支会把该行丢弃，过滤纯属白算。
            removed = self._drop_unknown_columns(model, row)
            if "id" in row:
                log.debug(f"  ↳ {spec.table} 忽略显式主键: {row['id']!r}（按自增主键入库）")
            row.pop("id", None)
            if removed:
                log.debug(f"  ↳ {spec.table} 忽略非列字段: {sorted(removed)}")
            obj = model(**row)
            self.session.add(obj)
            await self.session.flush()
            if pk_column is not None:
                parent_id = int(getattr(obj, pk_column.key))
            written = 1
        else:
            log.info(f"  ↳ 跳过已存在行: {spec.table} {self._key_repr(spec, row)}")
            written = 0

        if not children:
            return written
        if parent_id is None:
            log.warning(
                f"⚠️ 种子 {spec.table} 的行含 {spec.children_field}，但该表没有单列主键"
                f"（无法作为父行），已跳过 {len(children)} 个子行"
            )
            return written

        for child in children:
            child = dict(child)
            # 嵌套位置即权威父行，分两步锁死：
            # ① 剥离与 ``parent_field`` 冲突的来源键（``relation.field == parent_field``
            #    的那条，如 ``parent_code``）—— 否则本轮递归的 ``_resolve_relations`` 会拿
            #    它二次改写父键：可解析 ⇒ 静默挂到引用目标；解析不到 ⇒ 整行跳过、子行消失。
            #    剥离后该来源键缺失 ⇒ 走 ``value is None: continue``，父键不再被触碰。
            # ② 无条件下发父键：子行自带的 ``parent_field``（``None``、旧值、或引用解析结果）
            #    一律以嵌套位置的父行为准，否则会出现孤儿行或静默挂错父行。
            # 顺序不可颠倒：若 ``source_field`` 恰好就是 ``parent_field``，先赋值再剥离会把
            # 刚下发的父键删掉。需要跨父引用时，把该行放到顶层 ``rows``，不要放进 ``children``。
            for relation in spec.relations:
                if relation.field == spec.parent_field:
                    child.pop(relation.source_field, None)
            child[spec.parent_field] = parent_id
            written += await self._write_row(model, spec, child)
        return written

    @staticmethod
    def _drop_unknown_columns(model: type, row: dict[str, Any]) -> set[str]:
        """剔除不是模型列的键，避免 ``model(**row)`` 抛 TypeError。

        这同时负责剥离 ``relations`` 的 ``source_field``：当它是真实列时保留
        （如 ``sys_dict_data.dict_type``），否则删除（如 ``sys_user_roles.user_name``）。

        参数:
        - model (type): 目标模型类。
        - row (dict[str, Any]): 单行数据（就地修改）。

        返回:
        - set[str]: 被剔除的键。
        """
        columns = {column.key for column in sa_inspect(model).columns}
        unknown = {key for key in row if key not in columns}
        for key in unknown:
            row.pop(key, None)
        return unknown

    async def _resolve_relations(self, model: type, spec: SeedSpec, row: dict[str, Any]) -> bool:
        """解析并回填外键字段。

        引用键语义（区分「无关系」与「解析失败」）：

        - ``relation.source_field`` **缺失或为 ``None``** ⇒ 本行不涉及此关系（如根部门
          无 ``parent_code``、根菜单显式写 ``parent_code: null``、子行已由父行回填
          ``parent_id``），跳过该条规则，该行照常写入（对应列留空）。
        - 引用键**有值但解析不到** ⇒ 视为脏数据，跳过整行并记 WARNING（fail-safe）。

        参数:
        - model (type): 目标模型类（仅用于日志）。
        - spec (SeedSpec): 种子声明。
        - row (dict[str, Any]): 单行数据（就地修改）。

        返回:
        - bool: ``True`` 表示全部解析成功（含「无关系」）；``False`` 表示应跳过该行。
        """
        for relation in spec.relations:
            value = row.get(relation.source_field)
            if value is None:
                # 源行没给引用键（键缺失，或显式写成 null）⇒ 该行不涉及此关系。
                # 必须按「无关系」而非「解析失败」处理：否则像「根菜单 parent_code: null」
                # 这样的行会被整行丢弃，造成静默数据丢失。
                # 反之，给了键却查不到引用行 ⇒ 视为脏数据，跳过整行（见下方 return False）。
                continue
            ref_model = resolve_model(relation.ref_table)
            if ref_model is None:
                log.warning(f"⚠️ 外键解析失败：引用表 {relation.ref_table} 无模型，跳过该行")
                return False
            ref_id = await self.session.scalar(
                select(ref_model.id).where(getattr(ref_model, relation.ref_key) == value).limit(1)
            )
            if ref_id is None:
                log.warning(
                    f"⚠️ 外键解析失败：{relation.ref_table}.{relation.ref_key}={value!r} 不存在，"
                    f"跳过 {model.__tablename__} 的一行"
                )
                return False
            row[relation.field] = ref_id
        return True

    async def _find_existing(
        self, model: type, spec: SeedSpec, row: dict[str, Any], pk_column: Any | None
    ) -> tuple[bool, int | None]:
        """按自然键查找既有行。

        返回主键（而非布尔值）是为了让父行命中时能继续把既有父行主键传给子行。

        参数:
        - model (type): 目标模型类。
        - spec (SeedSpec): 种子声明。
        - row (dict[str, Any]): 单行数据。
        - pk_column (Any | None): 单列主键列；``None`` 表示复合主键表。

        返回:
        - tuple[bool, int | None]: ``(是否存在, 既有行的单列主键)``；不存在、自然键
          字段缺失时两元素均为假值；复合主键表只判定存在性（第二元素恒为 ``None``）。
        """
        assert spec.natural_key is not None
        conditions = []
        for key in _as_tuple(spec.natural_key):
            if key not in row:
                log.warning(f"⚠️ 种子 {spec.table} 缺少自然键字段 {key!r}，按不存在处理")
                return False, None
            conditions.append(getattr(model, key) == row[key])
        if pk_column is None:
            # 复合主键表（关联表）没有单值主键可回传：只判定"有没有"。
            found_exists = await self.session.scalar(select(exists().where(*conditions)))
            return bool(found_exists), None
        found = await self.session.scalar(select(pk_column).where(*conditions).limit(1))
        if found is None:
            return False, None
        return True, int(found)

    @staticmethod
    def _key_repr(spec: SeedSpec, row: dict[str, Any]) -> str:
        """生成日志用的自然键表示。

        参数:
        - spec (SeedSpec): 种子声明。
        - row (dict[str, Any]): 单行数据。

        返回:
        - str: 形如 ``code=GROUP`` 的字符串。
        """
        if spec.natural_key is None:
            return "?"
        return ", ".join(f"{k}={row.get(k)!r}" for k in _as_tuple(spec.natural_key))
