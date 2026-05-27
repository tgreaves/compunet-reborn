# Vintage Oddities

Behaviours inherited from the original client ROM that are quirky but not bugs.

* **Welcome frame lost after editor exit** — The landing page (welcome frame)
  is sent once during login and is not a navigable page. After entering and
  exiting the editor (or any screen-replacing command), the client sends 'P'
  which redisplays the directory listing, not the welcome frame.

# Known Limitations

* **C64 Ultimate: auto-connect reconnect fails** — After LEAVE, the auto-connect
  client cannot reconnect without reloading the PRG. The Ultimate's SwiftLink
  bridge captures the server's goodbye frame into its AT command buffer, corrupting
  the next ATDT hostname. The manual client (type hostname) is not affected as the
  typing delay allows the bridge buffer to clear. See docs/ultimate-investigation.md.
