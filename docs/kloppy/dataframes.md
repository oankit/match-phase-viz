Skip to content
kloppy 3.18.0
Dataframes
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
Loading data
Transforming data
Exporting data
Dataframes
Sportscode XML
Table of contents
Basic usage
Event data
Tracking data
Code data
Selecting output columns
Adding metadata as columns
Attribute transformers
Combine it all
Home
User guide
Exporting data
Exporting to a dataframe
Kloppy datasets can be easily exported to either Pandas or Polars dataframes. This functionality connects kloppy with the broader Python data analytics ecosystem, enabling you to:

Explore and manipulate tracking or event data using Pandas or Polars.
Export data to formats like CSV, Excel, or Parquet.
Perform advanced feature engineering on-the-fly.
Integrate with machine learning and visualization libraries that require tabular input.
Basic usage
Kloppy represents data using structured Python objects (like TrackingDataset and EventDataset). The to_df() method flattens these objects into a tabular form.

df = dataset.to_df()
The default output columns of the DataFrame depend on the type of dataset:

Event data
For an EventDataset, the default columns include:

Column	Description
event_id	Unique identifier of the event
event_type	Type of the event (e.g., pass, shot)
period_id	Match period
timestamp	Start time of the event
end_timestamp	End time of the event (if available)
team_id	ID of the team performing the event
player_id	ID of the player performing the event
result	Result of the action (e.g., COMPLETE)
success	Boolean indicating if the event was completed successfully
coordinates_x/y	Location of the event on the pitch
ball_state	Current state of the game
ball_owning_team	Which team owns the ball
Other columns are added depending on the event types and qualifiers of the events in the dataset.

Example:


event_id	event_type	period_id	timestamp	end_timestamp	ball_state	ball_owning_team	team_id	player_id	coordinates_x	coordinates_y	end_coordinates_x	end_coordinates_y	receiver_player_id	set_piece_type	result	success	body_part_type	card_type
18226900000006	PASS	1	0 days 00:00:00	None	alive	None	DFL-CLU-00000S	DFL-OBJ-000172	0.500000	0.500000	0.745238	0.501471	DFL-OBJ-0001I0	KICK_OFF	COMPLETE	True	None	None
18226900000007	PASS	1	0 days 00:00:04.110000	None	alive	None	DFL-CLU-00000S	DFL-OBJ-0001I0	0.745238	0.501471	0.275905	0.914853	None	None	COMPLETE	True	None	None
18226900000008	GENERIC:TacklingGame	1	0 days 00:00:06.365000	None	alive	None	None	None	0.275905	0.914853	NaN	NaN	None	None	None	None	None	None
Tracking data
For a TrackingDataset, the output columns include:

Column	Description
frame_id	Frame number
period_id	Match period
timestamp	Frame timestamp
ball_x, ball_y, ball_z, ball_speed	Ball position and speed
<player_id>_x, <player_id>_y, <player_id>_d, <player_id>_s	Player coordinates, distance (since previous frame), and speed
ball_state	Current state of the ball
ball_owning_team	Which team owns the ball
Example:


