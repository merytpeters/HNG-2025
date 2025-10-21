"""Functions That Analyze Strings"""

import re
import hashlib


def palindrome(string: str):
    """Palindrome, word that is the same when reversed"""
    is_palindrome = False
    new_word = "".join(reversed(string))
    if new_word == string:
        is_palindrome = True
    return is_palindrome


def unique_char(string: str):
    """Unique characters in string"""
    num_of_uniq_char = len(set(string))
    return num_of_uniq_char


def word_count(sentence: str):
    """Return the number of words in the given sentence (split by whitespace)."""
    if not sentence:
        return 0
    words = re.split(r"[^A-Za-z0-9]+", sentence)
    words = [word for word in words if word]
    return len(words)


def sha256_hash(string: str):
    """Hash of string identification"""
    return hashlib.sha256(string.encode("utf-8")).hexdigest()


def character_frequency_map(string: str):
    """Mapping each character to its occurrence count"""
    word_map = {}
    for char in string:
        if char in word_map:
            word_map[char] += 1
        else:
            word_map[char] = 1
    return word_map


"""if __name__ == '__main__':
    sample = "racecar"
    print(palindrome(sample))
    print(unique_char(sample))
    sample_word = "sha256_hash_value"
    other_sample = "string to analyze"
    print(word_count(sample_word))
    print(character_frequency_map(sample))
    print(sha256_hash(sample))
    print(sha256_hash(sample_word))
    print(word_count(other_sample))
    print(sha256_hash(other_sample))"""
