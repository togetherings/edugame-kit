# Accessibility

A game made with the kit should be playable with a keyboard alone, with a screen reader, with colour blindness,
with motion turned down, on a phone, and in the learner's language and keyboard layout. This page says what the
kit does for you, what each game still has to do, and how to check it. SINGE (togetherings/singe) does all of it
and is the example to copy from.

## What the kit does

- **Light, dark and automatic themes** (Options, `<html data-theme>`), and the language choice.
- **The Options panel** holds the keyboard while it's open: Tab stays inside it, Escape cancels, Enter on a choice
  applies, and the keyboard goes back to the Options button when it closes.
- **The starter menu** (`edugame menu`): Tab and Enter, the arrow keys to the nearest package in that direction
  (from nowhere, to "Next"), Home and End to the first and last, and 1-9 for the package with that number.
- **Three helpers** (docs/HELPER.md has the full list of calls):
  - `EduGame.say(text)`: screen readers read the text out. Use it for the prompt, for right and wrong answers, and
    for anything else that changes on the screen without the keyboard moving. `{urgent: true}` interrupts.
  - `EduGame.dialog(el, {close, focus})` → `{open(), close(), isOpen()}`: a panel (help, information, a big
    picture) that holds the keyboard while it's open. Tab stays inside, Escape and a click on its backdrop close
    it, and the keyboard goes back to whatever had it. It marks the panel as a dialog for screen readers.
  - `EduGame.arrowNav(container, selector, {numbers, start})`: the arrow keys move between buttons laid out in a
    grid (any grid, however it wraps on a small screen), Home and End go to the first and last, and with
    `numbers: true` the keys 1-9 press the button with that `data-number`.

```js
var help = EduGame.dialog(document.getElementById("helpBack"), { close: document.getElementById("helpClose") });
document.getElementById("helpButton").onclick = help.open;
EduGame.arrowNav(document.getElementById("levels"), "button.level");
EduGame.say(EduGame.t("find", { name: "Ghana" }));
```

## What a game does

### Keyboard
- **Everything the mouse can do, a key can do.** A board or a map should have the keyboard while it's on screen
  (`tabindex="-1"`, focus it when the round starts, and give it `role="application"` so screen readers pass the
  keys through). Tab and Shift+Tab, or the arrow keys, move a highlight; Enter or Space chooses.
- **Escape closes what's open first** (a panel, then the round), so it never throws the learner out by surprise.
- **Keep the keys you use from the browser:** call `preventDefault()` for every key you handle. Firefox opens
  Quick Find on `/` and `'` when a page doesn't, and Space and the arrows scroll the page.
- **A second key for each action**, chosen for other keyboard layouts. On a French (AZERTY) keyboard `.` and `/`
  need Shift, `;` is unshifted next to `,`, and the number keys type `à é è` without Shift. So:
  - accept both the shifted and unshifted character (`.` and `>`; `?` and `/`), and `;` beside `.`;
  - match digits by the key's place (`e.code === "Digit0"` or `"Numpad0"`), not only `e.key === "0"`;
  - in each language's list of keys, show the keys that are easiest on that language's usual keyboard.
- **Avoid keys the browser keeps for itself** (Ctrl+W, Ctrl+T, F5, F11, F12) and F1, which opens Chrome's help.
- **A list of keys**: a button (⌨) and `?` (and `/`) open it, as a `dialog`. Put the keys in one two-column list
  so they line up, with headings for parts (the menu's keys, the board's keys), and show a row only where it
  applies. Write the keys and what they do in `lang/` like any other words.
- **Where the keyboard goes**: back to the button that opened a panel; back to the level's button when a round
  is left; to "Play again" on the results.
- **A hint the first time**: the first key pressed in a round can show one line of help for a few seconds
  ("Tab or Arrows: Move · Enter: Choose · ?: List of keys").

### Screen readers
- Say the prompt and every right or wrong answer with `EduGame.say`.
- Say what the keyboard highlight is on, but **never give the answer away**: a place not found yet is "a place you
  haven't found yet", not its name.
- A question shown only as a picture (a flag) needs the same question in text for screen readers.
- Every button showing only a symbol (⌨ ⌂ + − ×) needs a name: `aria-label`, in `lang/` (`data-t-attr`).

### Colour
- **Contrast where it matters**: text 4.5:1 against its background; borders, answers and the highlight 3:1 against
  what's next to them (WCAG 2.2, 1.4.3 and 1.4.11). Backgrounds and things that aren't in play can be calm and low
  in contrast.
- **Don't let colour carry meaning alone.** Pair it with an outline, a mark, a word or a pattern. In SINGE the
  highlight is a thick two-colour outline drawn above every border, so it shows on any colour.
- **Colours that stay apart with colour blindness**, from the palettes below, that also differ in lightness. Use at
  most about 8 colours for things that must be told apart.
- **Check them**: simulate deuteranopia, protanopia and tritanopia (the Machado, Oliveira and Fernandes 2009
  matrices) and make sure every pair that must be told apart is still far apart (a CIELAB ΔE of about 20 or more).
