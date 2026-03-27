Getting started
This chapter is here to help you get started quickly with kloppy. It gives a 10-minute introduction on how kloppy can be used to load, filter, transform, and export soccer match data. If you're already familiar with kloppy, feel free to skip ahead to the next chapters for a more in-depth discussion of all functionality.

Installing kloppy
The recommended and easiest way to install kloppy is through pip.

pip install kloppy
The installation guide provides an overview of alternative options.

Loading data
In soccer analytics, data typically comes in two main formats: event data and tracking data. Each format has unique advantages and they are often used together.

Yet, within these main formats, there are notable differences between data providers in terms of the structure, naming conventions, and the depth of information available. This implies that significant patchwork and data plumbing is needed to repeat the same analysis for different data sources. Kloppy aims to eliminate these challenges by providing a set of data parsers that can load data from all common data providers into a common standardized format.

Kloppy standardizes soccer data

We'll illustrate how to load a dataset in this standardized format using a sample of publicly available data provided by Sportec. For examples on loading data from other data providers, see the Loading Data section of the user guide.

Event data
The public Sportec dataset contains both event data and tracking data. We'll first load the event data.

from kloppy import sportec

event_dataset = sportec.load_open_event_data(match_id="J03WN1")
The resulting EventDataset contains a list of Event entities that represent actions such as passes, tackles, and shots. Each event is mapped to a specific subclass—e.g., shots become a ShotEvent, passes become a PassEvent, and so on. These events are annotated with contextual information, including the players involved, the outcome of the action, and the location on the pitch where it occurred.

A standardized event data model

Event data providers like Stats Perform, StatsBomb, and Wyscout have each developed their own event data catalogs, with unique definitions and categorizations for various event types. To address this lack of standardization, kloppy introduces its own event data model, which acts as a common denominator for event types and attributes used across data providers. This model facilitates the integration of data from diverse event data catalogs. If you need event types or data attributes that are not included in kloppy's datamodel, you can easily extend the data model.

You can retrieve specific events by their index or by their unique ID (as given by the data provider) using the .get_event_by_id() method. Below, we illustrate this by retrieving the opening goal in the match.

>>> goal_event = event_dataset.get_event_by_id("18226900000272")
>>> print(goal_event)
<ShotEvent event_id='18226900000272' time='P1T18:04' team='VfL Bochum 1848' player='P. Förster' result='GOAL'>
Often, you will not know the exact index or ID of an event. In that case, you can use the .find() and .find_all() methods for finding the right events. You can pass a string or a function. In case of a string, it must be either '<event_type>', '<event_type>.<result>' or '.<result>'. Some examples: 'shot.goal', 'pass' or '.complete'. Let's look at how this works by finding all shots in the dataset.

shot_events = event_dataset.find_all("shot")
goal_events = event_dataset.find_all("shot.goal")
On event-level there are also some useful methods for navigating: the .prev() and .next() methods allow you to quickly find previous or next events. Those two methods also accept the same filter argument as the .find() and .find_all() methods, which can be useful to find a certain type of event instead of just the one before/after. For example, we can use it to find the assist for a goal.

>>> assist_event = goal_event.prev("pass.complete")
>>> print(assist_event)
<PassEvent event_id='18226900000271' time='P1T18:00' team='VfL Bochum 1848' player='T. Asano' result='COMPLETE'>
Using the wonderful mplsoccer package we can now plot the goal and its assist.


Result
Source


Tracking data
Unlike event data, which focuses on on-the-ball actions, tracking data provides continuous spatial information about all players and the ball. Below we load the tracking data of the same game.

from kloppy import sportec

tracking_dataset = sportec.load_open_tracking_data(
    match_id="J03WN1",
    limit=30000  # optional: for efficiency, we only load the first 30 000 frames
)
This will create a TrackingDataset, which contains a sequence of Frame entities.

>>> first_frame = tracking_dataset[0]
>>> print(first_frame)
<Frame frame_id='10000' time='P1T00:00'>
Each frame has a .ball_coordinates attribute that stores the coordinates of the ball and a .players_coordinates attribute that stores the coordinates of each player.

