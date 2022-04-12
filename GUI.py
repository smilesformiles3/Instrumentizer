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
# containerColumn = sg.Column(layout=[[sg.Sizer(400, 100)]], pad=5, vertical_scroll_only=True, scrollable=True, background_color='#4b4b4b')
containerList = sg.Listbox(size=(40, 10), values=[], background_color='#4b4b4b', highlight_background_color='#ff9100')
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
        self.instrument = instrument  # meant to be waveform of instrument
        self.track = track
        self.msgs = midi.tracks[track]  # midi messages
        self.rate = rate
        self.pitch = self.instrument_base_pitch()
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
            if msg.type not in ['note_on', 'note_off']:
                continue
            pos += msg.time
            window.write_event_value('pbar', pos)
            notes.setdefault(msg.note, pos)  # structure: key = pitch, value = start position
            if msg.velocity == 0 or msg.type == 'note_off':  # note has ended - add it to the waveform!
                startpos = notes.pop(msg.note)
                # modify instrument clip with pitch and tempo, pad with zeros (convert ticks to samples)
                preclip = np.zeros(int(startpos * (self.tempo * self.rate / (self.ticks_per_beat * 1000000))))
                # print(pos)
                instrclip = pyrb.pitch_shift(pyrb.time_stretch(self.instrument, self.rate, len(self.instrument)/((pos - startpos) * (self.tempo * self.rate / (self.ticks_per_beat * 1000000)))), self.rate, -12*log2(self.pitch/(440*(2**((msg.note-69)/12)))))
                postclip = np.zeros(len(self.waveform) - len(preclip) - len(instrclip))
                clip = np.concatenate((preclip, instrclip, postclip))
                self.waveform += clip
        return self

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

    def export(self, filename):
        wav.write(filename + ".wav", self.rate, self.waveform)
        print('saved!')


while True:
    event, values = window.read()
    if event == 'Exit' or event == sg.WIN_CLOSED:
        break
    elif event == 'MIDI_SELECT':
        midiFilenameInput.update(value=values['MIDI_SELECT'])
    elif event == 'go':
        for element in [midiFilenameInput, wavFilenameInput, midiButton, wavButton, goButton]:
            element.update(disabled=True)
        rate, data = wav.read(values[1])
        try:
            data = data.T[0, :]
        except:
            pass
        midi = mido.MidiFile(values[0])
        track = 9
        totalticks = sum(msg.time for msg in midi.tracks[track] if msg.type in ['note_on', 'note_off'])
        progressBar.update(current_count=0, max=totalticks, visible=True)
        t = Track(data, midi, track, rate)
        # plt.plot(data)
        # plt.show()
        # print(t.tempo)
        # print(t.ticks_per_beat)
        # print(t.length)
        # print(t.midi.tracks[track])
        # print(t.rate)
        window.perform_long_operation(t.midi_to_waveform, 'instrumentized')
    elif event == 'pbar':
        progressBar.update(current_count=values['pbar'])
    elif event == 'instrumentized':
        for element in [midiFilenameInput, wavFilenameInput, midiButton, wavButton, goButton]:
            element.update(disabled=False)
        progressBar.update(visible=False)
        t = values['instrumentized']
        t.export('track' + str(t.track))
