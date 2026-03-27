Skip to content
kloppy 3.18.0
Event data
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
Kloppy's event data model
Event types
Qualifiers
Home
User guide
Concepts
Event data
Event (stream) data is a time-coded feed which describes the key events that occur during a match. The data is generally created by trained human annotators (assisted by computer vision) based on broadcast video of a game. Most of the events they annotate are on-the-ball player actions such as shots, passes, and dribbles. However, the data feed will typically also include other relevant events like substitutions and tactical changes. As an example, we load the open StatsBomb event data of the 2002 World Cup final.

from kloppy import statsbomb

dataset = statsbomb.load_open_data(match_id="3869685")
This will create an EventDataset that wraps a list of Event entities and implements a number of common operations to process the dataset. This section explains the Event entities. Later sections of the user guide will explain in-depth how to load and process an event dataset.

Kloppy's event data model
Event data is sold by specialized data vendors such as StatsBomb, Stats Perform (Opta), and Wyscout. All these data vendors annotate the same games but use their own set of event types, attributes, and data formats. This can make it difficult to write software or perform data analyses that can be applied to multiple event data sources. Therefore, kloppy implements its own vendor-independent data model for describing events.

Below is what the kick-off event looks like in the raw data. StatsBomb uses a JSON object to describe each event. You can get this raw representation trough the .raw_event attribute.

{'id': 'f651a6c4-55e3-4e0f-a178-59414ba83d6a', 'index': 5, 'period': 1, 'timestamp': '00:00:00.578', 'minute': 0, 'second': 0, 'type': {'id': 30, 'name': 'Pass'}, 'possession': 2, 'possession_team': {'id': 771, 'name': 'France'}, 'play_pattern': {'id': 9, 'name': 'From Kick Off'}, 'team': {'id': 771, 'name': 'France'}, 'player': {'id': 5487, 'name': 'Antoine Griezmann'}, 'position': {'id': 19, 'name': 'Center Attacking Midfield'}, 'location': [61.0, 40.1], 'duration': 0.975702, 'related_events': ['97b5dc82-547a-4f93-a632-a2a8daf5ac98'], 'pass': {'recipient': {'id': 10481, 'name': 'Aurélien Djani Tchouaméni'}, 'length': 13.364505, 'angle': 2.907503, 'height': {'id': 1, 'name': 'Ground Pass'}, 'end_location': [48.0, 43.2], 'type': {'id': 65, 'name': 'Kick Off'}, 'body_part': {'id': 38, 'name': 'Left Foot'}}}
For comparison, below is what the same kick-off looks like in kloppy's data model.

<StatsBombPassEvent event_id='f651a6c4-55e3-4e0f-a178-59414ba83d6a' time='P1T00:01' team='France' player='Antoine Griezmann' result='COMPLETE'>
Instead of JSON objects, kloppy uses Event objects to represent events. This provides a number of advantages over storing the raw data in a dictionary or data frame, such as better readability, type-safety, and autocompletion in most IDEs.

Each event has a number of default attributes, which are summarized in the table below.

Attribute	Type	Description
dataset	Dataset	Reference to the dataset that includes this event.
event_id	str	Unique event identifier provided by the data provider. Alias for record_id.
event_type	EventType	The specific type of event, such as pass, shot, or foul.
event_name	str	Human-readable name of the event type.
time	Time	Time during the match when the event occurs.
coordinates	Point	The location on the pitch where the event took place.
team	Team	The team associated with the event.
player	Player	The player involved in the event.
ball_owning_team	Team	The team in possession of the ball at the time of the event.
ball_state	BallState	Indicates whether the ball is in play or not.
raw_event	object	The original event data as received from the provider.
prev_record	Event	Link to the previous event in the sequence.
next_record	Event	Link to the next event in the sequence.
related_event_ids	[str]	Identifiers of events related to this one.
freeze_frame	Frame	Snapshot showing all players’ locations at the time of the event.
attacking_direction	AttackingDirection	The direction the team is attacking during this event.
state	{str -> object}	Additional contextual information about the game state.
Event types
Each event has a specific type, corresponding to passes, shots, tackles, etc. These event types are implemented as different subclasses of Event. For example, a pass is implemented by the PassEvent subclass, while a substitution is implemented by the SubstitutionEvent subclass. Each subclass implements additional attributes specific to that event type. For example, a pass has a .result attribute (a pass can be complete, incomplete, out, or offside); while a substitution has a .replacement_player attribute.

Let's look at the opening goal of the 2002 World Cup final as an example. It is a penalty by Lionel Messi.

>>> goal_event = dataset.get_event_by_id("6d527ebc-a948-4cd8-ac82-daced35bb715")
>>> print(goal_event)
<StatsBombShotEvent event_id='6d527ebc-a948-4cd8-ac82-daced35bb715' time='P1T22:24' team='Argentina' player='Lionel Andrés Messi Cuccittini' result='GOAL'>
In kloppy's data model, the penalty is represented by a ShotEvent. Each ShotEvent has a .result attribute that contains a ShotResult. As the penalty was scored, the result here is ShotResult.GOAL.

If a particular event type is not included in kloppy's data model, it will be deserialized as a GenericEvent. For example, kloppy does not (yet) have a data model for ball receival events.

>>> receival_event = dataset.get_event_by_id("0db72b17-bed3-446f-ae22-468480e33ad6")
>>> print(receival_event)
<GenericEvent:Ball Receipt* event_id='0db72b17-bed3-446f-ae22-468480e33ad6' time='P1T23:42' team='France' player='Adrien Rabiot'>
For an overview of all event types and their attributes, see the Event Type Reference.

Note

Kloppy's data model covers the event types and attributes that are commonly used by multiple data vendors. Some vendors might have certain specific event types or attributes that are not implemented in kloppy's data model, but kloppy's data model can easily be extended to support these if needed.

Qualifiers
In addition to event type-specific attributes, each event can have one or more qualifiers attached to it. While attributes define core properties of an event such as its outcome, qualifiers provide extra context about how an event happened. They add more descriptive details that help with deeper analysis.

For Messi's penalty that we looked at above, kloppy adds a SetPieceQualifier and a BodyPartQualifier.

>>> print(goal_event.qualifiers)
[SetPieceQualifier(value=<SetPieceType.PENALTY: 'PENALTY'>), BodyPartQualifier(value=<BodyPart.LEFT_FOOT: 'LEFT_FOOT'>)]
You can check if an event has a qualifier of a certain type using the .get_qualifier_value() method.

>>> from kloppy.domain import SetPieceQualifier
>>> sp_qualifiers = goal_event.get_qualifier_value(SetPieceQualifier)
>>> print(sp_qualifiers)
SetPieceType.PENALTY
For an overview of all qualifiers, see the Qualifier Type Reference.

 Back to top
Made with Material for MkDocs
