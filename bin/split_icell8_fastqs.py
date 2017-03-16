#!/usr/bin/env python
#
#     split_icell8_fastqs.py: splits fastq from Wafergen iCell8
#     Copyright (C) University of Manchester 2017 Peter Briggs
#
"""
split_icell8_fastqs.py

Utility to split FASTQ pair from Wafergen iCell8 into individual
FASTQ files based on the inline barcodes in read 1.

"""

######################################################################
# Imports
######################################################################

import os
import sys
import logging
import argparse
import time
from bcftbx.utils import mkdir
from auto_process_ngs.icell8_utils import ICell8WellList
from auto_process_ngs.icell8_utils import ICell8FastqIterator
from auto_process_ngs.fastq_utils import pair_fastqs
from auto_process_ngs.utils import OutputFiles

######################################################################
# Magic numbers
######################################################################

MAX_OPEN_FILES = 100
INLINE_BARCODE_QUALITY_CUTOFF = 10
UMI_QUALITY_CUTOFF = 30
DEFAULT_BATCH_SIZE = 5000000
READ_BUFFER_SIZE = 1000
BUFSIZE = 8192

######################################################################
# Classes
######################################################################

class BufferedOutputFiles(OutputFiles):
    def __init__(self,base_dir=None,bufsize=BUFSIZE):
        """Create a new OutputFiles instance

        Arguments:
          base_dir (str): optional 'base' directory
            which files will be created relative to

        """
        OutputFiles.__init__(self,base_dir=base_dir)
        self._bufsize = bufsize
        self._buffer = dict()
        self._mode = dict()

    def open(self,name,filen=None,append=False):
        """Open a new output file

        'name' is the handle used to reference the
        file when using the 'write' and 'close' methods.

        'filen' is the name of the file, and is unrelated
        to the handle. If not supplied then 'name' must
        be associated with a previously closed file (which
        will be reopened).

        If 'append' is True then append to an existing
        file rather than overwriting (i.e. use mode 'a'
        instead of 'w').

        """
        if append:
            mode = 'a'
        else:
            mode = 'w'
        if filen is None:
            filen = self.file_name(name)
        elif self._base_dir is not None:
            filen = os.path.join(self._base_dir,filen)
        else:
            filen = os.path.abspath(filen)
        self._file[name] = filen
        self._mode[name] = mode
        if not name in self._buffer:
            self._buffer[name] = ""

    def fp(self,name):
        try:
            return self._fp[name]
        except KeyError:
            # Close a file we have too many open at once
            # (to avoid IOError [Errno 24])
            if len(self._fp) == MAX_OPEN_FILES:
                self.close(self._fp.keys()[0])
            fp = open(self._file[name],self._mode[name])
            self._fp[name] = fp
            return fp

    def write(self,name,s):
        """Write content to file (newline-terminated)

        Writes 's' as a newline-terminated string to the
        file that is referenced with the handle 'name'.

        """
        self._buffer[name] += "%s\n" % s
        if len(self._buffer[name]) >= self._bufsize:
            self.dump_buffer(name)

    def dump_buffer(self,name):
        self.fp(name).write(self._buffer[name])
        self._buffer[name] = ""

    def close(self,name=None):
        """Close one or all open files

        If a 'name' is specified then only the file matching
        that handle will be closed; with no arguments all
        open files will be closed.

        """
        if name is not None:
            if self._buffer[name]:
                self.dump_buffer(name)
            try:
                self._fp[name].close()
                del(self._fp[name])
            except KeyError:
                pass
        else:
            names = self._file.keys()
            for name in names:
                self.close(name)

######################################################################
# Functions
######################################################################

def pass_quality_filter(seq,cutoff):
    for c in seq:
        if c < cutoff:
            return False
    return True

