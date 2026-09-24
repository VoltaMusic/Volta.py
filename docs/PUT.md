# PUT method
# Tables
- [PUT method](#put-method)
- [Tables](#tables)
  - [PUT in your library](#put-in-your-library)
      - [Base:](#base)
    - [playlist()](#playlist)
      - [Use:](#use)
    - [reorder()](#reorder)
      - [Use:](#use-1)
  - [Generic PUT](#generic-put)

## PUT in your library

Update your playlists.

A PUT is **never retried automatically** on a server error (5xx): a `ServerError` is raised right away.

#### Base:
```python
VoltaClient.put.library.
```

---
### playlist()
> Update the name, description and/or visibility of a playlist.
>
> Only the fields you pass are sent; the others are left unchanged.
> Passing no field at all raises an `InvalidArgumentError` (before any request is sent).
>
> Args:
> - playlist_id (str): The ID of the playlist.
> - name (str, optional): The new name. Defaults to None (unchanged).
> - description (str, optional): The new description. Defaults to None (unchanged).
> - is_public (bool, optional): The new visibility. Defaults to None (unchanged).
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    client.put.library.playlist("Playlist ID", name="Roadtrip 2026")  # Rename
    client.put.library.playlist("Playlist ID", is_public=True)        # Make it public
    client.put.library.playlist("Playlist ID", description="Summer")  # Change the description
```


---
### reorder()
> Reorder the tracks of a playlist.
>
> Args:
> - playlist_id (str): The ID of the playlist.
> - track_ids (list[str]): The track IDs of the playlist, in the new order.
>
> Scope: `playlists:write`

#### Use:
```python
with VoltaClient() as client:
    client.put.library.reorder("Playlist ID", ["Track 3", "Track 1", "Track 2"])
```


## Generic PUT

Call any PUT route that has no dedicated method, with a JSON body:

```python
with VoltaClient() as client:
    client.put.request("/api/v1/some/other/endpoint", {"key": "value"})
```
