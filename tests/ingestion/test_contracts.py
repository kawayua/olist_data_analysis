from src.ingestion.contracts import get_contract, required_filenames


def test_orders_contract_declares_primary_key_and_required_columns():
    contract = get_contract("orders")

    assert contract.primary_key == ("order_id",)
    assert {"order_id", "customer_id", "order_status"} <= set(contract.columns)


def test_all_nine_source_files_are_declared():
    filenames = required_filenames()

    assert len(filenames) == 9
    assert "olist_orders_dataset.csv" in filenames
    assert "olist_customers_dataset.csv" in filenames
