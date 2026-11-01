#!/usr/bin/env python3
"""Patch Daytona USA's exe in place (the PC disc's GAME\\DAYTONA.EXE, 726,528 bytes,
MD5 60a7746212a4909d85d61f08869fa063, linked 18 Oct 1996, "Daytona USA Native" 1.0).

  patch_exe.py game/DAYTONA.EXE

Applies every patch not yet applied and reports each; refuses (writes nothing) on unexpected bytes.
docs/TECHNICAL.md has more on each one. The routines were assembled with clang (i686,
Intel syntax); their source is in the comments below. Absolute addresses: the exe always loads at
0x400000 (its .reloc does not cover the new code; harmless).

  nocd     0x43a260 (WinMain 0x437dd1, before the window: 0x43a1d0 scans drives A: to Z: for a DRIVE_CDROM
           holding GAME\\DAYTONA.EXE; none: "Please insert DAYTONA USA CD." Retry/Cancel) jumps to a stub that
           calls timeBeginPeriod(1) and returns 1. The drive index 0x48ab84 keeps its -1, which the game
           already treats as "no drive" for CD audio (0x456970 opens the plain "cdaudio" device instead of
           "X:"). The dead scan and check (0x43a1d0..0x43a296) become the cave for the routines below.
           timeBeginPeriod (looked up with GetModuleHandleA("WINMM.dll") + GetProcAddress, the exe imports
           neither it nor Sleep) gives timeGetTime, which paces the game, and Sleep(1) 1 ms resolution on
           Windows; Wine has that already.
  musicbin "%c:\\GAME\\MUSIC.BIN" (0x48ca3c, wsprintf'd with the CD drive letter at 0x43ec2c) becomes
           ".\\MUSIC.BIN": the announcer, jingles and other 8-bit PCM sample banks the sound code
           (0x43eac0, commands 0xae10xxxx from 0x41f2dc) streams through DirectSound. The only other use of
           the drive letter; every other file is opened by bare name from the working directory.
  cdnotify the CD player loops tracks from the MM_MCINOTIFY handler (0x439250 -> 0x456f00, "CD repeat"); each
           MCI_STOP of a playing track (0x456e20 before every new track, 0x456b50 at exit) added one to
           0x494fe8, the number of notifications to swallow, because Windows answers a stopped play with
           MCI_NOTIFY_ABORTED. ogg-winmm sends a notification only when a track ends by itself, so after
           every change of track the next natural end was swallowed: the music stopped instead of looping.
           The two inc [0x494fe8] (0x456e75, 0x456b91) become nop.
  cdplay   _CDPlay (0x456fc0, run one main-loop turn after cd_play 0x43f540 stopped the old track) found the
           drive still in MCI_MODE_PLAY, sent MCI_STOP and returned, leaving the new track to the
           MCI_NOTIFY_ABORTED that ogg-winmm never sends: silence. ogg-winmm's stop returns before its
           player thread sets the mode to stopped, so this race is real. 0x457057 (after that MCI_STOP)
           jumps on to the normal play path 0x457062 instead of returning.
  idle     the frame timer 0x41aa20 (microseconds from timeGetTime; 16,666 us a frame in menus, 50,000 us
           in the race: 20 fps like the Saturn, table 0x469a48 indexed by mode byte 0x4870c8) returns 0
           while the frame is not due and the main loop (0x437f5e: PeekMessage, then 0x43a2a0) asks again at
           once: one core flat out (hot Deck, fans). The "not due" return 0x41aaf7 now sleeps 1 ms first
           while more than 3 ms of the frame are left, so pacing stays exact. The loop also spun while the
           window was inactive (0x437f92, [0x48abe4] = 0, WM_ACTIVATEAPP 0x4393b0); it sleeps 1 ms a turn.
  steer    PC_HANDLE (wheel) mode, the shipped one, is the analogue steering mode: the reader 0x445830 puts
           255 - (AXIS_LR >> 8) into 0xc577b4 and sets the analogue flag 0xc577b6 (0x445bbb), and the race
           (translated Saturn code, 0x41bd55) steers by (byte - 128), as with the Saturn Arcade Racer
           wheel. No dead zone: a stick off centre by 1/256 already steers. 0x4458a5 calls a routine at
           0x4458c8 (the reader's analogue-throttle code 0x4458c6..0x445942, dead: its result 0xc577d0 is
           written and never read, so it is skipped with a jmp): a pressed D-pad (POV hat; the reader asks
           joyGetPosEx for everything, flags 0xff, but ignored dwPOV) pushes the AXIS_LR / AXIS_UD values
           to their ends, 8 directions, so the D-pad steers and moves through the menus; then the steering
           byte gets a 6 % dead zone with the rest scaled back to full lock: c = (LR - 0x8000) >> 8,
           |c| <= 8 -> 0, else (|c| - 8) * 17 / 16 with its sign, byte = 128 - c (255 full left, 2 full right).
  buttons  the reader's fixed mapping of joystick buttons to Saturn pad bits (0x44597d..0x4459de: b1 A, b2 B,
           b3 C, b4 X, b5 Y, b6 Z, b7 R, b8 L, b9 Start) put Start on the left stick click of an Xbox pad and
           read no triggers. Now a table at 0x4459c0 (Xbox order under Proton and Windows): A -> C, B -> B,
           X -> A, Y -> X, LB -> Y, RB -> Z, View -> R, Menu -> Start, L3 -> Start, R3 -> L; and the Z axis
           (both triggers on one axis, resting at the centre; only if JOYCAPS_HASZ): below 0x6000 (right
           trigger past a quarter) -> C, above 0xA000 (left trigger) -> B. Saturn C and B are accelerate and
           brake (control type A) and decide / cancel in the menus. DAYTONA.INI [Joystick] maps the Saturn
           buttons to the game's functions (docs/TECHNICAL.md, "Pad").
  layout   control type A's defaults in the function table (0x488af8: 15 words per entry, the Saturn button mask
           of NO USE, ACCELERATE, BRAKE, GEAR 1-4, VIEW DOWN, VIEW UP, VIEW 1-4, SHIFT DOWN, SHIFT UP; entry 0 pad,
           entry 5 wheel) become C accelerate, B brake, Y / Z view down / up, A / X shift down / up, for both
           groups: Xbox A / RT accelerate, B / LT brake, LB / RB views, X / Y gears. First Deck run (17 Oct 2026)
           had the wheel defaults (brake Z = RB, views Y / B = LB / LT) although DAYTONA.INI [Joystick] said
           otherwise: the INI rewrite of the table (0x412280) did not reach the active layout (set_button
           0x4319c0 via 0x45d3b0 copies the table into the game's variables; why it kept the defaults is open).
  kbd      with Device=PC_HANDLE and no joystick 0 the reader returned nothing and the keyboard was dead too.
           The reader's call (0x445bc9) goes through 0x43a262: no joystick -> the keyboard reader 0x445670
           with the analogue flag cleared (digital steering), so the Windows zip plays on a keyboard too.
"""
import os, sys

