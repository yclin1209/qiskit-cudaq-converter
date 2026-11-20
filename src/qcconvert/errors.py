"""轉換錯誤（conversion errors）。"""


class ConversionError(Exception):
    """無法轉換輸入。"""


class UnsupportedFeatureError(ConversionError):
    """不支援的電路建構。"""
