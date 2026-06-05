# 🍅 Pomodoro Timer

A cross-platform terminal Pomodoro timer with a live progress bar and keyboard controls.

## Features

- 25-minute focus sessions with 5-minute short breaks and 15-minute long breaks
- Live ANSI progress bar and countdown
- Keyboard controls: `Space` pause/resume · `S` skip · `Q` quit
- Windows desktop notification at the end of each session
- Per-session activity log shown in the terminal

## Usage

```bash
python pomodoro.py
```

Requires Python 3.13+. No third-party dependencies.

## Session cycle

| # | Phase | Duration |
|---|-------|----------|
| 1–3 | Focus + Short break | 25 + 5 min |
| 4 | Focus + Long break | 25 + 15 min |
