"""Domain constants for Historical Connection Engine v1."""
from app.db.models.carpet_historical_connection import HistoricalConnectionLevelEnum

HISTORICAL_CONNECTION_VERSION = "historical-connection-v1"
HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS = 6

HISTORICAL_CONNECTION_LEVEL_LABELS = {
    HistoricalConnectionLevelEnum.VERY_CLOSE: "Çok Yakın Görsel Tarihsel Bağlantı",
    HistoricalConnectionLevelEnum.CLOSE: "Yakın Görsel Tarihsel Bağlantı",
    HistoricalConnectionLevelEnum.MODERATE: "Orta Düzey Görsel Tarihsel Bağlantı",
    HistoricalConnectionLevelEnum.LIMITED: "Sınırlı Görsel Tarihsel Bağlantı",
}

DETERMINISTIC_HISTORICAL_DISCLAIMER = (
    "Bu bağlantı yalnızca ölçülen görsel Style DNA yakınlığını ve doğrulanmış tarihsel referans bağlamını gösterir. "
    "Hedef halının kültürünü, dönemini, hanedanını, atölyesini veya özgünlüğünü doğrulamaz."
)

PARTIAL_COVERAGE_NOTE = "Karşılaştırma 9 boyutun tamamına değil, mevcut ölçülebilir boyutlara dayanmaktadır."