period_id	timestamp	frame_id	ball_state	ball_owning_team_id	ball_x	ball_y	ball_z	ball_speed	DFL-OBJ-0001I0_x	DFL-OBJ-0001I0_y	DFL-OBJ-0001I0_d	DFL-OBJ-0001I0_s	DFL-OBJ-000172_x	DFL-OBJ-000172_y	DFL-OBJ-000172_d	DFL-OBJ-000172_s	DFL-OBJ-0000YV_x	DFL-OBJ-0000YV_y	DFL-OBJ-0000YV_d	DFL-OBJ-0000YV_s	DFL-OBJ-0000XU_x	DFL-OBJ-0000XU_y	DFL-OBJ-0000XU_d	DFL-OBJ-0000XU_s	DFL-OBJ-000199_x	DFL-OBJ-000199_y	DFL-OBJ-000199_d	DFL-OBJ-000199_s	DFL-OBJ-J014F7_x	DFL-OBJ-J014F7_y	DFL-OBJ-J014F7_d	DFL-OBJ-J014F7_s	DFL-OBJ-J016C3_x	DFL-OBJ-J016C3_y	DFL-OBJ-J016C3_d	DFL-OBJ-J016C3_s	DFL-OBJ-0027FG_x	DFL-OBJ-0027FG_y	DFL-OBJ-0027FG_d	DFL-OBJ-0027FG_s	DFL-OBJ-0027LO_x	DFL-OBJ-0027LO_y	DFL-OBJ-0027LO_d	DFL-OBJ-0027LO_s	DFL-OBJ-0028NB_x	DFL-OBJ-0028NB_y	DFL-OBJ-0028NB_d	DFL-OBJ-0028NB_s	DFL-OBJ-002GM0_x	DFL-OBJ-002GM0_y	DFL-OBJ-002GM0_d	DFL-OBJ-002GM0_s	DFL-OBJ-0026NY_x	DFL-OBJ-0026NY_y	DFL-OBJ-0026NY_d	DFL-OBJ-0026NY_s	DFL-OBJ-0001UP_x	DFL-OBJ-0001UP_y	DFL-OBJ-0001UP_d	DFL-OBJ-0001UP_s	DFL-OBJ-J013O2_x	DFL-OBJ-J013O2_y	DFL-OBJ-J013O2_d	DFL-OBJ-J013O2_s	DFL-OBJ-0002LI_x	DFL-OBJ-0002LI_y	DFL-OBJ-0002LI_d	DFL-OBJ-0002LI_s	DFL-OBJ-002G02_x	DFL-OBJ-002G02_y	DFL-OBJ-002G02_d	DFL-OBJ-002G02_s	DFL-OBJ-J01B8R_x	DFL-OBJ-J01B8R_y	DFL-OBJ-J01B8R_d	DFL-OBJ-J01B8R_s	DFL-OBJ-002GAR_x	DFL-OBJ-002GAR_y	DFL-OBJ-002GAR_d	DFL-OBJ-002GAR_s	DFL-OBJ-002G8H_x	DFL-OBJ-002G8H_y	DFL-OBJ-002G8H_d	DFL-OBJ-002G8H_s	DFL-OBJ-002GOI_x	DFL-OBJ-002GOI_y	DFL-OBJ-002GOI_d	DFL-OBJ-002GOI_s	DFL-OBJ-002GBK_x	DFL-OBJ-002GBK_y	DFL-OBJ-002GBK_d	DFL-OBJ-002GBK_s	DFL-OBJ-J01KDN_x	DFL-OBJ-J01KDN_y	DFL-OBJ-J01KDN_d	DFL-OBJ-J01KDN_s
1	0 days 00:00:00	10000	alive	DFL-CLU-00000S	0.505810	0.505147	0.01	6.84	0.749619	0.576324	None	0.00	0.498190	0.505147	None	0.00	0.497524	0.802353	None	0.00	0.618190	0.631471	None	0.00	0.574190	0.623824	None	0.00	0.501619	0.855441	None	0.00	0.590476	0.472794	None	0.00	0.501143	0.355441	None	0.00	0.496857	0.538235	None	0.00	0.493619	0.630147	None	0.00	0.491429	0.744118	None	0.00	0.025619	0.504853	None	0.00	0.319238	0.747353	None	0.00	0.422190	0.737206	None	0.00	0.371238	0.551471	None	0.00	0.495810	0.366324	None	0.00	0.338667	0.403529	None	0.00	0.318476	0.611912	None	0.00	0.369429	0.647206	None	0.00	0.324190	0.825735	None	0.00	0.415619	0.496176	None	0.00	0.392000	0.778971	None	0.00
1	0 days 00:00:00.040000	10001	alive	DFL-CLU-00000S	0.515333	0.507794	0.03	6.84	0.749714	0.576618	None	2.27	0.498190	0.505000	None	1.12	0.496952	0.802206	None	5.57	0.617810	0.631912	None	4.60	0.573905	0.623824	None	2.98	0.500952	0.855294	None	6.80	0.590476	0.472794	None	0.66	0.500286	0.354118	None	11.45	0.496571	0.538382	None	2.49	0.492286	0.629853	None	12.71	0.490190	0.744412	None	12.39	0.026857	0.505147	None	10.96	0.319048	0.747500	None	1.95	0.422095	0.737647	None	3.41	0.371238	0.551471	None	0.31	0.496190	0.367059	None	7.04	0.338381	0.403676	None	3.20	0.318381	0.611912	None	0.97	0.369524	0.646912	None	2.49	0.324190	0.825882	None	0.53	0.415810	0.496176	None	2.10	0.392190	0.779118	None	1.68
1	0 days 00:00:00.080000	10002	alive	DFL-CLU-00000S	0.524762	0.510441	0.04	6.80	0.749905	0.576912	None	2.35	0.498095	0.504853	None	1.58	0.496286	0.802206	None	5.95	0.617333	0.632206	None	4.73	0.573619	0.623676	None	3.26	0.500190	0.855000	None	7.47	0.590381	0.472794	None	0.65	0.499333	0.352941	None	12.01	0.496381	0.538529	None	2.53	0.491048	0.629412	None	13.22	0.488762	0.745000	None	12.89	0.027905	0.505441	None	11.15	0.318952	0.747647	None	2.17	0.421905	0.738088	None	3.50	0.371238	0.551471	None	0.49	0.496762	0.367941	None	7.63	0.338000	0.403971	None	3.29	0.318286	0.611912	None	1.09	0.369714	0.646471	None	2.50	0.324095	0.825882	None	0.65	0.416190	0.496176	None	2.14	0.392286	0.779118	None	1.80
Code data
For a CodeDataset, the output columns include:

Column	Description
code_id	Code number
period_id	Match period
timestamp	Start timestamp
end_timestamp	End timestamp
code	Name of the code
Furthermore, one column is added for each label used in the dataset.

Example:


code_id	period_id	timestamp	end_timestamp	code	Player	Team
None	1	0 days 00:00:45.374000	0 days 00:00:57.374000	shot	S. Azmoun	Bayer 04 Leverkusen
None	1	0 days 00:00:50.383000	0 days 00:01:02.383000	shot	M. Diaby	Bayer 04 Leverkusen
None	1	0 days 00:01:43.052000	0 days 00:01:55.052000	shot	S. Azmoun	Bayer 04 Leverkusen
Selecting output columns
You can control which attributes are included in the output using arguments in .to_df(). Wildcard patterns (*) are supported to match multiple fields:

df = event_dataset.to_df("event_type", "team", "coordinates_*")

event_type	team	coordinates_x	coordinates_y
PASS	VfL Bochum 1848	0.5	0.5
This lets you include only the data you need, making downstream processing more efficient. The pattern is matched against all default attributes provided by the internal transformer.

Adding metadata as columns
You can inject constant metadata into your DataFrame by passing keyword arguments:

df = event_dataset.to_df("*", match_id="match_1234", competition="Premier League")

event_id	event_type	period_id	timestamp	end_timestamp	ball_state	ball_owning_team	team_id	player_id	coordinates_x	coordinates_y	end_coordinates_x	end_coordinates_y	receiver_player_id	set_piece_type	result	success	match_id	competition	body_part_type	card_type
18226900000006	PASS	1	0 days	None	alive	None	DFL-CLU-00000S	DFL-OBJ-000172	0.5	0.5	0.745238	0.501471	DFL-OBJ-0001I0	KICK_OFF	COMPLETE	True	match_1234	Premier League	None	None
These keyword arguments will be added as constant columns across all rows. This is useful for adding identifiers or context to the exported data.

Attribute transformers
Attribute Transformers let you derive new attributes on the fly during the conversion process. Kloppy includes a limited set of built-in transformers:

DistanceToGoalTransformer: Compute the distance to the goal.
DistanceToOwnGoalTransformer: Compute the distance to the own goal.
AngleToGoalTransformer: Compute the angle between the current location and the center of the goal.
Example usage:

from kloppy.domain.services.transformers.attribute import DistanceToGoalTransformer
from kloppy.domain import Orientation

df = (
    event_dataset
    .to_df("event_type", "team", "coordinates_*", DistanceToGoalTransformer())
)

event_type	team	coordinates_x	coordinates_y	distance_to_goal
PASS	VfL Bochum 1848	0.5	0.5	0.5
You can also define your own custom transformer. A transformer is a function that takes an Event (or Frame) and returns a dictionary of derived values:

def my_transformer(event):
    return {
        "is_shot": event.event_type.name == "SHOT",
        "x": event.coordinates.x if event.coordinates else None
    }

df = event_dataset.to_df("event_type", "team", "coordinates_*", my_transformer)

event_type	team	coordinates_x	coordinates_y	is_shot	x
PASS	VfL Bochum 1848	0.5	0.5	False	0.5
Alternatively, you can add named attributes using keyword arguments and pass a callable that returns any single value:

df = event_dataset.to_df(
    "event_type", "team", "coordinates_*", 
    is_pass=lambda event: event.event_type.name == "PASS"
)

event_type	team	coordinates_x	coordinates_y	is_pass
PASS	VfL Bochum 1848	0.5	0.5	True
This flexibility allows you to calculate exactly the attributes you need at export time.

Combine it all
Here's an example that shows everything working together:

from kloppy import sportec
from kloppy.domain.services.transformers.attribute import DistanceToGoalTransformer

event_dataset = sportec.load_open_event_data(match_id="J03WN1")

df = event_dataset.to_df(
    "event_type", "team", "coordinates_*",
    DistanceToGoalTransformer(),
    match_id="match_5678",
    is_pass=lambda e: e.event_type.name == "PASS"
)

event_type	team	coordinates_x	coordinates_y	distance_to_goal	match_id	is_pass
PASS	VfL Bochum 1848	0.500000	0.500000	0.500000	match_5678	True
PASS	VfL Bochum 1848	0.745238	0.501471	0.254766	match_5678	True
GENERIC:TacklingGame	None	0.275905	0.914853	0.834516	match_5678	False
 Back to top
Made with Material for MkDocs
