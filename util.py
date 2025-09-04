import re
import unicodedata


def handle_non_english_charcters(value:str):
    nfkd = unicodedata.normalize("NFKD", value)
    # Encode to ASCII, ignore errors (drops non-ASCII chars)
    only_ascii = nfkd.encode("ascii", "ignore").decode("ascii")
    # Replace spaces & non-word chars with underscore
    clean = re.sub(r"[^\w]+", "_", only_ascii).strip("_")
    # print(f"clean:{clean}")
    return clean