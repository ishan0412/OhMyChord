from mingus.core import chords, notes, keys, intervals
from midiutil import MIDIFile
from typing import Union
import random
import numpy as np

# Maps "strange" key signatures to more conventional ones:
KEYSIG_CORRECTION_MAPPING = {'a#': 'bb', 'A#': 'Bb', 'cb': 'b', 'db': 'c#', 'C#': 'Db',
                             'd#': 'eb', 'D#': 'Eb', 'e#': 'f', 'F#': 'Gb', 'gb': 'f#', 'G#': 'Ab'}

# Chords diatonic to the major scale:
MAJOR_DIATONIC_CHORDS = [chords.major_triad,
                         chords.minor_seventh,
                         chords.minor_seventh,
                         chords.major_seventh,
                         chords.dominant_seventh,
                         chords.minor_seventh,
                         chords.half_diminished_seventh]

# Chords diatonic to the minor scale:
MINOR_DIATONIC_CHORDS = [chords.minor_triad,
                         chords.half_diminished_seventh,
                         chords.major_seventh,
                         chords.minor_seventh,
                         chords.minor_seventh,
                         chords.major_seventh,
                         chords.dominant_seventh]


# Resolves key signatures not recognized by mingus:
def resolve_key_signature(keysig: str) -> str:
    return KEYSIG_CORRECTION_MAPPING.get(keysig, keysig)


# Defines the distance between key centers as steps around the circle of fifths:
def key_center_distance(key1: str, key2: str) -> int:
    if key1.islower(): key1 = keys.relative_major(key1)
    if key2.islower(): key2 = keys.relative_major(key2)
    # print(key1)
    # print(key2)
    match intervals.determine(key1, key2, shorthand=True):
        case '1': return 0
        case 'b2' | '#1': return 5
        case '2' | 'bb3': return 2
        case 'b3' | '#2': return 3
        case '3' | 'b4': return 4
        case '4' | '#3': return 1
        case 'b5' | '#4': return 6
        case '5': return 1
        case 'b6' | '#5': return 4
        case '6' | 'bb7': return 3
        case 'b7': return 2
        case '7' | 'b8' | 'b1': return 5
        case _:
            print(intervals.determine(key1, key2, shorthand=True))
            raise ValueError(f'Invalid key centers {key1}, {key2}')


# Parameters that the user can control (diatonicity/functional harmony rolled up into a "randomness" slider)
diatonicity_factor = max(min(random.gauss(mu=0.56, sigma=0.2), 1), 0)  # "spice" factor
functionalharmony_factor = max(min(random.gauss(mu=0.72, sigma=0.36), 1), 0)
numbars = 8


