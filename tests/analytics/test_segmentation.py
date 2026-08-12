import pandas as pd

from src.analytics.segmentation import assign_rfm_segments, score_recency


def test_score_recency_gives_recent_customer_a_higher_score():
    scores = score_recency(pd.Series([10, 100, 300]))

    assert scores.tolist() == [4, 3, 1]


def test_assign_rfm_segments_marks_recent_repeat_high_spender_as_high_value():
    frame = pd.DataFrame(
        {
            "customer_key": [1, 2, 3],
            "last_purchase_at": [
                pd.Timestamp("2018-08-20"),
                pd.Timestamp("2018-02-01"),
                pd.Timestamp("2016-10-20"),
            ],
            "frequency_orders": [2, 1, 1],
            "monetary_item_revenue": [300.0, 100.0, 20.0],
        }
    )

    result = assign_rfm_segments(frame, as_of_date=pd.Timestamp("2018-08-29"))

    assert result.loc[0, "recency_days"] == 9
    assert result.loc[0, "customer_segment"] == "high_value"
