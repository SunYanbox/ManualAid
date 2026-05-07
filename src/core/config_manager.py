"""配置管理器 - 统一管理应用程序配置."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, ClassVar

from src.core.database_manager import DatabaseManager

# 默认环境变量配置(与 .env.example 保持一致)
DEFAULT_ENVS = {
    "TOOL_MAX_DOC_LENGTH": {"value": "360", "description": "工具文档最大长度(字符数)"},
    "TOOL_MAX_FUNC_NAME_LENGTH": {"value": "80", "description": "函数名最大长度(字符数)"},
    "TOOL_MAX_RESULT_LENGTH": {"value": "30000", "description": "结果输出最大长度(字符数)"},
    "TOOL_LIST_TRUNCATE_THRESHOLD": {"value": "100", "description": "列表截断阈值(项目数量上限)"},
    "TOOL_DICT_TRUNCATE_THRESHOLD": {"value": "100", "description": "字典截断阈值(键值对数量上限)"},
    "RESULT_EXPIRE_MINUTES": {"value": "5", "description": "结果过期时间(分钟)"},
    "RESULT_CLEANUP_MINUTES": {"value": "15", "description": "清理任务间隔时间(分钟)"},
    "MANUALAID_AUTO_COPY": {"value": "true", "description": "是否自动复制结果(支持 true/false/yes/no/on/off)"},
    "SESSION_UPDATE_INTERVAL": {"value": "30", "description": "会话持续时间持久化间隔(秒)"},
    "SESSION_FLAG_CHECK_INTERVAL": {"value": "5", "description": "会话标志检查间隔(秒)"},
}

# 默认配置值
DEFAULTS: dict[str, Any] = {
    # Skill 配置
    "skills.disabled": [],
    # 通用配置
    "general.theme": "dark",
    "general.log_level": "INFO",
}

for __k, __v in DEFAULT_ENVS.items():
    DEFAULTS[f"env.{__k}"] = __v


def _parse_value(value: str) -> Any:
    """解析配置值.

    尝试解析为 JSON,失败则返回原始字符串.

    Args:
        value: 原始字符串值

    Returns:
        解析后的值
    """
    try:
        return json.loads(value)
    except json.JSONDecodeError, TypeError:
        return value


def _serialize_value(value: Any) -> str:
    """序列化配置值.

    Args:
        value: 配置值

    Returns:
        序列化后的字符串
    """
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


class ConfigManager:
    """配置管理器(单例模式).

    提供统一的配置访问接口,支持多种配置类型:
    - 环境变量配置
    - Skill 配置
    - 通用配置
    """

    _instance: ClassVar[ConfigManager | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> ConfigManager:
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._db: DatabaseManager | None = None
        self._cache: dict[str, Any] = {}
        self._initialized = True

    def initialize(self, workspace_root: Path) -> None:
        """初始化配置管理器.

        Args:
            workspace_root: 工作区根目录
        """
        self._db = DatabaseManager(str(workspace_root))
        self._cache.clear()
        self._load_from_db()

    def _load_from_db(self) -> None:
        """从数据库加载所有配置到缓存."""
        if self._db is None:
            return

        rows = self._db.get_all_config()
        for key, value, _category, _updated_at in rows:
            self._cache[key] = _parse_value(value)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值.

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        # 优先从缓存读取
        if key in self._cache:
            return self._cache[key]

        # 尝试从默认值获取
        if key in DEFAULTS:
            return DEFAULTS[key]

        return default

    def set(self, key: str, value: Any, category: str = "general") -> None:
        """设置配置值.

        Args:
            key: 配置键
            value: 配置值
            category: 配置类别
        """
        serialized = _serialize_value(value)
        self._cache[key] = value

        if self._db:
            self._db.set_config(key, serialized, category)

    def delete(self, key: str) -> None:
        """删除配置值.

        Args:
            key: 配置键
        """
        if key in self._cache:
            del self._cache[key]

        if self._db:
            self._db.delete_config(key)

    def get_category(self, category: str) -> dict[str, Any]:
        """获取指定类别的所有配置.

        Args:
            category: 配置类别

        Returns:
            配置字典
        """
        if self._db is None:
            return {}

        rows = self._db.get_all_config(category)
        return {row[0]: _parse_value(row[1]) for row in rows}

    def get_env_configs(self) -> dict[str, str]:
        """获取所有环境变量配置.

        Returns:
            环境变量配置字典
        """
        return {k[4:]: v for k, v in self._cache.items() if k.startswith("env.")}

    def set_env_config(self, key: str, value: str) -> None:
        """设置环境变量配置.

        Args:
            key: 环境变量名(不含 env. 前缀)
            value: 配置值
        """
        self.set(f"env.{key}", value, category="env")

    def get_env_config(self, key: str, default: str = "") -> str:
        """获取环境变量配置.

        Args:
            key: 环境变量名(不含 env. 前缀)
            default: 默认值

        Returns:
            配置值
        """
        return str(self.get(f"env.{key}", default))

    def apply_env_configs(self) -> None:
        """应用环境变量配置到 os.environ."""
        import os

        env_configs = self.get_env_configs()
        for key, value in env_configs.items():
            if value:  # 只设置非空值
                os.environ[key] = str(value)

    # -- Skill 配置快捷方法 --

    def get_disabled_skills(self) -> set[str]:
        """获取禁用的 Skill 列表.

        Returns:
            禁用的 Skill 名称集合
        """
        if self._db:
            return self._db.get_disabled_skills()
        return set()

    def set_disabled_skills(self, *names: str) -> None:
        """设置禁用的 Skill 列表.

        Args:
            names: 禁用的 Skill 名称集合
        """
        if self._db:
            self._db.set_disabled_skills(*names)

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例(用于测试)."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance._cache.clear()
                cls._instance._db = None
                cls._instance = None
