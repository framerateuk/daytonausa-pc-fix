# Daytona USA (PC, 1996) on modern PCs and the Steam Deck

## Why this exists

The arcade classic, ported to the Saturn, ported to the PC. It runs a little better than the Saturn
version but keeps that great original handling model. I spent most of my time with the Deluxe /
Championship Circuit Edition, but this version definitely handles better! On modern systems it looks
for its CD, loses the announcer, stops its music after a change of track, and ignores half of a
modern pad. This kit sorts that out, so it can be played again.

## What this does

Turns **your own** Daytona USA PC CD (the original 1996 Windows 95 port, not Deluxe) into a folder
that runs on the Steam Deck (Proton) or on Windows 10/11, with no installer and no registry entries:

- **Copied straight from the CD**: what the installer copied, so no CD is needed. The announcer and
  jingles (`MUSIC.BIN`), which the game read from the CD drive, come from the game folder too.
- **CD soundtrack** from OGG files ripped from your disc, with fixes so the music keeps looping and
  doesn't stop after a change of track, and each track cut so the game's track starts land exactly.
- **No black bars on the Steam Deck**: the game draws a 16:10 picture inside a 4:3 mode, so it fills
  the Deck's screen with nothing cut or stretched (thin bars at the sides on a 16:9 monitor).
- **Gamepad**: analogue steering on the left stick (with a dead zone), the D-pad, both triggers as
  accelerate and brake, and the buttons laid out from the start. No Steam Input set-up needed.
- **No busy wait**: the frame timer used to keep a CPU core at 100%.

**No game files are in this repository.** Everything from the game comes from your disc when you
run `build.py`.

## What you need

| | |
|---|---|
| The game | The **Daytona USA PC CD** (Sega, 1996; `GAME\DAYTONA.EXE` of 18 October 1996, "Daytona USA Native" 1.0) as `.cue` + `.bin` or CloneCD `.ccd` + `.img`, with its 21 audio tracks. `build.py` checks the exe and stops on another version (Daytona USA Deluxe is a different game and isn't supported). |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases) (tested with v2025.01.16). Keep the zip as downloaded. |

## Build

```
python3 build.py DAYTONAUSAPC.cue --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `DaytonaUSA/` with `game/` and `daytona_launch.sh` (for the Steam Deck), in about a minute.
The same `game/` folder runs on Windows; `--windows` leaves out the launch script. `--out DIR` puts
the result somewhere else. The disc's original exe and settings file are kept in `game/_spare/`.

## Play on the Steam Deck

1. Copy `DaytonaUSA/` to the Deck, for example to `/home/deck/Games/DaytonaUSA/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse > `.../DaytonaUSA/game/DAYTONA.EXE`. Rename
   the shortcut "Daytona USA".
3. Properties > Compatibility: force **Proton 9.0**. Pin it rather than floating on Experimental.
4. Properties > Launch Options:
   ```
   /home/deck/Games/DaytonaUSA/daytona_launch.sh %command%
   ```
5. Controller layout: the standard **Gamepad** layout. The game reads the pad itself.

## Play on Windows

Run `game/DAYTONA.EXE`. An Xbox pad works as on the Deck.

## Controls

| Pad | Does | Keyboard |
|---|---|---|
| Left stick (analogue) or D-pad (full lock) | steer | arrows |
| RT or A | accelerate; choose in menus | X |
| LT or B | brake; back in menus | Z |
| RB / LB | next / previous view | S / A (F5-F8 a view directly) |
| Y / X | shift up / down (manual gearbox) | V / C |
| Start (Menu) | start, pause | Enter (Esc in a race) |
| In pause: hold Y + LB + RB | restart the race / skip a replay | in pause: hold V + A + S |
| X + B + A + Start | back to the title | Alt+R |
| | quit | Alt+F4 |

Holding both triggers cancels out, since they share one axis: use A with LT, or A and B. Esc is the
game's pause and back key, so it doesn't quit; Alt+F4 does (or Steam's Exit Game). Options > KEY
ASSIGN in the game has other layouts (types B-D).

## Settings

`game/DAYTONA.INI` holds the settings; the kit's copy sets the pad with analogue steering, the
layout above and the farthest draw distance. Saves go in `game/DAYTONA.DAT`.

- Pad layout: `[Joystick]` (Saturn button = function), or Options > KEY ASSIGN.
- Digital steering: `[Input] Device=PC_ANALOG`. Keyboard only: `[Input] Device=KEYBOARD`.
- Draw distance: `[Screen] ClipLevel` 0 Normal, 1 Wide, 2 Vast (the kit's).
- The 4:3 picture of a 1996 monitor instead: in `game/dgVoodoo.conf` empty `DisplayROI =` and
  `ScalingMode = stretched_4_3`, with `[Screen] Window=Full` in the INI. Just the black bars back:
  empty `DisplayROI =`.
- Sharp pixels: `Resampling = pointsampled` in `game/dgVoodoo.conf`.
- Music level: `CDDAVolume` in `game/winmm.ini`.
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  DirectDraw instead of dgVoodoo.

## Troubleshooting

- *"Please insert DAYTONA USA CD."*: you're running the unpatched exe from `_spare/`.
- *No music*: on the Deck `launch.log` must show `WINEDLLOVERRIDES=winmm=n,b;...` (no log: the
  launch option is missing `%command%`), and `game/Music/Track02.ogg` must exist.
- *A track starts with a blip of the previous one*: the OGGs were changed or re-encoded; rebuild,
  so each is padded to whole 40 ms again.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files, patches the exe, rips and pads the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained (the new routines' source is in its comments); also runs on its own. |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 and audio tracks. |
| `config/` | The game's settings with the pad set up, and dgVoodoo2's. |
| `steamdeck/daytona_launch.sh` | Proton launch wrapper: DLL overrides. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Sega** made and published the PC port of Daytona USA. Please own the game: this kit needs your
  disc.
- **Dege**: dgVoodoo2. **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
