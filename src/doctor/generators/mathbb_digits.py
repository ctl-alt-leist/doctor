r"""
Double-struck digits for KaTeX \mathbb.

KaTeX's fonts carry double-struck glyphs only for the letters A-Z, and its
metrics tables know it: a digit inside \mathbb is emitted as a plain
"mord" span with no mathbb class at all, so $\mathbb{1}$ renders as an
ordinary roman "1". No CSS selector can catch it after the fact, and
\text{<double-struck codepoint>} throws a metrics error, so the rewrite
has to happen before KaTeX parses the math.

The fix has two halves, both injected into the generator templates:

1. A preProcess hook on renderMathInElement rewrites \mathbb{<digits>}
   into \htmlClass{doctor-bb}{<digits>} at render time (with trust
   enabled for \htmlClass only). The digits become normal "mord" spans
   inside a span carrying the doctor-bb class. \mathbb of letters is
   untouched and keeps the standard KaTeX path.
2. A CSS rule gives .doctor-bb the stack "KaTeX_AMS, Doctor Blackboard
   Digits": the digits are missing from KaTeX_AMS, so the browser's
   per-glyph fallback lands on the shipped face and draws them
   double-struck. The font travels as a data URI, so every generated
   document (single-page HTML, multi-page HTML, PDF via Playwright,
   slides) is self-contained.

The font is a ten-glyph subset of STIX Two Math (the mathematical
double-struck digits U+1D7D8-U+1D7E1, remapped onto ASCII 0-9), renamed
because the SIL Open Font License reserves the name "STIX" for the
original. To regenerate: subset
/System/Library/Fonts/Supplemental/STIXTwoMath.otf to those codepoints
with fontTools, copy the cmap entries onto 0x30-0x39, rename the family,
and save with flavor="woff".
"""

