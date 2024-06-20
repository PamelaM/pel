import re


day_name_pattern = re.compile("(Wednesday|Thursday|Friday|Saturday|Sunday)")

TIME_SLOTS = set()
for d in "WTFSZ":
    for n in range(9, 25):
        TIME_SLOTS.add(f"{d}{n:02}")


def read_pel_lines():
    with open("pel2.txt") as f:
        pel_text = f.read()

    pages = [
        page.split("P a g e", 1)[-1].split("\n", 1)[-1].strip()
        for page in pel_text.split("HISTORICON® 2024")
    ]
    for page in pages:
        yield from page.splitlines()


def read_pel_event_lines():
    event_lines = []

    for line in read_pel_lines():
        line = line.strip()
        start = line.split(":", 1)[0]
        if len(start) == 3 and start in TIME_SLOTS and event_lines:
            yield event_lines
            event_lines = []
        event_lines.append(line)
    if event_lines:
        yield event_lines


def pel_text_to_events():
    full_events = set(read_register_html_for_full_events())
    for event_lines in read_pel_event_lines():
        e = Event(event_lines)
        e.is_full = e.event_id in full_events
        yield e


def read_register_html_for_full_events():
    with open("register.html") as f:
        text = f.read()
    strikes = text.split("<strike>")[1:]
    strikes = [s.split("<b>FULL</b>")[0].strip() for s in strikes if "<b>FULL</b>" in s]
    for s in strikes:
        event_id = s.split(None, 1)[0]
        yield event_id


class EventBase:
    def __init__(self, lines):
        self.lines = lines
        self.event_type = ""
        self.event_id = ""
        self.name = ""
        self.day = ""
        self.length = ""
        self.bio = ""
        self.sponsor = ""
        self.prize = ""
        self.period = ""
        self.scale = ""
        self.rules = ""
        self.description = ""
        self.players = ""
        self.conflicts = set()
        self.is_full = False

    @property
    def safe_event_id(self):
        return self.event_id.replace(":", '-').strip()

    @property
    def time_slot(self):
        return self.event_id.split(":")[0].strip()

    @property
    def event_slot(self):
        event_slot = self.time_slot
        for idx, c in enumerate("WTFSZ"):
            event_slot = event_slot.replace(c, str(idx))
        return event_slot

    @property
    def time_slots(self):
        time_slot = self.time_slot
        start_hour = int(time_slot[1:])
        day_letter = time_slot[0]
        duration = round(float(self.length.split(None)[0]) + 0.5)
        return [f"{day_letter}{(start_hour + idx):02d}" for idx in range(duration)]

    def as_dict(self):
        return dict(
            event_id=self.safe_event_id,
            name=self.name,
            day=self.day,
            hour=self.hour,
            length=self.length,
            players=self.players,
            location=self.location,
            GM=self.GM,
            sponsor=self.sponsor,
            prize=self.prize,
            period=self.period,
            scale=self.scale,
            rules=self.rules,
            description=self.description,
            time_slots=self.time_slots,
            conflicts=sorted(self.conflicts),
            is_full=self.is_full,
        )


class Event(EventBase):
    SEPARATORS = ["Players", "Location", "GM", "Sponsor", "Prize", "Period", "Scale", "Rules", "Description"]

    def __init__(self, lines):
        super().__init__(lines)
        self.separators = self.SEPARATORS[::]
        self.text = " ".join(lines[1:])
        try:
            self.event_type = "Game"
            self.event_id, self.name = lines[0].split(None, 1)
            self.name = f"{self.name}{self.next()}".strip()
            pieces = day_name_pattern.split(self.name)
            self.name = self.clean_name(''.join(pieces[:-2]))
            self.day, extra = pieces[-2:]
            extra = extra.strip(",").strip()
            hour, length = extra.rsplit(",", 1)
            self.hour = hour.strip(",").strip().replace(":00:00", ":00")
            self.length = length.strip()
            self.players = self.next()
            self.location = self.next()
            self.GM = self.next()
            self.sponsor = self.next()
            self.prize = self.next()
            self.period = self.next()
            self.scale = self.next()
            self.rules = self.next()
            self.description = self.next()

        except Exception:
            print(len(lines), lines[0], self.text)
            raise

    def next(self):
        if not self.separators:
            val = self.text.strip()
        else:
            sep = self.separators.pop(0)
            value, self.text = self.text.split(f" {sep}: ")
            val = value.strip(",").strip()
        return "" if val == "NONE" else val

    @staticmethod
    def clean_name(name):
        name = name.replace("ThemeGame", "Theme Game")
        name = name.replace("—", " — ")
        name = " ".join(name.split(None))
        return name
