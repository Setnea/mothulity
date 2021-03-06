#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __author import __author__
from __version import __version__
from utilities import *
import time
import jinja2 as jj2
import argparse
import requests as rq
from tqdm import tqdm
import os
import sys
import glob
import ConfigParser
import shelve
import pandas as pd
from bs4 import BeautifulSoup as bs
import utilities

reload(sys)
sys.setdefaultencoding('utf8')


def load_template_file(template_file,
                       searchpath="/"):
    """
    Load jinja2 template file. Search path starts from root directory so no
    chroot.

    Parameters
    -------
    template_file: str
        Template file name.
    searchpath: str, default </>
        Root directory for template lookup.

    Returns
    -------
    jinja2.Template

    Examples
    -------
    >>> import jinja2
    >>> lt = load_template_file("./tests/test.jj2", searchpath=".")
    >>> isinstance(lt, jinja2.environment.Template)
    True
    """
    template_Loader = jj2.FileSystemLoader(searchpath=searchpath)
    template_Env = jj2.Environment(loader=template_Loader)
    template = template_Env.get_template(template_file)
    return template


def render_template(template_loaded,
                    template_vars):
    """
    Render jinja2.Template to unicode.

    Parameters
    -------
    loaded_template: jinj2.Template
        Template to render.
    template_vars: dict
        Variables to be rendered with the template.

    Returns
    -------
    unicode
        Template content with passed variables.

    Examples
    -------
    >>> lt = load_template_file("./tests/test.jj2",\
    searchpath=".")
    >>> vars = {"word1": "ipsum", "word2": "adipisicing", "word3": "tempor"}
    >>> rt = render_template(lt, vars)
    >>> isinstance(rt, unicode)
    True
    >>> str(rt)
    'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt.'
    """
    template_rendered = template_loaded.render(template_vars)
    return template_rendered


def save_template(out_file_name,
                  template_rendered):
    """
    Save rendered template to file.

    Parameters
    -------
    out_file_name: str
        Output file name.
    template_rendered: unicode
        Temlplate rendered to unicode object.
    """
    with open(out_file_name, "w") as fout:
        fout.write(template_rendered.encode("utf-8"))


def read_info_shared(input_file_name,
                     min_fold=5,
                     label_col="label",
                     group_col="Group",
                     otu_col="Otu",
                     num_col="numOtus",
                     sep="\t",
                     format_junk_grps=True):
    """
    Extracts information from mothur's shared file.

    Parameters
    -------
    input_file_name: str
        Input file name.
    min_fold: int
        Fraction of mean group size below which groups will be removed before
        analysis.
    label_col: str
        Label column name in shared file.
    group_col: str
        Group column name in shared file.
    otu_col: str
        OTU column name prefix in shared file.
    num_col: str
        Number of OTUs column name in shared file.
    sep: str, default <\t>
        Delimiter to use for reading-in shared file.
    format_junk_grps: bool, default <True>
        Join names of groups to remove by <-> before passing to mothur.

    Returns
    -------
    dict
        Information about label, number of samples and groups to remove.

    Examples
    -------
    >>> shared_info = read_info_shared(input_file_name="./tests/test.shared")
    >>> shared_info["samples_number"]
    9
    >>> float(shared_info["label"])
    0.03
    >>> shared_info["junk_grps"]
    'F3D141-F3D143-F3D144'
    """
    shared_df = pd.read_csv(input_file_name, sep=sep)
    otus_cols = [i for i in shared_df.columns if otu_col in i and i != num_col]
    grps_sizes = shared_df[[group_col] + otus_cols].sum(axis=1)
    label = shared_df[label_col][0]
    grps_num = len(shared_df[group_col])
    sizes_df = pd.DataFrame({"GROUPS": shared_df[group_col],
                             "GROUP_SIZES": grps_sizes})
    threshold = sizes_df.GROUP_SIZES.mean() / min_fold
    size_bool = (sizes_df.GROUP_SIZES < threshold)
    junk_grps = list(sizes_df[size_bool].GROUPS)
    if format_junk_grps is True:
        junk_grps = "-".join(junk_grps)
    out_dict = {"label": label,
                "samples_number": grps_num,
                "junk_grps": junk_grps}
    return out_dict


