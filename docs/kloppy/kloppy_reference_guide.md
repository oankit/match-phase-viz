# Kloppy Reference Guide

*Version covered: Kloppy 3.18.0*

This guide compiles the material you shared into a single Markdown reference covering installation, configuration, core concepts, Sportec usage, transformations, dataframe export, and Sportscode XML export.

---

## Quick overview

**Kloppy** is a Python library for working with soccer data from multiple providers through a shared, standardized model. It supports:

- event data
- tracking data
- code or timeline data

A typical workflow is:

1. install kloppy
2. load a dataset
3. inspect metadata
4. filter or transform the data
5. export it to a dataframe or Sportscode XML

---

## 1. Installation and verification

Kloppy supports **Python 3.9 through 3.12**.

### Recommended install

```bash
python -m pip install kloppy
```

### Development install from GitHub

```bash
pip install git+https://github.com/PySport/kloppy.git
```

### Install from a local clone

```bash
git clone git://github.com/PySport/kloppy.git
cd kloppy
python -m pip install -e .
```

### Verify installation

Open Python and run:

```python
import kloppy
print(kloppy.__version__)
```

---

## 2. Global configuration

Kloppy exposes configuration utilities under `kloppy.config`.

```python
from kloppy.config import get_config, set_config, config_context
```

### Main configuration functions

| Function | Purpose | Example use |
|---|---|---|
| `get_config()` | Read all config options or a single option | Inspect `cache`, `coordinate_system`, adapter settings |
| `set_config()` | Set one config value globally | Set `coordinate_system` before loading data |
| `config_context()` | Temporarily override config values inside a `with` block | Use a temporary coordinate system for one load block |

### Example: get all config values

```python
cfg = get_config()
print(cfg)
```

Example output shown in your material:

```python
{
  'cache': '/opt/buildhome/kloppy_cache',
  'coordinate_system': 'kloppy',
  'event_factory': None,
  'adapters.http.basic_authentication': None,
  'adapters.s3.s3fs': None,
  'adapters.zip.fo': None,
  'dataframe.engine': 'pandas'
}
```

### Example: get one config value

```python
cfg_coordinate_system = get_config("coordinate_system")
print(cfg_coordinate_system)
```

### Example: set a global config value

```python
from kloppy import statsbomb
set_config("coordinate_system", "opta")
dataset = statsbomb.load_open_data()
print(dataset.metadata.coordinate_system)
```

### Example: temporary config with a context manager

```python
print(f"Before context: {get_config('coordinate_system')}")
with config_context("coordinate_system", "statsbomb"):
    print(f"Within context: {get_config('coordinate_system')}")
    dataset = statsbomb.load_open_data()
print(f"After context: {get_config('coordinate_system')}")
print(dataset.metadata.coordinate_system)
```

---

## 3. Event data

Event data is a time-coded feed of important match actions such as:

- passes
- shots
- dribbles
- substitutions
- tactical changes

Kloppy maps provider-specific events into a provider-independent event model.

### Common event attributes

Depending on provider and event type, event records may include:

- `event_id`
- `event_type`
- `time`
- `coordinates`
- `team`
- `player`
- `ball_state`
- `ball_owning_team`
- related events
- freeze frame data
- game state

### Event subclasses

Kloppy uses specific subclasses for event types such as:

- `PassEvent`
- `ShotEvent`
- `SubstitutionEvent`

If a provider-specific event does not have a dedicated abstraction, Kloppy may fall back to `GenericEvent`.

### Useful navigation helpers

- `get_event_by_id()`
- `find()`
- `find_all()`
- `prev()`
- `next()`

### Qualifiers

Qualifiers add context to events, for example:

- set piece type
- body part used
- pass height
- defensive pressure

---

## 4. Tracking data

Tracking data provides frame-by-frame spatial coordinates for players and the ball.

Kloppy stores tracking feeds in a `TrackingDataset`, which is made up of `Frame` objects.

### Example: load Metrica tracking data

