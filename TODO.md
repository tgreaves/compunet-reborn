# TODO

## Bugs

- **Frame upload sends wrong data when Editor empty**: `$B175` reads from `$8019/$801A`. If the user hasn't entered the Editor and composed content, the pointer may reference uninitialised RAM. Works correctly when user has edited a frame in the Editor before sending.

## Features

- **Sub-directory creation**: Users should be able to create sub-directories under entries they own (DIR on owned non-directory entries).
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
