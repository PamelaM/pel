import fitz
import read_games


def pdf_to_txt(pdf_path, txt_path):
    doc = fitz.open(pdf_path)
    with open(txt_path, "w") as f:
        for page in doc:
            f.write(page.get_text())


def read_wc_lines():
    with open("warcollege.txt") as f:
        wc_text = f.read()

    pages = [
        page.split("P a g e", 1)[-1].split("\n", 1)[-1].strip()
        for page in wc_text.split("HISTORICON® 2024")
    ]
    for page in pages:
        yield from page.splitlines()


def read_wc_event_lines():
    event_lines = []

    for line in read_wc_lines():
        line = line.strip()
        start = line.split(":", 1)[0]
        if len(start) == 3 and start in read_games.TIME_SLOTS and event_lines:
            yield event_lines
            event_lines = []
        event_lines.append(line)
    if event_lines:
        yield event_lines


def warcollege_text_to_events():
    for evt_lines in read_wc_event_lines():
        e = WCEvent(evt_lines)
        yield e

class WCEvent(read_games.EventBase):
    def __init__(self, lines):
        super().__init__(lines)
        first_line = self.next()
        if ": 979  Thursday" in first_line:
            first_line = first_line.replace(": 979", ":979")
        elif "T16:9734:Thursday" in first_line:
            first_line = first_line.replace("9734:Thursday", "9734 Thursday")

        self.event_type = "War College"
        self.event_id, extra = first_line.split(None, 1)
        pieces = extra.split(None)
        self.day = pieces[0]
        self.hour = ' '.join([pieces[1], pieces[2]])
        self.length = "1 hr"
        self.name = self.next_until_blank()[1:-1].replace("\n", " ")
        self.GM = self.next('Speaker')
        self.location = self.next('Location')
        line = self.next('Type of Talk')
        self.rules, self.period = [p.strip() for p in line.split("Period:")]
        self.rules = self.rules.strip(',')
        self.description = self.next_until_blank('Description')
        self.bio = self.next_until_blank()
        self.bio = self.bio.replace(self.GM, "",1).strip()

    def next(self, label=None):
        line = self.lines.pop(0).strip()
        while not line:
            line = self.lines.pop(0).strip()
        if label and line.startswith(label):
            line = line.replace(label, '').strip()
            if line.startswith(':'):
                line = line[1:].strip()
        return line

    def next_until_blank(self, label=None):
        found_lines = [self.next(label)]
        while self.lines:
            line = self.lines.pop(0).strip()
            if line:
                found_lines.append(line)
            else:
                break
        return "\n".join(found_lines)


for idx, evt_lines in enumerate(read_wc_event_lines()):
    #for idx, line in enumerate(evt_lines):
    #    print(f"{idx:3}  '{line}'")
    e = WCEvent(evt_lines)