```python
from kloppy import metrica

dataset = metrica.load_open_data(
    match_id=1,
    limit=1000
)
```

### Frame rate

The dataset metadata includes the tracking frame rate:

```python
print(dataset.metadata.frame_rate)
```

Example output from your material:

```python
25
```

A frame rate of `25` means there are **25 frames per second** of match time.

### Inspect a frame

```python
frame = dataset.frames[500]
```

### Frame contents

Each `Frame` contains:

- the exact timestamp
- ball coordinates
- a mapping of players to coordinates

### Timestamp

```python
print(frame.time)
```

Example:

```python
P1T00:20
```

### Ball coordinates

```python
print(frame.ball_coordinates)
```

Example:

```python
Point(x=0.37413, y=0.33704999999999996)
```

If the provider includes height, ball coordinates may be a `Point3D` instead.

### Player coordinates

Each frame has a `players_coordinates` dictionary:

```python
print(f"Number of players in the frame: {len(frame.players_coordinates)}")
```

Example output:

```python
Number of players in the frame: 22
```

### Example: home team player coordinates

```python
home_team, away_team = dataset.metadata.teams
print("List home team players coordinates", [
   player_coordinates
   for player, player_coordinates
   in frame.players_coordinates.items()
   if player.team == home_team
])
```

### Typical use cases for tracking data

Tracking data is useful for:

- off-ball analysis
- passing lane analysis
- team shape and spacing
- defensive compactness
- pressure and coverage studies

---

## 5. Code data

Code data, also called **timeline data**, is a time-coded feed of analyst-tagged moments. It is often created with tools such as:

- Hudl Sportscode
- Metrica Nexus
- Nacsport

These moments are labeled with customizable tags such as:

- Pass
- Shot
- Counter

### Example raw Hudl Sportscode XML instance

```xml
<instance>
    <ID>P1</ID>
    <start>3.6</start>
    <end>9.7</end>
    <code>PASS</code>
    <label>
        <group>Team</group>
        <text>France</text>
    </label>
    <label>
        <group>Player</group>
        <text>Antoine Griezmann</text>
    </label>
    <label>
        <group>Packing.Value</group>
        <text>1</text>
    </label>
    <label>
        <group>Receiver</group>
        <text>Tchouaméni</text>
    </label>
</instance>
```

### Code object example in Kloppy

```python
from kloppy.domain import Code

Code(
    code_id="P1",
    timestamp=180.12,
    end_timestamp=182.67,
    code="Pass",
    labels={
      "team": "France",
      "player": "Antoine Griezmann",
      "receiver": "Tchouaméni",
      "Packing.Value": "1",
    }
)
```

### Code fields

A `Code` object has these main fields:

- `code_id`: unique identifier
- `timestamp`: start time in seconds
- `end_timestamp`: end time in seconds
- `code`: event type or code name
- `labels`: dictionary of metadata extracted from labels

This abstraction makes it possible to work with custom tagging feeds through one consistent structure.

---

## 6. Metadata

Every dataset in Kloppy exposes a `.metadata` attribute.

Metadata falls into two broad categories:

1. **match sheet data**
2. **technical specifications**

### Match sheet data

Match sheet metadata can include:

| Attribute | Type | Optional | Description |
|---|---|---|---|
| `game_id` | `str` | Yes | Game ID from the provider |
| `date` | `datetime` | Yes | Match date |
| `game_week` | `str` | Yes | Match day or competition stage |
| `periods` | `Period` | No | Match periods |
| `teams` | `Team` | No | Home and away team metadata |
| `officials` | `Official` | Yes | Referees and officials |
| `score` | `Score` | Yes | Final score |
| `attributes` | `Dict` | Yes | Stadium, weather, attendance, and similar extras |

### Technical specifications

Technical metadata can include:

| Attribute | Type | Optional | Description |
|---|---|---|---|
| `provider` | `Provider` | No | Data provider or vendor |
| `coordinate_system` | `CoordinateSystem` | No | Coordinate system used |
| `pitch_dimensions` | `PitchDimensions` | No | Pitch size |
| `orientation` | `Orientation` | No | Attacking direction convention |
| `flags` | `DatasetFlag` | No | Flags describing optional data present |
| `frame_rate` | `float` | Yes | Tracking frame rate in Hertz |

### Why metadata matters

Metadata is essential because it tells you:

- who played
- how the match is segmented
- which coordinate system is in use
- what pitch scale is being used
- what optional information is available
- how frequent tracking frames are sampled

---

## 7. Coordinates and orientation

Kloppy standardizes spatial information because providers differ in:

- origin point
- y-axis direction
- pitch scale
- attacking direction conventions

### Coordinate system definition

In Kloppy, a coordinate system is defined by:

- origin
- vertical orientation
- pitch dimensions

### Supported origins

Examples mentioned in your material:

- top-left
- bottom-left
- center

### Pitch dimensions

Pitch dimensions may be:

- metric
- imperial
- normalized
- Opta-style
- Wyscout-style
- custom

### Orientation modes

Kloppy supports multiple orientation modes, including:

- `home-away`
- `away-home`
- `static-home-away`
- `static-away-home`
- `action-executing-team`
- `ball-owning-team`
- `not-set`

### Why this matters

A standardized coordinate model makes it easier to:

- compare providers
- run consistent models across datasets
- keep analysis stable across halves
- synchronize data with video or tactical views

---

## 8. Time model

Kloppy represents match time using:

- a `Period`
- a timestamp relative to the start of that period

### Period IDs

The material you shared lists these period identifiers:

- `1`: first half
- `2`: second half
- `3`: first half of overtime
- `4`: second half of overtime
- `5`: penalty shootout

### Time formatting

Example:

```python
P1T22:24
```

This means:

- period 1
- 22 minutes
- 24 seconds into that period

### Time object behavior

The `Time` class supports:

- addition with timedeltas
- subtraction with timedeltas
- subtraction between `Time` values to get elapsed duration

---

## 9. Positions

Kloppy standardizes player positions with a hierarchical `PositionType`.

### Position types listed in your material

- Unknown
- Goalkeeper
- Defender
- FullBack
- LeftBack
- RightBack
- CenterBack
- LeftCenterBack
- RightCenterBack
- WingBack
- LeftWingBack
- RightWingBack
- Midfielder
- DefensiveMidfield
- LeftDefensiveMidfield
- CenterDefensiveMidfield
- RightDefensiveMidfield
- CentralMidfield
- LeftCentralMidfield
- CenterMidfield
- RightCentralMidfield
- AttackingMidfield
- LeftAttackingMidfield
- CenterAttackingMidfield
- RightAttackingMidfield
- WideMidfield
- LeftWing
- RightWing
- LeftMidfield
- RightMidfield
- Attacker
- LeftForward
- Striker
- RightForward

### Example usage

```python
from kloppy.domain import PositionType

print(PositionType.LeftCenterBack)
print(PositionType.LeftCenterBack.code)
```

Example output:

```python
Left Center Back
LCB
```

### Parent hierarchy

Positions are hierarchical:

```python
pos_lb = PositionType.LeftBack
print(f"{pos_lb} >> {pos_lb.parent} >> {pos_lb.parent.parent}")
```

Example output:

```python
Left Back >> Full Back >> Defender
```

### Check subtype relationship

```python
print(PositionType.LeftCenterBack.is_subtype_of(PositionType.Defender))
```

Example output:

```python
True
```

### Time-varying positions

A player’s match positions are stored in a time container that supports:

- `.ranges()`
- `.value_at(time)`
- `.at_start()`
- `.last()`

### Example with StatsBomb

```python
from kloppy import statsbomb

event_dataset = statsbomb.load_open_data(match_id="15946")
player = event_dataset.metadata.teams[0].get_player_by_jersey_number(5)

for start_time, end_time, position in player.positions.ranges():
    print(f"{start_time}:{end_time} - {position.code if position is not None else 'SUB'}")
```

