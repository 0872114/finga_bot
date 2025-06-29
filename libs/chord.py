from PIL import Image, ImageDraw, ImageFont
import re


class Semitone:

    def __init__(self, name, enharmonic=False):
        self.name = name
        self.is_note = not enharmonic

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class Note:

    MAJOR = {
        'C': Semitone('C'),
        'C#': Semitone('C#', enharmonic=True),
        'D': Semitone('D'),
        'D#': Semitone('D#', enharmonic=True),
        'E': Semitone('E'),
        'F': Semitone('F'),
        'F#': Semitone('F#', enharmonic=True),
        'G': Semitone('G'),
        'G#': Semitone('G#', enharmonic=True),
        'A': Semitone('A'),
        'A#': Semitone('A#', enharmonic=True),
        'B': Semitone('B'),
    }

    MINOR = {
        'C': Semitone('C'),
        'Db': Semitone('Db', enharmonic=True),
        'D': Semitone('D'),
        'Eb': Semitone('Eb', enharmonic=True),
        'E': Semitone('E'),
        'F': Semitone('F'),
        'Gb': Semitone('Gb', enharmonic=True),
        'G': Semitone('G'),
        'Ab': Semitone('Ab', enharmonic=True),
        'A': Semitone('A'),
        'Bb': Semitone('Bb', enharmonic=True),
        'B': Semitone('B'),
    }

    def __init__(self, key, octave=1, gamma=None):
        self.key = str(key).strip()[:2].capitalize()
        self.str_key = self.key
        self.octave = octave
        if gamma is None:
            self.gamma = self.get_gamma()
        else:
            self.gamma = gamma

    def get_gamma(self):
        if self.key in self.MAJOR:
            gamma = self.MAJOR
        else:
            gamma = self.MINOR
        return gamma

    def set_gamma(self, gamma):
        self.key = gamma[list(gamma)[list(self.gamma).index(self.key)]].name
        self.gamma = gamma

    @property
    def minor_key(self):
        gamma = self.MINOR
        key = gamma[list(gamma)[list(self.gamma).index(self.key)]]
        note = Note(key.name, octave=self.octave)
        note.key = key.name
        return note.key

    @property
    def major_key(self):
        gamma = self.MAJOR
        key = gamma[list(gamma)[list(self.gamma).index(self.key)]]
        note = Note(key.name, octave=self.octave)
        note.key = key.name
        return note.key

    @property
    def minor(self):
        gamma = self.MINOR
        key = gamma[list(gamma)[list(self.gamma).index(self.key)]]
        return Note(key.name, octave=self.octave)

    @property
    def major(self):
        gamma = self.MAJOR
        key = gamma[list(gamma)[list(self.gamma).index(self.key)]]
        return Note(key.name, octave=self.octave)

    @property
    def name(self):
        major = self.major
        return major.key

    @property
    def frequency(self):
        n = self - Note('A')
        f0 = 440 * 2 ** (n / 12)
        return f0

    @property
    def midi_key(self):
        n = Note('A') - self + 49
        return n

    def __add__(self, other):
        assert isinstance(other, int)
        octave, semitones = divmod(other, 12)
        keys = self.gamma
        key = list(keys).index(self.key)
        key += semitones
        inc_octave, clean_key = divmod(key, 12)
        octave += inc_octave + self.octave
        key = clean_key - inc_octave * 12
        key_char = keys[list(keys)[key]]
        return Note(key_char.name, octave=octave, gamma=self.gamma)

    def __sub__(self, other):
        if isinstance(other, Note):
            keys = self.MAJOR
            key0 = list(keys).index(self.major.key)
            key = list(keys).index(other.major.key)
            diff = (self.octave - other.octave) * 12 - (key - key0)
            return diff

        elif isinstance(other, int):
            return self.__add__(-other)

    def __str__(self):
        return '{}{}'.format(self.key, self.octave)

    def __repr__(self):
        return '{}{}'.format(self.key, self.octave)