>>> print(f"Ball coordinates: (x={first_frame.ball_coordinates.x:.2f}, y={first_frame.ball_coordinates.y:.2f})")
>>> for player, coordinates in first_frame.players_coordinates.items():
...     print(f"{player} ({player.team}): (x={coordinates.x:.2f}, y={coordinates.y:.2f})")
Ball coordinates: (x=0.51, y=0.51)
Manuel Riemann (VfL Bochum 1848): (x=0.75, y=0.58)
K. Stöger (VfL Bochum 1848): (x=0.50, y=0.51)
P. Hofmann (VfL Bochum 1848): (x=0.50, y=0.80)
D. Heintz (VfL Bochum 1848): (x=0.62, y=0.63)
A. Losilla (VfL Bochum 1848): (x=0.57, y=0.62)
I. Ordets (VfL Bochum 1848): (x=0.50, y=0.86)
S. Janko (VfL Bochum 1848): (x=0.59, y=0.47)
T. Asano (VfL Bochum 1848): (x=0.50, y=0.36)
P. Förster (VfL Bochum 1848): (x=0.50, y=0.54)
C. Antwi-Adjei (VfL Bochum 1848): (x=0.49, y=0.63)
E. Mašović (VfL Bochum 1848): (x=0.49, y=0.74)
L. Hrádecký (Bayer 04 Leverkusen): (x=0.03, y=0.50)
Jonathan Tah (Bayer 04 Leverkusen): (x=0.32, y=0.75)
S. Azmoun (Bayer 04 Leverkusen): (x=0.42, y=0.74)
N. Amiri (Bayer 04 Leverkusen): (x=0.37, y=0.55)
M. Diaby (Bayer 04 Leverkusen): (x=0.50, y=0.37)
M. Bakker (Bayer 04 Leverkusen): (x=0.34, y=0.40)
Edmond Tapsoba (Bayer 04 Leverkusen): (x=0.32, y=0.61)
Exequiel Palacios (Bayer 04 Leverkusen): (x=0.37, y=0.65)
Jeremie Frimpong (Bayer 04 Leverkusen): (x=0.32, y=0.83)
Florian Wirtz (Bayer 04 Leverkusen): (x=0.42, y=0.50)
A. Adli (Bayer 04 Leverkusen): (x=0.39, y=0.78)
A tracking data frame can provide useful context to an event as it shows the locations of all off-the-ball players. For example for a pass event, it can show which alternative passing options a player had. Unfortunately, matching the right tracking frame to an event can be challenging as recorded timestamps in event data are not always very precise. Luckily, Sportec has already done this matching for all shot events. Let's revisit the opening goal that we looked at earlier and see what additional context the tracking data can provide.

Event-tracking synchronization

Implementing automated event to tracking data synchronization is on kloppy's roadmap. See #61.

# Match the goal event with its corresponding tracking frame
matched_frame_idx = goal_event.raw_event["CalculatedFrame"]
goal_frame = tracking_dataset.get_record_by_id(int(matched_frame_idx))
With mplsoccer we can plot the frame.


Result
Source


Metadata
One of the main benefits of working with kloppy is that it loads metadata with each (event and tracking) dataset and makes it available in the dataset's .metadata property.

metadata = event_dataset.metadata
This metadata includes teams (name, ground, tactical formation, and provider ID) and players (name, jersey number, position, and provider ID). By default, the teams are stored in metadata.teams as a tuple where the first item is the home team and the second one is the away team.

>>> home_team, away_team = metadata.teams
>>> print(f"{home_team} vs {away_team}")
VfL Bochum 1848 vs Bayer 04 Leverkusen
From each Team entity, you can then retrieve the line-up as a list of Player entities.


Source
Result
home_team_players = []
for player in home_team.players:
    position = (
        player.starting_position.code
        if player.starting_position is not None
        else 'SUB'
    )
    description = f"{position}:{player} (#{player.jersey_no})"
    home_team_players.append(description)

print(home_team_players)

To select individual players, you can use the .get_player_by_id(), .get_player_by_jersey_number() or .get_player_by_position() methods. Below, we select Florian Wirtz by his Sportec ID ("DFL-OBJ-002GBK").

>>> player = away_team.get_player_by_id("DFL-OBJ-002GBK")
>>> print(player.name)
Florian Wirtz
The Team and Player entities also contain the magic methods to use those keys in dictionaries or use them in sets. This makes it easy to do some calculations, and show the results without mapping the player_id to a name.


Source
Result
from collections import defaultdict

passes_per_player = defaultdict(list)
for event in event_dataset.find_all("pass"):
    passes_per_player[event.player].append(event)

print("\n".join(
    f"{player} has {len(passes)} passes"
    for player, passes in passes_per_player.items()
))

The metadata contains much more than the players and teams. Later in this quick start guide, we will come across some more metadata attributes. The Reference Guide gives a complete overview of everything that is available.

Filtering data
Oftentimes, not all data in a match is relevant. The goal of the analysis might be to investigate a certain time window, set of events, game phase, or tactical pattern.

