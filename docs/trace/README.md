# TRACE log

The TRACE log is the development and testing record of the generator, kept in TRACE form so the model's documentation can show how it was built and checked (structure §8). One entry, `phase-N.md`, is written when each phase closes, before its version tag is cut. It records what the phase built, how it was tested (which checks ran on which golden worlds, and their results), and every place where the build departed from the design, with the reason. Entries are written at phase close, not per commit or per work order.
