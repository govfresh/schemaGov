#!/usr/bin/env python3
"""Flesch-Kincaid grade level check for vocabulary (codelist + term) descriptions.

Run with no arguments to list every description currently above grade 9.
This is a gate, not a style guide: passing it doesn't guarantee plain
language, active voice, or jargon-free text on its own, but a description
that fails it needs shortening or simplifying no matter what else is true
about it.
"""
import re
import sys
import json
import glob


def syllables(word):
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    count, prev_vowel = 0, False
    for ch in word:
        is_vowel = ch in "aeiouy"
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def fk_grade(text):
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    if not sentences or not words:
        return 0.0
    syl = sum(syllables(w) for w in words)
    return 0.39 * (len(words) / len(sentences)) + 11.8 * (syl / len(words)) - 15.59


def main():
    threshold = 9.0
    over = 0
    for f in sorted(glob.glob("profiles/*/codelists/*.json")):
        d = json.load(open(f))
        texts = [("codelist", d.get("description", ""))]
        texts += [("term:" + t["termCode"], t.get("description", "")) for t in d.get("hasDefinedTerm", [])]
        for label, text in texts:
            if not text:
                continue
            g = fk_grade(text)
            if g > threshold:
                over += 1
                print(f"{f} [{label}]: grade {g:.1f}")
    print(f"\n{over} description(s) above grade {threshold}.")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