def parse_html(input_file_name,
               html_type,
               parser="html.parser",
               newline="\n"):
    """
    Extract particular tags from html so that they can be placed in
    another html without iframe.

    Parameters
    -------
    input_file_name: str
        Input file name.

    """
    with open(input_file_name) as fin:
        html = fin.read()
    soup = bs(html, parser)
    if html_type == "krona":
        head = [str(i) for i in soup.head if i != newline]
        body = [str(i) for i in soup.body if i != newline]
        return {"head": {"link": head[1],
                         "script_not_found": head[2],
                         "script_functional": head[3]},
                "body": {"img_hidden": body[0],
                         "img_loading": body[1],
                         "img_logo": body[2],
                         "noscript": body[3],
                         "div_krona": body[4]}}
    elif html_type == "summary":
        tags = [str(i) for i in list(soup.children) if i != "\n"]
        return {"link": tags[0],
                "table": tags[1],
                "googleapis_script": tags[3],
                "datatables_script": tags[4],
                "script": tags[5]}
    elif html_type == "rarefaction" or html_type == "nmds":
        return {"div": str(soup.div),
                "script": str(soup.script)}


def main():
    parser = argparse.ArgumentParser(prog="mothulity",
                                     usage="mothulity [OPTION]",
                                     description="creates headnode-suitable\
                                     mothur script",
                                     version=__version__)
    headnode = parser.add_argument_group("headnode options")
    mothur = parser.add_argument_group("mothur options")
    advanced = parser.add_argument_group("advanced options")
    settings = parser.add_argument_group("configuration settings")
    parser.add_argument(action="store",
                        dest="files_directory",
                        metavar="path/to/files",
                        default=".",
                        help="input directory path. It is used as working\
                        directory for the job. Default CWD.")
    parser.add_argument("-n",
                        "--job-name",
                        action="store",
                        dest="job_name",
                        metavar="",
                        default="mothur.job",
                        help="job name. Used for naming scripts, queued job\
                        and html output. Default <mothur.job>.")
    parser.add_argument("-d",
                        "--output-dir",
                        action="store",
                        dest="output_dir",
                        metavar=".",
                        default=".",
                        help="output directory path for script. It is NOT\
                        output directory for actual job.")
    parser.add_argument("-r",
                        "--run",
                        action="store",
                        dest="run",
                        metavar="",
                        default=None,
                        help="shell call. Use if you want to run the mothur\
                        script immediately, in current directory. eg -r sh for\
                         regular bash or -r sbatch for slurm.")
    parser.add_argument("-a",
                        "--analysis-only",
                        action="store_true",
                        dest="analysis_only",
                        default=False,
                        help="outputs just the part involved in statistical\
                        analysis and drawing.")
    parser.add_argument("--render-html",
                        action="store_true",
                        dest="render_html",
                        default=False,
                        help="path/to/html-template-file. Use to pass args into\
                        fancy html.")
    parser.add_argument("--notify-email",
                        action="store",
                        dest="notify_email",
                        metavar="",
                        default=None,
                        help="email address you want to notify when job is\
                        done.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        default=False,
                        help="prevents mothur script execution. Default\
                        <False>")
    headnode.add_argument("--partition",
                          action="store",
                          dest="partition",
                          metavar="",
                          default="long",
                          help="headnode's partition. Values: test, short, big,\
                          long, accel. Accel necessary for phi/gpu nodes\
                          Default <long>.")
    headnode.add_argument("--nodes",
                          action="store",
                          dest="nodes",
                          metavar="",
                          default=1,
                          help="number of nodes. Default: <1>.")
    headnode.add_argument("--ntasks-per-node",
                          action="store",
                          dest="ntasks_per_node",
                          metavar="",
                          default=6,
                          help="number of tasks to invoke on each node.\
                          Default <6>")
    headnode.add_argument("--node-list",
                          action="store",
                          dest="node_list",
                          metavar="",
                          default=None,
                          help="request a specific list of nodes")
    headnode.add_argument("--processors",
                          action="store",
                          dest="processors",
                          metavar="",
                          default=1,
                          help="number of logical processors. Default: <24>")
    headnode.add_argument("--resources",
                          action="store",
                          dest="resources",
                          metavar="",
                          default=None,
                          help="shortcut for headnode's resources reservation.\
                          Accepted values are: si<N>gle for single n node.\
                          <S>mall, <M>edium, <L>arge, <XL>arge for regular\
                          nodes with MPI. <PHI> for single phi node, <JUMBO>\
                          for two phi nodes. Overrides all the other headnode\
                          arguments. WARNING! Options for MPI require\
                          MPI-enabled version of mothur which is NOT included\
                          with mothulity and must be compiled by the user and\
                          callable system-wide.")
    mothur.add_argument("--max-ambig",
                        action="store",
                        dest="max_ambig",
                        metavar="",
                        default=0,
                        help="maximum number of ambiguous bases allowed.\
                        screen.seqs param. Default <0>.")
    mothur.add_argument("--max-homop",
                        action="store",
                        dest="max_homop",
                        metavar="",
                        default=8,
                        help="maximum number of homopolymers allowed.\
                        screen.seqs param. Default <8>.")
    mothur.add_argument("--min-length",
                        action="store",
                        dest="min_length",
                        metavar="",
                        default=None,
                        help="minimum length of read allowed.\
                        screen.seqs param. Default <400>.")
    mothur.add_argument("--max-length",
                        action="store",
                        dest="max_length",
                        metavar="",
                        default=None,
                        help="minimum length of read allowed.\
                        screen.seqs param. Default <500>.")
    mothur.add_argument("--min-overlap",
                        action="store",
                        dest="min_overlap",
                        metavar="",
                        default=25,
                        help="minimum number of bases overlap in contig.\
                        screen.seqs param. Default <25>.")
    mothur.add_argument("--screen-criteria",
                        action="store",
                        dest="screen_criteria",
                        metavar="",
                        default=95,
                        help="trim start and end of read to fit this\
                        percentage of all reads.\
                        screen.seqs param. Default <95>.")
    mothur.add_argument("--chop-length",
                        action="store",
                        dest="chop_length",
                        metavar="",
                        default=250,
                        help="cut all the reads to this length. Keeps front\
                        of the sequences. chop.seqs argument.\
                        Default <250>")
    mothur.add_argument("--precluster-diffs",
                        action="store",
                        dest="precluster_diffs",
                        metavar="",
                        default=2,
                        help="number of differences between reads treated as\
                        insignificant. screen.seqs param. Default <2>.")
    mothur.add_argument("--chimera-dereplicate",
                        action="store",
                        dest="chimera_dereplicate",
                        metavar="",
                        default="T",
                        help="checking for chimeras by group. chimera.uchime\
                        param. Default <T>.")
    mothur.add_argument("--classify-seqs-cutoff",
                        action="store",
                        dest="classify_seqs_cutoff",
                        metavar="",
                        default=80,
                        help="bootstrap value for taxonomic assignment.\
                        classify.seqs param. Default <80>.")
    mothur.add_argument("--classify-ITS",
                        action="store_true",
                        dest="classify_ITS",
                        default=False,
                        help="removes align.seqs step and modifies\
                        classify.seqs with <method=knn>,\
                                           <search=blast>,\
                                           <match=2>,\
                                           <mismatch=-2>,\
                                           <gapopen=-2>,\
                                           <gapextend=-1>,\
                                           <numwanted=1>).\
                        Default <False>")
    mothur.add_argument("--align-database",
                        action="store",
                        dest="align_database",
                        metavar="",
                        default=None,
                        help="path/to/align-database. Used by align.seqs\
                        command as <reference> argument. Default\
                        <~/db/Silva.nr_v119/silva.nr_v119.align>.")
    mothur.add_argument("--taxonomy-database",
                        action="store",
                        dest="taxonomy_database",
                        metavar="",
                        default=None,
                        help="path/to/taxonomy-database. Used by\
                        classify.seqs as <taxonomy> argument.\
                        Default <~/db/Silva.nr_v119/silva.nr_v119.tax>")
    mothur.add_argument("--cluster-cutoff",
                        action="store",
                        dest="cluster_cutoff",
                        metavar="",
                        default=0.03,
                        help="cutoff value. Smaller == faster cluster param.\
                        Default <0.03>.")
    mothur.add_argument("--cluster-method",
                        action="store",
                        dest="cluster_method",
                        metavar="",
                        default="agc",
                        help="Clustering method. Available options are:\
                        opticlust <opti>,\
                        average neighbor <average>,\
                        furthest neighbor <furthest>,\
                        nearest neighbor <nearest>,\
                        Vsearch agc <agc>,\
                        Vsearch dgc <dgc>.\
                        For detailed info visit\
                        https://www.mothur.org/wiki/Cluster.split Default <agc>")
    mothur.add_argument("--full-ram-load",
                        action="store_true",
                        dest="full_ram_load",
                        default=False,
                        help="Use if you want to use cluster command instead\
                        of cluster.split.")
    mothur.add_argument("--label",
                        action="store",
                        dest="label",
                        metavar="",
                        default=0.03,
                        help="label argument for number of commands for OTU\
                        analysis approach. Default 0.03.")
    mothur.add_argument("--keep-all",
                        action="store_true",
                        dest="keep_all",
                        default=False,
                        help="Keep all groups, even if they can distort\
                        analysis due to small size during subsampling.")
    advanced.add_argument("--exclude-krona",
                          action="store_true",
                          dest="exclude_krona",
                          default=False,
                          help="Do not include krona pie chart into final html.\
                          Krona can be included only as an iframe.")
    settings.add_argument("--set-align-database-path",
                          action="store",
                          dest="set_align_database_path",
                          metavar="",
                          default=None,
                          help="Set persistent path to align database.")
    settings.add_argument("--set-taxonomy-database-path",
                          action="store",
                          dest="set_taxonomy_database_path",
                          metavar="",
                          default=None,
                          help="Set persistent path to taxonomy database.")
    args = parser.parse_args()
