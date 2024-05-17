#!/usr/bin/env python
from __future__ import print_function, division
import sys, os, argparse, glob
from collections import OrderedDict, defaultdict
from Bio.SeqIO.FastaIO import SimpleFastaParser

import pandas as pd

# Soothsayer Ecosystem
from genopype import *
from soothsayer_utils import *

# DATABASE_EUKARYOTIC="/usr/local/scratch/CORE/jespinoz/db/veba/v1.0/Classify/Eukaryotic/"

pd.options.display.max_colwidth = 100
# from tqdm import tqdm
__program__ = os.path.split(sys.argv[0])[-1]
__version__ = "2022.12.07b"


# GTDB-Tk
# Assembly
def get_preprocess_cmd( input_filepaths, output_filepaths, output_directory, directories, opts):
    if not os.path.exists(os.path.join(directories["checkpoints"], "0__preprocess")):

        # MAG -> Filepath
        mag_to_filepath = dict()
        filepaths = glob.glob(os.path.join(opts.eukaryotic_binning_directory, "*", "output", "genomes", "*.fa"))
        assert len(filepaths) > 0, "No files found with wildcard: {}".format(os.path.join(opts.eukaryotic_binning_directory, "*", "output", "genomes", "*.fa"))

        for fp in filepaths:
            id_mag = fp.split("/")[-1][:-3]
            assert id_mag not in mag_to_filepath, f"Dataset has non-unique MAG identifiers: {id_mag}"
            mag_to_filepath[id_mag] = fp
        mag_to_filepath = pd.Series(mag_to_filepath)
        mag_to_filepath.to_frame().to_csv(os.path.join(output_directory, "all_samples.genomes.tsv"), sep="\t", header=None)


        # Scaffolds -> MAG
        scaffold_to_bin = OrderedDict()

        for id_mag, fp in mag_to_filepath.items():
            with open(fp, "r") as f:
                for header, seq in pv(SimpleFastaParser(f), f"Getting scaffold identifiers from {id_mag}", unit=" scaffolds"):
                    id_scaffold = header.split(" ")[0]
                    scaffold_to_bin[id_scaffold] = id_mag 
        scaffold_to_bin = pd.Series(scaffold_to_bin)
        scaffold_to_bin.to_frame().to_csv(os.path.join(output_directory, "all_samples.scaffolds_to_bins.tsv"), sep="\t", header=None)

        # Identifier Mapping
        dataframes = list() 
        filepaths = glob.glob(os.path.join(opts.eukaryotic_binning_directory, "*", "output", "identifier_mapping.metaeuk.tsv"))
        assert len(filepaths) > 0, "No files found with wildcard: {}".format(os.path.join(opts.eukaryotic_binning_directory, "*", "output", "identifier_mapping.metaeuk.tsv"))
        
        for fp in filepaths:
            dataframes.append(pd.read_csv(fp, sep="\t", index_col=4))
        df_metaeuk = pd.concat(dataframes, axis=0)
        df_metaeuk = pd.DataFrame(df_metaeuk.to_dict(into=OrderedDict)) # HACK: Remove duplicates
        df_metaeuk.to_csv(os.path.join(output_directory, "all_samples.identifier_mapping.metaeuk.tsv"), sep="\t")

        # Concatenate proteins
        f_out = open(os.path.join(directories["tmp"], "proteins.faa"), "w")

        filepaths = glob.glob(os.path.join(opts.eukaryotic_binning_directory, "*", "output", "genomes", "*.faa"))
        assert len(filepaths) > 0, "No files found with wildcard: {}".format(os.path.join(opts.eukaryotic_binning_directory, "*", "output", "genomes", "*.fa"))
        
        for fp in filepaths:
            with open(fp, "r") as f_in:
                for line in f_in:
                    f_out.write(line)
        f_out.close()

    return []

