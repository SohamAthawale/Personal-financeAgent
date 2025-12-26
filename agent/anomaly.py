import numpy as np

def detect_spikes(df, window=30, z=3):
    rolling = df["withdrawal"].rolling(window)
    zscore = (
        (df["withdrawal"] - rolling.mean()) / rolling.std()
    )
    return df[zscore > z]