# Define variables that can overridden by CLI, config or other function and should cause exit if None in a proper place in the decision tree.
    align_database_abs = None
    taxonomy_database_abs = None
    junk_grps = 0
    sampl_num = None
    krona_html = None
    sum_html = None
    raref_html = None
    nmds_jc_html = None
    nmds_th_html = None
# Read-in config file.
    config_path_abs = get_dir_path("mothulity.config")
    config = ConfigParser.SafeConfigParser()
    config.read(config_path_abs)
# Set config file options.
    if any([args.set_align_database_path,
            args.set_taxonomy_database_path]):
        if args.set_align_database_path:
            utilities.set_config(filename=config_path_abs,
                                 section="databases",
                                 options=["align"],
                                 values=[args.set_align_database_path])
        if args.set_taxonomy_database_path:
            utilities.set_config(filename=config_path_abs,
                                 section="databases",
                                 options=["taxonomy"],
                                 values=[args.set_taxonomy_database_path])
        exit()
# Read options from config file.
# If config file is the only source of the variable content and it is not found - quit from here.
    try:
        preproc_template = config.get("templates", "preproc")
        analysis_template = config.get("templates", "analysis")
        output_template = config.get("templates", "output")
    except Exception as e:
        print "Templates not found in config file! Quitting..."
        time.sleep(2)
        exit()
    try:
        align_database_abs = config.get("databases", "align")
    except Exception as e:
        print "Align database path not found in config file."
        time.sleep(2)
    try:
        taxonomy_database_abs = config.get("databases", "taxonomy")
    except Exception as e:
        print "Taxonomy database path not found in config file."
        time.sleep(2)
    try:
        datatables_css = config.get("css", "datatables")
        w3_css = config.get("css", "w3")
    except Exception as e:
        print "CSS links not found in config file! Output will not display properly!"
        time.sleep(2)
    try:
        datatables_js = get_dir_path(config.get("js", "datatables"))
        slideshow_js = get_dir_path(config.get("js", "slideshow"))
    except Exception as e:
        print "Javascript links not found in config file. Output will not display properly!"
        time.sleep(2)
