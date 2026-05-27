# Vintage Oddities

Behaviours inherited from the original client ROM that are quirky but not bugs.

* **Welcome frame lost after editor exit** — The landing page (welcome frame)
  is sent once during login and is not a navigable page. After entering and
  exiting the editor (or any screen-replacing command), the client sends 'P'
  which redisplays the directory listing, not the welcome frame.

# Known Limitations

* **VICE: reconnect after LEAVE fails** — After LEAVE, both SFX and auto-connect
  clients cannot reconnect in the same session (returns to READY after "Dialling").
  VICE's SwiftLink emulation does not re-establish the TCP socket after the
  connection is closed. Workaround: reload the PRG. The manual LOAD+SYS client
  is also affected. Root cause is in VICE's socket lifecycle management.