Selecting events or frames
To select a subset of events or frames, kloppy provides the filter, find and find_all methods. We've already introduced the find and find_all methods above for finding events. The filter method works similarly, the only difference being that it returns a new dataset while the other two methods return a list of events or frames. With these methods we can easily create a dataset that only contains a specific type of event.

# Create a new dataset which contains all goals
goals_dataset = event_dataset.filter('shot.goal')
We can do slightly more complicated things by providing a (lambda) function. This works for both event data and tracking datasets.

# Create a new dataset with all frames where the ball is in the final third
pitch_max_x = tracking_dataset.metadata.pitch_dimensions.x_dim.max
f3_dataset = tracking_dataset.filter(
    lambda frame: frame.ball_coordinates.x > (2 / 3) * pitch_max_x
)
Pattern matching
For finding patterns in a game (that is, groups of events), you can use kloppy's event_pattern_matching module. This module implements a versatile domain-specific language for finding patterns in event data, inspired by regular expressions. We won't get into detail here but rather show how it can be used to create movement chains to illustrate its versatility.

Movement chains describe the pattern of four consecutive player involvements in an uninterrupted passage of play by displaying the locations of the first touches of the players involved, where a player can be involved more than once within the chain. In kloppy, you can define this pattern as follows:

from kloppy import event_pattern_matching as pm

pattern = (
    # match all successful passes
    pm.match_pass(
        success=True,
        capture="first_touch"
    )
    # ... that are followed by 3 successful passes by the same team
    + pm.match_pass(
        success=True,
        team=pm.same_as("first_touch.team"),
    ) * 3
    # ... ending with a shot by the same team
    + pm.match_shot(
        team=pm.same_as("first_touch.team")
    )
)
Now, we can search for this pattern in an event dataset.

>>> shot_ending_chains = pm.search(event_dataset, pattern)
>>> print(f"Found {len(shot_ending_chains)} matches")
Found 2 matches
We've only found two matches, one for the home team and one for the away team. Let's take a closer look at the players involved in those shot-ending movement chains.

>>> for match in shot_ending_chains:
...     print(" -> ".join([e.player.name for e in match.events]))
Jonathan Tah -> Jeremie Frimpong -> Florian Wirtz -> Jeremie Frimpong -> M. Diaby
P. Förster -> A. Losilla -> P. Hofmann -> K. Stöger -> C. Antwi-Adjei
Transforming data
Apart from the data format and event definitions, another aspect that differs between data providers is how they represent coordinates. These differences can include where the origin of the pitch is placed (e.g., top-left, center, bottom-left), which direction the axes increase (left to right, top to bottom, etc.), and the units used (normalized values, metric dimensions, or imperial dimensions). As a result, even if two datasets describe the same event, the x and y positions may not be directly comparable without converting them into a shared reference frame.

Sportec even uses different coordinate systems for their event and tracking data. For event data, the origin is at the top left, while it is at the center of the pitch for tracking data. The direction of the y-axis is different too.




To avoid issues with differences between coordinate systems, kloppy converts all data to a common default coordinate system when loading a dataset: the KloppyCoordinateSystem.

>>> print(event_dataset.metadata.coordinate_system)
<kloppy.domain.models.common.KloppyCoordinateSystem object at 0x7fbb3ce6d2e0>
In this coordinate system the pitch is scaled to a unit square where the x-axis ranges from 0 (left touchline) to 1 (right touchline), and the y-axis ranges from 0 (bottom goal line) to 1 (top goal line). All spatial data are expressed relative to this 1×1 pitch.




You can convert from this normalized system to any supported provider format using the .transform(to_coordinate_system=...) method, allowing interoperability with other tools or datasets.

>>> from kloppy import sportec
>>> from kloppy.domain import Provider
>>> event_dataset = (
...     sportec.load_open_event_data(match_id="J03WN1")
...     .transform(to_coordinate_system=Provider.SPORTEC)
... )
>>> print(event_dataset.metadata.coordinate_system)
<kloppy.domain.models.common.SportecEventDataCoordinateSystem object at 0x7fbb3cfb7380>
Alternatively (and more efficiently) you can directly load the data in your preferred coordinate system by setting the coordinates parameter. For example, to load the data with Sportec's coordinate system:

>>> from kloppy import sportec
>>> from kloppy.domain import Provider
>>> event_dataset = sportec.load_open_event_data(
...     match_id="J03WN1",
...     coordinates=Provider.SPORTEC
... )
>>> print(event_dataset.metadata.coordinate_system)
<kloppy.domain.models.common.SportecEventDataCoordinateSystem object at 0x7fbb3aa924e0>
Another aspect of how coordinates are represented is the orientation of the data. For this game, the default orientation setting is "away-home". This means, the away team plays from left to right in the first period. The home team plays from left to right in the second period.

