#!/usr/bin/env python
from __future__ import print_function, division
import sys, os, argparse, glob
from collections import defaultdict
import numpy as np
import pandas as pd
from tqdm import tqdm 

pd.options.display.max_colwidth = 100
# from tqdm import tqdm
__program__ = os.path.split(sys.argv[0])[-1]
__version__ = "2023.10.3"


def main(args=None):
    # Path info
    script_directory  =  os.path.dirname(os.path.abspath( __file__ ))
    script_filename = __program__
    # Path info
    description = """
    Running: {} v{} via Python v{} | {}""".format(__program__, __version__, sys.version.split(" ")[0], sys.executable)
    usage = "{} -i <global_clustering_directory> -o <output_table>".format(__program__)
    epilog = "Copyright 2021 Josh L. Espinoza (jespinoz@jcvi.org)"

    # Parser
    parser = argparse.ArgumentParser(description=description, usage=usage, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
    # Pipeline

    parser.add_argument("-i","--global_clustering_directory",  type=str, default="veba_output/cluster/output/global", help = "path/to/global_clustering_directory [Default: veba_output/cluster/output/global/]")
    parser.add_argument("-o","--output", type=str, default="stdout", help = "path/to/core_pangenomes_table.tsv [Default: stdout]")
    # parser.add_argument("-t","--organism_type", type=str, default="infer", help = "organism type [Default: infer]")
    # parser.add_argument("--genome_fasta_extension", default="fa", type=str, help = "File extension. Don't include period/fullstop/. [Default: fa]")
    # parser.add_argument("--protein_fasta_extension", default="faa", type=str, help = "File extension. Include the period/fullstop/. [Default: faa]")
    parser.add_argument("-a", "--absolute", action="store_true", help = "Use absolute paths instead of relative paths")
    parser.add_argument("-e", "--allow_missing_files", action="store_true", help = "Allow missing files")
    parser.add_argument("--volume_prefix", type=str, help = "Docker container prefix to volume path")
    parser.add_argument("--header", action="store_true", help = "Write header")

    # Options
    opts = parser.parse_args()
    opts.script_directory  = script_directory
    opts.script_filename = script_filename

    output = defaultdict(dict)
    # Build table from binning directory
    for fp in tqdm(glob.glob(os.path.join(opts.global_clustering_directory, "pangenome_core_sequences", "*")), "Reading files in {}".format(opts.global_clustering_directory)):

        id_genome_cluster = ".".join(fp.split("/")[-1].split(".")[:-1])

        if fp.endswith(".faa"):
            output[id_genome_cluster]["proteins"] = fp
        if fp.endswith(".ffn"):
            output[id_genome_cluster]["cds"] = fp


    df_output = pd.DataFrame(output).reindex([ "proteins", "cds"]).T.sort_index()
    assert not df_output.empty, "Did not find any matches in the following directory: {}".format(opts.global_clustering_directory)
    df_output.index.name = "id_genome_cluster"

    # Check missing values
    if not opts.allow_missing_files:
        assert not np.any(df_output.isnull()), "Missing files detected.  Check error or allow with --allow_missing_files: \n{}".format(df_output.loc[df_output.isnull().sum(axis=1) > 0].to_string())
    
    # Absolute paths
    if opts.absolute:
        df_output = df_output.applymap(lambda fp: os.path.abspath(fp))

    # Docker volume prefix
    if opts.volume_prefix:
        df_output = df_output.applymap(lambda fp: os.path.join(opts.volume_prefix, fp) if pd.notnull(fp) else fp)

    if opts.output == "stdout":
        opts.output = sys.stdout 

    df_output.to_csv(opts.output, sep="\t", header=bool(opts.header))

if __name__ == "__main__":
    main()