def generatechords(diatonicity_factor: float = 0.56,
                   functionalharmony_factor: float = 0.72,
                   numbars: int = 4,
                   return_functional_analysis: bool = True) \
        -> list[list[str]] | tuple[list[list[str]], list[str], list[int]]:
    # Randomly selects the key the progression is in:
    startingkey = notes.int_to_note(random.randint(0, 11))
    if random.random() < 0.5:
        startingkey = startingkey.lower()
    startingkey = resolve_key_signature(startingkey)
    modprob_by_keydist = np.array(
        [diatonicity_factor ** i for i in range(7)])
    modprob_by_keydist = modprob_by_keydist / modprob_by_keydist.sum()

    keys_throughout_progression = [startingkey]
    roman_numerals_throughout_progression = [0]
    progression = [chords.I(startingkey)]

    for _ in range(numbars - 1):
        currentkey = startingkey if (random.random() < diatonicity_factor) else keys_throughout_progression[0]
        currentkey = resolve_key_signature(currentkey)
        # currentkey = keys_throughout_progression[0]
        prevchord = progression[0]

        # TODO: penalize circle-of-fifths distance of a (ANY) modulation from the starting key based on diatonicity_factor
        # penalize diatonic deviations based on how long it's been since the last one and how long that one went on for
        currchord_can_be_tonic = intervals.perfect_fifth(prevchord[0]) == prevchord[2]
        temp_currentkey = prevchord[0]
        if intervals.minor_third(temp_currentkey) == prevchord[1]:
            temp_currentkey = temp_currentkey.lower()

        # if (random.random() < diatonicity_factor) or (random.random() > key_center_distance()) and currchord_can_be_tonic:
        if ((random.random() > modprob_by_keydist[key_center_distance(startingkey, temp_currentkey)])
                and (currentkey == keys_throughout_progression[0])):
            # if random.random() < functionalharmony_factor:
                # Strictly diatonic functional harmony (tonics, predominants, and dominants all in the same key):
                nextchord_roman_numeral = (roman_numerals_throughout_progression[0]
                                           + (4 if (random.random() <= functionalharmony_factor) else 6)) % 7
                # Plagal cadences:
                if (len(progression) == 1) and (random.random() >= functionalharmony_factor):
                    nextchord_roman_numeral = 3
            # else:
            #     # Pick a chord in the key that voice-leads smoothly:
            #     nextchord_roman_numeral = (roman_numerals_throughout_progression[0]
            #                                + (2 if (random.random() <= 0.5) else 5)) % 7
        elif (random.random() < functionalharmony_factor) and currchord_can_be_tonic:
            # Functional harmony, but allowed to assume secondary key centers:
            currentkey = temp_currentkey

            # deceptive cadences to III and VI:
            temp_currentkey = keys.get_notes(currentkey)[mediantkey := (0 if ((len(prevchord) > 3)
                                                                              and currentkey[0].isupper()
                                                                              and (intervals.minor_seventh(currentkey)
                                                                                   == prevchord[3]))
                                                                        else random.choice([0, 2, 5]))]
            if (currentkey != temp_currentkey) and currentkey[0].isupper():
                currentkey = temp_currentkey.lower()

            nextchord_roman_numeral = 4 if ((random.random() <= functionalharmony_factor) or (mediantkey == 5)) else 6

        else:
            # Voice-leading based on common tones and intervallic distance between chords:
            # print(prevchord)
            # print('Voice-leading chord')
            tonic = resolve_key_signature(prevchord[0])
            mediant = keys.get_notes(prevchord[0])[2]
            submediant = keys.get_notes(prevchord[0])[5]
            dominant = keys.get_notes(prevchord[0])[4]
            if intervals.major_third(prevchord[0]) == prevchord[1]:
                # major: (vi > iii) > (bVI > bIII) > (VI > III)
                if intervals.perfect_fifth(prevchord[0]) == prevchord[2]:
                    keychoices = [mediant.lower(), submediant.lower(),
                                  notes.diminish(mediant), notes.diminish(submediant),
                                  mediant, submediant]
                    keychoice_probs = np.array([modprob_by_keydist[key_center_distance(startingkey,
                                                                                       resolve_key_signature(k))]
                                                for k in keychoices])
                    # currentkey = np.random.choice(keychoices, p=(keychoice_probs / keychoice_probs.sum()))
                    # print([key_center_distance(tonic, k) for k in keychoices])
                    # print(keychoices)

                    # currentkey = random.choice([mediant.lower(), submediant.lower(),
                    #                             notes.diminish(mediant), notes.diminish(submediant),
                    #                             mediant, submediant])
                # augmented: (1, 3, 5 major)
                else:
                    keychoices = [mediant, submediant, notes.augment(dominant)]
                    keychoice_probs = np.array([modprob_by_keydist[key_center_distance(startingkey,
                                                                                       resolve_key_signature(k))]
                                                for k in keychoices])
                    # currentkey = np.random.choice(keychoices, p=(keychoice_probs / keychoice_probs.sum()))
            else:
                # minor: (VI > III) > (#vi > #iii) > (vi > iii)
                if intervals.perfect_fifth(prevchord[0]) == prevchord[2]:
                    keychoices = [notes.diminish(mediant), notes.diminish(submediant),
                                  mediant.lower(), submediant.lower(),
                                  notes.diminish(mediant).lower(), notes.diminish(submediant).lower()]
                    keychoice_probs = np.array([modprob_by_keydist[key_center_distance(startingkey,
                                                                                       resolve_key_signature(k))]
                                                for k in keychoices])
                    # currentkey = np.random.choice(keychoices, p=(keychoice_probs / keychoice_probs.sum()))
                    # print([key_center_distance(tonic, k) for k in keychoices])
                    # print(keychoices)

                    # currentkey = random.choice([notes.diminish(mediant), notes.diminish(submediant),
                    #                             mediant.lower(), submediant.lower(),
                    #                             notes.diminish(mediant).lower(), notes.diminish(submediant).lower()])
                # diminished: (1, 3, 5, 7 minor)
                else:
                    keychoices = [x.lower() for x in prevchord[:2]]
                    keychoice_probs = np.array([modprob_by_keydist[key_center_distance(startingkey,
                                                                                       resolve_key_signature(k))]
                                                for k in keychoices])
            currentkey = np.random.choice(keychoices, p=(keychoice_probs / keychoice_probs.sum()))
            nextchord_roman_numeral = 0

        currentkey = resolve_key_signature(currentkey)
        currentkey_is_major = currentkey[0].isupper()
        nextchord = ((MAJOR_DIATONIC_CHORDS if currentkey_is_major else MINOR_DIATONIC_CHORDS)
                     [nextchord_roman_numeral](keys.get_notes(currentkey)[nextchord_roman_numeral]))
        if (not currentkey_is_major) and (random.random() <= functionalharmony_factor):
            if nextchord_roman_numeral == 4:
                nextchord = chords.dominant_seventh(keys.get_notes(currentkey)[4])
            elif nextchord_roman_numeral == 6:
                nextchord = chords.diminished_seventh(notes.augment(keys.get_notes(currentkey)[6]))

        # Randomly augment dominant chords:
        if ((nextchord_roman_numeral == 4)
                and (intervals.major_third(prevchord[0]) == prevchord[1])
                and (random.random() > diatonicity_factor)):
            # print('Augmented chord')
            nextchord = nextchord[:2] + [notes.augment(nextchord[2])] + nextchord[3:]

        # TODO: maybe a part purely meant for adding "spice" (augmenting random major chords, mode/quality mixture, etc)
        # Randomly change the current chord:
        if random.random() > (diatonicity_factor + functionalharmony_factor):
            # choose randomly selected key based on tonic distance from last chord?
            # keychoices = [k for x in range(12) if (((k := notes.int_to_note(x)) not in keys_throughout_progression)
            #                                        and (intervals.major_sixth(k).lower()
            #                                             not in keys_throughout_progression))]
            # print(keychoices)
            # keychoice_probs = np.array([modprob_by_keydist[key_center_distance(keys_throughout_progression[0],
            #                                                                    resolve_key_signature(k))]
            #                             for k in keychoices])
            # print(keys_throughout_progression)
            # currentkey = np.random.choice(keychoices, p=(keychoice_probs / keychoice_probs.sum()))
            # if random.random() < 0.5:
            #     currentkey = intervals.major_sixth(currentkey).lower()
            currentkey = random.choice([notes.int_to_note(x) for x in range(12)])
            if random.random() < 0.5:
                currentkey = currentkey.lower()
            currentkey = resolve_key_signature(currentkey)
            nextchord_roman_numeral = 0
            nextchord = chords.I(currentkey)

        keys_throughout_progression = [currentkey] + keys_throughout_progression  # !!! REPLACE CURRENTKEY EVENTUALLY
        roman_numerals_throughout_progression = [nextchord_roman_numeral] + roman_numerals_throughout_progression
        progression = [nextchord] + progression

    progression = [progression[-1]] + progression[:-1]
    return (progression if not return_functional_analysis else
            (progression,
             [keys_throughout_progression[-1]] + keys_throughout_progression[:-1],
             [roman_numerals_throughout_progression[-1]] + roman_numerals_throughout_progression[:-1]))


