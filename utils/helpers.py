import os
import shutil
import json
import yaml
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载YAML文件
    Args:
        file_path: YAML文件路径
    Returns:
        YAML文件内容
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    保存数据到YAML文件
    Args:
        data: 要保存的数据
        file_path: YAML文件路径
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True)

def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载JSON文件
    Args:
        file_path: JSON文件路径
    Returns:
        JSON文件内容
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    保存数据到JSON文件
    Args:
        data: 要保存的数据
        file_path: JSON文件路径
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """
    计算文件哈希值
    Args:
        file_path: 文件路径
        algorithm: 哈希算法（md5/sha1/sha256）
    Returns:
        文件哈希值
    """
    hash_obj = getattr(hashlib, algorithm)()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def ensure_dir(directory: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    Args:
        directory: 目录路径
    Returns:
        目录Path对象
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def clean_dir(directory: Union[str, Path], pattern: str = '*') -> None:
    """
    清理目录中的文件
    Args:
        directory: 目录路径
        pattern: 文件匹配模式
    """
    path = Path(directory)
    for item in path.glob(pattern):
        if item.is_file():
            item.unlink()

def get_timestamp(dt: Optional[datetime.datetime] = None) -> str:
    """
    获取时间戳字符串
    Args:
        dt: datetime对象，默认为当前时间
    Returns:
        格式化的时间戳字符串
    """
    if dt is None:
        dt = datetime.datetime.now()
    return dt.strftime('%Y%m%d_%H%M%S')

def format_size(size_in_bytes: int) -> str:
    """
    格式化文件大小
    Args:
        size_in_bytes: 文件大小（字节）
    Returns:
        格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f}{unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f}PB"

def get_env_var(key: str, default: Optional[str] = None) -> str:
    """
    获取环境变量值
    Args:
        key: 环境变量名
        default: 默认值
    Returns:
        环境变量值
    Raises:
        ValueError: 如果环境变量不存在且没有提供默认值
    """
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is not set")
    return value

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    将嵌套字典展平为单层字典
    Args:
        d: 要展平的字典
        parent_key: 父键
        sep: 键的分隔符
    Returns:
        展平后的字典
    """
    items: List = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def unflatten_dict(d: Dict[str, Any], sep: str = '.') -> Dict[str, Any]:
    """
    将展平的字典还原为嵌套字典
    Args:
        d: 展平的字典
        sep: 键的分隔符
    Returns:
        嵌套字典
    """
    result: Dict[str, Any] = {}
    for key, value in d.items():
        parts = key.split(sep)
        target = result
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return result

def move_file(src_path: Union[str, Path], dst_path: Union[str, Path]) -> bool:
    """
    移动文件(剪切操作)
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径,若目标路径已存在同名文件则覆盖
    """
    try:
        src_path = Path(src_path)
        dst_path = Path(dst_path)
        if src_path.exists():
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
        # 如果目标文件存在则先删除
        if dst_path.exists():
            dst_path.unlink()
        # 移动文件
        shutil.move(str(src_path), str(dst_path))
        return True
    except Exception as e:
        return False

