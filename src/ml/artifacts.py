"""Write auditable persistence artifacts for a selected repurchase model."""

import json
from pathlib import Path

import joblib
import pandas as pd

from src.ml.calibration import SigmoidCalibrator
from src.ml.train import FEATURE_COLUMNS, TrainingResult

FEATURE_MEANINGS = {
    "first_order_item_count": "首笔订单商品件数",
    "first_order_item_revenue": "首笔订单商品金额",
    "first_order_freight_revenue": "首笔订单运费金额",
    "first_order_payment_value": "首笔订单支付金额",
    "first_order_delivery_days": "首笔订单配送时长（天）",
    "first_order_distinct_category_count": "首笔订单商品品类数",
}

FORBIDDEN_FUTURE_FIELDS = [
    "repurchased_within_90d",
    "future_order_count",
    "future_order_item_revenue",
    "future_order_payment_value",
    "future_order_delivered_customer_date",
]

_REPRESENTATIVE_ID_TIME_COLUMNS = (
    "customer_key",
    "customer_unique_id",
    "customer_id",
    "order_id",
    "prediction_time",
)
_REPRESENTATIVE_CUSTOMER_IDENTIFIER_COLUMNS = (
    "customer_key",
    "customer_unique_id",
)
_REPRESENTATIVE_PROBABILITY_COLUMNS = (
    "raw_probability",
    "calibrated_probability",
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _representative_columns(frame: pd.DataFrame) -> list[str]:
    allowed = (
        *_REPRESENTATIVE_ID_TIME_COLUMNS,
        *FEATURE_COLUMNS,
        *_REPRESENTATIVE_PROBABILITY_COLUMNS,
    )
    return [column for column in allowed if column in frame.columns]


def _validate_representative_customer_identifier(frame: pd.DataFrame) -> None:
    if not any(
        column in frame.columns
        for column in _REPRESENTATIVE_CUSTOMER_IDENTIFIER_COLUMNS
    ):
        raise ValueError(
            "representative_predictions must include a customer identifier"
        )


def _model_card(selected_name: str, metrics: dict[str, object]) -> str:
    metric_summary = json.dumps(metrics, ensure_ascii=False, indent=2, default=str)
    return f"""# 复购预测模型卡

## 样本

模型样本仅使用首笔已送达订单，并在该订单送达时刻构造可观测特征。

## 时间切分与校准

数据按时间严格划分为训练、模型选择、独立校准和最终测试四个时间段；概率校准仅在独立校准时间段完成。

## 模型选择

本次选定模型为 `{selected_name}`，以模型选择时间段上的 PR-AUC 与 Lift@10% 为依据，不使用最终测试集参与选择。

## 最终测试

最终测试集只用于一次性报告泛化表现，记录的指标如下：

```json
{metric_summary}
```

## 局限性

该模型用于复购排序支持，不构成因果推断，也不能替代业务实验。特征重要性反映关联而非因果关系。
"""


def write_training_artifacts(
    output_dir: Path,
    selected_name: str,
    selected_result: TrainingResult,
    calibrator: SigmoidCalibrator,
    metrics: dict[str, object],
    representative_predictions: pd.DataFrame,
) -> None:
    """Persist the selected pipeline and its Chinese-language audit evidence."""
    _validate_representative_customer_identifier(representative_predictions)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": selected_result.model,
            "calibrator": calibrator,
            "selected_name": selected_name,
            "feature_columns": list(FEATURE_COLUMNS),
        },
        output_dir / "repurchase_pipeline.joblib",
    )
    _write_json(
        output_dir / "feature_schema.json",
        {
            "feature_columns": list(FEATURE_COLUMNS),
            "feature_meanings": FEATURE_MEANINGS,
            "prediction_time_rule": "首笔已送达订单的送达时间",
            "label_rule": "90天内是否存在后续已送达订单",
            "forbidden_future_fields": FORBIDDEN_FUTURE_FIELDS,
        },
    )
    _write_json(output_dir / "metrics.json", metrics)
    representative_predictions.loc[:, _representative_columns(
        representative_predictions
    )].to_json(
        output_dir / "representative_predictions.json",
        orient="records",
        force_ascii=False,
        indent=2,
        date_format="iso",
    )
    (output_dir / "model_card.md").write_text(
        _model_card(selected_name, metrics), encoding="utf-8"
    )
