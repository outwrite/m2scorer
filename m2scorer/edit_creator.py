#!/usr/bin/env python

from __future__ import print_function
import sys
from getopt import getopt
from m2scorer.levenshtein import (
    equals_ignore_whitespace_casing,
    levenshtein_matrix,
    edit_graph,
    merge_graph,
    transitive_arcs,
    set_weights,
    best_edit_seq_bf,
)


def print_usage():
    print("Usage: m2scorer.py [OPTIONS] source target", file=sys.stderr)
    print("where", file=sys.stderr)
    print("  source          -   the source input", file=sys.stderr)
    print(
        "  target          -   the target side of a parallel corpus or a system output",
        file=sys.stderr,
    )

    print("OPTIONS", file=sys.stderr)
    print(
        "  -v    --verbose                   	-  print verbose output", file=sys.stderr
    )
    print(
        "        --very_verbose              	-  print lots of verbose output",
        file=sys.stderr,
    )
    print(
        "        --max_unchanged_words N     	-  Maximum unchanged words when extraction edit. Default 0.",
        file=sys.stderr,
    )
    print(
        "        --ignore_whitespace_casing  	-  Ignore edits that only affect whitespace and caseing. Default no.",
        file=sys.stderr,
    )
    print(
        "        --output  	                  -  The output file. Otherwise, it prints to standard output ",
        file=sys.stderr,
    )


def main(
    source,
    target,
    max_unchanged_words=0,
    ignore_whitespace_casing=False,
    verbose=False,
    very_verbose=False,
    output_name=None,
):
    write_output = sys.stdout
    if output_name is not None:
        write_output = open(output_name, "w")
    count = 0
    print("Process line by line: ", end=" ", file=sys.stderr)
    for candidate, source in zip(target, source):
        if not count % 1000:
            print(count, end=" ", file=sys.stderr)
        count += 1
        candidate = candidate.strip()
        source = source.strip()

        candidate_tok = candidate.split()
        source_tok = source.split()
        # lmatrix, backpointers = levenshtein_matrix(source_tok, candidate_tok)
        lmatrix1, backpointers1 = levenshtein_matrix(source_tok, candidate_tok, 1, 1, 1)
        lmatrix2, backpointers2 = levenshtein_matrix(source_tok, candidate_tok, 1, 1, 2)

        # V, E, dist, edits = edit_graph(lmatrix, backpointers)
        V1, E1, dist1, edits1 = edit_graph(lmatrix1, backpointers1)
        V2, E2, dist2, edits2 = edit_graph(lmatrix2, backpointers2)

        V, E, dist, edits = merge_graph(V1, V2, E1, E2, dist1, dist2, edits1, edits2)
        V, E, dist, edits = transitive_arcs(
            V, E, dist, edits, max_unchanged_words, very_verbose
        )

        # print the source sentence and target sentence
        # S = source, T = target
        print("S {0}".format(source), file=write_output)
        if verbose:
            print("T {0}".format(candidate), file=write_output)

        # Find the shortest path with an empty gold set
        gold = []
        localdist = set_weights(E, dist, edits, gold, verbose, very_verbose)
        editSeq = best_edit_seq_bf(V, E, localdist, edits, very_verbose)
        if ignore_whitespace_casing:
            editSeq = [
                x for x in editSeq if not equals_ignore_whitespace_casing(x[2], x[3])
            ]

        for ed in list(reversed(editSeq)):
            # Only print those "changed" edits
            if ed[2] != ed[3]:
                # Print the edits using format: A start end|||origin|||target|||anno_ID
                # At the moment, the annotation ID is always 0
                # print "A {0} {1}|||{2}|||{3}|||{4}".format(ed[0], ed[1], ed[2], ed[3], 0)
                print(
                    "A {0} {1}|||{2}|||{3}|||{4}|||{5}|||{6}".format(
                        ed[0], ed[1], "UNK", ed[3], "REQUIRED", "-NONE-", 0
                    ),
                    file=write_output,
                )
        print("", file=write_output)
    print("Done!", file=sys.stderr)
    if output_name:
        write_output.close()


if __name__ == "__main__":
    max_unchanged_words = 0
    ignore_whitespace_casing = False
    verbose = False
    very_verbose = False
    output = None
    opts, args = getopt(
        sys.argv[1:],
        "v",
        [
            "max_unchanged_words=",
            "verbose",
            "ignore_whitespace_casing",
            "very_verbose",
            "output=",
        ],
    )
    # print opts
    for o, v in opts:
        if o in ("-v", "--verbose"):
            verbose = True
        elif o == "--very_verbose":
            very_verbose = True
        elif o == "--max_unchanged_words":
            max_unchanged_words = int(v)
        elif o == "--ignore_whitespace_casing":
            ignore_whitespace_casing = True
        elif o == "--output":
            output = v
        else:
            print("Unknown option :", o, file=sys.stderr)
            print_usage()
            sys.exit(-1)

    # starting point
    if len(args) != 2:
        print_usage()
        sys.exit(-1)

    source_file = args[0]
    target_file = args[1]

    # read the input files
    system_read = open(target_file, "r")
    source_read = open(source_file, "r")

    main(
        source_read,
        system_read,
        max_unchanged_words,
        ignore_whitespace_casing,
        verbose,
        very_verbose,
        output,
    )
    system_read.close()
    source_read.close()
