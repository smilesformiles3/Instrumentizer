from scipy.io import wavfile as wav
from scipy import fftpack
import mido
import numpy as np
import pyrubberband as pyrb
import matplotlib.pyplot as plt
from math import log2
import PySimpleGUI as sg

bg_color = '#2b2b2b'
title_text = sg.Text("Instrumentizer", size=30, font=(None, 14), background_color=bg_color, justification='center',
                     pad=(0, 10))
midiFilenameInput = sg.Input(size=10, border_width=4, disabled=True, pad=5)
wavFilenameInput = sg.Input(size=10, border_width=4, pad=5)
midiButton = sg.FileBrowse(file_types=(("MIDI Files", ".mid .midi"),), pad=5, enable_events=True, key='MIDI_SELECT',
                           target='MIDI_SELECT')
wavButton = sg.FileBrowse(file_types=(("WAV files", ".wav"),), pad=5, key='WAV_SELECT')
goButton = sg.Button(button_text="Go!", pad=5, enable_events=True, key="go")
containerList = sg.Listbox(size=(40, 10), values=[], background_color='#4b4b4b', highlight_background_color='#ff9100',
                           key='TRACK_SELECT', select_mode='multiple')
progressBar = sg.ProgressBar(max_value=1, size=(10, 10), visible=False, bar_color=('#ff9100', '#ffffff'))

layout = [[title_text],
          [sg.Text("MIDI Filepath:", background_color=bg_color), midiFilenameInput, midiButton],
          [sg.Text("WAV (Instrument) Filepath:", background_color=bg_color), wavFilenameInput, wavButton],
          [containerList],
          [progressBar],
          [goButton, sg.Exit()]]

window = sg.Window(title="Instrumentizer", layout=layout, background_color=bg_color, margins=(50, 50),
                   element_justification='center', button_color='#ff9100')


class Track:
    def __init__(self, instrument, midi, track, rate=48000):  # length in seconds, rate in samples/sec
        # the tempo of the test song, wii sports, is 504201 and tpb = 960
        self.instrument = Instrument(instrument, rate)  # meant to be waveform of instrument
        self.track = track
        self.msgs = midi.tracks[track]  # midi messages
        self.rate = rate
        self.pitch = self.instrument.pitch
        # print('pitch', self.pitch)
        self.midi = midi
        self.tempo = [i for i in midi.tracks[0] if i.type == 'set_tempo'][0].tempo
        self.ticks_per_beat = midi.ticks_per_beat
        self.length = midi.length
        self.waveform = np.zeros(int(self.length * rate))  # output waveform

    def midi_to_waveform(self):
        pos = 0  # in ticks
        notes = dict()
        for msg in self.msgs:
            pos += msg.time
            window.write_event_value('pbar', pos)
            if msg.type not in ['note_on', 'note_off']:
                continue
            notes.setdefault(msg.note, pos)  # structure: key = pitch, value = start position
            if msg.velocity == 0 or msg.type == 'note_off':  # note has ended - add it to the waveform!
                startpos = notes.pop(msg.note)
                # modify instrument clip with pitch and tempo, pad with zeros (convert ticks to samples)
                preclip = np.zeros(int(startpos * (self.tempo * self.rate / (self.ticks_per_beat * 1000000))))
                # print(pos)
                instrclip = pyrb.pitch_shift(pyrb.time_stretch(self.instrument.instrument, self.rate, len(self.instrument)/((pos - startpos) * (self.tempo * self.rate / (self.ticks_per_beat * 1000000)))), self.rate, -12*log2(self.pitch/(440*(2**((msg.note-69)/12)))))
                postclip = np.zeros(len(self.waveform) - len(preclip) - len(instrclip))
                clip = np.concatenate((preclip, instrclip, postclip))
                self.waveform += clip

    def export(self, filename):
        wav.write(filename + ".wav", self.rate, self.waveform)
        print('saved!')


class Midi:
    def __init__(self, midi, instrument, rate=48000):
        self.midi = midi
        self.waveform = np.zeros(int(midi.length * rate))
        self.instrument = instrument
        self.rate = rate

    def instrumentize_multiple(self, tracks):
        for track in tracks:
            t = Track(self.instrument, self.midi, track, self.rate)
            t.midi_to_waveform()
            self.waveform += t.waveform
            window.write_event_value('trackcomplete', sum(msg.time for msg in midi.tracks[track]))
        return self

    def export(self, filename):
        wav.write(filename + ".wav", self.rate, self.waveform)
        print('saved!')


class Instrument:
    def __init__(self, instrument, rate):
        self.instrument = instrument
        self.rate = rate
        self.pitch = self.instrument_base_pitch()

    def __len__(self):
        return len(self.instrument)

    def instrument_base_pitch(self):
        out = fftpack.rfft(self.instrument)  # real fast fourier transform, to convert time domain into frequency domain
        power = np.abs(out) ** 2  # power array
        freqs = fftpack.fftfreq(out.size, d=1 / self.rate)
        # plt.plot(freqs, power)
        # plt.show()
        x = freqs[np.argmax(power)]
        if x == 0:
            power[np.argmax(power)] = 0
            x = freqs[np.argmax(power)]
        return x


counter = 0  # used for progress bar
while True:
    event, values = window.read()
    if event == 'Exit' or event == sg.WIN_CLOSED:
        break
    elif event == 'MIDI_SELECT':
        midiFilenameInput.update(value=values['MIDI_SELECT'])
        midi = mido.MidiFile(values['MIDI_SELECT'])
        names = []
        for i, track in enumerate(midi.tracks):
            for msg in track:
                if msg.type == 'track_name':
                    names.append('Track ' + str(i) + ': ' + msg.name)
                    break
            else:
                names.append('Track ' + str(i))
        containerList.update(values=names)
    elif event == 'go':
        print(values)
        counter = 0
        for element in [midiFilenameInput, wavFilenameInput, midiButton, wavButton, goButton]:
            element.update(disabled=True)
        rate, data = wav.read(values['WAV_SELECT'])  # read from wav file specified
        try:
            data = data.T[0, :]
        except:
            pass
        midi = mido.MidiFile(values['MIDI_SELECT'])  # read from midi file specified
        mobj = Midi(midi, data, rate)
        tracks = [int(track.split()[1].strip(':')) for track in values['TRACK_SELECT']]
        totalticks = sum(msg.time for track in tracks for msg in midi.tracks[track])
        progressBar.update(current_count=0, max=totalticks, visible=True)
        # tobjs = [Track(data, midi, track, rate) for track in tracks]
        # plt.plot(data)
        # plt.show()
        # print(t.tempo)
        # print(t.ticks_per_beat)
        # print(t.length)
        # print(t.midi.tracks[track])
        # print(t.rate)
        window.perform_long_operation(lambda: mobj.instrumentize_multiple(tracks), 'instrumentized')
    elif event == 'pbar':
        progressBar.update(current_count=counter + values['pbar'])
    elif event == 'trackcomplete':
        counter += values['trackcomplete']
    elif event == 'instrumentized':
        for element in [midiFilenameInput, wavFilenameInput, midiButton, wavButton, goButton]:
            element.update(disabled=False)
        progressBar.update(visible=False)
        m = values['instrumentized']
        m.export('trackcombo1')