- Give the dark theme its own colours rather than inverting the light ones, and check both.
- Make hover and keyboard focus look the same, so keyboard players see what a mouse player sees.

### Motion
- Anything that flashes or pulses must still make sense without it, and stop under
  `@media (prefers-reduced-motion: reduce)`.

### Touch and small screens
- Labels and tips must stay on the screen: open them on the other side of the finger near an edge.
- Make small targets bigger than they look (a ring at least 26 pixels across around a small place).

## Colour-blind-friendly palettes

These are the palettes compared in Joachim Goedhart's
[Data visualization with flying colors](https://thenode.biologists.com/data-visualization-with-flying-colors/research/)
(The Node, 2019), with the colours of each. His advice: Okabe-Ito is a good first choice, but no palette suits
everything, so test yours in the real game. The colours come from
[Okabe and Ito's Color Universal Design](https://jfly.uni-koeln.de/color/) and
[Paul Tol's colour schemes](https://personal.sron.nl/~pault/); Tol says his bright, vibrant and muted schemes are
colour-blind safe, and the light one is for filling labelled areas.

**Okabe-Ito** (8 colours)

| Black | Orange | Sky blue | Bluish green | Yellow | Blue | Vermillion | Reddish purple |
|---|---|---|---|---|---|---|---|
| `#000000` | `#E69F00` | `#56B4E9` | `#009E73` | `#F0E442` | `#0072B2` | `#D55E00` | `#CC79A7` |

**Paul Tol: bright** (7)

| Blue | Cyan | Green | Yellow | Red | Purple | Grey |
|---|---|---|---|---|---|---|
| `#4477AA` | `#66CCEE` | `#228833` | `#CCBB44` | `#EE6677` | `#AA3377` | `#BBBBBB` |

**Paul Tol: vibrant** (7)

| Blue | Cyan | Teal | Orange | Red | Magenta | Grey |
|---|---|---|---|---|---|---|
| `#0077BB` | `#33BBEE` | `#009988` | `#EE7733` | `#CC3311` | `#EE3377` | `#BBBBBB` |

**Paul Tol: muted** (9, and pale grey for missing data)

| Indigo | Cyan | Teal | Green | Olive | Sand | Rose | Wine | Purple | Pale grey |
|---|---|---|---|---|---|---|---|---|---|
| `#332288` | `#88CCEE` | `#44AA99` | `#117733` | `#999933` | `#DDCC77` | `#CC6677` | `#882255` | `#AA4499` | `#DDDDDD` |

**Paul Tol: light** (9; for backgrounds of labelled areas)

| Light blue | Light cyan | Mint | Pear | Olive | Light yellow | Orange | Pink | Pale grey |
|---|---|---|---|---|---|---|---|---|
| `#77AADD` | `#99DDFF` | `#44BB99` | `#BBCC33` | `#AAAA00` | `#EEDD88` | `#EE8866` | `#FFAABB` | `#DDDDDD` |

**Paul Tol: high contrast** (3, with white and black): blue `#004488`, yellow `#DDAA33`, red `#BB5566`. For
when a few colours must also work printed in black and white.

### What SINGE uses
Answers are Okabe-Ito **bluish green `#009E73`** (first try), **yellow `#F0E442`** (a later try) and
**vermillion `#D55E00`** (needed the hint), in both themes. They differ in lightness as well as hue, and the
closest pair is still about ΔE 34 apart in all three simulations. A real yellow can't reach 3:1 against light
land, so in the light theme yellow is the one answer that relies on its outline. Before choosing these SINGE tried
Tol's bright green `#228833` with vermillion for a darker dark theme, which came out too close (ΔE about 10) in a
simulation, and blue and orange (the pairing Wordle's high contrast mode uses), which left no clear third colour.

The rest of SINGE's colours, for reference:

| | Light | Dark |
|---|---|---|
| Page and sea | `#d6e9f5` | `#0b1d2e` |
| Text and borders | `#000000` | `#ffffff` |
| Cards and buttons | `#ffffff` | `#17314a` |
| Land not answered | `#f5f3ec` | `#2a2a2a` |
| Land not in the game | `#e4e4e4`, edge `#a8a8a8` | `#34404c`, edge `#4b5a69` |
| Button hover (white text) | teal `#1f6f8b` | teal `#2f7f9f` |

## Checking

- Play a whole round with the keyboard only, then with a screen reader (NVDA or VoiceOver).
- Turn on "reduce motion" in the system settings and play again.
- Look at every screen in light and dark, and through a colour-blindness simulator.
- In Firefox, check that no key you use opens Quick Find.
- A browser test can press the keys (Playwright's `page.keyboard.press`) and check where the keyboard is
  (`document.activeElement`); SINGE's `check_keyboard` in tests/e2e_browser.py is an example.

## Coming next

The kit will take a game's list of keys and do the rest: a ⌨ button beside Options in its header, the list of keys
(lined up, in parts, per language), `?` and `/`, the order Escape closes things in, digits by the key's place, and
the first-key hint. Until then, a game does these itself as above.