# Override databases paths from config file with CLI args if specified.
    if args.align_database:
        align_database_abs = os.path.abspath(os.path.expanduser(args.align_database))
    if args.taxonomy_database:
        taxonomy_database_abs = os.path.abspath(os.path.expanduser(args.taxonomy_database))
# Override or not headnode options with args.resources.
    if args.resources is not None:
        node_list = None
        resources = args.resources.upper()
        partition = config.get(resources, "partition")
        nodes = int(config.get(resources, "nodes"))
        ntasks_per_node = int(config.get(resources, "ntasks_per_node"))
        processors = int(config.get(resources, "processors"))
    else:
        nodes = args.nodes
        node_list = args.node_list
        ntasks_per_node = args.ntasks_per_node
        processors = args.processors
        partition = args.partition
# Make sure essential variables that can be overriden by CLI are defined.
# Unless args.analysis_only or args.render_html are True - quit from here.
    if not args.analysis_only and not args.render_html:
        if not align_database_abs:
            print "No align database path defined in config nor command-line. Quitting..."
            exit()
        if not taxonomy_database_abs:
            print "No taxonomy database path defined in config nor command-line. Quitting..."
            exit()
# Validate if input and output directories exist and make them absolute paths.
    if os.path.exists(args.files_directory):
        files_directory_abs = "{}/".format(os.path.abspath(args.files_directory))
    else:
        print "Input directory not found. Quitting..."
        exit()
    if os.path.exists(args.output_dir):
        output_dir_abs = "{}/".format(os.path.abspath(args.output_dir))
    else:
        print "Output directory not found. Quitting..."
        exit()
