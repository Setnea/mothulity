#!/usr/bin/env python


from __init__ import __author__, __version__
import os
import argparse
import requests as rq
from tqdm import tqdm


def get_db(url,
           save_path,
           chunk=8192):
    """
    Download from url to file. Handles different chunk sizes saving RAM. Shows
    progress with tqdm progress bar.

    Parameters
    -------
    url: str
        URL to download from.
    save_path: str
        Local URL to save to.
    chunk: int, default 8192
        Size of chunk the stream is divided to. Smaller it is less memory it
        uses.

    Examples
    -------
    >>> import os
    >>> get_db("http://google.com", "./tests/google.html")
    >>> os.path.getsize("./tests/google.html") > 0
    True
    """
    res = rq.get(url, stream=True)
    total_len = int(res.headers.get("content-length"))
    if res.status_code == 200:
        with open(save_path, "wb") as fout:
            for i in tqdm(res.iter_content(chunk_size=chunk),
                          total=total_len / chunk):
                fout.write(i)
    else:
        print "Status code {0}".format(status_code)


def main():
    parser = argparse.ArgumentParser(prog="mothulity_dbaser",
                                     usage="mothulity_dbaser [OPTION]",
                                     description="downloads mothur-suitable\
                                     databases",
                                     version="0.9.4")
    parser.add_argument("--unite-ITS-02",
                        action="store",
                        dest="unite_ITS_02",
                        metavar="",
                        default=None,
                        help="path/to/download-parser. Use if you want to\
                        download UNITE ITS 02 parser.")
    parser.add_argument("--unite-ITS-s-02",
                        action="store",
                        dest="unite_ITS_s_02",
                        metavar="",
                        default=None,
                        help="path/to/download-parser. Use if you want to\
                        download UNITE ITS s 02 parser.")
    parser.add_argument("--silva-102",
                        action="store",
                        dest="silva_102",
                        metavar="",
                        default=None,
                        help="path/to/download-parser. Use if you want to\
                        download Silva v102.")
    parser.add_argument("--silva-119",
                        action="store",
                        dest="silva_119",
                        metavar="",
                        default=None,
                        help="path/to/download-parser. Use if you want to\
                        download Silva v119.")
    parser.add_argument("--silva-123",
                        action="store",
                        dest="silva_123",
                        metavar="",
                        default=None,
                        help="path/to/download-parser. Use if you want to\
                        download Silva v123.")
    args = parser.parse_args()

    if args.unite_ITS_02 is not None:
        download_path = "{0}/Unite_ITS_02.zip".format(args.unite_ITS_02)
        print "Downloading to {0}".format(download_path)
        get_db("https://www.mothur.org/w/images/4/49/Unite_ITS_02.zip",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.system("unzip {0} -d {1}".format(download_path,
                                            args.unite_ITS_02))
        os.system("rm {0}".format(download_path))
        print "Unpacking done!"

    if args.unite_ITS_s_02 is not None:
        download_path = "{0}/Unite_ITS_s_02.zip".format(args.unite_ITS_s_02)
        print "Downloading to {0}/Unite_ITS_s_02.zip".format(args.unite_ITS_s_02)
        get_db("https://www.mothur.org/w/images/2/27/Unite_ITS_s_02.zip",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.system("unzip {0} -d {1}".format(download_path,
                                            args.unite_ITS_s_02))
        os.system("rm {0}".format(download_path))

    if args.silva_102 is not None:
        download_path = "{0}/Silva.bacteria.zip".format(args.silva_102)
        print "Downloading to {0}/Silva.bacteria.zip".format(args.silva_102)
        get_db("https://www.mothur.org/w/images/9/98/Silva.bacteria.zip",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.system("unzip {0} -d {1}".format(download_path,
                                            args.silva_102))
        os.system("rm {0}".format(download_path))
        print "Unpacking done!"
        download_path = "{0}/Silva.archaea.zip".format(args.silva_102)
        print "Downloading to {0}/Silva.archaea.zip".format(args.silva_102)
        get_db("https://www.mothur.org/w/images/3/3c/Silva.archaea.zip",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.system("unzip {0} -d {1}".format(download_path,
                                            args.silva_102))
        os.system("rm {0}".format(download_path))
        print "Unpacking done!"
        download_path = "{0}/Silva.eukarya.zip".format(args.silva_102)
        print "Downloading to {0}/Silva.eukarya.zip".format(args.silva_102)
        get_db("https://www.mothur.org/w/images/1/1a/Silva.eukarya.zip",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.system("unzip {0} -d {1}".format(download_path,
                                            args.silva_102))
        os.system("rm {0}".format(download_path))
        print "Unpacking done!"

    if args.silva_119 is not None:
        download_path = "{0}/Silva.nr_v119.tgz".format(args.silva_119)
        print "Downloading to {0}/Silva.nr_v119.tgz".format(args.silva_119)
        get_db("http://www.mothur.org/w/images/2/27/Silva.nr_v119.tgz",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.mkdir("{0}/Silva.nr_v119".format(args.silva_119))
        os.system("tar -xf {0} --directory {1}".format(download_path,
                                                       "{0}/Silva.nr_v119".format(args.silva_119)))
        os.system("rm {0}".format(download_path))
        print "Unpacking done!"

    if args.silva_123 is not None:
        download_path = "{0}/Silva.nr_v123.tgz".format(args.silva_123)
        print "Downloading to {0}/Silva.nr_v123.tgz".format(args.silva_123)
        get_db("https://www.mothur.org/w/images/b/be/Silva.nr_v123.tgz",
               download_path)
        print "Downloading done!"
        print "Unpacking..."
        os.mkdir("{0}/Silva.nr_v123".format(args.silva_123))
        os.system("tar -xf {0} --directory {1}".format(download_path,
                                                       "{0}/Silva.nr_v123".format(args.silva_123)))
        os.system("rm {0}".format(download_path))
        print "Unpacking done!"


if __name__ == '__main__':
    main()