def s(text, size):                     # string patch, NUL-padded to the original's room
    b = text.encode() + b"\0"
    assert len(b) <= size
    return b + b"\0" * (size - len(b))

def rel32(src, dst):                   # e8/e9 at src (5 bytes) -> dst
    return (dst - (src + 5)).to_bytes(4, "little", signed=True)

TEXT = 0x400c00                        # .text: VA 0x401000 at file offset 0x400
DATA = 0x401800                        # .data: VA 0x481000 at file offset 0x7f800

# 0x43a1d0..0x43a293 (the dead CD scan 0x43a1d0 and CD check 0x43a260), assembled at 0x43a1d0:
#   43a1d0 sleep1: push "KERNEL32.dll" (0x11d7f34, the import name) / call [GetModuleHandleA] / push "Sleep" /
#                  push eax / call [GetProcAddress] / test eax,eax / jz r / push 1 / call eax / r: ret
#   43a1f0 timer:  push "WINMM.dll" (0x11d7a84) / call [GetModuleHandleA] / test / jz r / push "timeBeginPeriod"
#                  / push eax / call [GetProcAddress] / test / jz r / push 1 / call eax / r: mov eax,1 / ret
#   43a219 idlef:  fld qword [ebx*8+0x469a48] (frame interval) / fsub qword [0x498e58] (elapsed) /
#                  fcomp dword [3000.0] / fnstsw ax / test ah,0x41 / jnz k / call sleep1 /
#                  k: xor eax,eax / pop ebp / pop edi / pop esi / jmp 0x41aafc
#   43a242 idlei:  cmp dword [0x48abe4],0 / jne 0x437f9b / call sleep1 / jmp 0x437f5e
#   43a260 nocd:   jmp timer        (int3 padding before it)
#   43a262 kbdw:   push 0 / call 0x412580 (JOYCAPS of joystick 0, or 0) / pop ecx / test eax,eax / jz k /
#                  jmp 0x445830 / k: xor esi,esi / jmp 0x445670
#   43a27a 3000.0f, "Sleep", "timeBeginPeriod"
CAVE_OLD = bytes.fromhex(
    "83ec5053565733db55ff15d0731d018be88b35d4731d018b3dd8731d01b8010000008acbd3e085c574418d43418d4c2410"
    "506860af480051ff15d0741d018d4c241c83c40c51ffd783f805751e8d442410684caf480050ff1504741d018d4424106a"
    "0050ffd683f8ff75084383fb207caceb0750ff15dc731d01b8ffffffff83fb2074028bc35d5f5e5b83c450c3cccc568b35"
    "60741d01e864ffffffa384ab480083f8ffa1c0ab480075156a35506868af48006a00ffd683f80275db33c05ec3b8010000")