def process_roman_numeral_analysis(chords_: list[list[str]],
                                   keys_: list[str],
                                   numerals: list[int]) -> (list[str], list[str]):
    roman_numeral_analysis = []
    startingchord = chords_[0]
    startingkey = chords_[0][0][0].upper() + chords_[0][0][1:]
    for currentchord, currentkey, numeral in zip(chords_, keys_, numerals):
        # print(f'chord: {currentchord}, {numeral}/{currentkey}')
        roman_numeral_str = ''
        currentchord_is_major = intervals.major_third(currentchord[0]) == currentchord[1]
        resetkey = False
        if numeral == 0:
            interval_with_startingkey = intervals.determine(startingkey, currentchord[0], shorthand=True)
            # if (intervals.minor_third(startingchord[0]) == startingchord[1]) and
            if ((intervals.minor_third(startingchord[0]) == startingchord[1])
                    and (currentchord[0] not in keys.get_notes(keys_[0]))):
                if interval_with_startingkey[0] in ('#', 'b'):
                    roman_numeral_str += interval_with_startingkey[:-1]
                else:
                    roman_numeral_str += f'#{interval_with_startingkey[:-1]}'
            elif ((intervals.major_third(startingchord[0]) == startingchord[1])
                  and (len(interval_with_startingkey) > 1)):
                roman_numeral_str += interval_with_startingkey[:-1]
            print(interval_with_startingkey)
            numeral = int(interval_with_startingkey[-1]) - 1
            resetkey = True
        # Convert integer to Roman numeral
        if numeral < 3:
            roman_numeral_str += 'I' * (numeral + 1)
        elif numeral == 3:
            roman_numeral_str += 'IV'
        elif numeral >= 4:
            roman_numeral_str += 'V' + (((numeral + 1) % 5) * 'I')
        else:
            raise ValueError('Invalid Roman numerals')
        if not currentchord_is_major:
            roman_numeral_str = roman_numeral_str.lower()
        if intervals.minor_fifth(currentchord[0]) == currentchord[2]:
            roman_numeral_str += ('ø'
                                  if ((len(currentchord) > 3)
                                      and (intervals.minor_seventh(currentchord[0]) == currentchord[3]))
                                  else '°')
        elif intervals.major_fifth(currentchord[0]) != currentchord[2]:
            roman_numeral_str += '+'
        if len(currentchord) == 4:
            roman_numeral_str += '7'
        print(f'chord: {currentchord}, {roman_numeral_str}/{keys_[0] if resetkey else currentkey}')
        roman_numeral_analysis.append(replace_flat_and_sharp_symbols(f'{roman_numeral_str}'
                                                                     f'/{keys_[0] if resetkey else currentkey}',
                                                                     is_roman_numeral=True))

    # print(chords_)
    # print(keys)
    # print(numerals)
    # print([intervals.determine(k[0].upper() + k[1:], c[0], shorthand=True) for c, k in zip(chords_, keys)])
    return roman_numeral_analysis


