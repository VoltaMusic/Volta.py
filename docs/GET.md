# GET method
# Tables
* [In your library](#get-in-your-library)
  * [tracks()](#tracks)
  * [albums()](#albums)
  * [artists()](#artists)
    - [artist_albums()](#artist_albums)
    - [artist_tracks()](#artist_tracks)
  * [playlists()](#playlists)
* [In global app](#get-in-global-app)
  * [search()](#search)
  * [artist()](#artist-1)

## GET in your library

Fetch many data in your library,
you cannot use this for a global use or search.

#### Base:
```python
VoltaClient.get.library.
```

---
### tracks()
> Get all liked tracks.
>
> If a search string is provided, filter the tracks by title containing the search string (case-insensitive).
>
> Args:
> - search (str, optional): A string to filter tracks by title. Defaults to None.

#### Use:
```python
with VoltaClient() as client:
    client.get.library.tracks()             # Fetch all liked song
    client.git.library.tracks("Song Title") # Search all match with the title in your liked song
```


---
### albums()
> Get all liked albums.
>
> If a search string is provided, filter the albums by title containing the search string (case-insensitive).
>
> Args:
> - search (str, optional): A string to filter albums by title. Defaults to None.

#### Use:
```python
with VoltaClient() as client:
    client.get.library.albums()              # Fetch all album in your liked song
    client.git.library.tracks("Album Title") # Search all match with the title album in your liked song
```


---
### artists()
> Get all liked artists.
>
> If a search string is provided, filter the artists by name containing the search string (case-insensitive).
>
> Args:
> - search (str, optional): A string to filter artists by name. Defaults to None.

#### Use:
```python
with VoltaClient() as client:
    client.get.library.artists()             # Fetch all artists followed
    client.git.library.tracks("Artist name") # Search all match with the artists name in your followed
```


---
### artist_albums()
> Get all albums of a specific artist by their ID.
>
> Args:
> - id (str): The ID of the artist.

#### Use:
```python
with VoltaClient() as client:
    client.get.library.artist_albums("Artist id") # Fetch all artist albums
```


---
### artist_tracks()
> Get all tracks of a specific artist by their ID.
>
> Args:
> - id (str): The ID of the artist.

#### Use:
```python
with VoltaClient() as client:
    client.get.library.artist_tracks("Artist id") # Fetch all artist tracks
```


---
### playlists()
> Get all liked playlists or a specific playlist by ID.
>
> If a search string is provided, filter the playlists by name containing the search string (case-insensitive).
> If both search and id are provided, a ValueError will be raised.
>
> Args:
> - search (str, optional): A string to filter playlists by name. Defaults to None.
>   - search is just for finding playlists by name, while id is for fetching a specific playlist.
> - id (str, optional): The ID of a specific playlist. Defaults to None.
>   - id is for fetching all data and tracks of a specific playlist, while search is just for finding playlists by name.

#### Use:
```python
with VoltaClient() as client:
    client.get.library.playlists()                       # Fetch all your playlists
    client.get.library.playlists(search="Playlist name") # Fetch every match with the research
    client.get.library.playlists(id="Playlist id")       # Fetch all data and tracks in one playlist
```





## GET in global app

Fetch data from global,
you cannot use this for fetch your data like before

#### Base:
```python
VoltaClient.get.catalog.
```

---
### search()
> Search for tracks, albums, artists, and playlists globally.

> Args:
> - query (str): The search query string.

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.search("Your query") # Search tracks, artists, albums
```

---
### artists()
> Get details of a specific artist by their ID.
> Get famous tracks, all albums, and all related information.
>
> Args:
> - id (str): The ID of the artist.

#### Use:
```python
with VoltaClient() as client:
    client.get.catalog.artist("Artists ID") # Search with the artists ID
```
