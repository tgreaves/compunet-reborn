# Vintage Oddities

Behaviours inherited from the original client ROM that are quirky but not bugs.

* **Welcome frame lost after editor exit** — The landing page (welcome frame)
  is sent once during login and is not a navigable page. After entering and
  exiting the editor (or any screen-replacing command), the client sends 'P'
  which redisplays the directory listing, not the welcome frame.

* **UCAT: SHOW doesn't work on entries** — After displaying UCAT, attempting
  SHOW on a text entry shows "PLEASE USE BUY". The client reads the page type
  from a fixed screen column and gets the wrong character in UCAT mode.
  LIFE/EXTEND works correctly. Root cause: likely a 1-column offset difference
  between UCAT and normal directory rendering that shifts the type character
  position on screen.
