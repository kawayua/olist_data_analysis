from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetContract:
    """Structural contract for one Olist source CSV file."""

    name: str
    filename: str
    primary_key: tuple[str, ...]
    columns: tuple[str, ...]


CONTRACTS: dict[str, DatasetContract] = {
    "customers": DatasetContract(
        name="customers",
        filename="olist_customers_dataset.csv",
        primary_key=("customer_id",),
        columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
    ),
    "orders": DatasetContract(
        name="orders",
        filename="olist_orders_dataset.csv",
        primary_key=("order_id",),
        columns=(
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    "order_items": DatasetContract(
        name="order_items",
        filename="olist_order_items_dataset.csv",
        primary_key=("order_id", "order_item_id"),
        columns=(
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
    ),
    "payments": DatasetContract(
        name="payments",
        filename="olist_order_payments_dataset.csv",
        primary_key=("order_id", "payment_sequential"),
        columns=(
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
    ),
    "reviews": DatasetContract(
        name="reviews",
        filename="olist_order_reviews_dataset.csv",
        primary_key=("review_id", "order_id"),
        columns=(
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
    ),
    "products": DatasetContract(
        name="products",
        filename="olist_products_dataset.csv",
        primary_key=("product_id",),
        columns=(
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    "sellers": DatasetContract(
        name="sellers",
        filename="olist_sellers_dataset.csv",
        primary_key=("seller_id",),
        columns=(
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ),
    ),
    "geolocation": DatasetContract(
        name="geolocation",
        filename="olist_geolocation_dataset.csv",
        primary_key=(),
        columns=(
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
    ),
    "category_translation": DatasetContract(
        name="category_translation",
        filename="product_category_name_translation.csv",
        primary_key=("product_category_name",),
        columns=(
            "product_category_name",
            "product_category_name_english",
        ),
    ),
}


def get_contract(name: str) -> DatasetContract:
    """Return the contract registered under a logical dataset name."""

    return CONTRACTS[name]


def required_filenames() -> set[str]:
    """Return all source filenames required for a complete Olist load."""

    return {contract.filename for contract in CONTRACTS.values()}
