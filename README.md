To download the archive of variety and acrostic puzzles from the New York Times:

1. Go to https://www.nytimes.com/crosswords and log in.
2. From the JavaScript console, run the following command:

```js
copy(new Map(document.cookie.split("; ").map(c=>[c.slice(0,c.indexOf("=")),c.slice(c.indexOf("=")+1)])).get("NYT-S"));
```

3. Paste into a new text file called `nyt-s.txt` in the main directory.
4. Run `python nyt.py`.

Interactive puzzles will be saved as `.jpz` files. You can use the [Crossword Nexus solver](https://crosswordnexus.com/solve/) to open them.
