Skip to content
kloppy 3.18.0
Time
Search

 PySport/kloppy
v3.18.0
499
88
Home
User guide
How-to guides
Reference
Development
Releases
User guide
Getting started
Installation
Configuration
Concepts
Event data
Tracking data
Code data
Metadata
Coordinates
Time
Positions
Loading data
Transforming data
Exporting data
Table of contents
Periods
Timestamps
Operations on time
Subtraction (-)
Addition (+)
Home
User guide
Concepts
Time
Soccer data is fundamentally tied to time. Seasons, matches within a season, and events within a match are all ordered. Hence, each event needs to carry information about when it happened.

However, the representation of time varies significantly across data providers. Time may be represented using absolute timestamps (e.g., a specific UTC time like 2024-12-01T15:45:13Z) or through a match-specific game clock (e.g., 75:13, as seen on a scoreboard). Even when using a game clock, there are further variations, such as how extra time is handled or whether the clock resets at the start of each period.

To address these inconsistencies, kloppy introduces a standardized approach to managing time. In short, the game is split up in periods (i.e., the two 45-minute halves and possibly overtime) which have absolute timestamps to denote their start and end timestamps. Within each period, time is then expressed relatively with respect to the start of the period using a game clock. Let's illustrate this by looking at the time of an event. In kloppy's data model, each record (i.e., event, frame, or code) has a .time attribute.

>>> from kloppy import statsbomb
>>> dataset = statsbomb.load_open_data(match_id="3869685")
>>> goal_event = dataset.find("shot.goal")
>>> print(goal_event.time)
P1T22:24
A Time entity consist of two parts: a reference to a period and a timestamp relative to the kick-off in that period.

>>> print(f"{goal_event.time.period} - {goal_event.time.timestamp}")
Period(id=1, start_timestamp=datetime.timedelta(0), end_timestamp=datetime.timedelta(seconds=3154, microseconds=569000), prev_period=None, next_period=Period(id=2, start_timestamp=datetime.timedelta(seconds=3154, microseconds=569000), end_timestamp=datetime.timedelta(seconds=6372, microseconds=490000), prev_period=..., next_period=Period(id=3, start_timestamp=datetime.timedelta(seconds=6372, microseconds=490000), end_timestamp=datetime.timedelta(seconds=7337, microseconds=138000), prev_period=..., next_period=Period(id=4, start_timestamp=datetime.timedelta(seconds=7337, microseconds=138000), end_timestamp=datetime.timedelta(seconds=8484, microseconds=610000), prev_period=..., next_period=Period(id=5, start_timestamp=datetime.timedelta(seconds=8484, microseconds=610000), end_timestamp=datetime.timedelta(seconds=8843, microseconds=476000), prev_period=..., next_period=None))))) - 0:22:24.114000
Let's take a closer look at both of these.

Periods
Period entities are used to split up a game into periods.

from kloppy.domain import Period
from datetime import datetime, timezone

periods = [
    Period(
        id=1,
        start_timestamp=datetime(2024, 12, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2024, 12, 1, 15, 45, 10, tzinfo=timezone.utc),
    ),
    Period(
        id=2,
        start_timestamp=datetime(2024, 12, 1, 16, 00, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2024, 12, 1, 16, 48, 30, tzinfo=timezone.utc),
    ),
]
Ideally, the start_timestamp and end_timestamp values are expressed as absolute time-zone aware datetime objects, with the start_timestamp marking the exact time of the period's kick-off and the end_timestamp marking the time of the final whistle. This allows users to link and sync different datasets (e.g., tracking data with video).

However, when absolute times are not available, kloppy falls back to using offsets. In this case, the start_timestamp is defined as the offset between the start of the data feed for the period and the kick-off of the period, while the end_timestamp is defined as the offset between the start of the data feed and the final whistle of the period. This ensures that even in the absence of absolute time data, a relative timeline is maintained.

from kloppy.domain import Period
from datetime import timedelta

periods = [
    Period(
        id=1,
        start_timestamp=timedelta(seconds=0),
        end_timestamp=timedelta(minutes=45, seconds=10),
    ),
    Period(
        id=2,
        start_timestamp=timedelta(minutes=60),
        end_timestamp=timedelta(minutes=93, seconds=30),
    ),
]
Each period also has an id. Therefore, kloppy uses the following convention.

1: First half
2: Second half
3: First half of overtime
4: Second half of overtime
5: Penalty shootout
Timestamps
The timestamp represents the time elapsed since the start of the period.

>>> rel_time = goal_event.time.timestamp
>>> print(rel_time)
0:22:24.114000
The absolute time in the match can be obtained by combining both the period and timestamp.

>>> abs_time = goal_event.time.period.start_time + goal_event.time.timestamp
>>> print(abs_time)
P1T22:24
Note

Kloppy uses the built-in datetime objects to handle absolute timestamps and timedelta objects to handle relative timestamps. Absolute timestamps always include timezone information.

Operations on time
The Time class supports mathematical operations that allow navigation across different periods and timestamps seamlessly.

Subtraction (-)
You can subtract:

A timedelta from a Time, resulting in a new Time. If the result would move the Time before the start of the current period, it automatically moves back to the previous period if available.
A Time from another Time, resulting in a timedelta. The periods are taken into account: if they belong to different periods, the full durations of the intermediate periods are summed.
Examples:

# Subtracting timedelta
new_time = time_obj - timedelta(seconds=30)

# Subtracting two Time instances
duration = time_obj1 - time_obj2
Addition (+)
You can add a timedelta to a Time, resulting in a new Time. If the addition moves the Time beyond the end of the current period, it transitions into the next period automatically.

Examples:

# Adding timedelta
future_time = time_obj + timedelta(minutes=2)
 Back to top
Made with Material for MkDocs
