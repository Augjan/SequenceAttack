import curses
import random
import time

NUCLEOTIDES = ["A", "T", "G", "C"]


def make_base_sequence(width):
    return [random.choice(NUCLEOTIDES) for _ in range(width)]


def clamp(value, low, high):
    return max(low, min(value, high))


def new_falling_segment(base_seq, seg_len):
    if seg_len >= len(base_seq):
        segment = base_seq[:]
        start = 0
    else:
        start = random.randint(0, len(base_seq) - seg_len)
        segment = base_seq[start : start + seg_len]

    mutated = []
    for ch in segment:
        roll = random.random()
        if roll < 0.01:
            continue
        if roll < 0.02:
            mutated.append(random.choice([n for n in NUCLEOTIDES if n != ch]))
        elif roll < 0.03:
            mutated.append(ch)
            mutated.append(random.choice(NUCLEOTIDES))
        else:
            mutated.append(ch)
    if not mutated:
        mutated.append(random.choice(NUCLEOTIDES))
    return mutated, start


def insert_space(seq, cursor):
    seq.insert(cursor, " ")


def score_alignment(falling, fall_x, bottom, bottom_y):
    score = 0
    aligned = 0
    for i, ch in enumerate(falling):
        bx = fall_x + i
        if 0 <= bx < len(bottom) and ch != " " and bottom[bx] != " ":
            if ch == bottom[bx]:
                score += 1
                aligned += 1
            else:
                score -= 1
    perfect = aligned > 0 and aligned == sum(1 for i, ch in enumerate(falling) if 0 <= fall_x + i < len(bottom) and ch != " " and bottom[fall_x + i] != " ")
    if perfect:
        score += 100
    return score, perfect


def blink_message(stdscr, text, times):
    height, width = stdscr.getmaxyx()
    y = height // 2
    x = max(0, (width - len(text)) // 2)
    for _ in range(times):
        stdscr.addstr(y, x, text, curses.A_BOLD)
        stdscr.refresh()
        time.sleep(0.18)
        stdscr.addstr(y, x, " " * len(text))
        stdscr.refresh()
        time.sleep(0.18)


def draw_sequence(stdscr, y, x, seq, highlight_idx=None):
    for i, ch in enumerate(seq):
        attr = curses.A_REVERSE if highlight_idx == i else curses.A_NORMAL
        stdscr.addch(y, x + i, ch, attr)


def game(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLUE, -1)

    height, width = stdscr.getmaxyx()
    if height < 6 or width < 20:
        stdscr.addstr(0, 0, "Terminal too small. Resize to at least 20x6. Press Q to quit.")
        stdscr.refresh()
        while True:
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                return
            time.sleep(0.05)

    play_width = width - 2
    top_y = 2
    bottom_y = height - 2
    base_seq = make_base_sequence(play_width)
    bottom_seq = base_seq[:]

    seg_len = max(8, play_width // 2)
    falling_seq, fall_base_start = new_falling_segment(base_seq, seg_len)
    fall_x = clamp(fall_base_start, 0, play_width - len(falling_seq))
    fall_y = top_y

    score = 0
    mode = "move"  # move, edit_top
    cursor = 0
    last_tick = time.time()
    base_fall_delay = 0.5
    fall_delay = base_fall_delay

    while True:
        now = time.time()
        if now - last_tick >= fall_delay:
            fall_y += 1
            last_tick = now

        if fall_y >= bottom_y:
            delta, perfect = score_alignment(falling_seq, fall_x, bottom_seq, bottom_y)
            score += delta
            if perfect:
                blink_message(stdscr, "PERFECT ALIGNMENT!", 3)
            fall_y = top_y
            falling_seq, fall_base_start = new_falling_segment(base_seq, seg_len)
            fall_x = clamp(fall_base_start, 0, play_width - len(falling_seq))
            fall_delay = base_fall_delay
            mode = "move"
            cursor = 0

        key = stdscr.getch()
        if key != -1:
            if key in (ord("q"), ord("Q")):
                break
            elif key == curses.KEY_UP:
                mode = "edit_top"
                cursor = clamp(cursor, 0, len(falling_seq) - 1)
            elif key in (curses.KEY_ENTER, 10, 13, 27):
                mode = "move"
            elif mode == "move" and key == curses.KEY_LEFT:
                fall_x = clamp(fall_x - 1, 0, play_width - len(falling_seq))
            elif mode == "move" and key == curses.KEY_RIGHT:
                fall_x = clamp(fall_x + 1, 0, play_width - len(falling_seq))
            elif mode == "move" and key == curses.KEY_DOWN:
                fall_delay = max(0.005, fall_delay / 10.0)
            elif mode == "edit_top" and key == curses.KEY_LEFT:
                cursor = clamp(cursor - 1, 0, len(falling_seq) - 1)
            elif mode == "edit_top" and key == curses.KEY_RIGHT:
                cursor = clamp(cursor + 1, 0, len(falling_seq) - 1)
            elif mode == "edit_top" and key == ord(" "):
                if len(falling_seq) < play_width:
                    insert_space(falling_seq, cursor)
                    fall_x = clamp(fall_x, 0, play_width - len(falling_seq))
            elif mode == "edit_top" and key in (curses.KEY_BACKSPACE, 127, 8):
                if falling_seq:
                    falling_seq.pop(cursor)
                    fall_x = clamp(fall_x, 0, play_width - len(falling_seq))
                    cursor = clamp(cursor, 0, len(falling_seq) - 1)

        stdscr.erase()
        stdscr.addstr(0, 1, "SequenceAttack  |  Score: {}".format(score))
        stdscr.addstr(
            1,
            1,
            "Move: LEFT/RIGHT  Speed: DOWN  Edit falling: UP  Insert space: SPACE  Backspace: DEL  Exit edit: ENTER/ESC  Quit: Q",
        )

        draw_sequence(stdscr, fall_y, 1 + fall_x, falling_seq, cursor if mode == "edit_top" else None)
        if bottom_y - 1 > 1:
            if curses.has_colors():
                stdscr.attron(curses.color_pair(1))
            draw_sequence(stdscr, bottom_y - 1, 1 + fall_x, falling_seq, None)
            if curses.has_colors():
                stdscr.attroff(curses.color_pair(1))
        draw_sequence(stdscr, bottom_y, 1, bottom_seq, None)

        stdscr.refresh()
        time.sleep(0.01)


def main():
    curses.wrapper(game)


if __name__ == "__main__":
    main()
