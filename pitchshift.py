import numpy as np
from scipy.io import wavfile as wav
from scipy import fftpack
import matplotlib.pyplot as plt
import ffmpy


def tempo_change(_input, scale, output):
    ff = ffmpy.FFmpeg(inputs={_input: None}, outputs={output: ["-filter:a", "atempo=" + str(scale)]})
    ff.run()


def pitch_change(_input, origrate, scale, output):
    ff = ffmpy.FFmpeg(inputs={_input: None},
                      outputs={output: ["-af", "asetrate=" + str(origrate) + "*" + str(scale) + ",atempo=" + str(
                          1 / scale) + ",aresample=" + str(origrate)]})
    ff.run()


rate, data = wav.read('converted.wav')
print(rate)
print(len(data))
x = np.arange(len(data))
frq = x / rate
out = fftpack.rfft(data.T[0])
power = np.abs(out) ** 2
freqs = fftpack.fftfreq(out.size, d=1 / rate)
plt.plot(freqs, power)
# plt.show()

pos_mask = np.where(freqs > 0)
f = freqs[pos_mask]
peak_freq = freqs[power[pos_mask].argmax()]
print(peak_freq)

shift = 300
np.roll(out, shift)
out[0:shift] = 0
shifted = fftpack.irfft(out)

m = np.max(np.abs(shifted))
sigf32 = (shifted / m).astype(np.float32)
wav.write('shifted.wav', rate, sigf32)

# #Pitch correcting... not necessary for our project, but interesting to listen to?
# high_freq_fft = out.copy()
# high_freq_fft[np.abs(freqs) > peak_freq] = 0
# filtered = fftpack.irfft(high_freq_fft)
#
# m = np.max(np.abs(filtered))
# sigf32 = (filtered/m).astype(np.float32)
#
# wav.write("pitch-corrected.wav", rate, sigf32)
