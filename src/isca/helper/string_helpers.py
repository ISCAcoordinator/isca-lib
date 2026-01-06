import difflib
import re


def find_diffs(s1: str, s2: str, label_s1="-", label_s2="+") -> list[str]:
    """Helper to list the difference between two strings.

    Each string is split per sentence for better readability.

    Parameters
    ----------
    s1: str
        First string
    s2: str
        Second string
    label_s1: str
        Label of the first string
    label_s2: str
        Label of the second string

    Returns
    -------
    list[str]
        The list of differences prefixed with the string labels
    """
    # Split by punctuation to have a more refined comparison
    s1 = re.sub("[ \t]+", " ", s1)
    info1 = [f"{s}\n" for s in re.split(r"[.;:] ", s1)]
    info2 = [f"{s}\n" for s in re.split(r"[.;:] ", s2)]

    # Compute diff
    diff = difflib.ndiff(info1, info2)

    # Filter out equal lines
    final_diff = []
    for l in list(diff):
        if not l.startswith(" "):
            l = l.strip()
            if l.startswith("-"):
                l = label_s1 + l[1:]
            elif l.startswith("+"):
                l = label_s2 + l[1:]
            else:
                l = l[:1] + (" " * (len(label_s2) - 1)) + l[1:]
            final_diff.append(l)

    return final_diff