def get_hmmsearch_cmd( input_filepaths, output_filepaths, output_directory, directories, opts):
    cmd = [ 
        os.environ["hmmsearch"],
        "--tblout {}".format(os.path.join(output_directory, "hmmsearch_tblout.tsv")),
        "--cpu {}".format(opts.n_jobs),
        "--seed {}".format(opts.random_state + 1),
        "--{}".format(opts.hmmsearch_threshold) if opts.hmmsearch_threshold != "e" else "-E {}".format(opts.hmmsearch_evalue),
        opts.hmms,
        os.path.join(directories["tmp"], "proteins.faa"),

        "&&",

        os.environ["filter_hmmsearch_results.py"],
        "-i {}".format(os.path.join(output_directory, "hmmsearch_tblout.tsv")),
        "-s {}".format(opts.scores_cutoff),
        "-f name",
        ">",
       os.path.join(output_directory, "hmmsearch_tblout.score_filtered.tsv"),

       "&&",

       "cat",
        os.path.join(output_directory, "hmmsearch_tblout.score_filtered.tsv"),
        "|",
        "tail -n +3",
        "|",
         "cut -f1",
         "|",
         "sort -u",
         "|",
        # os.path.join(output_directory, "hmmsearch_tblout.score_filtered.identifiers.list"),
        os.environ["subset_table.py"],
        "-t {}".format(os.path.join(directories["preprocessing"], "all_samples.identifier_mapping.metaeuk.tsv")),
        ">",
        os.path.join(directories["preprocessing"], "all_samples.identifier_mapping.metaeuk.score_filtered.tsv"),

    ]


    return cmd

def get_compile_cmd( input_filepaths, output_filepaths, output_directory, directories, opts):
    cmd = [ 
        os.environ["compile_eukaryotic_classifications.py"],
        "-i {}".format(input_filepaths[0]),
        "-s {}".format(input_filepaths[1]),
        "--eukaryotic_database {}".format(opts.eukaryotic_database),
        "-o {}".format(output_filepaths[0]),
        "--debug",
    ]
    # if opts.clusters:
    #     cmd += ["-c {}".format(opts.clusters)]

    return cmd



def get_consensus_genome_classification_cmd( input_filepaths, output_filepaths, output_directory, directories, opts):

    # Command
    cmd = [ 

        "cat",
        input_filepaths[0],
        "|",
        "cut -f1,3,6,7",
        "|",
        "tail -n +2",
        "|",
        os.environ["consensus_genome_classification.py"],
        "--leniency {}".format(opts.leniency),
        "-o {}".format(output_filepaths[0]),
        "-r c__,o__,f__,g__,s__",
        # "--simple",
    ]
    return cmd

def get_consensus_cluster_classification_cmd( input_filepaths, output_filepaths, output_directory, directories, opts):

    # Command
    cmd = [ 

        # cat gtdbtk.summary.tsv | cut -f1,3,18 | tail -n +2 |
        "cat",
        input_filepaths[0],
        "|",
        "cut -f1-3",
        "|",
        "tail -n +2",
        "|",
        os.environ["insert_column_to_table.py"],
        "-c {}".format(opts.clusters),
        "-n id_slc",
        "-i 0",
        "|",
        os.environ["consensus_genome_classification.py"],
        "--leniency {}".format(opts.leniency),
        "-o {}".format(output_filepaths[0]),
        "-r c__,o__,f__,g__,s__",


    ]
    return cmd





# Symlink
# def get_symlink_cmd(input_filepaths, output_filepaths, output_directory, directories, opts):
    
#     # Command
#     cmd = ["("]
#     for filepath in input_filepaths:
#         # cmd.append("ln -f -s {} {}".format(os.path.realpath(filepath), os.path.realpath(output_directory)))
#         cmd.append("ln -f -s {} {}".format(os.path.realpath(filepath), output_directory))
#         cmd.append("&&")
#     cmd[-1] = ")"
#     return cmd

