from python_speech_features import mfcc
import ffmpeg
import scipy.io.wavfile as wav
from numpy import zeros, sum, linalg, argmax, multiply, mean, std
import os

def std_mfcc(mfcc):
    return (mfcc - mean(mfcc, axis=0)) / std(mfcc, axis=0)

def cross_correlation(mfcc1, mfcc2, nframes):
    n1, mdim1 = mfcc1.shape
    n2, mdim2 = mfcc2.shape
    n = n1 - nframes + 1
    c = zeros(n)
    for k in range(n):
        cc = sum(multiply(mfcc1[k:k+nframes], mfcc2[:nframes]), axis=0)
        c[k] = linalg.norm(cc)
    return c

def find_offset(full, preview, samplerate=8000):
    if (preview == "skip"):
        return 0, 10
    
    filename_full_tmp = full.strip(".wav") + "_tmp.wav"
    filename_preview_tmp = preview.strip(".wav") + "_preview_tmp.wav"

    if (not os.path.isfile(full) or not os.path.isfile(preview)):
        return 0, 10

    ffmpeg.input(full).output(filename_full_tmp, ar=samplerate).global_args('-loglevel', 'error').overwrite_output().run()
    ffmpeg.input(preview).output(filename_preview_tmp, ar=samplerate).global_args('-loglevel', 'error').overwrite_output().run()

    _, full_sig = wav.read(filename_full_tmp)
    _, preview_sig = wav.read(filename_preview_tmp)

    if (full_sig is None or preview_sig is None):
        return 0, 10

    full_len = len(full_sig) / samplerate
    full_mfcc = std_mfcc(mfcc(full_sig, samplerate, nfft=256))

    preview_len = len(preview_sig) / samplerate
    preview_mfcc = std_mfcc(mfcc(preview_sig, samplerate, nfft=256))

    c = cross_correlation(full_mfcc, preview_mfcc, len(preview_mfcc))
    max_k_index = argmax(c)

    offset = max_k_index / len(full_mfcc) * full_len

    os.remove(filename_full_tmp)
    os.remove(filename_preview_tmp)

    return offset, preview_len

def compress_audio(filename, target, quality = "128k"):
    ffmpeg.input(filename).output(target, ab=quality).global_args('-loglevel', 'error').overwrite_output().run()

def decode_audio(filename, target):
    ffmpeg.input(filename).output(target, map_metadata=0).global_args('-loglevel', 'error').overwrite_output().run()