def main():
    # Handle the command line
    p = argparse.ArgumentParser()
    p.add_argument("FQ_R1",help="R1 FASTQ file")
    p.add_argument("FQ_R2",help="Matching R2 FASTQ file")
    p.add_argument("FQ",nargs='*',help="Additional FASTQ file pairs")
    p.add_argument("-w","--well-list",
                   dest="well_list_file",default=None,
                   help="iCell8 'well list' file")
    p.add_argument("-m","--mode",
                   dest="splitting_mode",default="barcodes",
                   choices=["barcodes","batch","none"],
                   help="how to split the input FASTQs: 'barcodes' "
                   "(one FASTQ pair per barcode), 'batch' (one or "
                   "more FASTQ pairs with fixed number of reads not "
                   "exceeding BATCH_SIZE), or 'none' (output all "
                   "reads to a single FASTQ pair) (default: "
                   "'barcodes')")
    p.add_argument("-s","--size",type=int,
                   dest="batch_size",default=DEFAULT_BATCH_SIZE,
                   help="number of reads per batch in 'batch' mode "
                   "(default: %d)" % DEFAULT_BATCH_SIZE)
    p.add_argument("-b","--basename",
                   default="icell8",
                   help="basename for output FASTQ files (default: "
                   "'icell8')")
    p.add_argument("-o","--outdir",
                   dest="out_dir",default=None,
                   help="directory to write output FASTQ files to "
                   "(default: current directory)")
    p.add_argument("-n","--no-filter",
                   dest='no_filter',action='store_true',
                   help="don't filter reads by barcode and UMI "
                   "quality (default: do filter reads)")
    args = p.parse_args()

    # Convert quality cutoffs to character encoding
    barcode_quality_cutoff = chr(INLINE_BARCODE_QUALITY_CUTOFF + 33)
    umi_quality_cutoff = chr(UMI_QUALITY_CUTOFF + 33)

    # Get well list and expected barcodes
    well_list_file = args.well_list_file
    if well_list_file is not None:
        well_list_file = os.path.abspath(args.well_list_file)
    well_list = ICell8WellList(well_list_file)
    expected_barcodes = set(well_list.barcodes())
    print "%d expected barcodes" % len(expected_barcodes)

    # Filtering mode
    do_filter = not args.no_filter

    # Splitting mode
    splitting_mode = args.splitting_mode
    batch_size = args.batch_size

    # Count barcodes and rejections
    assigned = 0
    unassigned = 0
    filtered = 0
    barcode_list = set()
    filtered_counts = {}

    # Input Fastqs
    fastqs = [args.FQ_R1,args.FQ_R2]
    for fq in args.FQ:
        fastqs.append(fq)
    fastqs = pair_fastqs(fastqs)[0]

    # Output Fastqs
    output_fqs = BufferedOutputFiles(base_dir=args.out_dir)
    if args.out_dir is not None:
        out_dir = os.path.abspath(args.out_dir)
        mkdir(out_dir)
    else:
        out_dir = os.getcwd()
    basename = args.basename

    # Iterate over pairs of Fastqs
    for fastq_pair in fastqs:
        # Iterate over read pairs from the Fastqs
        print "-- %s\n   %s" % fastq_pair
        print "   Starting at %s" % time.ctime()
        start_time = time.time()
        for i,read_pair in enumerate(ICell8FastqIterator(*fastq_pair),start=1):
            # Deal with read pair
            if (i % 100000) == 0:
                print "   Examining read pair #%d (%s)" % \
                    (i,time.ctime())
            inline_barcode = read_pair.barcode
            barcode_list.add(inline_barcode)
            if do_filter:
                # Do filtering
                if inline_barcode not in expected_barcodes:
                    assign_to = "unassigned"
                    unassigned += 1
                else:
                    assigned += 1
                    if not pass_quality_filter(read_pair.barcode_quality,
                                               barcode_quality_cutoff):
                        assign_to = "failed_barcode"
                    elif not pass_quality_filter(read_pair.umi_quality,
                                                 umi_quality_cutoff):
                        assign_to = "failed_umi"
                    else:
                        assign_to = inline_barcode
                        filtered += 1
                logging.debug("%s" % '\t'.join([assign_to,
                                                inline_barcode,
                                                read_pair.umi,
                                                read_pair.min_barcode_quality,
                                                read_pair.min_umi_quality]))
            else:
                # No filtering
                assign_to = inline_barcode
                filtered += 1
            # Post filtering counts
            if assign_to == inline_barcode:
                try:
                    filtered_counts[inline_barcode] += 1
                except KeyError:
                    filtered_counts[inline_barcode] = 1
                # Reassign read pair to appropriate output files
                if splitting_mode == "batch":
                    # Output to a batch-specific file pair
                    batch_number = filtered/batch_size
                    assign_to = "B%03d" % batch_number
                elif splitting_mode == "none":
                    # Output to a single file pair
                    assign_to = "filtered"
            # Write read pair
            fq_r1 = "%s_R1" % assign_to
            fq_r2 = "%s_R2" % assign_to
            #if output_mode == OUTPUTFILES:
            if fq_r1 not in output_fqs:
                try:
                    # Try to reopen file and append
                    output_fqs.open(fq_r1,append=True)
                except KeyError:
                    # Open new file
                    output_fqs.open(fq_r1,
                                    "%s.%s.r1.fastq" %
                                    (basename,assign_to))
            output_fqs.write(fq_r1,"%s" % read_pair.r1)
            if fq_r2 not in output_fqs:
                try:
                    # Try to reopen file and append
                    output_fqs.open(fq_r2,append=True)
                except KeyError:
                    # Open new file
                    output_fqs.open(fq_r2,
                                    "%s.%s.r2.fastq" %
                                    (basename,assign_to))
            output_fqs.write(fq_r2,"%s" % read_pair.r2)
            # DEBUGGING: break here
            if (i % 10000000) == 0:
                print "*** BREAKING (debugging) ***"
                break
        print "   Finished at %s" % time.ctime()
        print "   (Took %.0fs)" % (time.time()-start_time)
    # Close output files
    output_fqs.close()

    # Summary output to screen
    total_reads = assigned + unassigned
    print "Summary:"
    print "--------"
    print "Number of barcodes         : %d" % len(barcode_list)
    print "Number of expected barcodes: %d/%d" % \
        (len(filtered_counts.keys()),
         len(expected_barcodes))
    print "Total reads                : %d" % total_reads
    print "Total reads (assigned)     : %d" % assigned
    print "Total reads (filtered)     : %d" % filtered
    print "Unassigned reads           : %d" % unassigned

######################################################################
# Main
######################################################################

if __name__ == "__main__":
    main()