# ============
# Run Pipeline
# ============
# Set environment variables
def add_executables_to_environment(opts):
    """
    Adapted from Soothsayer: https://github.com/jolespin/soothsayer
    """
    required_executables = {
        "hmmsearch",
    }
    accessory_scripts = set([ 
        "filter_hmmsearch_results.py",
        "subset_table.py",
        "compile_eukaryotic_classifications.py",
        "consensus_genome_classification.py",
        "insert_column_to_table.py",
        # "consensus_orthogroup_annotation.py",
    ])

    
    required_executables = required_executables | accessory_scripts

    if opts.path_config == "CONDA_PREFIX":
        executables = dict()
        for name in required_executables:
            executables[name] = os.path.join(os.environ["CONDA_PREFIX"], "bin", name)
    else:
        if opts.path_config is None:
            opts.path_config = os.path.join(opts.script_directory, "veba_config.tsv")
        opts.path_config = format_path(opts.path_config)
        assert os.path.exists(opts.path_config), "config file does not exist.  Have you created one in the following directory?\n{}\nIf not, either create one, check this filepath:{}, or give the path to a proper config file using --path_config".format(opts.script_directory, opts.path_config)
        assert os.stat(opts.path_config).st_size > 1, "config file seems to be empty.  Please add 'name' and 'executable' columns for the following program names: {}".format(required_executables)
        df_config = pd.read_csv(opts.path_config, sep="\t")
        assert {"name", "executable"} <= set(df_config.columns), "config must have `name` and `executable` columns.  Please adjust file: {}".format(opts.path_config)
        df_config = df_config.loc[:,["name", "executable"]].dropna(how="any", axis=0).applymap(str)
        # Get executable paths
        executables = OrderedDict(zip(df_config["name"], df_config["executable"]))
        assert required_executables <= set(list(executables.keys())), "config must have the required executables for this run.  Please adjust file: {}\nIn particular, add info for the following: {}".format(opts.path_config, required_executables - set(list(executables.keys())))

    # Display
    for name in sorted(accessory_scripts):
        executables[name] = "python " + os.path.join(opts.script_directory, "scripts", name)
    print(format_header( "Adding executables to path from the following source: {}".format(opts.path_config), "-"), file=sys.stdout)
    for name, executable in executables.items():
        if name in required_executables:
            print(name, executable, sep = " --> ", file=sys.stdout)
            os.environ[name] = executable.strip()
    print("", file=sys.stdout)

