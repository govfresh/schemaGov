# Invalid fixtures

These files are wrong on purpose. Each faulty node has one fault, such as an unknown code, a
missing required field, a dangling reference or a reference to the wrong kind of thing. Some
nodes are clean, to show that valid data is not rejected. The faults and the clean nodes are
listed in `tools/check-invalid.py`.

`python3 tools/check-invalid.py` (`npm run validate:invalid`) runs the validators over it and
fails unless every fault is rejected with its own expected message and no clean node is. Passing data proves
nothing if a validator accepts everything.

Nothing here is published, and the JSON-LD audit skips it.
