import math

import streamlit as st


def shifted_key(camelot_key: str, orig_bpm: float, target_bpm: float) -> str:
    """
    Calculate the new Camelot key of a track when its tempo is changed
    by resampling (so pitch follows tempo).

    Parameters
    ----------
    camelot_key : str
        Original Camelot key, e.g. "4A" or "9B"
    orig_bpm : float
        Original BPM
    target_bpm : float
        Target BPM

    Returns
    -------
    str
        New Camelot key after pitch shift
    """
    camelot_key = camelot_key.strip().upper()
    if len(camelot_key) < 2:
        raise ValueError("Camelot key must look like '4A' or '9B'")

    try:
        orig_num = int(camelot_key[:-1])
        letter = camelot_key[-1]
    except ValueError as e:
        raise ValueError("Invalid Camelot format") from e

    if letter not in ("A", "B"):
        raise ValueError("Camelot letter must be 'A' or 'B'")

    # Compute semitone shift
    ratio = target_bpm / orig_bpm
    semitones = 12 * math.log2(ratio)
    semitones_rounded = round(semitones)

    # Convert semitone shift → Camelot step
    step_change = (semitones_rounded * 7) % 12

    new_num = (orig_num + step_change - 1) % 12 + 1

    return f"{new_num}{letter}"


def main():
    st.header(":material/database: Key Shifter")
    st.write(
        "Calculate the new Camelot key of a track when its tempo is changed by resampling (so pitch follows tempo)."
    )
    st.divider()

    c1, c2, _ = st.columns((1.3, 1, 1))
    with c1:
        key = st.pills(
            "Original Camelot Key", [f"{i}{mode}" for mode in ("A", "B") for i in range(1, 13)], default="8A"
        )
        bpm = st.number_input("Original BPM", min_value=100, max_value=180, value=128, step=1)
        target_bpm = st.number_input("Target BPM", min_value=100, max_value=180, value=140, step=1)
        key_shifted = shifted_key(key, bpm, target_bpm)
    with c2.container(border=True):
        st.write("Shifted Camelot Key")
        st.code(f"{key_shifted}@{target_bpm}", width="content")


if __name__ == "__main__":
    main()
