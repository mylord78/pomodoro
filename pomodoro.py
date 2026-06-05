import time
import sys
import os
import threading
from datetime import datetime

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import tty
    import termios
    WINDOWS = False

# ANSI color codes
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
GRAY    = "\033[90m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

WORK_MINUTES   = 25
SHORT_BREAK    = 5
LONG_BREAK     = 15
SESSIONS_UNTIL_LONG = 4

BAR_WIDTH = 40


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def enable_ansi_windows():
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


def render_bar(elapsed, total, color):
    filled = int(BAR_WIDTH * elapsed / total)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    pct = int(100 * elapsed / total)
    return f"{color}{bar}{RESET} {BOLD}{pct:3d}%{RESET}"


def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def notify(message):
    """Simple terminal bell + message."""
    sys.stdout.write("\a")
    sys.stdout.flush()
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "Pomodoro", 0x40 | 0x1000)
        except Exception:
            pass


def draw_ui(phase, session, elapsed, total, paused, log):
    clear()
    is_work = phase == "work"
    color = GREEN if is_work else CYAN

    print(f"\n  {BOLD}{MAGENTA}🍅 Pomodoro Timer{RESET}\n")

    # Session dots
    dots = ""
    for i in range(SESSIONS_UNTIL_LONG):
        if i < session % SESSIONS_UNTIL_LONG:
            dots += f"{GREEN}●{RESET} "
        else:
            dots += f"{GRAY}○{RESET} "
    cycle = (session - 1) // SESSIONS_UNTIL_LONG + 1
    print(f"  Cycle {BOLD}{cycle}{RESET}  Session {BOLD}{session}{RESET}   {dots}")
    print()

    # Phase label
    if phase == "work":
        label = f"{GREEN}{BOLD}FOCUS TIME{RESET}"
    elif phase == "short_break":
        label = f"{CYAN}{BOLD}SHORT BREAK{RESET}"
    else:
        label = f"{MAGENTA}{BOLD}LONG BREAK{RESET}"
    print(f"  {label}")
    print()

    # Timer
    remaining = total - elapsed
    big_time = format_time(remaining)
    print(f"  {BOLD}{color}{big_time}{RESET}", end="")
    if paused:
        print(f"  {YELLOW}⏸ PAUSED{RESET}", end="")
    print("\n")

    # Progress bar
    print(f"  {render_bar(elapsed, total, color)}\n")

    # Controls
    print(f"  {GRAY}[Space] pause/resume   [S] skip   [Q] quit{RESET}\n")

    # Log
    if log:
        print(f"  {GRAY}{'─' * 44}{RESET}")
        print(f"  {GRAY}Recent sessions:{RESET}")
        for entry in log[-5:]:
            print(f"  {GRAY}{entry}{RESET}")

    sys.stdout.flush()


def get_key_nonblocking():
    """Return a key if pressed, else None. Non-blocking."""
    if WINDOWS:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                msvcrt.getwch()
                return None
            return ch.lower()
    else:
        # Unix non-blocking via select
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return ch.lower()
    return None


def run_phase(phase, duration_minutes, session, log):
    total = duration_minutes * 60
    elapsed = 0
    paused = False

    if not WINDOWS:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)

    try:
        while elapsed < total:
            draw_ui(phase, session, elapsed, total, paused, log)
            time.sleep(1)

            key = get_key_nonblocking()
            if key == " ":
                paused = not paused
            elif key == "s":
                return "skip"
            elif key == "q":
                return "quit"

            if not paused:
                elapsed += 1
    finally:
        if not WINDOWS:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return "done"


def main():
    enable_ansi_windows()

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    session = 1
    log = []

    try:
        while True:
            # Work phase
            result = run_phase("work", WORK_MINUTES, session, log)
            if result == "quit":
                break

            ts = datetime.now().strftime("%H:%M")
            skipped = " (skipped)" if result == "skip" else ""
            log.append(f"{ts}  ✓ Session {session} work{skipped}")
            notify(f"Session {session} done! Time for a break.")

            if result != "skip":
                # Break phase
                if session % SESSIONS_UNTIL_LONG == 0:
                    break_phase = "long_break"
                    break_min = LONG_BREAK
                    break_label = f"Long break ({LONG_BREAK} min)"
                else:
                    break_phase = "short_break"
                    break_min = SHORT_BREAK
                    break_label = f"Short break ({SHORT_BREAK} min)"

                result = run_phase(break_phase, break_min, session, log)
                if result == "quit":
                    break

                ts = datetime.now().strftime("%H:%M")
                skipped = " (skipped)" if result == "skip" else ""
                log.append(f"{ts}  ☕ {break_label}{skipped}")
                if result != "skip":
                    notify("Break over! Back to focus.")

            session += 1

    finally:
        # Restore cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        clear()

        total_work = sum(1 for e in log if "work" in e and "skipped" not in e)
        print(f"\n{BOLD}{MAGENTA}🍅 Session ended{RESET}")
        print(f"  Completed {GREEN}{BOLD}{total_work}{RESET} focus session(s).\n")
        if log:
            print(f"  {GRAY}Log:{RESET}")
            for entry in log:
                print(f"  {GRAY}{entry}{RESET}")
        print()


if __name__ == "__main__":
    main()
