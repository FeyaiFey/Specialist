import yaml
from typing import Any, Dict

def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    从YAML文件加载配置
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        Dict[str, Any]: 配置字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise Exception(f"加载YAML文件失败: {e}")