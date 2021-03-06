#######################################################################
# Tests for autoprocessor.py module: make_fastqs
#######################################################################

import unittest
import tempfile
import shutil
import os
from bcftbx.mock import MockIlluminaRun
from auto_process_ngs.mock import MockBcl2fastq2Exe
from auto_process_ngs.auto_processor import AutoProcess

class TestAutoProcessMakeFastqs(unittest.TestCase):
    """
    Tests for AutoProcess.make_fastqs
    """
    def setUp(self):
        # Create a temp working dir
        self.wd = tempfile.mkdtemp(suffix='TestAutoProcessMakeFastqs')
        # Create a temp 'bin' dir
        self.bin = os.path.join(self.wd,"bin")
        os.mkdir(self.bin)
        # Store original location
        self.pwd = os.getcwd()
        # Store original PATH
        self.path = os.environ['PATH']
        # Move to working dir
        os.chdir(self.wd)
        # Placeholders for test objects
        self.ap = None

    def tearDown(self):
        # Delete autoprocessor object
        if self.ap is not None:
            del(self.ap)
        # Return to original dir
        os.chdir(self.pwd)
        # Restore PATH
        os.environ['PATH'] = self.path
        # Remove the temporary test directory
        ##shutil.rmtree(self.wd)

    def test_make_fastqs_standard_protocol(self):
        """make_fastqs: standard protocol
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_M00879_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"))
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_M00879_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        ap.make_fastqs(protocol="standard")
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_M00879_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_M00879_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info",
                      "processing_qc.html"):
            self.assertTrue(os.path.isfile(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)

    def test_make_fastqs_icell8_protocol(self):
        """make_fastqs: icell8 protocol
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_SN7001250_00002_AHGXXXX",
            "hiseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        # Check that bases mask is as expected
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"),
                                 assert_bases_mask="y25n76,I8,I8,y101")
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_SN7001250_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        ap.make_fastqs(protocol="icell8")
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_SN7001250_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_SN7001250_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs_icell8"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info",
                      "processing_qc.html"):
            self.assertTrue(os.path.isfile(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)

    def test_make_fastqs_missing_fastqs_no_placeholders(self):
        """make_fastqs: missing fastqs, no placeholders
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_M00879_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"),
                                 missing_fastqs=(
                                     "Sample1_S1_L001_R1_001.fastq.gz",
                                     "Sample1_S1_L001_R2_001.fastq.gz",))
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_M00879_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        self.assertRaises(Exception,
                          ap.make_fastqs,
                          protocol="standard",
                          create_empty_fastqs=False)
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_M00879_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_M00879_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info",
                      "processing_qc.html"):
            self.assertFalse(os.path.exists(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)
        self.assertTrue(
            os.path.exists(
                os.path.join(analysis_dir,
                             "logs",
                             "002_make_fastqs",
                             "missing_fastqs.log")))

    def test_make_fastqs_missing_fastqs_with_placeholders(self):
        """make_fastqs: missing fastqs with placeholders
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_M00879_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"),
                                 missing_fastqs=(
                                     "Sample1_S1_L001_R1_001.fastq.gz",
                                     "Sample1_S1_L001_R2_001.fastq.gz",))
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_M00879_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        ap.make_fastqs(protocol="standard",
                       create_empty_fastqs=True)
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_M00879_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_M00879_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info"):
            self.assertTrue(os.path.exists(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)
        self.assertTrue(
            os.path.exists(
                os.path.join(analysis_dir,
                             "logs",
                             "002_make_fastqs",
                             "missing_fastqs.log")))

    def test_make_fastqs_handle_bcl2fastq2_failure(self):
        """make_fastqs: handle bcl2fastq2 failure
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_M00879_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq which will fail (i.e.
        # return non-zero exit code)
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"),
                                 exit_code=1)
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_M00879_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        self.assertRaises(Exception,
                          ap.make_fastqs,
                          protocol="standard")
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_M00879_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_M00879_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info",
                      "processing_qc.html"):
            self.assertFalse(os.path.exists(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)

    def test_make_fastqs_unknown_platform(self):
        """make_fastqs: unknown platform raises exception
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_UNKNOWN_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"))
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_UNKNOWN_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        self.assertRaises(Exception,
                          ap.make_fastqs,
                          protocol="standard")

    def test_make_fastqs_explicitly_specify_platform(self):
        """make_fastqs: explicitly specify the platform
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_UNKNOWN_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"),
                                 platform="miseq")
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_UNKNOWN_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        ap.make_fastqs(protocol="standard",
                       platform="miseq")
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_UNKNOWN_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_UNKNOWN_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info",
                      "processing_qc.html"):
            self.assertTrue(os.path.isfile(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)

    def test_make_fastqs_specify_platform_via_metadata(self):
        """make_fastqs: implicitly specify the platform via metadata
        """
        # Create mock source data
        illumina_run = MockIlluminaRun(
            "171020_UNKNOWN_00002_AHGXXXX",
            "miseq",
            top_dir=self.wd)
        illumina_run.create()
        # Create mock bcl2fastq
        MockBcl2fastq2Exe.create(os.path.join(self.bin,
                                              "bcl2fastq"),
                                 platform="miseq")
        os.environ['PATH'] = "%s:%s" % (self.bin,
                                        os.environ['PATH'])
        # Do the test
        ap = AutoProcess()
        ap.setup(os.path.join(self.wd,
                              "171020_UNKNOWN_00002_AHGXXXX"))
        self.assertTrue(ap.params.sample_sheet is not None)
        self.assertTrue(ap.metadata.platform is None)
        ap.metadata["platform"] = "miseq"
        ap.make_fastqs(protocol="standard")
        # Check outputs
        analysis_dir = os.path.join(
            self.wd,
            "171020_UNKNOWN_00002_AHGXXXX_analysis")
        for subdir in (os.path.join("primary_data",
                                    "171020_UNKNOWN_00002_AHGXXXX"),
                       os.path.join("logs",
                                    "002_make_fastqs"),
                       "bcl2fastq"):
            self.assertTrue(os.path.isdir(
                os.path.join(analysis_dir,subdir)),
                            "Missing subdir: %s" % subdir)
        for filen in ("statistics.info",
                      "statistics_full.info",
                      "per_lane_statistics.info",
                      "per_lane_sample_stats.info",
                      "projects.info",
                      "processing_qc.html"):
            self.assertTrue(os.path.isfile(
                os.path.join(analysis_dir,filen)),
                            "Missing file: %s" % filen)