# Read file globs from specified directories.
    shared_files_list = glob.glob("{}{}".format(files_directory_abs,
                                                config.get("file_globs",
                                                           "shared")))
    tax_sum_files_list = glob.glob("{}{}".format(files_directory_abs,
                                                 config.get("file_globs",
                                                            "tax_sum")))
    design_files_list = glob.glob("{}{}".format(files_directory_abs,
                                                config.get("file_globs",
                                                           "design")))
# Make decision what to do based on file globs.
    if len(shared_files_list) > 1:
        if args.render_html is True:
            pass
        else:
            print "More than 1 shared files found. Quitting..."
            time.sleep(2)
            exit()
    elif len(shared_files_list) == 1:
        shared_file = shared_files_list[0]
        print "Found {} shared file".format(shared_file)
        if len(tax_sum_files_list) != 1:
            print "WARNING!!! No proper tax.summary file found. The analysis will be incomplete."
            time.sleep(2)
            tax_sum_file = None
        else:
            tax_sum_file = tax_sum_files_list[0]
            print "Found {} tax.summary file".format(tax_sum_file)
        if len(design_files_list) != 0:
            if len(design_files_list) > 1:
                print "More than 1 design files found. Will skip this part of analysis."
                time.sleep(2)
                design_file = None
            else:
                design_file = design_files_list[0]
        else:
            design_file = None
        if any([args.analysis_only, args.render_html]) is True:
            shared_info = read_info_shared(shared_file)
            print "Found {} shared file".format(shared_file)
            time.sleep(2)
        elif any([args.analysis_only, args.render_html]) is False:
            print "Found shared file but you do not want to run the analysis on it. Running preprocessing would overwrite it. Quitting..."
            time.sleep(2)
            exit()
    elif len(shared_files_list) == 0:
        if any([args.analysis_only, args.render_html]) is True:
            print "No shared file found. Quitting..."
            time.sleep(2)
            exit()
        else:
            if os.path.isfile(align_database_abs) is False:
                print "No align database found in {}. Quitting...".format(args.align_database)
                time.sleep(2)
                exit()
            if os.path.isfile(taxonomy_database_abs) is False:
                print "No align database found in {}. Quitting...".format(args.taxonomy_database)
                time.sleep(2)
                exit()
            shared_file = None
            tax_sum_file = None
            design_file = None
    else:
        "I don't know what you what me to do!!! There are no files I can recognize in here!"
        time.sleep(2)
        exit()
# Get current time and create logfile.
    run_time_sig = "{}{}{}{}{}{}".format(time.localtime().tm_year,
                                         time.localtime().tm_mon,
                                         time.localtime().tm_mday,
                                         time.localtime().tm_hour,
                                         time.localtime().tm_min,
                                         time.localtime().tm_sec)
    logfile_name = "{}.{}.{}".format(files_directory_abs,
                                     args.job_name,
                                     run_time_sig)

    with open(logfile_name, "a") as fin:
        fin.write("{} was called with these arguments:\n\n".format(sys.argv[0]))
        for k, v in vars(args).iteritems():
            if v is not None:
                fin.write("--{}: {}\n".format(k, v))
# Load preproc_template if args.analysis_only and args.render_html are False.
# Label must be from args.label.
# Rest of the variables must explicitly set to None or zero.
    if all([args.analysis_only, args.render_html]) is False:
        loaded_template = load_template_file(preproc_template,
                                             searchpath=get_dir_path())
        label = args.label
        with open(logfile_name, "a") as fin:
            fin.write("\nTemplate used:\n\n{}".format(loaded_template))