def replace_flat_and_sharp_symbols(s: str, is_roman_numeral: bool = False) -> str:
    if is_roman_numeral:
        sepindex = s.find('/')
        if s[sepindex + 1].islower():
            s = s[:sepindex + 1] + s[sepindex + 1].upper() + s[sepindex + 2:] + 'm'
    else:
        if s[-1] == 'M':
            s = s[:-1]
        elif (s[-1] == '+') and (s[-3] == 'm'):
            s = s[:-3] + '+' + s[-2]
        elif s[-2] == 'M':
            s = s[:-2] + 'maj' + s[-1]
        elif s[-2:] == 'b5':
            s = s[:-2] + '<sup>(♭5)</sup>'
        elif s[-4:-1] == 'dim':
            s = s[:-4] + '°' + s[-1]
    return s.translate(str.maketrans({'b': '♭', '#': '♯', '7': '<sup>7</sup>', 'ø': '<sup>ø</sup>'}))


def chords_to_chordsymbols(chords_: list[list[str]]) -> list[str]:
    try:
        return [replace_flat_and_sharp_symbols(chords.determine(chord, shorthand=True, no_inversions=True)[0])
                for chord in chords_]
    except IndexError:
        print(chords_)


def chords_to_midi(chords_: list[list[str]], path: str = './static'):
    # Outputting audio playback of the generated chord progression:
    track = 0
    channel = 0
    time = 0  # In beats
    duration = 4  # In beats
    tempo = 120  # In BPM
    volume = 72  # 0-127, as per the MIDI standard

    midioutput = MIDIFile(4)
    midioutput.addTempo(0, time, tempo)
    midioutput.addTempo(1, time, tempo)
    midioutput.addTempo(2, time, tempo)
    midioutput.addTempo(3, time, tempo)
    for i, chord in enumerate(chords_):
        midioutput.addNote(0, channel, 36 + notes.note_to_int(chord[0]), time + (duration * i), duration - 0.1, volume=volume)
        midioutput.addNote(0, channel, 48 + notes.note_to_int(chord[0]), time + (duration * i), duration - 0.1,
                           volume=volume)
        for j, pitch in enumerate(chord):
            midioutput.addNote(0, channel, 60 + notes.note_to_int(pitch), time + (duration * i), duration - 0.1, volume=volume)

    patchid = random.randint(0, 128)
    print(patchid)
    # patchid = 81, 95
    patchid = 90
    midioutput.addProgramChange(0, channel, 0, patchid)
    # midioutput.addProgramChange(1, channel, 0, patchid)
    # midioutput.addProgramChange(2, channel, 0, patchid)
    # midioutput.addProgramChange(3, channel, 0, patchid)

    with open(f'{path}/sample-chord-progression.mid', 'wb') as outputfile:
        midioutput.writeFile(outputfile)