---

## 10. Sportec usage

Kloppy includes dedicated loaders for **Sportec** event and tracking data.

### Load local event files

```python
from kloppy import sportec

dataset = sportec.load_event(
    event_data="../../kloppy/tests/files/sportec_events.xml",
    meta_data="../../kloppy/tests/files/sportec_meta.xml",
    coordinates="sportec",
    event_types=["pass", "shot"],
)

dataset.to_df().head()
```

### Example event dataframe columns shown

The example you provided includes columns such as:

- `event_id`
- `event_type`
- `result`
- `success`
- `period_id`
- `timestamp`
- `end_timestamp`
- `ball_state`
- `ball_owning_team`
- `team_id`
- `player_id`
- `coordinates_x`
- `coordinates_y`
- `end_coordinates_x`
- `end_coordinates_y`
- `receiver_player_id`
- `set_piece_type`
- `body_part_type`

### Load local tracking files

```python
from kloppy import sportec

dataset = sportec.load_tracking(
    raw_data="../../kloppy/tests/files/sportec_positional.xml",
    meta_data="../../kloppy/tests/files/sportec_meta.xml",
    sample_rate=1,
    limit=10,
    coordinates="sportec",
    only_alive=False,
)

dataset.to_df().head()
```

### Example tracking dataframe columns shown

The example you provided includes fields such as:

- `period_id`
- `timestamp`
- `frame_id`
- `ball_state`
- `ball_owning_team_id`
- `ball_x`
- `ball_y`
- `ball_z`
- `ball_speed`
- per-player coordinate, distance, and speed fields

### Load open Sportec data

There are **7 games** of open Sportec Open DFL Tracking and Event Data in the material you shared.

### Open match IDs

| Match ID | Home | Away |
|---|---|---|
| `J03WMX` | 1. FC Köln | FC Bayern München |
| `J03WN1` | VfL Bochum 1848 | Bayer 04 Leverkusen |
| `J03WPY` | Fortuna Düsseldorf | 1. FC Nürnberg |
| `J03WOH` | Fortuna Düsseldorf | SSV Jahn Regensburg |
| `J03WQQ` | Fortuna Düsseldorf | FC St. Pauli |
| `J03WOY` | Fortuna Düsseldorf | F.C. Hansa Rostock |
| `J03WR9` | Fortuna Düsseldorf | 1. FC Kaiserslautern |

### Open event and tracking examples

```python
from kloppy import sportec

match_id = "J03WMX"
event_dataset = sportec.load_open_event_data(match_id=match_id)
tracking_dataset = sportec.load_open_tracking_data(match_id=match_id)
```

### Load remote files

Kloppy supports remote files through **fsspec**.

Example:

```python
from kloppy import sportec

dataset = sportec.load_tracking(
    raw_data="s3://.../sportec_positional.xml",
    meta_data="s3://.../sportec_meta.xml",
    sample_rate=1,
    limit=10,
    coordinates="sportec",
    only_alive=False,
)
```

This can work with storage systems such as:

- AWS S3
- Google Cloud
- Azure Blob
- HDFS
- FTP
- SFTP

---

## 11. Dataset transformations

Kloppy provides a `transform()` method to adapt the spatial representation of a dataset.

### Main transformation arguments

| Argument | What it changes | Typical use case |
|---|---|---|
| `to_orientation` | Attacking direction convention | Standardize actions so one side always attacks left-to-right |
| `to_pitch_dimensions` | Pitch size and scaling | Normalize several matches to a shared pitch size |
| `to_coordinate_system` | Origin, y-axis direction, and pitch dimensions together | Convert a dataset into a provider-style coordinate format |

### Guidance from the provided material