class Tuning:

    DEFAULT_OCTAVE_ORDER = 2, 1, 1, 1, 0
    DEFAULT_TUNING_NAME = 'EBGDAE'

    def __init__(self, name=DEFAULT_TUNING_NAME, octave_order=DEFAULT_OCTAVE_ORDER):
        if not re.match(r'^[ABCDEFGH#b]+$', name):
            raise ValueError('bad tune')
        self.name = name
        self.octave_order = octave_order
        self.strings = list()
        for string in name:
            if string == '#':
                self.strings[len(self.strings) - 1] += 1
            else:
                self.add_string(string)

    def get_string_octave(self, n):
        if len(self.octave_order) <= n:
            octave = self.octave_order[len(self.octave_order) - 1]
        else:
            octave = self.octave_order[n]
        return octave

    def add_string(self, key, octave=None):
        if octave is None:
            octave = self.get_string_octave(len(self.strings))
        self.strings.append(Note(key, octave=octave))

    def __str__(self):
        return str(self.strings)

    def __iter__(self):
        for n in self.strings:
            yield n

    def __getitem__(self, item):
        assert isinstance(item, int)
        if item >= len(self.strings):
            return IndexError('No string with order number {} in tuning "{}"'.format(item, self.name))

        return self.strings[item]


class Fretboard:

    def __init__(self, tuning=None, frets=22):
        self.frets = frets
        self.allow_bass = True
        self.allow_octaves = True
        if tuning is None:
            self.tuning = Tuning()
        else:
            self.tuning = tuning
        assert isinstance(self.tuning, Tuning)

    def note(self, n, fret=None):
        if n > len(self.tuning.name):
            raise IndexError('No string {} on {}-string guitar'.format(n, len(self.tuning.name)))

        start_note = self.tuning[n-1]
        return start_note + int(fret)

    def find_chord_(self, chord, kapo=0, max_frets=3):
        noteset = set()
        chord_pos = list()
        major_steps = [note.major for note in chord.steps.values()]
        for k, n in enumerate(self.tuning):
            n = n.major
            nearest_notes = list()
            for i in range(-24, 24, 12):
                nearest_notes += [note + i - n for note in major_steps
                                  if note + i - n >= 0]

            for nearest_note in nearest_notes:
                chord_pos.append((k + 1, nearest_note))
                noteset.add(nearest_note)

        return sorted(chord_pos), chord

    @property
    def strings(self):
        return len(list(self.tuning))

    def draw_chord(self, chord_data):
        inner_steps, chord = chord_data
        steps = inner_steps
        frets = [v for k, v in steps if v is not None]
        if not frets:
            return ['Failed to build']

        fret_max = 11
        fret_min = min(frets)

        fretboard = list()
        for n in range(self.strings, 0, -1):
            string = list()
            found = False
            for i in range(fret_min, fret_max + 2):
                if (n, i) in inner_steps:
                    template = ' {} '
                    current_note = self[n, i]
                    if current_note.major_key == chord.tonic.major_key:
                        template = '`{} '
                    elif chord.steps.get(3) is not None and current_note.major_key == chord.steps[3].major_key:
                        template = '³{} '
                    elif chord.steps.get(7) is not None and current_note.major_key == chord.steps[7].major_key:
                        template = '⁷{} '
                    symb = template.format(n)
                    found = True
                else:
                    symb = '  '
                string.append('{}'.format(symb).rjust(5))
            if not found:
                string[0] = '  X  '
            fretboard.append('|'.join(string))
        string = list()
        for i in range(fret_min, fret_max + 2):
            string.append('{}'.format(i).rjust(5))
        fretboard.append(' '.join(string))
        return fretboard

    def find_note(self, note, exact=False, frets=22, kapo=0):
        for string, n in enumerate(self.tuning):
            i = 0
            if exact:
                if frets >= note - n >= kapo:
                    yield string + 1, note - n
            else:
                while (n + i).name != note.name:
                    i += 1
                yield string + 1, i

    def find_chord(self, chord, exact=False, frets=22, kapo=0):
        applicature = dict()
        for step, note in chord.steps.items():
            positions = list()
            for string, fret in self.find_note(note, exact=exact, frets=frets, kapo=kapo):
                positions.append((string, fret))
            applicature[step] = positions
        return applicature, chord.steps

    def draw_note(self, notes, start=0, end=None):
        if end is None:
            end = self.frets + 1
        fretboard = list()
        for n in reversed(list(self.tuning)):
            string = list()
            for i in range(start, end + 1):

                if (n + i).major_key in notes:
                    symb = (n + i).major
                elif (n + i).minor_key in notes:
                    symb = (n + i).minor
                else:
                    symb = '  '
                string.append(' {}'.format(symb).rjust(4))
            print('|'.join(string))
        string = list()
        for i in range(start, end + 1):
            string.append('{}'.format(i).rjust(4))
        print(' '.join(string))

    def get_schema(self, notes, as_string=True, start=0, end=11):
        schema = list()
        steps = {v.key: k for k, v in notes.notes.items()}
        # notes
        for n in reversed(list(self.tuning)):
            string = list()
            for i in range(start, end + 1):

                if (n + i).major_key in steps:
                    symb = steps[(n + i).major_key]
                elif (n + i).minor_key in steps:
                    symb = steps[(n + i).minor_key]
                else:
                    symb = ' '
                if symb == 1:
                    symb = 'R'
                string.append(' {}'.format(symb).rjust(3))
            schema.append('|'.join(string))
        # frets
        schema.append(' ' * (4 * (end - start + 1) - 1))
        string = list()
        for i in range(start, end + 1):
            string.append('{}'.format(i).rjust(3))
        schema.append(' '.join(string))
        if as_string:
            return '\n'.join(schema)
        else:
            return schema

    def __getitem__(self, item):
        return self.note(*item)


