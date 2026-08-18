"""
"season" metadata sources (Plex match-request type=3). No example source
ships here - a season lookup is usually keyed off its parent show plus a
season number rather than a free-text query, so there's no single obvious
free API to demo with. See app/client/source/show/example_show.py for how
a season source should populate SourceMetadata's parent/grandparent
hierarchy fields.

Enabled by default (ENABLE_SEASON_SOURCES=true) with an empty
SEASON_SOURCES list - a source added here is picked up once listed there.
"""
