# How it works

Notes on the original PC port of Daytona USA (Sega, 1996), `GAME\DAYTONA.EXE` 726,528 bytes, linked
18 October 1996, "Daytona USA Native" 1.0, MD5 `60a7746212a4909d85d61f08869fa063`. Addresses are
virtual addresses in that exe. `patch_exe.py` holds each patch with the source of its new routines.

## The disc

Track 1 is the data track; tracks 2-22 are the music. The installer copied `GAME\` to
`C:\SEGA\DAYTONA`. `build.py` copies the same, with the English help and readme from `HLP\`.
Everything is opened by bare name from the working directory: the data files, the saves
(`DAYTONA.DAT`), the resource DLL (`RES_USA.DLL`, picked by the system language: German, Spanish,
French, else English). The exe already asks for `.\DAYTONA.INI`, so the settings live in the game
folder without a patch.

## Disc check (nocd, musicbin)

WinMain (0x437c60) calls 0x43a260 before the window opens: 0x43a1d0 scans drives A: to Z: for the
first CD-ROM drive holding `GAME\DAYTONA.EXE` ("Please insert DAYTONA USA CD."). The drive index
(0x48ab84, initially -1) is used twice more: the CD audio open (-1 gives the plain `cdaudio` device)
and `"%c:\GAME\MUSIC.BIN"` (0x48ca3c). `nocd` returns 1 at once (the dead scan becomes room for the
other patches' routines, 0x43a1d0..0x43a293) and calls `timeBeginPeriod(1)` once; `musicbin` makes
the path `.\MUSIC.BIN`. `MUSIC.BIN` isn't CD music: three banks of raw 8-bit clips, the announcer and
jingles, played through DirectSound. With no CD drive there would have been no voices.

## CD audio (cdnotify, cdplay) and the track lengths

The CD module (0x456770..0x457200) opens `cdaudio` by type string, reads every track's position
into a table and plays track N "from the position of track N to the position of track N+1", with
notify while CD Loop is on; `MM_MCINOTIFY` replays the track. Two places relied on Windows'
`MCI_NOTIFY_ABORTED` for a stopped play, which ogg-winmm never sends (it notifies only a natural
end):

- Every stop of a playing track added one to a count of notifications to swallow (0x456e75,
  0x456b91), so after any change of track the next natural end was swallowed and the music stopped
  instead of looping. `cdnotify` removes the two increments.
- When `_CDPlay` still found the drive playing, it sent `MCI_STOP` and returned, waiting for the
  aborted notification to start the new track (0x457034); that could leave silence. `cdplay` goes
  on to the normal play.

ogg-winmm keeps track starts in milliseconds, the running sum of the OGG durations truncated to
whole ms, and converts to and from the game's MSF (1/75 s frames) rounding down each way. Unless a
start is a multiple of 40 ms (3 frames), it comes back a few ms early and a play begins in the
previous track. `build.py` pads every track with silence to 1,764k + 1 samples (k x 40 ms; at most
40 ms added) after trimming its trailing digital silence, and checks the encoder kept the length.

## Graphics

A software renderer drawing 16-bit pixels into DirectDraw surfaces, exclusive full screen. With
`[Screen] Window=Normal` (shipped) it's a 640x480 mode with the 640x400 picture at line 40, black bars
above and below; `Window=Full` is a 640x400 mode. The 2D and 3D are the Saturn's 352x208 coordinates
scaled to 640x400 (0x454540). No colour-depth check, no port I/O.

dgVoodoo2 2.79.3's `ddraw.dll`: full screen, `stretched_ar`, bilinear, vsync, no frame cap (the game
paces itself), and `DisplayROI = 16_10, pos:centered`: dgVoodoo shows only the middle 640x400 of the
640x480 mode, the game's whole picture, scaled to the screen. That's the picture at square pixels,
as on a 1996 PC in 640x480; a CRT in the 640x400 mode squeezed it to 4:3.

## Frame pacing (idle)

The frame timer (0x41aa20) works in microseconds from `timeGetTime`: 16,666 us in the menus,
50,000 us in a race, so **races run at 20 fps, as on the Saturn**. Until a frame is due it returned 0
and the main loop asked again at once: a core at 100%. `idle` makes the "not due yet" return call
`Sleep(1)` while more than 3 ms are left (the rest is still spun, so pacing is exact), and the
inactive-window branch sleep 1 ms a turn. `Sleep` is found with `GetProcAddress`; the exe doesn't
import it.

## Keys

`[Input]` holds the keyboard bindings (Windows virtual keys). Fixed keys: Enter Start; Esc is Start
(pause) in a race and B (cancel) in the menus, so it doesn't quit; F1 help, F4 the low-res mode,
F5-F8 a view, Alt+R the Saturn soft reset (A+B+C+Start, back to the title), Alt+F4 quits. The kit's
`[Input]` moves V1-V4 from F5-F8 to C V A S, so F5-F8 keep jumping to a view by themselves.

## Pad (steer, buttons, layout, kbd)

`[Input] Device=PC_HANDLE` (shipped) reads joystick 0 once a frame (`joyGetPosEx`, `JOY_RETURNALL`)
and passes the stick's X to the race as an Arcade Racer wheel: analogue steering. Saturn button
functions come from a table (0x488af8) per control type; `[Joystick]` with `Sections=Enable`
rewrites type A from the INI at every start.

- `buttons`: the fixed physical-button code (0x44597d) put Start on the left stick click of an Xbox
  pad. It's now a table, plus the triggers: both report on the Z axis, resting at the centre; below
  0x6000 (the right trigger) adds C (accelerate), above 0xA000 (the left) adds B (brake).
- `steer`: the D-pad (the POV hat, returned but never read) pushes the stick values to their ends in
  8 directions, so it steers at full lock and works in the menus; and the steering gets a 6% dead
  zone with the rest scaled to full lock (a routine at 0x4458c8, in the dead analogue-throttle code).
- `layout`: the same layout baked into control type A's defaults, for when the INI's `[Joystick]`
  isn't applied.
- `kbd`: with `PC_HANDLE` and no joystick, the reader returned nothing, keyboard included; it now
  falls back to the keyboard reader.
