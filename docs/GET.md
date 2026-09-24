# GET method
# Tables
- [GET method](#get-method)
- [Tables](#tables)
  - [GET in your library](#get-in-your-library)
      - [Base:](#base)
    - [tracks()](#tracks)
      - [Use:](#use)
    - [albums()](#albums)
      - [Use:](#use-1)
    - [artists()](#artists)
      - [Use:](#use-2)
    - [artist\_albums()](#artist_albums)
      - [Use:](#use-3)
    - [artist\_tracks()](#artist_tracks)
      - [Use:](#use-4)
    - [playlists()](#playlists)
      - [Use:](#use-5)
  - [GET in global app](#get-in-global-app)
      - [Base:](#base-1)
    - [search()](#search)
      - [Use:](#use-6)
    - [artist()](#artist)
      - [Use:](#use-7)
    - [album()](#album)
      - [Use:](#use-8)
    - [track()](#track)
      - [Use:](#use-9)
    - [playlist()](#playlist)
      - [Use:](#use-10)
    - [home()](#home)
      - [Use:](#use-11)
    - [stream()](#stream)
      - [Use:](#use-12)
    - [state()](#state)
      - [Use:](#use-13)
    - [me()](#me)
      - [Use:](#use-14)
  - [Generic GET](#generic-get)

## GET in your library

Fetch data from your own library (liked tracks, albums, followed artists, your playlists).
To search the global Volta catalog, use [`get.catalog`](#get-in-global-app) instead.

About `search=`: the filtering is done client-side, on the list returned by the API.
It is case- and accent-insensitive (`"beyonce"` finds `"Beyoncé"`).
If the API doesn't return a list, an `InvalidResponseError` is raised.

#### Base:
```python
VoltaClient.get.library.
```

---
### tracks()
> Get all liked tracks.
>
> If a search string is provided, filter the tracks by title containing the search string (case- and accent-insensitive).
>
> Args:
> - search (str, optional): A string to filter tracks by title. Defaults to None.
>
> Scope: `library:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.library.tracks()                    # Fetch all liked tracks
    client.get.library.tracks(search="Song Title") # Liked tracks whose title matches
```


---
### albums()
> Get all liked albums.
>
> If a search string is provided, filter the albums by title containing the search string (case- and accent-insensitive).
>
> Args:
> - search (str, optional): A string to filter albums by title. Defaults to None.
>
> Scope: `library:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.library.albums()                     # Fetch all albums of your library
    client.get.library.albums(search="Album Title") # Albums whose title matches
```


---
### artists()
> Get all followed artists.
>
> If a search string is provided, filter the artists by name containing the search string (case- and accent-insensitive).
>
> Args:
> - search (str, optional): A string to filter artists by name. Defaults to None.
>
> Scope: `library:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.library.artists()                     # Fetch all followed artists
    client.get.library.artists(search="Artist name") # Followed artists whose name matches
```


---
### artist_albums()
> Get the albums of a specific artist that are in your library.
>
> Args:
> - id (str): The ID of the artist.
>
> Scope: `library:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.library.artist_albums("Artist ID") # Albums of this artist in your library
```


---
### artist_tracks()
> Get the tracks of a specific artist that are in your library.
>
> Args:
> - id (str): The ID of the artist.
>
> Scope: `library:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.library.artist_tracks("Artist ID") # Tracks of this artist in your library
```


---
### playlists()
> Get all your playlists, or a specific playlist by ID.
>
> If a search string is provided, filter the playlists by name containing the search string (case- and accent-insensitive).
> If both search and id are provided, an `InvalidArgumentError` is raised (before any request is sent).
>
> Args:
> - search (str, optional): A string to filter playlists by name. Defaults to None.
>   - search is just for finding playlists by name, while id is for fetching a specific playlist.
> - id (str, optional): The ID of a specific playlist. Defaults to None.
>   - id is for fetching all data and tracks of a specific playlist, while search is just for finding playlists by name.
>
> Scope: `playlists:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.library.playlists()                       # Fetch all your playlists
    client.get.library.playlists(search="Playlist name") # Playlists whose name matches
    client.get.library.playlists(id="Playlist ID")       # All data and tracks of one playlist
```





## GET in global app

Fetch data from the global Volta catalog.
These routes also work without any token (public access), `catalog:read` only matters for personalised results.
To read your own library, use [`get.library`](#get-in-your-library) instead.

#### Base:
```python
VoltaClient.get.catalog.
```

---
### search()
> Search for tracks, albums, artists, and playlists globally.
>
> Args:
> - query (str): The search query string. Special characters (`&`, `#`, `/`...) are URL-encoded automatically.
>
> Scope: `catalog:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.search("AC/DC & Queen") # Search tracks, artists, albums, playlists
```

---
### artist()
> Get details of a specific artist by their ID.
> Get famous tracks, all albums, and all related information.
>
> Args:
> - id (str): The ID of the artist.
>
> Scope: `catalog:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.artist("Artist ID")
```


---
### album()
> Get details of a specific album by its ID.
> Get all tracks of the album.
>
> Args:
> - id (str): The ID of the album.
>
> Scope: `catalog:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.album("Album ID")
```


---
### track()
> Get metadata of a specific track by its ID.
>
> Args:
> - id (str): The ID of the track.
>
> Scope: `catalog:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.track("Track ID")
```


---
### playlist()
> Get details of a public or shared playlist by its ID.
> Get all tracks of the playlist.
>
> Args:
> - id (str): The ID of the playlist.
>
> Scope: `catalog:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.playlist("Playlist ID")
```


---
### home()
> Get the home page data,
> including recommended tracks, albums, artists, and playlists.
>
> Scope: `catalog:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.home()
```


---
### stream()
> Get the track info and a short-lived streaming URL.
> `stream_url` is an opaque reference to the Volta backend (`/api/v1/stream_relay_ref?ref=...`), resolved server-side.
> There is no raw audio download.
>
> Args:
> - id (str): The ID of the track.
>
> Scope: `stream:read` (limited to 10 requests / minute)

#### Use:
```python
with VoltaClient() as client:
    info = client.get.catalog.stream("Track ID")
    info["stream_url"]
```


---
### state()
> Get what is playing right now on your account: track, position, device, shuffle and repeat mode.
> When nothing is playing, you still get a normal response with `is_playing: False` and the other fields set to `None`.
>
> To get the live position without calling the API again: `progress_ms + (now_ms - server_time_ms)`.
>
> Scope: `playback:read`

#### Use:
```python
with VoltaClient() as client:
    state = client.get.catalog.state()
    if state["is_playing"]:
        print(state["item"]["title"], "on", state["device"]["name"])
```


---
### me()
> Get the current user's public profile:
> `sub` (user ID), `name`, `preferred_username`, `nickname` and `picture` (avatar URL).
> The email address is never returned.
>
> Scope: `profile:read`

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.me()
```


## Generic GET

Call any GET route that has no dedicated method:

```python
with VoltaClient() as client:
    client.get.request("/api/v1/some/other/endpoint")
```