# Load analysis_template if args.analysis_only is True.
# Label, number of samples and junk groups must be read from shared file.
    if args.analysis_only is True:
        loaded_template = load_template_file(analysis_template,
                                             searchpath=get_dir_path())
        sampl_num = shared_info["samples_number"]
        label = shared_info["label"]
        junk_grps = shared_info["junk_grps"]
        print "Detected {} groups with {} label".format(sampl_num, label)
        time.sleep(2)
        if len(junk_grps) > 0:
            print "{} can distort the analysis due to size too small".format(junk_grps)
            time.sleep(2)
            if args.keep_all is True:
                print "All groups will be kept due to --keep-all argument"
                time.sleep(2)
                junk_grps = 0
            else:
                print "{} will be removed".format(junk_grps)
                time.sleep(2)
        with open(logfile_name, "a") as fin:
            fin.write("\nTemplate used:\n\n{}".format(loaded_template))
# Load output_template if args.render_html is True.
# All non-output-html variables must be read from shared file.
# Output-html varialbles must explicitly set.
    if args.render_html is True:
        loaded_template = load_template_file(output_template,
                                             searchpath=get_dir_path())
        label = shared_info["label"]
        junk_grps = shared_info["junk_grps"]
        sampl_num = shared_info["samples_number"]
        krona_html = parse_html("alpha/{}.krona.html".format(args.job_name),
                                html_type="krona")
        sum_html = parse_html("alpha/{}.sum.html".format(args.job_name),
                              html_type="summary")
        raref_html = parse_html("alpha/{}.raref.html".format(args.job_name),
                                html_type="rarefaction")
        nmds_jc_html = parse_html("beta/{}.jclass.nmds.html".format(args.job_name),
                                  html_type="nmds")
        nmds_th_html = parse_html("beta/{}.thetayc.nmds.html".format(args.job_name),
                                  html_type="nmds")
        with open(logfile_name, "a") as fin:
            fin.write("\nTemplate used:\n\n{}".format(loaded_template))
# Pass all the variables to template and render to str.
    template_vars = {"files_directory": files_directory_abs,
                     "output_dir": output_dir_abs,
                     "job_name": args.job_name,
                     "run": args.run,
                     "partition": partition,
                     "nodes": nodes,
                     "ntasks_per_node": ntasks_per_node,
                     "node_list": node_list,
                     "processors": processors,
                     "max_ambig": args.max_ambig,
                     "max_homop": args.max_homop,
                     "min_length": args.min_length,
                     "max_length": args.max_length,
                     "min_overlap": args.min_overlap,
                     "screen_criteria": args.screen_criteria,
                     "chop_length": args.chop_length,
                     "precluster_diffs": args.precluster_diffs,
                     "chimera_dereplicate": args.chimera_dereplicate,
                     "classify_seqs_cutoff": args.classify_seqs_cutoff,
                     "classify_ITS": args.classify_ITS,
                     "align_database": align_database_abs,
                     "taxonomy_database": taxonomy_database_abs,
                     "design_file": design_file,
                     "cluster_cutoff": args.cluster_cutoff,
                     "cluster_method": args.cluster_method,
                     "full_ram_load": args.full_ram_load,
                     "label": label,
                     "junk_grps": junk_grps,
                     "notify_email": args.notify_email,
                     "sampl_num": sampl_num,
                     "shared_file": shared_file,
                     "tax_sum_file": tax_sum_file,
                     "w3_css": w3_css,
                     "datatables_css": datatables_css,
                     "datatables_js": datatables_js,
                     "slideshow_js": slideshow_js,
                     "krona_html": krona_html,
                     "sum_html": sum_html,
                     "raref_html": raref_html,
                     "nmds_jc_html": nmds_jc_html,
                     "nmds_th_html": nmds_th_html,
                     "exclude_krona": args.exclude_krona}
    rendered_template = render_template(loaded_template,
                                        template_vars)
# Save template as bash script of HTML file depending on args.render_html value.
    if args.render_html is True:
        save_template("{}.html".format(args.job_name), rendered_template)
    else:
        save_template("{}{}.sh".format(output_dir_abs, args.job_name),
                      rendered_template)
# Run outputted script or not depending on args.run and args.dry-run
    if args.run is not None and args.dry_run is not True:
        os.system("{} {}".format(args.run, "{}{}.sh".format(output_dir_abs,
                                                            args.job_name)))


if __name__ == "__main__":
    main()
