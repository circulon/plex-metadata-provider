"""
"episode" metadata sources (Plex match-request type=4). No example source
ships here - see app/client/source/season/__init__.py for why. An episode
lookup is usually keyed off its parent show/season plus a season/episode
number or broadcast date (see MatchRequest's grandparentTitle/index/
parentIndex/originallyAvailableAt fields).

Enabled by default (ENABLE_EPISODE_SOURCES=true) with an empty
EPISODE_SOURCES list - a source added here is picked up once listed there.
"""
