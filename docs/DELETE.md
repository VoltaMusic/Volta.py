# DELETE method
# Tables
- [DELETE method](#delete-method)
- [Tables](#tables)
  - [DELETE in your library](#delete-in-your-library)
      - [Base:](#base)
    - [track()](#track)
      - [Use:](#use)
    - [album()](#album)
      - [Use:](#use-1)
    - [artist()](#artist)
      - [Use:](#use-2)
    - [playlist()](#playlist)
      - [Use:](#use-3)
    - [playlist\_track()](#playlist_track)
      - [Use:](#use-4)
  - [Generic DELETE](#generic-delete)

## DELETE in your library

Remove things from your library and delete playlists.

A DELETE is **never retried automatically** on a server error (5xx): a `ServerError` is raised right away.
Deleting something that doesn't exist raises a `NotFoundError` (404).

#### Base:
```python
VoltaClient.delete.library.
```

---
### track()
> Remove a track from your library (unlike it).
>
> Args:
> - track_id (str): The ID of the track.
>
> Scope: `library:write`

#### Use:
```python
with VoltaClient() as client:
    client.delete.library.track("Track ID")
```


---
### album()
> Remove every track of an album from your library.
>
> Args:
> - album_id (str): The ID of the album.
>
> Scope: `library:write`

#### Use:
```python
with VoltaClient() as client:
    client.delete.library.album("Album ID")
```


---
### artist()
> Unfollow an artist.
>
> Args:
> - artist_id (str): The ID of the artist.
>
> Scope: `library:write`

#### Use:
```python
with VoltaClient() as client:
    client.delete.library.artist("Artist ID")
```


---
### playlist()
> Delete one of your playlists. This cannot be undone.
>
> Args:
> - playlist_id (str): The ID of the playlist.
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    client.delete.library.playlist("Playlist ID")
```


---
### playlist_track()
> Remove a track from one of your playlists.
>
> Args:
> - playlist_id (str): The ID of the playlist.
> - track_id (str): The ID of the track to remove.
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    client.delete.library.playlist_track("Playlist ID", "Track ID")
```


## Generic DELETE

Call any DELETE route that has no dedicated method (the JSON body is optional):

```python
with VoltaClient() as client:
    client.delete.request("/api/v1/some/other/endpoint")
```
