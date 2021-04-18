import unicodedata

# -------------------------------------------------------------------------
#
# constants
#
# -------------------------------------------------------------------------
IGNORE = "HW~!@#$%^&*()_+=-`[]\\|;:'/?.,<>\" \t\f\v"
TABLE = bytes.maketrans(b"ABCDEFGIJKLMNOPQRSTUVXYZ", b"012301202245501262301202")

# -------------------------------------------------------------------------
#
# soundex - returns the soundex value for the specified string
#
# -------------------------------------------------------------------------
def soundex(strval):
    "Return the soundex value to a string argument."

    strval = unicodedata.normalize("NFKD", str(strval.upper().strip())).encode(
        "ASCII", "ignore"
    )
    if not strval:
        return "Z000"
    strval = strval.decode("ASCII", "ignore")
    str2 = strval[0]
    translator = strval.maketrans("", "", IGNORE)
    strval = strval.translate(translator)
    strval = strval.translate(TABLE)
    if not strval:
        return "Z000"
    prev = strval[0]
    for character in strval[1:]:
        if character != prev and character != "0":
            str2 = str2 + character
        prev = character
    # pad with zeros
    str2 = str2 + "0000"
    return str2[:4]