- Use `home-away` or `away-home` when you want actual match direction, which helps with video synchronization.
- Use `static-home-away` or `static-away-home` when you want each team to attack in one fixed direction across both halves.
- Use `action-executing-team` when you want all actions standardized left-to-right.
- Use `ball-owning-team` when you want all possessions standardized left-to-right.
- Use metric or imperial pitch dimensions when real-world distances matter.
- Use normalized dimensions when you want a fixed scale for zone-based analysis or machine learning.
- Do **not** use `to_pitch_dimensions` and `to_coordinate_system` together in the same `transform()` call.

---

## 12. Exporting to dataframes

Kloppy’s `to_df()` method converts datasets into dataframes.

It supports:

- `EventDataset`
- `TrackingDataset`
- `CodeDataset`

### Supported engines

The material references:

- Pandas
- Polars

### Event dataframe exports commonly include

- `event_id`
- `event_type`
- `period_id`
- `timestamp`
- `end_timestamp`
- `team_id`
- `player_id`
- `result`
- `success`
- coordinates
- ball state
- ball-owning team

### Tracking dataframe exports commonly include

- `frame_id`
- `period_id`
- `timestamp`
- `ball_x`
- `ball_y`
- `ball_z`
- `ball_speed`
- per-player x/y/distance/speed columns

### Code dataframe exports commonly include

- `code_id`
- `period_id`
- `timestamp`
- `end_timestamp`
- `code`
- one column per label

### Helpful export features mentioned

- choose only the columns you need
- use wildcard patterns such as `coordinates_*`
- add constant metadata columns
- compute derived features during export

### Built-in attribute transformers referenced

- distance to goal
- distance to own goal
- angle to goal

---

## 13. Exporting to Hudl Sportscode XML

Kloppy supports exporting event-derived clips to **Hudl Sportscode XML**.

### Step 1: create a `CodeDataset`

A common workflow is:

1. load an event dataset
2. filter to actions of interest, such as shots
3. map each event into a `Code` object
4. save the resulting `CodeDataset` as Sportscode XML

### Example workflow from your material

```python
from kloppy import statsbomb
from kloppy.domain import Code, CodeDataset, EventType

dataset_shots = (
    statsbomb.load_open_data()
    .filter(
        lambda event: event.event_type == EventType.SHOT
    )
)

code_dataset = (
    CodeDataset
    .from_dataset(
        dataset_shots,
        lambda event: Code(
            code_id=None,
            code=event.event_name,
            period=event.period,
            timestamp=max(0, event.timestamp - 7),
            end_timestamp=event.timestamp + 5,
            labels={
                'Player': str(event.player),
                'Team': str(event.team)
            },

            ball_owning_team=None,
            ball_state=None
        )
    )
)
```

### Step 2: save to Sportscode XML

```python
from kloppy import sportscode

sportscode.save(code_dataset, "output_file.xml")
```

This produces an XML file ready to import into Hudl Sportscode.

### Why this is useful

This makes it possible to:

- import supported provider events into a Sportscode timeline
- attach labels such as team and player
- connect data-driven tagging with video review workflows

---

## 14. Practical workflow summary

A practical Kloppy workflow looks like this:

1. Install kloppy and verify the version.
2. Load a dataset from a provider such as StatsBomb, Metrica, or Sportec.
3. Inspect metadata for teams, pitch dimensions, frame rate, and orientation.
4. Find or filter the records you need.
5. Transform orientation, pitch dimensions, or coordinate system if needed.
6. Export the result to a dataframe or Sportscode XML.

---

## Appendix: representative commands

```bash
python -m pip install kloppy
pip install git+https://github.com/PySport/kloppy.git
```

```python
from kloppy import sportec

event_dataset = sportec.load_open_event_data(match_id="J03WN1")
tracking_dataset = sportec.load_open_tracking_data(match_id="J03WN1")
```

```python
dataset = dataset.transform(to_orientation="action-executing-team")
df = dataset.to_df(engine="pandas")
```

```python
from kloppy import sportscode
sportscode.save(code_dataset, "output_file.xml")
```

---

*Compiled from the Kloppy materials you provided in this conversation.*