CAVE = bytes.fromhex(
    "68347f1d01ff15a4731d01687ea2430050ff15b0731d0185c074046a01ffd0c368847a1d01ff15a4731d0185c07414688"
    "4a2430050ff15b0731d0185c074046a01ffd0b801000000c3dd04dd489a4600dc25588e4900d81d7aa24300dfe0f6c441"
    "7505e898ffffff31c05d5f5ee9ba08feff833de4ab4800000f854cddffffe87cffffffe905ddffffcccccccccccccceb8e"
    "6a00e81783fdff5985c07405e9bdb5000031f6e9f6b3000000803b45536c6565700074696d65426567696e506572696f6400")
SLEEP1, IDLEF, IDLEI, KBDW = 0x43a1d0, 0x43a219, 0x43a242, 0x43a262

# 0x4458c8 steer (in the dead analogue-throttle code; 0x4458c6 jmp 0x445943 skips it):
#   push eax / push edx / mov eax,[eax+0x28] (dwPOV) / cmp eax,36000 / jae dz / add eax,2250 / xor edx,edx /
#   mov ebp,4500 / div ebp / movzx eax, byte [eax+tbl] / test al,1: xor edi,edi / test al,2: mov edi,0xffff /
#   test al,4: xor ecx,ecx / test al,8: mov ecx,0xffff /
#   dz: lea eax,[ecx-0x8000] / sar eax,8 / cdq / xor eax,edx / sub eax,edx / sub eax,8 / jg s / xor eax,eax /
#   s: imul eax,eax,17 / shr eax,4 / xor eax,edx / sub eax,edx / neg eax / sub eax,-128 / pop edx /
#   mov [edx],ax / pop eax / ret / tbl: 1,9,8,10,2,6,4,5,1 (octant -> 1 up, 2 down, 4 left, 8 right)
STEER_OLD = bytes.fromhex(
    "f60539661b01f07474f60539661b0110741181ff008000007309baff7f00002bd7eb17f60539661b0120741781ff0080000076"
    "0f8d910080ffffc1ea078815d077c500f60539661b0180741081f90080000076088d910080ffffeb18f60539661b014074188"
    "1f9008000007310baff7f00002bd1")
STEER = bytes.fromhex("eb7b") + bytes.fromhex(
    "50528b40283da08c0000733305ca08000031d2bd94110000f7f50fb68031594400a801740231ffa8027405bfffff0000a8047402"
    "31c9a8087405b9ffff00008d810080ffffc1f8089931d029d083e8087f0231c06bc011c1e80431d029d0f7d883e8805a66890258"
    "c30109080a0206040501")

