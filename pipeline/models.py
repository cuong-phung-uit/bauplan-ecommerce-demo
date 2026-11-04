from typing import Annotated

import pyarrow

import bauplan


# Source columns are nullable in the catalog, so source projections use bauplan.Any:
# a required type (bauplan.String, ...) fails with "cannot cast from optional to required".
class SessionEvents(bauplan.TableSchema):
    event_time: bauplan.Any
    event_type: bauplan.Any
    product_id: bauplan.Any
    category_code: bauplan.Any
    brand: bauplan.Any
    price: bauplan.Any
    user_id: bauplan.Any


class PurchaseEvents(bauplan.TableSchema):
    event_time: bauplan.String
    product_id: bauplan.Int64
    category_code: bauplan.String
    brand: bauplan.String
    price: bauplan.Float64
    user_id: bauplan.Int64


@bauplan.model(materialization_strategy='REPLACE')
@bauplan.python('3.11', pip={'polars': '2.0.0'})
def purchase_events(
    raw: Annotated[
        pyarrow.Table,
        bauplan.Model(
            'sessions_feed',
            projection_schema=SessionEvents,
            filter="event_type = 'purchase' AND price > 0",
        ),
    ],
) -> Annotated[pyarrow.Table, PurchaseEvents]:
    import polars as pl

    df = pl.DataFrame(raw)

    result = df.with_columns(
        pl.col('brand').fill_null('Unknown'),
        pl.col('category_code').fill_null('uncategorized'),
    ).drop('event_type')
    return result.to_arrow()


class PurchaseInputs(bauplan.TableSchema):
    event_time: bauplan.String
    category_code: bauplan.String
    brand: bauplan.String
    price: bauplan.Float64
    user_id: bauplan.Int64


class UserSegments(bauplan.TableSchema):
    user_id: bauplan.Any
    customer_segment: bauplan.Any


class SegmentedPurchases(bauplan.TableSchema):
    event_time: bauplan.String
    category_code: bauplan.String
    brand: bauplan.String
    price: bauplan.Float64
    customer_segment: bauplan.String


@bauplan.model(materialization_strategy='REPLACE')
@bauplan.python('3.11', pip={'polars': '2.0.0'})
def purchases_by_segment(
    purchases: Annotated[
        pyarrow.Table,
        bauplan.Model(
            'purchase_events',
            projection_schema=PurchaseInputs,
        ),
    ],
    users: Annotated[
        pyarrow.Table,
        bauplan.Model(
            'bauplan.ecommerce_users',
            projection_schema=UserSegments,
        ),
    ],
) -> Annotated[pyarrow.Table, SegmentedPurchases]:
    import polars as pl

    purchases_df = pl.DataFrame(purchases)

    users_df = pl.DataFrame(users)

    result = purchases_df.join(
        users_df,
        on='user_id',
    ).drop('user_id')
    return result.to_arrow()


class SegmentStatsInputs(bauplan.TableSchema):
    event_time: bauplan.String
    price: bauplan.Float64
    customer_segment: bauplan.String


class DailySegmentStats(bauplan.TableSchema):
    date: bauplan.String
    customer_segment: bauplan.String
    total_purchases: bauplan.Int64
    total_revenue: bauplan.Float64
    avg_order_value: bauplan.Float64


@bauplan.model(materialization_strategy='REPLACE')
@bauplan.python('3.11', pip={'polars': '2.0.0'})
def daily_segment_stats(
    data: Annotated[
        pyarrow.Table,
        bauplan.Model(
            'purchases_by_segment',
            projection_schema=SegmentStatsInputs,
        ),
    ],
) -> Annotated[pyarrow.Table, DailySegmentStats]:
    import polars as pl

    df = pl.DataFrame(data)

    result = df.with_columns(
        pl.col('event_time').str.slice(0, 10).alias('date'),
    ).group_by(['date', 'customer_segment']).agg([
        pl.len().cast(pl.Int64).alias('total_purchases'),
        pl.col('price').sum().round(2).alias('total_revenue'),
        pl.col('price').mean().round(2).alias('avg_order_value'),
    ]).sort('date', 'customer_segment')
    return result.to_arrow()
