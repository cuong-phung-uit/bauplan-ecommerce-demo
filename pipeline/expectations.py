from typing import Annotated

import pyarrow

import bauplan


class StatsDate(bauplan.TableSchema):
    date: bauplan.String


@bauplan.expectation()
@bauplan.python('3.11')
def test_daily_segment_stats_not_empty(
    data: Annotated[
        pyarrow.Table,
        bauplan.Model(
            'daily_segment_stats',
            projection_schema=StatsDate,
        ),
    ],
) -> bool:
    assert data.num_rows > 0, 'daily_segment_stats is empty'
    return data.num_rows > 0
