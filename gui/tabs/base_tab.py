# gui/tabs/base_tab.py
from PySide6.QtWidgets import QWidget

class BaseTab(QWidget):
    """
    选项卡的基类。
    定义了所有选项卡的通用行为，例如加载和保存配置的方法。
    """
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager # 传递配置管理器实例

    def load_config(self):
        """
        从配置管理器加载配置到UI。
        子类应重写此方法以实现特定逻辑。
        """
        raise NotImplementedError("Subclasses must implement load_config")

    def save_config(self):
        """
        从UI保存配置到配置管理器。
        子类应重写此方法以实现特定逻辑。
        """
        raise NotImplementedError("Subclasses must implement save_config")