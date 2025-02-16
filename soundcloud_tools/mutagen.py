from mutagen.id3._frames import Frame
from mutagen.id3._specs import EncodedTextSpec, Encoding, EncodingSpec, MultiSpec


class TextFrameComma(Frame):
    """Text strings.

    Text frames support casts to unicode or str objects, as well as
    list-like indexing, extend, and append.

    Iterating over a TextFrame iterates over its strings, not its
    characters.

    Text frames have a 'text' attribute which is the list of strings,
    and an 'encoding' attribute; 0 for ISO-8859 1, 1 UTF-16, 2 for
    UTF-16BE, and 3 for UTF-8. If you don't want to worry about
    encodings, just set it to 3.
    """

    _framespec = [
        EncodingSpec("encoding", default=Encoding.UTF16),
        MultiSpec("text", EncodedTextSpec("text"), sep="\u0000", default=[]),
    ]


class TPE1(TextFrameComma): ...