>>> print(metadata.orientation)
Orientation.AWAY_HOME
This orientation reflects the actual playing direction, which switches at half-time. It aligns with how the match appears on broadcast footage, making it convenient when synchronizing tracking or event data with video.

However, for some types of analysis, it can be more convenient to normalize the orientation so that one team (usually the team of interest) always attacks in the same direction (e.g., left-to-right). One concrete example is creating a heatmap of a player's actions. Let’s look at an example where we visualize the locations of all Florian Wirtz' his passes, first without transforming the orientation.


Result
Source


The heatmap shows activity spread over the entire pitch. This is because teams switch directions at halftime, and the data reflects that change.

We can transform the data so that direction of all on-the-ball actions is aligned left-to-right. Therefore, we'll use the "action-executing-team" orientation.

>>> transformed_events = player_events.transform(to_orientation="ACTION_EXECUTING_TEAM")
>>> print(transformed_events.metadata.orientation)
Orientation.ACTION_EXECUTING_TEAM
Now, the heatmap makes a lot more sense.


Result
Source


Exporting data
Until now, we've worked with kloppy's object oriented data model. This format is well-suited to preprocess the data. However, to do some actual analysis of the data, it can often be more convenient and efficient to use dataframes or SportsCode XML.

To a Polars/Pandas dataframe
kloppy allows you to export a dataset to a dataframe. Both Polars and Pandas are supported. You can use the following engines: polars, pandas, pandas[pyarrow].

Note

You'll first have to install Pandas or Polars.

Simply calling dataset.to_df() results in a default output, but we can modify how the resulting dataframe looks as shown in the code below.

df_shots_and_key_passes = (
    event_dataset
    # filter for shots
    .filter("shot")
    # put all shots on the same side of the pitch
    .transform(to_orientation="ACTION_EXECUTING_TEAM")
    # convert to dataframe
    .to_df(
        "player_id",
        lambda event: {
            "player_name": str(event.player),
            "is_goal": event.result.is_success,
        },
        "coordinates_*",
        key_pass=lambda event: str(event.prev("pass").player),
        team=lambda event: str(event.team),
        engine="pandas",
    )
)

player_id	player_name	is_goal	coordinates_x	coordinates_y	key_pass	team
DFL-OBJ-J013O2	S. Azmoun	False	0.862571	0.405588	N. Amiri	Bayer 04 Leverkusen
DFL-OBJ-002G02	M. Diaby	False	0.904571	0.640147	N. Amiri	Bayer 04 Leverkusen
DFL-OBJ-J013O2	S. Azmoun	False	0.897905	0.418824	N. Amiri	Bayer 04 Leverkusen
DFL-OBJ-002G8H	Exequiel Palacios	False	0.844476	0.712353	A. Adli	Bayer 04 Leverkusen
DFL-OBJ-0027LO	P. Förster	True	0.940095	0.465441	A. Adli	VfL Bochum 1848
To Sportscode XML
Sportscode XML is a format associated with Hudl Sportscode, a popular platform for video analysis in sports. It integrates video clips with detailed tagging of game events, making it ideal for coaches and analysts who need synchronized video and event data to dissect team and player performances.

To support this popular data format, kloppy provides a CodeDataset. You can use kloppy to load Sportscode XML files, but perhaps more interestingly, you can also generate these files from another dataset allowing you to automatically create playlists from event and/or tracking data that can be used by a video analyst. We will illustrate this by creating a playlist with all shots.

from datetime import timedelta

from kloppy.domain import Code, CodeDataset, EventType

code_dataset = (
    CodeDataset
    .from_dataset(
        event_dataset.filter("shot"),
        lambda event: Code(
            code_id=None,  # make it auto increment on write
            code=event.event_name,
            period=event.period,
            timestamp=max(timedelta(seconds=0), event.timestamp - timedelta(seconds=7)),  # start 7s before the shot
            end_timestamp=event.timestamp + timedelta(seconds=5),  # end 5s after the shot
            labels={
                'Player': str(event.player),
                'Team': str(event.team)
            },

            # in the future, the next two won't be needed anymore
            ball_owning_team=None,
            ball_state=None,
            statistics=None
        )
    )
)
You can now export the dataset to an XML file.

from kloppy import sportscode

sportscode.save(code_dataset, "playlist.xml")
 Back to top
Made with Material for MkDocs