# Pipeline
def create_pipeline(opts, directories, f_cmds):

    # .................................................................
    # Primordial
    # .................................................................
    # Commands file
    pipeline = ExecutablePipeline(name=__program__,  f_cmds=f_cmds, checkpoint_directory=directories["checkpoints"], log_directory=directories["log"])

    # ==========
    # Preprocess
    # ==========
    # if not opts.scaffolds_to_bins:
    step = 0

    program = "preprocess"
    program_label = "{}__{}".format(step, program)
    # Add to directories
    output_directory = directories["preprocessing"]

    # Info
    description = "Getting scaffolds to bins for genomes"


    # i/o
    input_filepaths = [
        opts.eukaryotic_binning_directory,
        ]
    output_filenames = ["all_samples.scaffolds_to_bins.tsv", "all_samples.identifier_mapping.metaeuk.tsv"]
    output_filepaths = list(map(lambda filename: os.path.join(directories["preprocessing"], filename), output_filenames))

    params = {
        "input_filepaths":input_filepaths,
        "output_filepaths":output_filepaths,
        "output_directory":output_directory,
        "opts":opts,
        "directories":directories,
    }

    cmd = get_preprocess_cmd(**params)

    pipeline.add_step(
                id=program,
                description = description,
                step=step,
                cmd=cmd,
                input_filepaths = input_filepaths,
                output_filepaths = output_filepaths,
                validate_inputs=True,
                validate_outputs=True,
    )
    # opts.scaffolds_to_bins = os.path.join(directories["preprocessing"], "scaffolds_to_bins.tsv")

   # ==========
    # Get classifications
    # ==========
    if not opts.include_all_genes:
        step += 1

        program = "hmmsearch"
        program_label = "{}__{}".format(step, program)
        # Add to directories
        output_directory = directories["intermediate"]

        # Info
        description = "Identify eukaryotic core markers"


        # i/o
        input_filepaths = [
            opts.eukaryotic_binning_directory,
            os.path.join(directories["preprocessing"], "all_samples.identifier_mapping.metaeuk.tsv"),
            os.path.join(directories["preprocessing"], "all_samples.scaffolds_to_bins.tsv"),
            opts.hmms,
            opts.scores_cutoff,
            ]
        # if opts.clusters:
        #     input_filepaths += [opts.clusters]
        output_filepaths = [os.path.join(directories["preprocessing"], "all_samples.identifier_mapping.metaeuk.score_filtered.tsv")]


        params = {
            "input_filepaths":input_filepaths,
            "output_filepaths":output_filepaths,
            "output_directory":output_directory,
            "opts":opts,
            "directories":directories,
        }

        cmd = get_hmmsearch_cmd(**params)

        pipeline.add_step(
                    id=program,
                    description = description,
                    step=step,
                    cmd=cmd,
                    input_filepaths = input_filepaths,
                    output_filepaths = output_filepaths,
                    validate_inputs=True,
                    validate_outputs=True,
        )
  
    # ==========
    # Get classifications
    # ==========
    step += 1

    program = "compile"
    program_label = "{}__{}".format(step, program)
    # Add to directories
    output_directory = directories["output"] 

    # Info
    description = "Compile eukaryotic classifications"


    # i/o
    if opts.include_all_genes:
        input_filepaths = [ os.path.join(directories["preprocessing"], "all_samples.identifier_mapping.metaeuk.tsv")]
    else:
        input_filepaths = [ os.path.join(directories["preprocessing"], "all_samples.identifier_mapping.metaeuk.score_filtered.tsv")]

    input_filepaths += [
        os.path.join(directories["preprocessing"], "all_samples.scaffolds_to_bins.tsv"),
        opts.eukaryotic_database,
        ]
    # if opts.clusters:
    #     input_filepaths += [opts.clusters]
    output_filenames = ["gene-source_lineage.tsv"]
    output_filepaths = list(map(lambda filename: os.path.join(directories["output"], filename), output_filenames))

    params = {
        "input_filepaths":input_filepaths,
        "output_filepaths":output_filepaths,
        "output_directory":output_directory,
        "opts":opts,
        "directories":directories,
    }

    cmd = get_compile_cmd(**params)

    pipeline.add_step(
                id=program,
                description = description,
                step=step,
                cmd=cmd,
                input_filepaths = input_filepaths,
                output_filepaths = output_filepaths,
                validate_inputs=True,
                validate_outputs=True,
    )

    # ==========
    # consensus genome classification
    # ==========
    step += 1

    program = "consensus_genome_classification"
    program_label = "{}__{}".format(step, program)
    # Add to directories
    output_directory = directories["output"]# = create_directory(os.path.join(directories["intermediate"], program_label))

    # Info
    description = "Consensus genome classification"


    # i/o
    input_filepaths = output_filepaths
    
    output_filenames = ["eukaryotic_taxonomy.tsv"]
    output_filepaths = list(map(lambda filename: os.path.join(output_directory, filename), output_filenames))

    params = {
        "input_filepaths":input_filepaths,
        "output_filepaths":output_filepaths,
        "output_directory":output_directory,
        "opts":opts,
        "directories":directories,
    }

    cmd = get_consensus_genome_classification_cmd(**params)

    pipeline.add_step(
                id=program,
                description = description,
                step=step,
                cmd=cmd,
                input_filepaths = input_filepaths,
                output_filepaths = output_filepaths,
                validate_inputs=True,
                validate_outputs=True,
    )

    if opts.clusters:
        # ==========
        # consensus cluster classification
        # ==========
        step += 1

        program = "consensus_cluster_classification"
        program_label = "{}__{}".format(step, program)
        # Add to directories
        output_directory = directories["output"]# = create_directory(os.path.join(directories["intermediate"], program_label))

        # Info
        description = "Consensus genome classification"


        # i/o
        input_filepaths = output_filepaths
        
        output_filenames = ["eukaryotic_taxonomy.clusters.tsv"]
        output_filepaths = list(map(lambda filename: os.path.join(output_directory, filename), output_filenames))

        params = {
            "input_filepaths":input_filepaths,
            "output_filepaths":output_filepaths,
            "output_directory":output_directory,
            "opts":opts,
            "directories":directories,
        }

        cmd = get_consensus_cluster_classification_cmd(**params)

        pipeline.add_step(
                    id=program,
                    description = description,
                    step=step,
                    cmd=cmd,
                    input_filepaths = input_filepaths,
                    output_filepaths = output_filepaths,
                    validate_inputs=True,
                    validate_outputs=True,
        )


    return pipeline

