# Vintage Oddities

Behaviours inherited from the original client ROM that are quirky but not bugs.

* **Welcome frame lost after editor exit** — The landing page (welcome frame)
  is sent once during login and is not a navigable page. After entering and
  exiting the editor (or any screen-replacing command), the client sends 'P'
  which redisplays the directory listing, not the welcome frame.