MATHBB_DIGITS_FONT_WOFF_BASE64 = (
    "d09GRk9UVE8AAAqYAAwAAAAAC+wAAiFIAAAAAAAAAAAAAAAAAAAAAAAAAABDRkYgAAADJAAABtIAAAdTOebl9UdERUYAAAn4"
    "AAAAFgAAABYAEAALR1BPUwAAChAAAAAgAAAAIER2THVHU1VCAAAKMAAAADsAAAA8AKz2lk9TLzIAAAF8AAAAVAAAAGBqKHMt"
    "Y21hcAAAAuAAAAAvAAAAPAASsIZoZWFkAAABHAAAADYAAAA2I+jqnGhoZWEAAAFUAAAAIAAAACQGUwGFaG10eAAACmwAAAAs"
    "AAAALBciAbFtYXhwAAABdAAAAAYAAAAGAAtQAG5hbWUAAAHQAAABDwAAAgwstEiTcG9zdAAAAxAAAAATAAAAIP+1ADMAAQAA"
    "AAIhSGKhFKtfDzz1AAgD6AAAAADb/8ZZAAAAAOZuv7AACv9XAlMDEQAAAAYAAgAAAAAAAHicY2BkYGD69V+I4RdTLAMXAxdT"
    "MANQBAVwAwBqhQPdAABQAAALAAB4nGNgYTrKOIGBlYGB8QvjFwYGhl8QGoiNGaUZGJiY2JhZWViZmFkYoIAJSgeHeEYwHGAw"
    "+P+f6dd/IYZfXM5smUBhRpAc402miUBKgYEJAFBSESN4nJWQS04CQRRFTwsanRiXQBxpIog4MJGRSkwYmBglhqkoQivahob4"
    "WZVLcgWuwVNFowycmE6nTt1336cesModJZLyGvDhP+OEurcZL7HOZ8El7vkquLzgWWYz6Ra8wk7yXvBG9JyQ8cwbY1IGDJlQ"
    "oWGkzh7VSA2pQsdY3/NSatOVTs180p/L5+Zn9u9zEyscMfUcqo1jfCtWntgp55Bdv4H9gmNKj5pZGY+quVqqK6jz26tbmHfa"
    "piWHHqFyhWNGXHt/0J9JY25VW/Etacy4cKaB9UYx+t/spspvRlMlTJZbc+J2Mier/mykw4vKmXXCu670hLencfaw05p73Jd6"
    "ngf+i7P8NcnCHN91eFNqAHicY2BgYGJgYGABYhEGZgYuMM3DAAIaDBAAkjcAYksgZmRgvH4DiB+C2AAzTQRGAHicY2BmAIP/"
    "mxiMGbAAACySAegAeJxNk3tQVNcdx+9luXtxgZVwPUxzt7m7ohigqOALa0qD4dFAIgTEBDs+WJ4L7MvL3V2fzWqsvHw0Kglv"
    "EHksICjCXliMVixKDSZatFpsYpI+zExNYjul/V08O7W725lM//nM/M6c3/f7e5xDEv5+BEmSizbnpOXm2EybtIJueXZRiUWv"
    "5b3ny6UIQlpGSi8HEVKknxQpk6L8E4JkV4L863CC9PV8FyUtWyj+UP73UCn6BWKhR4ugiWCCIV4k1EQE8SMijognEojXiB5i"
    "npSTQZa45Pjk9T7+2MeNPr7mY5KPyT6m+JjqZUqsj3GrVsStjvXWqUk1GYUKjdZYqPGFnro1Wr5II/DawiKDli+v0JiKNTm6"
    "Ik2asUIoFSxCkfcgRV9UIPClBVq9L/V/oclYWlChSTGWlBqLiviKGE9KwYokk3kPX1qiEzSrYmPjlq+KXRXnk/s/87d4U5kn"
    "X7PRIuhMfIVGJwjmig0lpYLOkr+iwGTw+Jot+R7uLvbe/75O74AzTLxBqyf8SDIo9H7ik3agE4Zn/hr4nIi2E4EkWbmACPQO"
    "soD4IxlAHvAL9yv2eyjjZV3+A1RiF064CgTQUvvQrSuhdVdyYXOi5qWbv2aemaWvcQJ6luH+/D8ZtNR7Fbmt848lqxxXuH+L"
    "mmggYe0svMz+c81Y1LLU7A3bWoV+jpk3n22v71Mzc2aNgnl2YXaxQnnILkrTIjnqmhLhTXHKJZM64A6CsC2QizNx5haci8Nw"
    "2ATeCpmQOQFbIYzDX8Fp1NzZV3dedb7v4N5OtbuO3svrD5aoSvR1zbx6KdShmeYvxeuceyOdd33vVzMsPIIyJGY1r0tmk/eu"
    "y8vilDip1ilJNhKWitOiDJZKg8g9CNHz4TRuwMH1hRQs/hhNOyj3yBu0MqPG+YlTelsMHbu8bRTyxEkX8x0IEIXm/kwNOmbv"
    "wAIWFq75dDFeEL8eB3Oj8u9OfnTziaqlufpIsxp/TtfUVNfU1AQw/8a1WEf9XPoBfQmiKTylRXBUbk2j8A05VEkONGDpKMxg"
    "083bDTpO+TO7CAOirQ0qxVCYEvXdZucFl9HF/MEOU9JjhA9F5tHMjB1kuFP+S6tQJahefafrLq/e8S61uutO/lMV+D+9Bi+o"
    "mRH7w4LriT3cMZpxEVPnhsZn2H+t/Sguam1WhJ0bl882Xbo4q/LINjZVVzWovZKE+1X0jqW03MpBBX3R1LhzJ8vMEumgR/A2"
    "7djdashjC/cVlldwSqHWCUqnxFyttYXCJfGmyHwm9cJ65IyTXt9Cu2l3OlUAvXg9RMJ6mvkmHObQzXuUe3QTnSe9gvCH2Ewr"
    "sz2Nfjsy45x0ks/JWDux+CXvM0iTDqBrsJjCD+Tr8PvUiPyT6cO2y+oaPEUdtloqedUrW7/v9q6327C/PIJFkIpXDuOV6rMz"
    "VIMTtU5SsEduyaYysRZdMHfkZ7JZwo5iI6es9ng+ccIbTnLKdU2EZHHCY1k8H4YwV4PpbWlJAZsz9OsiWLzkBg6HFEDf/gk8"
    "O97wBQ4u2P4L3shVAyf/eOJxDxBHA3CjW0TQTff3DjeOqc60Vx1uUeN79CHBVGlQFZWfauDVedJq5A6h88cPzNxhH7ZND17m"
    "oNG9BEEnPWhs3ZHFpu/ervPUldNulXjnbSfpkMwySS3xCGe4eeqKHKrnFZR7pTwdx1AS40R4Ru64TcFtudLqaaVXhFox9PK4"
    "cXxwRP+ciLQTz58/9YAI8aLdTnxgHy4dGXIZXIymSgqALxETFXK35dKV+yz4RfwGy7BixWbslziae3cPV00zvwpYY9mWHc9i"
    "xVwmhEDI3BQoOCax6ousyYQzHDOpwWll6FSn48SA6pzjyMEuNT5Gv7fLeKRMVW44cXqXmslPhJ/CDDrsGYFeZTAfP2lRHwUb"
    "dbKj67hD1e2ofK9LzeRE4hJ3Kyo7YxtwseMtQ4OdHNzCfminTVcqcFBID/BtJTtYJvotfM3zfQ1t+/tFdqy5t6eNg4sxKG+f"
    "3mjjYBPdbWsxalll9WERUp3wjZOccE14V3rNs9IFoEBpW2J4TVVAHv0UUNen99W/mx76x99YWJIBMTgJo6g1+EUc8lk80GPj"
    "9Z0O7pgcHvjjTrrcULB/h8piPX5yjxp+T5/u6DnRqxrqP7SvUy26Y5GkoEe2Nmx8k02wbdJt43CjtAThLlrn2D02yd5qHR/s"
    "5ZT7G6XSps62e/UNzafqB5vk+N1G+v0ghUPxKNDxYVDQo9NBwfOFi6QHSGQIGUmymlVD1qPn2L7ujhvTw7qfcHgFlhXjMHYX"
    "HYiVKFwR2Gft0RVbzOVlrcLF8+1n+7nA/wJRqE+sAAAAAQAAAAwAAAAAAAAAAgABAAAACgABAAAAAQAAAAoAHAAeAAFERkxU"
    "AAgABAAAAAD//wAAAAAAAHicY2BkYGDgYrBgsGJgdXHzCWFQSK4symHQSi9KzWbQykksyWPQyk0syWDQYmABqmT4/58BDgBU"
    "QgszAAJdAAoCOgAsAZQAIQIGAC0B/wA2AiwAEgIKACQCQQA8AgwAHQIuADICQQA2"
)

