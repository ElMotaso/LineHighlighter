Write a program in python that transforms the cursor into a transparent but highlighting bar so users can easier stay in a line while reading. use python for that. also provide a small window where users can set the width, height, transparency and colour. the program should run on macos, linux and windows. do it in whatever means you deem most practical.

current issues (assume all other issues known to you are solved if you dont find them here):
- bar is a square in the top left corner that does not move with the cursor
- the shortcut does not quit the program
- i can not scroll or click anything beneath the bar
- as soon as i press start i get this error:
"U:\Pcharm Projects\LineHighlighter\.venv\Scripts\python.exe" "U:\Pcharm Projects\LineHighlighter\highlighter.py" 
Exception in Tkinter callback
Traceback (most recent call last):
  File "C:\Users\thomas.moissl\AppData\Local\Programs\Python\Python39\lib\tkinter\__init__.py", line 1892, in __call__
    return self.func(*args)
  File "U:\Pcharm Projects\LineHighlighter\highlighter.py", line 96, in start
    self.register_abort_key()
  File "U:\Pcharm Projects\LineHighlighter\highlighter.py", line 113, in register_abort_key
    self.overlay.bind_all(f'<{key}>', self.stop)
  File "C:\Users\thomas.moissl\AppData\Local\Programs\Python\Python39\lib\tkinter\__init__.py", line 1406, in bind_all
    return self._bind(('bind', 'all'), sequence, func, add, 0)
  File "C:\Users\thomas.moissl\AppData\Local\Programs\Python\Python39\lib\tkinter\__init__.py", line 1346, in _bind
    self.tk.call(what + (sequence, cmd))
_tkinter.TclError: bad event type or keysym "esc"