# 0x44597d buttons (to 0x4459de, then on at 0x4459df as before):
#   mov ecx,[eax+0x20] (dwButtons) / mov edx,tbl / l: shr ecx,1 / jnc n / movzx edi,word [edx] / or esi,edi /
#   n: add edx,2 / cmp edx,tbl_end / jb l / test byte [ebx+0x60],1 (JOYCAPS wCaps & JOYCAPS_HASZ) / jz e /
#   mov ecx,[eax+0x10] (dwZpos) / cmp ecx,0x6000 / jae h / or esi,0x200 / h: cmp ecx,0xa000 / jbe e /
#   or esi,0x100 / e: jmp 0x4459df / tbl (0x4459c0, buttons 1..10): C, B, A, X, Y, Z, R, Start, Start, L
BUTTONS_OLD = bytes.fromhex(
    "8b4020a801740681ce00040000a802740681ce00010000a804740681ce00020000a808740383ce40a810740383ce20a8207403"
    "83ce10a84074168b4b3c83f907750881ce00080000eb0681ce80000000a880740383ce08f6c401740681ce00080000")
BUTTONS = bytes.fromhex(
    "8b4820bac0594400d1e973050fb73a09fe83c20281fad459440072ecf6436001741f8b481081f900600000730681ce0002000081"
    "f900a00000760681ce00010000eb1f"
    "0002" "0001" "0004" "4000" "2000" "1000" "8000" "0008" "0008" "0800"   # tbl: A..R3 (little-endian words)
    "cccccccccccccccccccccc")

PATCHES = {
    "nocd":     [(0x43a1d0 - TEXT, CAVE_OLD[:len(CAVE)], CAVE)],
    "musicbin": [(0x48ca3c - DATA, s("%c:\\GAME\\MUSIC.BIN", 20), s(".\\MUSIC.BIN", 20))],
    "cdnotify": [(0x456e75 - TEXT, bytes.fromhex("ff05e84f4900"), b"\x90" * 6),
                 (0x456b91 - TEXT, bytes.fromhex("ff05e84f4900"), b"\x90" * 6)],
    "cdplay":   [(0x457057 - TEXT, bytes.fromhex("5e5b"), bytes.fromhex("eb09"))],              # jmp 0x457062
    "idle":     [(0x41aaf7 - TEXT, bytes.fromhex("33c05d5f5e"), b"\xe9" + rel32(0x41aaf7, IDLEF)),
                 (0x437f92 - TEXT, bytes.fromhex("833de4ab48000074c3"), b"\xe9" + rel32(0x437f92, IDLEI) + b"\x90" * 4)],
    "steer":    [(0x4458a5 - TEXT, bytes.fromhex("8be9c1ed0866f7d56681e5ff0066892a"),
                  b"\xe8" + rel32(0x4458a5, 0x4458c8) + b"\x90" * 11),
                 (0x4458c6 - TEXT, STEER_OLD, STEER)],
    "buttons":  [(0x44597d - TEXT, BUTTONS_OLD, BUTTONS)],
    "layout":   [(0x488af8 - DATA, bytes.fromhex("000000020001000000000000000008008000000000000000000000100020"), bytes.fromhex("000000020001000000000000000020001000000000000000000000044000")),               # pad TYPE A
                 (0x488af8 + 5 * 30 - DATA, bytes.fromhex("000000021000000000000000000020000001000000000000000000100020"), bytes.fromhex("000000020001000000000000000020001000000000000000000000044000"))],  # wheel TYPE A
    "kbd":      [(0x445bc9 - TEXT, bytes.fromhex("e862fcffff"), b"\xe8" + rel32(0x445bc9, KBDW))],
}
assert len(CAVE) == 196 and len(STEER) == len(STEER_OLD) == 116 and len(BUTTONS) == len(BUTTONS_OLD) == 98

def patch(data, label="DAYTONA.EXE"):
    """Returns `data` with every patch applied; exits (nothing written) on unexpected bytes."""
    data = bytearray(data)
    if len(data) != 726528: sys.exit(f"{label}: {len(data)} bytes, expected 726528; nothing written")
    for pname, edits in PATCHES.items():
        state = set()
        for off, old, new in edits:
            assert len(old) == len(new), pname
            cur = bytes(data[off:off + len(old)])
            state.add("new" if cur == new else "old" if cur == old else "bad")
        if state == {"new"}: print(f"  {pname}: already applied"); continue
        if state != {"old"}: sys.exit(f"{label}: {pname}: unexpected bytes, not this exe? nothing written")
        for off, old, new in edits: data[off:off + len(new)] = new
        print(f"  {pname}: applied")
    return bytes(data)

def main(path):
    out = patch(open(path, "rb").read(), path)
    open(path, "wb").write(out)

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
