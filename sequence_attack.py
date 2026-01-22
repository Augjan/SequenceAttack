import curses
import json
import random
import time

NUCLEOTIDES = ["A", "T", "G", "C"]
LEADERBOARD_PATH = "leaderboard.json"
MAX_NAME_LEN = 12


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
    deletions = 0
    snps = 0
    insertions = 0
    for base in segment:
        roll = random.random()

        if roll < 0.01:
            # Deletion
            deletions += 1
            continue
        if roll < 0.02:
            # SNP
            mutated.append(random.choice([n for n in NUCLEOTIDES if n != base]))
            snps += 1
        elif roll < 0.03:
            # Insertion
            mutated.append(base)
            mutated.append(random.choice(NUCLEOTIDES))
            insertions += 1
        else:
            # Unchanged
            mutated.append(base)
    if not mutated:
        mutated.append(random.choice(NUCLEOTIDES))
    return mutated, start, {"deletions": deletions, "snps": snps, "insertions": insertions}


def centered_fall_x(play_width, seq_len):
    return clamp((play_width - seq_len) // 2, 0, max(0, play_width - seq_len))


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
        score += 50
    return score, perfect


def blink_message(stdscr, text, times):
    height, width = stdscr.getmaxyx()
    if isinstance(text, (list, tuple)):
        lines = list(text)
    else:
        lines = [text]
    max_len = max(len(line) for line in lines)
    start_y = (height // 2) - (len(lines) // 2)
    start_x = max(0, (width - max_len) // 2)
    for _ in range(times):
        for i, line in enumerate(lines):
            y = start_y + i
            x = max(0, start_x + (max_len - len(line)) // 2)
            stdscr.addstr(y, x, line, curses.A_BOLD)
        stdscr.refresh()
        time.sleep(0.5)
        for i, line in enumerate(lines):
            y = start_y + i
            x = max(0, start_x + (max_len - len(line)) // 2)
            stdscr.addstr(y, x, " " * len(line))
        stdscr.refresh()
        time.sleep(0.1)


def draw_sequence(stdscr, y, x, seq, highlight_idx=None):
    for i, ch in enumerate(seq):
        attr = curses.A_REVERSE if highlight_idx == i else curses.A_NORMAL
        stdscr.addch(y, x + i, ch, attr)


def load_leaderboard():
    try:
        with open(LEADERBOARD_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return [
                {"name": item.get("name", ""), "score": int(item.get("score", 0))}
                for item in data
                if isinstance(item, dict)
            ]
    except (OSError, ValueError):
        return []
    return []


def save_leaderboard(entries):
    with open(LEADERBOARD_PATH, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2)


def sorted_leaderboard(entries):
    return sorted(entries, key=lambda item: (-item["score"], item["name"].lower()))


def add_leaderboard_entry(name, score):
    entries = load_leaderboard()
    entries.append({"name": name, "score": score})
    entries = sorted_leaderboard(entries)
    save_leaderboard(entries)
    return entries


def prompt_name(stdscr, score):
    stdscr.nodelay(False)
    curses.curs_set(1)
    name = ""
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        title = "GAME OVER"
        subtitle = "Final Score: {}".format(score)
        prompt = "Enter name (A-Z only):"
        name_line = name if name else "_"
        stdscr.addstr(height // 2 - 2, max(0, (width - len(title)) // 2), title, curses.A_BOLD)
        stdscr.addstr(height // 2 - 1, max(0, (width - len(subtitle)) // 2), subtitle)
        stdscr.addstr(height // 2 + 1, max(0, (width - len(prompt)) // 2), prompt)
        stdscr.addstr(height // 2 + 2, max(0, (width - len(name_line)) // 2), name_line)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_ENTER, 10, 13):
            if name:
                curses.curs_set(0)
                return name
        elif key in (27,):
            curses.curs_set(0)
            return ""
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            name = name[:-1]
        else:
            ch = chr(key) if 0 <= key <= 255 else ""
            if ch.isascii() and ch.isalpha() and len(name) < MAX_NAME_LEN:
                name += ch


def show_leaderboard(stdscr, entries):
    stdscr.nodelay(False)
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    title = "LEADERBOARD"
    stdscr.addstr(1, max(0, (width - len(title)) // 2), title, curses.A_BOLD)
    if not entries:
        msg = "No scores yet."
        stdscr.addstr(3, max(0, (width - len(msg)) // 2), msg)
    else:
        start_y = 3
        for idx, entry in enumerate(entries[: min(len(entries), height - start_y - 2)], start=1):
            line = "{:>2}. {:<12} {:>6}".format(idx, entry["name"], entry["score"])
            stdscr.addstr(start_y + idx - 1, max(0, (width - len(line)) // 2), line)
    footer = "Press any key to return"
    stdscr.addstr(height - 2, max(0, (width - len(footer)) // 2), footer)
    stdscr.refresh()
    stdscr.getch()


def menu(stdscr):
    stdscr.nodelay(False)
    options = ["Start", "Leaderboard"]
    selected = 0
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        title = "SequenceAttack"
        stdscr.addstr(1, max(0, (width - len(title)) // 2), title, curses.A_BOLD)
        for idx, option in enumerate(options):
            label = f"[ {option} ]" if idx == selected else f"  {option}  "
            stdscr.addstr(3 + idx, max(0, (width - len(label)) // 2), label)
        footer = "Use UP/DOWN + ENTER (Q to quit)"
        stdscr.addstr(height - 2, max(0, (width - len(footer)) // 2), footer)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), ord("Q")):
            return None
        if key in (curses.KEY_UP, ord("k"), ord("K")):
            selected = (selected - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
            selected = (selected + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[selected]


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

    seg_len = 20
    falling_seq, _, mutation_counts = new_falling_segment(base_seq, seg_len)
    fall_x = centered_fall_x(play_width, len(falling_seq))
    fall_y = top_y

    score = 0
    multiplier = 1
    edits_remaining = sum(mutation_counts.values())
    mode = "move"  # move, edit_top
    cursor = 0
    last_tick = time.time()
    base_fall_delay = 0.5
    fall_delay = base_fall_delay

    if any(mutation_counts.values()):
        lines = ["! Mutations Detected !"]
        if mutation_counts["deletions"]:
            lines.append("Deletions x{}".format(mutation_counts["deletions"]))
        if mutation_counts["snps"]:
            lines.append("SNPs x{}".format(mutation_counts["snps"]))
        if mutation_counts["insertions"]:
            lines.append("Insertions x{}".format(mutation_counts["insertions"]))
        blink_message(stdscr, lines, 3)
        last_tick = time.time()

    while True:
        now = time.time()
        if now - last_tick >= fall_delay:
            fall_y += 1
            last_tick = now

        if fall_y >= bottom_y:
            delta, perfect = score_alignment(falling_seq, fall_x, bottom_seq, bottom_y)
            score += delta * multiplier
            if delta < 0:
                name = prompt_name(stdscr, score)
                if name:
                    entries = add_leaderboard_entry(name, score)
                    show_leaderboard(stdscr, entries)
                return
            if perfect:
                multiplier *= 2
                blink_message(stdscr, ["PERFECT ALIGNMENT", "+50", f"x{multiplier} MULTIPLIER"], 3)
            else:
                multiplier = 1
            fall_y = top_y
            falling_seq, _, mutation_counts = new_falling_segment(base_seq, seg_len)
            fall_x = centered_fall_x(play_width, len(falling_seq))
            fall_delay = base_fall_delay
            base_fall_delay = max(0.005, fall_delay * 0.8)
            mode = "move"
            cursor = 0
            edits_remaining = sum(mutation_counts.values())
            if any(mutation_counts.values()):
                lines = ["! Mutations Detected !"]
                if mutation_counts["deletions"]:
                    lines.append("Deletions x{}".format(mutation_counts["deletions"]))
                if mutation_counts["snps"]:
                    lines.append("SNPs x{}".format(mutation_counts["snps"]))
                if mutation_counts["insertions"]:
                    lines.append("Insertions x{}".format(mutation_counts["insertions"]))
                blink_message(stdscr, lines, 3)
                last_tick = time.time()

        key = stdscr.getch()
        if key != -1:
            if key in (ord("q"), ord("Q")):
                return
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
                if edits_remaining > 0 and len(falling_seq) < play_width:
                    insert_space(falling_seq, cursor)
                    fall_x = clamp(fall_x, 0, play_width - len(falling_seq))
                    edits_remaining -= 1
            elif mode == "edit_top" and key in (curses.KEY_BACKSPACE, 127, 8):
                if edits_remaining > 0 and falling_seq:
                    falling_seq.pop(cursor)
                    fall_x = clamp(fall_x, 0, play_width - len(falling_seq))
                    cursor = clamp(cursor, 0, len(falling_seq) - 1)
                    edits_remaining -= 1
            elif mode == "edit_top" and key in (ord("a"), ord("A"), ord("t"), ord("T"), ord("g"), ord("G"), ord("c"), ord("C")):
                if edits_remaining > 0 and falling_seq:
                    new_base = chr(key).upper()
                    if new_base in NUCLEOTIDES and falling_seq[cursor] != new_base:
                        falling_seq[cursor] = new_base
                        edits_remaining -= 1

        stdscr.erase()
        stdscr.addstr(0, 1, "SequenceAttack  |  Score: {}  |  Multiplier: x{}".format(score, multiplier))
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
    def run_app(stdscr):
        while True:
            choice = menu(stdscr)
            if choice is None:
                break
            if choice == "Leaderboard":
                entries = sorted_leaderboard(load_leaderboard())
                show_leaderboard(stdscr, entries)
            elif choice == "Start":
                game(stdscr)

    curses.wrapper(run_app)


if __name__ == "__main__":
    main()
