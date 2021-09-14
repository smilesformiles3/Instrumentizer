import mido
import numpy
import ffmpy


def tempo_change(_input, scale, output):
    ff = ffmpy.FFmpeg(inputs={_input: None}, outputs={output: ["-filter:a", "atempo=" + str(scale)]})
    ff.run()


def pitch_change(_input, origrate, scale, output):
    ff = ffmpy.FFmpeg(inputs={_input: None},
                      outputs={output: ["-af", "asetrate=" + str(origrate) + "*" + str(scale) + ",atempo=" + str(
                          1 / scale) + ",aresample=" + str(origrate)]})
    ff.run()


class Track:
    def __init__(self, instrument, length, rate=48000):  # length in seconds, rate in samples/sec
        self.instrument = instrument
        self.msgs = []
        self.waveform = numpy.zeros(length * rate)

    def midi_to_waveform(self, msgs):
        pos = 0  # in ticks
        notes = []
        for msg in msgs:
            if msg.time == 0:
                notes.append(msg.note)
            else:
                for note in notes:
                    # modify instrument clip with pitch and tempo, pad with zeros
                    clip = numpy.zeros(pos)
                    clip += self.instrument  # todo: tune the instrument
                    clip += numpy.zeros(self.waveform.length - len(clip))
                    self.waveform = numpy.add(self.waveform, clip)
                pos += msg.time


mid = mido.MidiFile('wii-wiisports-titlescreen.midi')

for i, track in enumerate(mid.tracks):
    print('Track {}: {}'.format(i, track.name))
print(mid.ticks_per_beat)
print(mid.tracks[2])
