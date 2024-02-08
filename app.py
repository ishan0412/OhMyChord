from flask import Flask, render_template, request
from chordgenerator import generatechords, chords_to_chordsymbols, chords_to_midi, process_roman_numeral_analysis
from mingus.core.mt_exceptions import NoteFormatError
from mingus.core.notes import note_to_int
from mingus.core.intervals import major_third, minor_fifth, perfect_fifth
from colorsys import hsv_to_rgb

app = Flask(__name__)
app.jinja_env.filters['zip'] = zip

global randomfactor

@app.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        randomfactor = int(request.form['randomness-slider'])
    validchords = False
    while not validchords:
        try:
            try:
                randomfactor_as_decimal = 1 - (randomfactor / 100)
            except UnboundLocalError:
                randomfactor = 50
                randomfactor_as_decimal = 0.5
            print(f'randomfactor: {randomfactor_as_decimal}')
            chords, keys, numerals = generatechords(return_functional_analysis=True, numbars=4,
                                                    diatonicity_factor=randomfactor_as_decimal,
                                                    functionalharmony_factor=randomfactor_as_decimal)
            numerals = process_roman_numeral_analysis(chords, keys, numerals)
            chordsymbols = chords_to_chordsymbols(chords)
            validchords = chordsymbols is not None
        except (ValueError, NoteFormatError, IndexError) as e:
            print(e)

    chords_to_midi(chords)

    if chordsymbols is None:
        print('Mettu')
        print(chordsymbols)

    # Color chords based on quality:
    hues = ['#%02x%02x%02x' %
            tuple(map(lambda x: round(x * 255), hsv_to_rgb(
                ((((note_to_int(c[0]) * 15) + (320 if (major_third(c[0]) == c[1]) else 140)) % 360) / 360),
                0.28, 0.54))) for c in chords]  # s = 0.54-0.57, v = 0.60-0.62 -> s = 0.24-0.32, v = 0.54
    # hues = [((note_to_int(c[0]) * 15) + (320 if (major_third(c[0]) == c[1]) else 140)) % 360
    #         for c in chords]
    print(hues)
    return render_template('index.html', chords=chordsymbols, hues=hues, numerals=numerals, randomfactor=randomfactor)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
