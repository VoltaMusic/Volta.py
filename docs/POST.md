# POST method
# Tables
- [POST method](#post-method)
- [Tables](#tables)
  - [POST in your library](#post-in-your-library)
      - [Base:](#base)
    - [track()](#track)
      - [Use:](#use)
    - [playlist()](#playlist)
      - [Use:](#use-1)
    - [playlist\_track()](#playlist_track)
      - [Use:](#use-2)
  - [Generic POST](#generic-post)

## POST in your library

Add things to your library and create playlists.

A POST is **never retried automatically** on a server error (5xx): the server may already have
processed it, and replaying it could create a duplicate. A `ServerError` is raised right away instead.

#### Base:
```python
VoltaClient.post.library.
```

---
### track()
> Add a track to your library (like it).
>
> Args:
> - track_id (str): The ID of the track.
>
> Scope: `library:write`

#### Use:
```python
with VoltaClient() as client:
    client.post.library.track("Track ID") # Like a track
```


---
### playlist()
> Create a new playlist.
>
> Only the fields you pass are sent; the others keep the server's defaults.
> An empty `name` raises an `InvalidArgumentError` (before any request is sent).
>
> Args:
> - name (str): The name of the playlist.
> - description (str, optional): The description of the playlist. Defaults to None.
> - is_public (bool, optional): Whether the playlist is public. Defaults to None (server default).
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    client.post.library.playlist("Roadtrip")                     # Create a playlist
    client.post.library.playlist("Roadtrip", description="Summer 2026", is_public=False)
```


---
### playlist_track()
> Add a track to one of your playlists.
>
> Args:
> - playlist_id (str): The ID of the playlist.
> - track_id (str): The ID of the track to add.
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    client.post.library.playlist_track("Playlist ID", "Track ID") # Add a track to a playlist
```


## Generic POST

Call any POST route that has no dedicated method, with a JSON body:

```python
with VoltaClient() as client:
    client.post.request("/api/v1/some/other/endpoint", {"key": "value"})
```