# Configure parameters
def configure_parameters(opts, directories):
    if not opts.include_all_genes:
        assert opts.hmms is not None, "If not --include_all_genes then you must provide --hmms"
        assert opts.scores_cutoff is not None, "If not --include_all_genes then you must provide --scores_cutoff"

    # Set environment variables
    add_executables_to_environment(opts=opts)

def main(args=None):
    # Path info
    script_directory  =  os.path.dirname(os.path.abspath( __file__ ))
    script_filename = __program__
    # Path info
    description = """
    Running: {} v{} via Python v{} | {}""".format(__program__, __version__, sys.version.split(" ")[0], sys.executable)
    usage = "{} -i <eukaryotic_binning_directory> -o <output_directory>".format(__program__)
    epilog = "Copyright 2021 Josh L. Espinoza (jespinoz@jcvi.org)"

    # Parser
    parser = argparse.ArgumentParser(description=description, usage=usage, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
    # Pipeline
    parser_io = parser.add_argument_group('Required I/O arguments')
    parser_io.add_argument("-i","--eukaryotic_binning_directory", type=str, required=True, help = "path/to/eukaryotic_binng_directory")
    # parser_io.add_argument("-m","--mags", type=str, required=True, help = "Tab-seperated value table of [id_mag]<tab>[path/to/genome.fasta]")
    # parser_io.add_argument("-i","--metaeuk_identifier_mapping", type=str, required=True, help = "path/to/identifier_mapping.metaeuk.tsv")
    # parser_io.add_argument("-s","--scaffolds_to_bins", type=str, required=False, help = "path/to/scaffolds_to_bins.tsv")
    parser_io.add_argument("-c","--clusters", type=str, help = "path/to/clusters.tsv, Format: [id_mag]<tab>[id_cluster], No header.")
    parser_io.add_argument("-o","--output_directory", type=str, default="veba_output/classify/eukaryotic", help = "path/to/output_directory [Default: veba_output/classify/eukaryotic]")

    # Utility
    parser_utility = parser.add_argument_group('Utility arguments')
    parser_utility.add_argument("--path_config", type=str,  default="CONDA_PREFIX", help="path/to/config.tsv [Default: CONDA_PREFIX]")  #site-packges in future
    parser_utility.add_argument("-p", "--n_jobs", type=int, default=1, help = "Number of threads [Default: 1]")
    parser_utility.add_argument("--random_state", type=int, default=0, help = "Random state [Default: 0]")
    parser_utility.add_argument("--restart_from_checkpoint", type=str, default=None, help = "Restart from a particular checkpoint [Default: None]")
    parser_utility.add_argument("-v", "--version", action='version', version="{} v{}".format(__program__, __version__))

    # HMMER
    parser_hmmer = parser.add_argument_group('HMMSearch arguments')
    parser_hmmer.add_argument("--hmmsearch_threshold", type=str, default="e", help="HMMSearch | Threshold {cut_ga, cut_nc, gut_tc, e} [Default:  e]")
    parser_hmmer.add_argument("--hmmsearch_evalue", type=float, default=10.0, help="HMMSearch | E-Value [Default: 10.0]")
    parser_hmmer.add_argument("--hmmsearch_options", type=str, default="", help="HMMSearch | More options (e.g. --arg 1 ) [Default: '']")

    # Databases
    parser_databases = parser.add_argument_group('Database arguments')
    parser_databases.add_argument("--veba_database", type=str,  help=f"VEBA database location.  [Default: $VEBA_DATABASE environment variable]")
    # parser_databases.add_argument("--eukaryotic_database", type=str, default=DATABASE_EUKARYOTIC, help="Database | path/to/eukaryotic_database (e.g. --arg 1 ) [Default: {}]".format(DATABASE_EUKARYOTIC))
    # parser_databases.add_argument("--hmms", type=str, default=os.path.join(DATABASE_EUKARYOTIC, "hmms", "eukaryota_odb10.hmm"), help="Core HMMs for HMMER's hmmsearch [Default: {}]".format(os.path.join(DATABASE_EUKARYOTIC, "hmms", "eukaryota_odb10.hmm"))) # 
    # parser_databases.add_argument("--scores_cutoff", default=os.path.join(DATABASE_EUKARYOTIC, "hmms", "eukaryota_odb10.scores_cutoff.tsv.gz"), help="Tab-separated value file with [id_query]<tab>[score] [Default: {}]".format(os.path.join(DATABASE_EUKARYOTIC, "hmms", "eukaryota_odb10.scores_cutoff.tsv.gz")))
    parser_databases.add_argument("--include_all_genes",  action="store_true", help="Use if you want to include all genes for taxonomy classification instead of only core markers from BUSCO's eukaryota_odb10")

    # Consensus genome classification
    parser_consensus= parser.add_argument_group('Consensus genome arguments')
    parser_consensus.add_argument("-l","--leniency", default=1.382, type=float, help = "Leniency parameter. Lower value means more conservative weighting. A value of 1 indiciates no weight bias. A value greater than 1 puts higher weight on higher level taxonomic assignments. A value less than 1 puts lower weights on higher level taxonomic assignments.  [Default: 1.382]")
    parser_consensus.add_argument("--similarity_threshold", type=float, default=0.8, help = "Threshold for similarity analysis [Default: 0.8]")
    parser_consensus.add_argument("--retain_unannotated", type=int, default=1, help = "Consider unannotations (i.e., blank functions) in the scording system [Default: 1]")
    parser_consensus.add_argument("--unannotated_weight", type=float, default=0.382, help = "Weight for unannotations (i.e., blank functions) in the scording system? [Default: 0.382]")
    parser_consensus.add_argument("--representative_threshold", type=float, default=0.618, help = "Score to consider as representative [Default: 0.618]")

    # Options
    opts = parser.parse_args()
    opts.script_directory  = script_directory
    opts.script_filename = script_filename

    # Database
    if opts.veba_database is None:
        assert "VEBA_DATABASE" in os.environ, "Please set the following environment variable 'export VEBA_DATABASE=/path/to/veba_database' or provide path to --veba_database"
        opts.veba_database = os.environ["VEBA_DATABASE"]
    opts.eukaryotic_database = os.path.join(opts.veba_database, "Classify", "Microeukaryotic")
    opts.hmms = os.path.join(opts.veba_database, "MarkerSets", "eukaryota_odb10.hmm")
    opts.scores_cutoff = os.path.join(opts.veba_database, "MarkerSets", "eukaryota_odb10.scores_cutoff.tsv.gz")

    # Directories
    directories = dict()
    directories["project"] = create_directory(opts.output_directory)
    directories["preprocessing"] = create_directory(os.path.join(directories["project"], "preprocessing"))
    directories["output"] = create_directory(os.path.join(directories["project"], "output"))
    directories["log"] = create_directory(os.path.join(directories["project"], "log"))
    directories["tmp"] = create_directory(os.path.join(directories["project"], "tmp"))
    directories["checkpoints"] = create_directory(os.path.join(directories["project"], "checkpoints"))
    directories["intermediate"] = create_directory(os.path.join(directories["project"], "intermediate"))
    os.environ["TMPDIR"] = directories["tmp"]

    # Info
    print(format_header(__program__, "="), file=sys.stdout)
    print(format_header("Configuration:", "-"), file=sys.stdout)
    print("Python version:", sys.version.replace("\n"," "), file=sys.stdout)
    print("Python path:", sys.executable, file=sys.stdout) #sys.path[2]
    print("Script version:", __version__, file=sys.stdout)
    print("VEBA Database:", opts.veba_database, file=sys.stdout)
    print("Moment:", get_timestamp(), file=sys.stdout)
    print("Directory:", os.getcwd(), file=sys.stdout)
    print("Commands:", list(filter(bool,sys.argv)),  sep="\n", file=sys.stdout)
    configure_parameters(opts, directories)
    sys.stdout.flush()

    # Run pipeline
    with open(os.path.join(directories["project"], "commands.sh"), "w") as f_cmds:
        pipeline = create_pipeline(
                     opts=opts,
                     directories=directories,
                     f_cmds=f_cmds,
        )
        pipeline.compile()
        pipeline.execute(restart_from_checkpoint=opts.restart_from_checkpoint)

if __name__ == "__main__":
    main()
