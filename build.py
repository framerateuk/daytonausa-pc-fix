#!/usr/bin/env python3
"""Build a ready-to-run Daytona USA folder for modern PCs from your own CD.

Usage:
  python3 build.py DISC.cue|DISC.ccd --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip [--out DIR] [--windows]

  DISC          your Daytona USA PC CD (Sega, 1996, the original Windows 95 port, "Daytona USA Native" 1.0) as
                .cue + .bin or .ccd + .img, with its audio tracks
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm release zip (or folder)
  --out         where to create DaytonaUSA/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, patch_exe

EXE_MD5 = "60a7746212a4909d85d61f08869fa063"            # GAME\DAYTONA.EXE, 18 Oct 1996, "Daytona USA Native" 1.0
PATCHED_MD5 = "cca5f4ba7a6caaf777bcd1d5365d7048"
STEP = 1764                                              # 40 ms at 44.1 kHz


def md5(data): return hashlib.md5(data).hexdigest()


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def last_granule(path):                   # total samples of a single-stream Ogg Vorbis file
    d = open(path, "rb").read(); i = d.rfind(b"OggS")
    return struct.unpack_from("<q", d, i + 6)[0] if i >= 0 else -1


def rip(tracks, music):
    """Each track from its INDEX 01 to the next track's start, minus up to 2 s of digital silence at the end, then
    padded with silence to 1764 * k + 1 samples: exactly k * 40 ms. The game plays a track as "from the position of
    track N to the position of track N+1", positions it asked for in MSF (1/75 s frames); ogg-winmm keeps its track
    starts in whole milliseconds and rounds both ways down, so unless every start is a multiple of 40 ms (3 frames,
    the only exact ms <-> frame steps) a play starts with the last milliseconds of the previous song. The extra
    sample keeps the truncation of k * 0.04 s from falling to 40k - 1 ms."""
    enc = encoder(); os.makedirs(music, exist_ok=True); zero = bytes(2352); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)
            tail = 0
            while tail < 150 and data[len(data) - (tail + 1) * 2352:len(data) - tail * 2352] == zero: tail += 1
            if tail: data = data[:len(data) - tail * 2352]
            samples = len(data) // 4
            target = ((samples - 1 + STEP - 1) // STEP) * STEP + 1 if samples > 1 else 1
            data += bytes(4 * (target - samples))
            wav = os.path.join(tmp, f"track{t.n:02d}.wav"); ogg = os.path.join(music, f"Track{t.n:02d}.ogg")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, ogg), check=True); os.remove(wav)
            if last_granule(ogg) != target: sys.exit(f"Track{t.n:02d}: the encoder changed its length; try oggenc")
            print(f"  Music/Track{t.n:02d}.ogg  {(target - 1) // STEP * 40 / 1000:6.2f} s"); n += 1
    if n != 21: sys.exit(f"expected 21 audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    entries = {p.upper(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk()}
    if "GAME/DAYTONA.EXE" not in entries: sys.exit("no GAME\\DAYTONA.EXE on this CD: it isn't the Daytona USA PC disc")
    got = md5(dt.read_file(*entries["GAME/DAYTONA.EXE"][2:]))
    if got != EXE_MD5:
        sys.exit(f"this CD's DAYTONA.EXE is not the 1996 original port the kit was made for (MD5 {got}); "
                 "Daytona USA Deluxe and others aren't supported")

    pkg = os.path.join(os.path.abspath(a.out), "DaytonaUSA"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    # The disc's GAME\, what the installer copied to C:\SEGA\DAYTONA; everything is opened by bare name from the
    # working directory (MUSIC.BIN too, once patched)
    print("1/5 game files from the CD")
    for key, (p, is_dir, l, s) in entries.items():
        if is_dir or not key.startswith("GAME/") or key.count("/") != 1: continue
        name = p.split("/")[1]
        dst = os.path.join(game, "_spare", "DAYTONA_disc.ini") if key == "GAME/DAYTONA.INI" else os.path.join(game, name)
        dt.copy_file(l, s, dst)
    dt.copy_file(*entries["GAME/DAYTONA.EXE"][2:], os.path.join(game, "_spare", "DAYTONA_retail.exe"))
    for src, dst in [("HLP/DAYTONAE.HLP", "DAYTONAE.HLP"), ("HLP/DAYTONAE.CNT", "DAYTONAE.CNT"),   # F1 help (English)
                     ("HLP/READMEE.TXT", "README.TXT")]:
        dt.copy_file(*entries[src][2:], os.path.join(game, dst))
    shutil.copyfile(os.path.join(HERE, "config", "DAYTONA.INI"), os.path.join(game, "DAYTONA.INI"))  # pad, full screen

    print("2/5 exe patches")
    out = patch_exe.patch(dt.read_file(*entries["GAME/DAYTONA.EXE"][2:]))
    if md5(out) != PATCHED_MD5: sys.exit("patching gave an unexpected DAYTONA.EXE")
    open(os.path.join(game, "DAYTONA.EXE"), "wb").write(out)

    print("3/5 soundtrack (each track padded to whole 40 ms)")
    rip(tracks, os.path.join(game, "Music"))

    print("4/5 wrappers and settings")
    open(os.path.join(game, "ddraw.dll"), "wb").write(take(a.dgvoodoo, "MS/x86/DDraw.dll"))
    for name in ("winmm.dll", "winmm.ini"):
        open(os.path.join(game, name), "wb").write(take(a.ogg_winmm, name))
    shutil.copyfile(os.path.join(HERE, "config", "dgVoodoo.conf"), os.path.join(game, "dgVoodoo.conf"))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "daytona_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "daytona_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