MATHBB_DIGITS_CSS = """\
        /* Double-struck digits for \\mathbb -- KaTeX has none. The preProcess
           hook on renderMathInElement rewrites \\mathbb digits into
           .doctor-bb spans; digits are missing from KaTeX_AMS, so they fall
           through to the shipped face and come out double-struck. */
        @font-face {{
            font-family: "Doctor Blackboard Digits";
            src: url("data:font/woff;base64,{font}") format("woff");
            unicode-range: U+30-39;
        }}
        .katex .doctor-bb {{
            font-family: KaTeX_AMS, "Doctor Blackboard Digits", serif;
        }}
""".format(font=MATHBB_DIGITS_FONT_WOFF_BASE64)

# Written for insertion directly after "renderMathInElement(document.body, {".
# The options blocks in the templates set no preProcess or trust of their own
# (the document template's explicit "trust" was removed in favor of this).
MATHBB_DIGITS_RENDER_OPTIONS = (
    "\n"
    "                // KaTeX cannot typeset \\mathbb digits; reroute them to the\n"
    "                // shipped double-struck digit font (see mathbb_digits.py)\n"
    r"""                preProcess: function(math) {
                    return math.replace(/\\mathbb\{(\d+)\}/g, '\\htmlClass{doctor-bb}{$1}');
                },
                trust: function(context) { return context.command === '\\htmlClass'; },"""
)


def inject_mathbb_digits(template: str) -> str:
    """Wire the double-struck digit fix into a KaTeX-rendering template.

    Adds the font and its CSS rule to the first <style> block, and the
    preProcess/trust options to every renderMathInElement call. Both edits
    are no-ops on templates without the corresponding anchor text.
    """
    template = template.replace("<style>", "<style>\n" + MATHBB_DIGITS_CSS, 1)
    template = template.replace(
        "renderMathInElement(document.body, {",
        "renderMathInElement(document.body, {" + MATHBB_DIGITS_RENDER_OPTIONS,
    )

    return template
