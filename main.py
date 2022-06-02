import mido
import numpy as np
from scipy.io import wavfile as wav
from scipy import fftpack
import pyrubberband as pyrb
from math import log2
import matplotlib.pyplot as plt


class Track:
    def __init__(self, instrument, midi, track, rate=48000):  # length in seconds, rate in samples/sec
        # the tempo of the test song, wii sports, is 504201 and tpb = 960
        self.instrument = instrument  # meant to be waveform of instrument
        self.msgs = midi.tracks[track]  # midi messages
        self.rate = rate
        self.pitch = self.instrument_base_pitch()
        print('pitch', self.pitch)
        self.midi = midi
        self.tempo = [i for i in midi.tracks[0] if i.type == 'set_tempo'][0].tempo
        self.ticks_per_beat = midi.ticks_per_beat
        self.length = midi.length
        self.waveform = np.zeros(int(self.length * rate))  # output waveform

    def midi_to_waveform(self):
        pos = 0  # in ticks
        notes = dict()
        for msg in self.msgs:
            if not msg.type == 'note_on':
                continue
            notes.setdefault(msg.note, pos)  # structure: key = pitch, value = start position
            pos += msg.time
            if msg.velocity == 0 or msg.type == 'note_off':  # note has ended - add it to the waveform!
                startpos = notes.pop(msg.note)
                # modify instrument clip with pitch and tempo, pad with zeros (convert ticks to samples)
                preclip = np.zeros(int(startpos * (self.tempo * self.rate / (self.ticks_per_beat * 1000000))))
                print(pos)
                instrclip = pyrb.pitch_shift(pyrb.time_stretch(self.instrument, self.rate, len(self.instrument)/((pos - startpos) * (self.tempo * self.rate / (self.ticks_per_beat * 1000000)))), self.rate, -12*log2(self.pitch/(440*(2**((msg.note-69)/12)))))
                postclip = np.zeros(len(self.waveform) - len(preclip) - len(instrclip))
                clip = np.concatenate((preclip, instrclip, postclip))
                self.waveform += clip

    def instrument_base_pitch(self):
        out = fftpack.rfft(self.instrument)  # real fast fourier transform, to convert time domain into frequency domain
        power = np.abs(out) ** 2  # power array
        freqs = fftpack.fftfreq(out.size, d=1 / self.rate)
        plt.plot(freqs, power)
        plt.show()
        x = freqs[np.argmax(power)]
        if x == 0:
            power[np.argmax(power)] = 0
            x = freqs[np.argmax(power)]
        return x

    def export(self, filename):
        wav.write(filename + ".wav", self.rate, self.waveform)
        print('saved!')


mid = mido.MidiFile(r"C:\Users\nikhi\PycharmProjects\Instrumentizer\Test Files\wii-wiisports-titlescreen.mid")
# print(mid.tracks[0])
# rate, data = wav.read('converted.wav')
#
# print(mid.tracks[2])
#
# # test = Track(data.T[0,:], mid.tracks[2], 504201, 960, 125)
# # test.midi_to_waveform()
# # test.export()
