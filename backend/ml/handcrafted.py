import numpy as np
import librosa
from ml.audio_utils import SAMPLE_RATE, preprocess


def score_handcrafted(audio: np.ndarray) -> float:
    """
    Layer 2: spectral/MFCC heuristics.
    Returns spoof probability in [0, 1]; higher = more likely fake.
    """
    audio = preprocess(audio)

    # MFCC temporal variation — natural speech has high dynamic variation (~5-15 per coeff).
    # TTS/vocoders are smoother; low std -> suspicious.
    mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=20,
                                  n_fft=512, hop_length=160)
    mfcc_std = float(np.mean(np.std(mfccs, axis=1)))
    # std>=8 -> score=0 (real), std<=2 -> score=1 (fake)
    mfcc_score = float(np.clip(1.0 - (mfcc_std - 2.0) / 6.0, 0.0, 1.0))

    # Spectral flatness — voiced speech has harmonic structure -> low flatness (0.01-0.05).
    # Vocoders and some GAN models produce unnaturally flat spectra.
    flatness = librosa.feature.spectral_flatness(y=audio, n_fft=512,
                                                  hop_length=160)[0]
    mean_flatness = float(np.mean(flatness))
    # flatness>=0.10 -> score=1, flatness<=0.01 -> score=0
    flatness_score = float(np.clip((mean_flatness - 0.01) / 0.09, 0.0, 1.0))

    # Spectral centroid coefficient of variation — natural speech shifts centroid
    # significantly as phonemes change; low CV = monotone/synthetic.
    centroid = librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE,
                                                  n_fft=512, hop_length=160)[0]
    cv = float(np.std(centroid) / (np.mean(centroid) + 1e-8))
    # CV>=0.30 -> score=0 (natural dynamics), CV<=0.05 -> score=1
    centroid_score = float(np.clip(1.0 - (cv - 0.05) / 0.25, 0.0, 1.0))

    return float(np.clip(
        0.45 * mfcc_score + 0.35 * flatness_score + 0.20 * centroid_score,
        0.0, 1.0
    ))
