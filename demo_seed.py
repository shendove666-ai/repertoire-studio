"""Synthetic repertoire fields and practice scenarios for the disposable demo."""

# Piece fields match the existing INSERT order, excluding user_id.
DEMO_WORKS = (
    ("Sonata in C Major", "Wolfgang Amadeus Mozart", "K. 545", "C Major",
     "Sonata Form", "Scale articulation", 3, "Polishing", "Example: isolate the transition."),
    ("Arabesque No. 1", "Claude Debussy", "L. 66, No. 1", "E Major",
     "Ternary Form", "Two-against-three rhythm", 4, "In Progress", "Example: alternate hand entries."),
    ("Intermezzo in A Major", "Johannes Brahms", "Op. 118, No. 2", "A Major",
     "Ternary Form", "Inner-voice balance", 4, "In Progress", "Example: compare two voicing plans."),
    ("Sonata in G Major", "Ludwig van Beethoven", "Op. 49, No. 2", "G Major",
     "Sonata Form", "Phrase articulation", 3, "Performance Ready", "Example: mark phrase releases."),
    ("Venetian Boat Song", "Felix Mendelssohn", "Op. 30, No. 6", "F-sharp Minor",
     "Ternary Form", "Even accompaniment", 3, "In Progress", "Example: plan the first reading."),
)

# Piece index, days before launch, duration, target BPM, measure range, notes.
DEMO_SESSIONS = (
    (0, 6, 25, 72, "mm. 1-8", "Example: compare two articulations."),
    (1, 5, 35, 60, "mm. 6-13", "Example: count the shared subdivision."),
    (2, 4, 20, 54, "mm. 1-8", "Example: rehearse the inner line alone."),
    (0, 3, 30, 80, "mm. 13-21", "Example: connect adjacent phrases."),
    (3, 2, 15, 76, "mm. 1-8", "Example: check release timing."),
    (1, 1, 25, 64, "mm. 14-21", "Example: repeat hands together."),
    (0, 0, 20, 84, "mm. 1-12", "Example: record a comparison take."),
)