class ChordBuilder:
    """
    1. get steps amount, set steps in major
    2. modify tonic if minor
    3. alternate chord (sus, add, remove, reduce, enlarge)
    4. modify all if dim
    5. modify last(?) if aug :todo
    6.(?) find lowest, then add bass note :todo

    #todo:
    parser to class
    :symbol bank (in)
    comparsion for Note
    change H to B ?
    tonic tone - to note
    : do not change
    ? is_minor
    ...
    fretboard find_note()
    : order is first, last, third, seventh, others; can drop 5, 9 ,11
    ...
    draw fretboard
    ...
    next: harmony
    """

    NATURAL_MAJOR_STEPS = 'CDEFGAB'

    def __init__(self, tonic: Note):
        assert isinstance(tonic, Note)
        self.steps = dict()
        self.steps[1] = tonic
        self.is_minor = False
        print(' 1 {} tonic'.format(self.tonic))

    @property
    def tonic(self):
        return self.steps[1]

    @classmethod
    def step_interval(cls, step):
        steps = cls.NATURAL_MAJOR_STEPS * (step // 7 + 1)
        octave = (step - 1) // 7
        interval = Note(steps[step - 1], octave=octave) - Note('C', octave=0)
        return interval

    def add_natural_major_step(self, step):
        interval = self.step_interval(step)
        self.steps[step] = self.tonic + interval
        self.steps[step].set_gamma(self.tonic.gamma)
        print(' {} {} added'.format(step, self.steps[step]))

    def enlarge(self, step):
        if self.steps.get(step) is None:
            print('no step {} to enlarge'.format(step))
            return
        print('♯{} {} enlarged'.format(step, self.steps[step]))
        self.steps[step] += 1
        self.steps[step].set_gamma(Note.MAJOR)

    def reduce(self, step):
        if self.steps.get(step) is None:
            print('no step {} to reduce'.format(step))
            return
        print('♭{} {} reduced'.format(step, self.steps[step]))
        self.steps[step] -= 1
        self.steps[step].set_gamma(Note.MINOR)

    def expand_to(self, target_step, maj=False):
        for step in range(3, target_step+1, 2):
            if self.steps.get(step) is None:
                self.add_natural_major_step(step)
                if not maj and step in (7, ):
                    self.reduce(step)
        if not target_step % 2 and self.steps.get(target_step) is None:
            self.add_natural_major_step(target_step)

    def maj(self, target_step=5):
        self.expand_to(target_step)

    def min(self, target_step=5):
        self.expand_to(target_step)
        self.reduce(3)
        self.is_minor = True

    def maj7(self):
        self.maj(7)

    def hitchcock7(self):
        self.expand_to(7)
        self.reduce(7)
        self.is_minor = True

    def min_maj7(self):
        self.min(7)
        self.is_minor = True

    def dominant7(self):
        self.maj(7)
        self.reduce(7)
        self.is_minor = True

    def sus(self, target=4, base=3):
        """ suspended 3 or base
            r"sus[249]"
            as last
        """
        print(' {} {} suspended to {}'.format(base,  self.steps[base], target))
        if base in self.steps:
            del self.steps[base]

        self.add_natural_major_step(target)

    def add(self, step):
        self.add_natural_major_step(step)

    def dim(self):
        """ reduce all
            r"dim"
            as last
        """
        self.is_minor = True
        for k, step in self.steps.items():
            if k != 1:
                self.reduce(k)

    def aug(self):
        """ enlarge the last step
            r"\+$" - + at the end
            as last
        """
        # todo: theory
        self.enlarge(max(self.steps))

    def add_bass(self, key):
        """ add a bass note
        """
        i = 0
        while self.steps.get(i):
            i -= 1
        self.steps[i] = Note(key, octave=self.tonic.octave-1)

    def omit(self, step):
        print(' {} {} omitted'.format(step, self.steps[step]))
        if self.steps.get(step) is not None:
            del self.steps[step]

    def next(self, step):
        next_note = self.tonic + self.step_interval(step)
        return ChordBuilder(next_note)

    @property
    def notes(self):
        return self.steps

    def edit_notes(self):
        for key in sorted(self.steps.keys()):
            if self.steps[key] == self.tonic:
                continue

            if key in {2}:
                self.steps[key].str_key = self.steps[key].minor_key
            elif key in {4, 5, 6}:
                self.steps[key].str_key = self.steps[key].major_key
            elif (self.steps[key] - self.tonic) % 3:
                self.steps[key].str_key = self.steps[key].major_key
            else:
                self.steps[key].str_key = self.steps[key].minor_key

    def __iter__(self):
        self.edit_notes()
        for key in sorted(self.steps.keys()):
            yield self.steps[key].str_key

    @property
    def dominant(self):
        return self.steps[max(self.steps.keys())]

    def __str__(self):
        self.edit_notes()
        note_names = list()
        for key in sorted(self.steps.keys()):
            note_names.append(self.steps[key].str_key)
        return ' '.join(note_names)


class ChordParser:

    BASE_PATTERS = re.compile(r"^([A-H][b#]?)(sus(?!\d)|m(?!aj)|maj(?!\d)||[+-])(dim|aug|)")
    ALTERATIONS_PATTERN = re.compile(r"((?:[#b+-/]|add|sus|no|omit|maj|))(\d+)")
    BASS_PATTERN = re.compile(r"/([A-H][b#+-]?)")

    @classmethod
    def parse(cls, chord):
        print(chord)
        to_replace = {
            'H': 'B',
            'Ø': 'm7b5',
            '°7': 'dim7',
            '°': 'dim7',
            'o7': 'dim7',
            'Δ7': 'maj7',
            'Δ': 'maj7',
            'M': 'maj',
        }
        for pattern, replace in to_replace.items():
            if pattern in chord:
                prev = chord
                chord = chord.replace(pattern, replace)
                print('Pattern "{}": Replaced {} to {}'.format(pattern, prev, chord))
        is_bms = chord.endswith('+')
        if is_bms:
            chord = chord[:-1]

        main = re.search(cls.BASE_PATTERS, chord)
        if main is None:
            return None

        chord = chord[len(main[1]):]
        alterations = re.findall(cls.ALTERATIONS_PATTERN, chord)
        add_bass = re.findall(cls.BASS_PATTERN, chord)

        return dict(
            tonic=main[1],
            character=main[2],
            modifier=main[3],
            alterations=alterations,
            bass_to_add=add_bass,
            is_bms=is_bms
        )

    @staticmethod
    def build(data):
        """
        1. get steps amount, set steps in major
        2. modify tonic if minor
        3. alternate chord (sus, add, remove, reduce, enlarge)
        4. modify all if dim
        5. modify last(?) if aug :todo
        6.(?) find lowest, then add bass note :todo
        """
        # set tonic
        tonic = data['tonic']
        chord = ChordBuilder(Note(tonic))
        # set character
        character = data['character']
        major = 'maj', ''
        minor = 'm', 'min'
        sus4 = 'sus',
        if character in major:
            chord.maj()
            chord.tonic.set_gamma(Note.MAJOR)
        elif character in minor:
            chord.min()
            chord.tonic.set_gamma(Note.MINOR)
        elif character in sus4:
            chord.maj()
            chord.sus(4)
        # add additional steps
        major = 'maj',
        minor = '',
        add = '/', 'add'
        for cmd, attr in data['alterations']:
            step = int(attr)
            if cmd in major:
                chord.expand_to(step, maj=True)
            elif cmd in minor:
                chord.expand_to(step)
                # Special A5
                if step == 5:
                    chord.omit(3)
            elif cmd in add:
                chord.add_natural_major_step(step)

        # modify steps
        reduce = 'b', '-'
        enlarge = '#', '+'
        sus = 'sus',
        for cmd, attr in data['alterations']:
            step = int(attr)
            if cmd in reduce:
                chord.expand_to(step)
                chord.reduce(step)
            elif cmd in enlarge:
                chord.expand_to(step)
                chord.enlarge(step)
            elif cmd in sus:
                chord.sus(step)
        # omit notes
        omit = 'no', 'omit'
        for cmd, attr in data['alterations']:
            step = int(attr)
            if cmd in omit:
                chord.omit(step)
        # modify result
        dim = 'dim',
        aug = 'aug',
        cmd = data['modifier']
        if cmd in dim:
            chord.dim()
        elif cmd in aug or data['is_bms']:
            chord.aug()
        # add bass
        for note in data['bass_to_add']:
            chord.add_bass(note)
        return chord

    @classmethod
    def chord(cls, chord_name):
        chord_data = cls.parse(chord_name)
        chord_obj = cls.build(chord_data)
        print('→', chord_obj)
        return chord_obj

    @staticmethod
    def draw_text(lines):
        width = 512
        height = len(lines) * 16 + 32
        font = ImageFont.truetype("assets/source.ttf", size=16)
        img = Image.new('RGB', (width, height), color='#f0f0e0')
        imgDraw = ImageDraw.Draw(img)
        for n, line in enumerate(lines):
            imgDraw.text((16, 16 + n * 16), line, font=font, fill=(0, 0, 0), stroke_fill=(0, 0, 0))
        return img

    @classmethod
    def explain(cls, chord_name):
        chord_parsed = cls.parse(chord_name)
        chord = cls.build(chord_parsed)
        title = '{}: {}'.format(chord_name, chord)
        fretboard = Fretboard()
        schema = fretboard.get_schema(chord)
        return title, schema

    @classmethod
    def explain_draw(cls, chord_name, tuning=None, reverse=False):
        chord_parsed = cls.parse(chord_name)
        chord = cls.build(chord_parsed)
        title = '{}: {}'.format(chord_name, chord)
        fretboard = Fretboard(tuning=tuning)
        schema = fretboard.get_schema(chord, as_string=False)

        if reverse:
            title += ' (fret is mirrored)'
        else:
            schema = schema[::-1]

        # Legend
        annotation = ['', chord_name + ':']
        steps = sorted([(k, v) for k, v in chord.notes.items()])
        for key, note in steps:
            if key == 1:
                key = 'R'
            annotation.append('{}: {}'.format(key, note.str_key))
        if len(schema) >= len(annotation):
            for i, legend_line in enumerate(annotation):
                schema[i] += ' ' * 3 + legend_line
        else:
            schema.append('')
            schema.append('  '.join(annotation))
        img = cls.draw_text(schema)
        return title, img


if __name__ == '__main__':
    res = Note('G#', octave=3) - Note('Db', octave=3)  # 6
    res2 = Note('F#', octave=3) - Note('A', octave=3)  #3
    res2 = Note('Eb', octave=3) - Note('Db', octave=3)  #3
    print(res, res2)
