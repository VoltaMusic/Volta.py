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
> The API needs the track's name, artist and album, not just its ID: pass the **whole track**,
> as returned by `get.catalog.track()`, `get.catalog.search()` or `get.library.tracks()`.
> Both shapes are converted automatically. Passing only an ID, or a track without a name / artist / album,
> raises an `InvalidArgumentError` (before any request is sent).
>
> Args:
> - track (dict): The track to add.
>
> Scope: `library:write`

#### Use:
```python
with VoltaClient() as client:
    track = client.get.catalog.track("Track ID")
    client.post.library.track(track) # Like a track
```


---
### playlist()
> Create a new playlist.
>
> Only the fields you pass are sent; the others keep the server's defaults.
> An empty `name` raises an `InvalidArgumentError` (before any request is sent).
>
> The API ignores `description` on creation, so the library sets it right after with a PUT:
> the returned playlist has its description either way.
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
> Like [`track()`](#track), it needs the **whole track** (from `get.library.tracks()`,
> `get.catalog.track()` or `get.catalog.search()`), not just its ID.
>
> Args:
> - playlist_id (str): The ID of the playlist.
> - track (dict): The track to add.
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    playlist = client.post.library.playlist("Daft Punk mix")
    for track in client.get.library.tracks():
        if "daft punk" in track["artist"].lower():
            client.post.library.playlist_track(playlist["id"], track)
```


## Generic POST

Call any POST route that has no dedicated method, with a JSON body:

```python
with VoltaClient() as client:
    client.post.request("/api/v1/some/other/endpoint", {"key": "value"})
```
